# 7.5.4 条件分支、循环、并行

> 掌握工作流中的三种控制流：条件分支（If-Else）、循环（Iteration）、并行执行。

## 🎯 学习目标

完成本文档后，你将能够：
- 实现条件分支节点（If-Else）
- 实现循环节点（Iteration）
- 理解并行的实现方式（async + 线程池）
- 看懂 dify 中控制流节点的实现

## 📚 前置知识

- [Workflow Engine](./28-workflow-engine.md)
- [Workflow Nodes](./29-workflow-nodes.md)
- Python asyncio（详见 [async/asyncio](../01-fundamentals/14-async-asyncio.md)）

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

## 3. 关键要点总结

- 控制流三类：条件分支、循环、并行
- If-Else 用变量比较选分支
- Iteration 对列表逐项执行子图
- 并行通过 DAG 拓扑分析自动识别
- 用 asyncio.gather 实现并发

---

**文档版本**：v1.0
**最后更新**：2026-07-13
