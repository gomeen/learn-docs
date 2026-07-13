# 7.5.4 条件分支、循环、并行

> 掌握工作流中的三种控制流：条件分支（If-Else）、循环（Iteration）、并行执行。

## 🎯 学习目标

完成本文档后，你将能够：
- 实现条件分支节点（If-Else）
- 实现循环节点（Iteration）
- 理解并行的实现方式（async + 线程池）
- 看懂 dify 中控制流节点的实现

## 📚 前置知识

- 07-rag-and-agent/24-workflow-engine.md
- 07-rag-and-agent/25-workflow-nodes.md
- Python asyncio 基础

## 1. 核心概念

### 1.1 三种控制流

| 控制流 | 节点类型 | 用途 |
|--------|----------|------|
| **条件分支** | If-Else | 根据条件选不同路径 |
| **循环** | Iteration | 遍历列表，对每个元素执行子流程 |
| **并行** | 并行执行块 | 多节点同时执行 |

### 1.2 If-Else 实现思路

```
条件表达式：{{ llm_1.response | length > 10 }}
  → True  → 走 true 分支
  → False → 走 false 分支
```

### 1.3 Iteration 实现思路

```
输入：list（如 10 个文档）
对每个元素：
  执行子流程
  收集结果
输出：list of results
```

### 1.4 并行执行

dify 用 `asyncio` 实现节点并行：
- 找出所有"ready"节点（依赖已满足）
- `asyncio.gather(*[run_node(n) for n in ready_nodes])`

## 2. 代码示例

### 2.1 简单 If-Else 节点

```python
class IfElseNode:
    """条件分支节点"""

    def __init__(self, config: dict):
        self.conditions = config["conditions"]
        self.true_branch = config["true_branch_id"]
        self.false_branch = config.get("false_branch_id")

    def evaluate(self, variables: dict) -> str:
        """评估条件，返回下一个节点 ID"""
        for cond in self.conditions:
            left = self._get_value(cond["variable_selector"], variables)
            right = cond["value"]
            op = cond["comparison_operator"]

            if self._compare(left, op, right):
                return self.true_branch
        return self.false_branch

    def _compare(self, left, op, right) -> bool:
        if op == "is": return left == right
        if op == "is not": return left != right
        if op == "contains": return right in left
        if op == ">": return left > right
        if op == "<": return left < right
        return False

    def _get_value(self, selector, variables):
        """从 variables dict 中按 selector 取值"""
        cur = variables
        for key in selector:
            cur = cur[key]
        return cur
```

### 2.2 Iteration 节点

```python
class IterationNode:
    """循环节点：遍历列表"""

    def __init__(self, config: dict, sub_workflow):
        self.input_selector = config["input_selector"]  # 列表变量
        self.sub_workflow = sub_workflow
        self.output_var = config["output_var"]

    def run(self, variables: dict) -> dict:
        items = self._get_value(self.input_selector, variables)
        results = []
        for i, item in enumerate(items):
            # 子流程可以用 item 作为输入
            sub_input = {"item": item, "index": i}
            result = self.sub_workflow.run(sub_input, variables)
            results.append(result)
        return {self.output_var: results}
```

### 2.3 并行执行

```python
import asyncio
from typing import Coroutine, Any


class ParallelExecutor:
    """并发执行多个独立的节点"""

    async def execute_nodes(self, nodes: list, pool: VariablePool) -> list[Any]:
        # 找出所有 ready 的节点（互不依赖）
        ready = [n for n in nodes if n.is_ready(pool)]

        # 并发执行
        results = await asyncio.gather(*[
            self._run_node(n, pool) for n in ready
        ])
        return results

    async def _run_node(self, node, pool):
        # 同步节点用 run_in_executor 包装
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, node.run, pool)
```

### 2.4 常见错误：循环无终止条件

```python
# ❌ 错误：while True 循环
while True:
    process(item)

# ✅ 正确：限制最大迭代次数 + 明确的终止条件
max_iter = 100
for i in range(max_iter):
    if should_stop(variables):
        break
    process(item, i)
```

## 3. dify 仓库源码解读

### 3.1 Iteration 节点示例

dify 的 Iteration 节点在 graphon 库中（dify 的核心依赖），结构示意：

```python
class IterationNode(BaseNode):
    """Iteration 节点（位于 graphon 库）"""

    node_type = BuiltinNodeTypes.ITERATION

    def _run(self) -> Generator[NodeEventBase, None, None]:
        # 1. 读取输入列表
        input_list = self._get_input_list()

        # 2. 对每个元素执行子图
        results = []
        for index, item in enumerate(input_list):
            # 把 item 注入到子图的变量池
            child_state = self._build_child_state(item, index)
            child_result = self._run_subgraph(child_state)
            results.append(child_result)
            yield IterationItemEvent(index=index, result=child_result)

        # 3. 输出结果列表
        yield NodeRunResult(outputs={"result": results})
```

**解读**：
- 每次迭代都会构建一个子图状态
- 子图执行结果被收集到 results 列表
- 通过 `Generator` 流式返回每个迭代项的事件（前端可实时展示进度）

### 3.2 拓扑中并行能力的体现

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`
**核心代码**（节选）：

```python
def is_upstream(self, *, source_node_id: str, target_node_id: str) -> bool:
    """判断 source 是否在 target 的上游

    在 DAG 中：source 是 target 的前驱 → 不能并行
                source 与 target 互不依赖 → 可以并行
    """
    if source_node_id == target_node_id:
        return False
    visited: set[str] = set()
    queue: deque[str] = deque(self._incoming.get(target_node_id, ()))
    while queue:
        candidate = queue.popleft()
        if candidate == source_node_id:
            return True
        if candidate in visited:
            continue
        visited.add(candidate)
```

**解读**：
- 引擎通过 `is_upstream` 判断两个节点是否可以并行
- 不在同一条上下游链上的节点 → 可以并行执行
- dify 利用这一点自动并行独立节点

### 3.3 节点工厂中的节点注册

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/node_factory.py`（节选）
**核心代码**：

```python
def resolve_workflow_node_class(node_type: str) -> type[Node]:
    """根据 node_type 返回对应的节点类"""
    # 优先查找 dify 自定义节点
    if node_type in DIFY_CUSTOM_NODE_TYPES:
        return DIFY_CUSTOM_NODE_TYPES[node_type]
    # 否则用 graphon 内置节点
    return BuiltinNodeTypes[node_type].get_node_class()
```

**解读**：
- dify 区分两类节点：自定义（知识检索、Agent）和内置（graphon 提供）
- 自定义节点在 dify 仓库维护，内置节点在 graphon 库

## 4. 关键要点总结

- 控制流三类：条件分支、循环、并行
- If-Else 用变量比较选分支
- Iteration 对列表逐项执行子图
- 并行通过 DAG 拓扑分析自动识别
- 用 asyncio.gather 实现并发

## 5. 练习题

### 练习 1：基础（必做）

实现一个 IfElseNode，支持 is / > / < / contains 四种比较操作符。

### 练习 2：进阶

实现一个 IterationNode，对一个字符串列表（5 个），每个字符串调一次"长度计算子流程"，返回所有长度的列表。

### 练习 3：挑战（选做）

实现一个并行执行器：给定一个 DAG，找出所有 ready 节点，asyncio.gather 并发执行。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/`
- `/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`
- `/Users/xu/code/github/dify/api/core/workflow/node_factory.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13