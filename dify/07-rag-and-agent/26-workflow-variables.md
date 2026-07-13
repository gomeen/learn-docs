# 7.5.3 变量系统：全局 / 会话 / 节点变量

> 理解 dify 工作流的变量系统：节点的"血液"，在节点之间传递数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分三类变量：系统变量 / 会话变量 / 节点变量
- 理解 VariablePool 的数据结构
- 用变量选择器引用变量
- 看懂 dify 中变量系统的实现

## 📚 前置知识

- 07-rag-and-agent/24-workflow-engine.md
- 07-rag-and-agent/25-workflow-nodes.md

## 1. 核心概念

### 1.1 三类变量

| 类型 | 作用域 | 来源 | 示例 |
|------|--------|------|------|
| **系统变量** | 整个工作流 | 引擎自动注入 | `query`、`conversation_id`、`timestamp` |
| **会话变量** | 跨节点共享 | 用户在节点中写入 | 用户偏好、上文信息 |
| **节点变量** | 单节点输出 | 节点 `_run` 返回 | LLM 输出、工具结果 |

### 1.2 VariablePool 数据结构

```python
class VariablePool:
    """所有变量的中央存储"""

    def __init__(self):
        self._variables: dict[str, Variable] = {}  # selector -> Variable

    def set(self, selector: list[str], value: Any):
        """写入变量（selector 是路径，如 ['node1', 'output']）"""
        self._variables[tuple(selector)] = Variable(value=value)

    def get(self, selector: list[str]) -> Any | None:
        """读取变量"""
        return self._variables.get(tuple(selector))

    def get_by_prefix(self, prefix: str) -> dict:
        """获取某个前缀的所有变量"""
        ...
```

### 1.3 变量选择器（Variable Selector）

变量在 VariablePool 中通过 selector（路径数组）寻址：

```
selector = ["node_id_1", "output_var_name"]
```

前端展示为：`node_id_1.output_var_name`

## 2. 代码示例

### 2.1 手写一个 VariablePool

```python
from typing import Any
from collections import defaultdict


class VariablePool:
    def __init__(self):
        # 用 tuple 作为 key（list 不可哈希）
        self._pool: dict[tuple, Any] = {}

    def set(self, selector: list[str], value: Any) -> None:
        self._pool[tuple(selector)] = value

    def get(self, selector: list[str]) -> Any | None:
        return self._pool.get(tuple(selector))

    def exists(self, selector: list[str]) -> bool:
        return tuple(selector) in self._pool


# 使用
pool = VariablePool()
pool.set(["start", "query"], "你好")
pool.set(["llm_1", "response"], "你好，有什么可以帮您？")
pool.set(["tool_1", "result"], {"temperature": 25})

print(pool.get(["start", "query"]))  # "你好"
print(pool.get(["llm_1", "response"]))  # "你好，有什么可以帮您？"
```

### 2.2 节点读写 VariablePool

```python
class LLMNode:
    """LLM 节点：从 pool 读 prompt 模板，写 response 到 pool"""

    def __init__(self, node_id: str, config: dict, pool: VariablePool):
        self.node_id = node_id
        self.config = config
        self.pool = pool

    def run(self):
        # 读：上游节点的输出作为 prompt 输入
        query = self.pool.get(self.config["query_selector"])
        prompt = f"用户问题：{query}"

        # 调用 LLM（mock）
        response = f"对「{query}」的回答"

        # 写：把结果写入 pool，下游节点可以读
        self.pool.set([self.node_id, "response"], response)
        return response


# 测试
pool = VariablePool()
pool.set(["start", "query"], "什么是 RAG？")

node = LLMNode(node_id="llm_1", config={"query_selector": ["start", "query"]}, pool=pool)
node.run()

print(pool.get(["llm_1", "response"]))  # "对「什么是 RAG？」的回答"
```

### 2.3 Conversation 变量（跨轮次）

```python
class ConversationVariables:
    """会话级变量：跨多轮对话保持"""

    def __init__(self):
        self.vars: dict[str, Any] = {}

    def set(self, key: str, value: Any):
        self.vars[key] = value

    def get(self, key: str, default=None):
        return self.vars.get(key, default)


# Chatflow 场景：第一轮保存用户偏好，后续轮次读取
conv = ConversationVariables()
conv.set("user_language", "zh")

# 第二轮：读上次保存的偏好
language = conv.get("user_language", "en")
print(f"使用语言：{language}")  # zh
```

### 2.4 常见错误：selector 路径错误

```python
# ❌ 错误：selector 拼写错误，get 返回 None
pool.set(["llm_1", "response"], "answer")
print(pool.get(["llm_1", "respnse"]))  # None

# ✅ 正确：用配置统一管理 selector，避免硬编码
class LLMNode:
    def __init__(self, config):
        self.input_selector = config["input_selector"]
        self.output_key = config["output_key"]

    def run(self, pool):
        value = pool.get(self.input_selector)
        # ...
        pool.set([self.node_id, self.output_key], value)
```

## 3. dify 仓库源码解读

### 3.1 VariablePool 注入器

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/variable_pool_initializer.py`
**核心代码**：

```python
def add_node_inputs_to_pool(
    variable_pool: VariablePool,
    node_id: str,
    inputs: dict[str, Any],
) -> None:
    """把节点的输入写入 variable pool"""
    for var_name, value in inputs.items():
        variable_pool.add([node_id, var_name], value)


def add_variables_to_pool(
    variable_pool: VariablePool,
    variables: Mapping[str, Any],
    prefix: str | None = None,
) -> None:
    """批量写入变量"""
    selector_prefix = [prefix] if prefix else []
    for var_name, value in variables.items():
        variable_pool.add(selector_prefix + [var_name], value)
```

**解读**：
- `add_node_inputs_to_pool` 把节点输入写入 pool（按 `node_id/var_name` 路径）
- `add_variables_to_pool` 批量写入（用于会话变量、系统变量）
- 通过 helper 函数封装 pool 的写入操作，避免直接调用

### 3.2 变量前缀常量

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/variable_prefixes.py`
**核心代码**：

```python
"""Variable pool 中不同类型变量的前缀。"""

CONVERSATION_VARIABLE_NODE_ID = "conversation"
ENVIRONMENT_VARIABLE_NODE_ID = "env"
RAG_PIPELINE_VARIABLE_NODE_ID = "rag_pipeline"
SYSTEM_VARIABLE_NODE_ID = "sys"
```

**解读**：
- 用常量定义特殊变量前缀，避免拼写错误
- `conversation` 前缀 → 会话变量
- `sys` 前缀 → 系统变量
- 通过前缀区分变量类型

### 3.3 系统变量预加载

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/system_variables.py`（节选）
**核心代码**：

```python
def preload_node_creation_variables(
    *,
    system_variables: SystemVariable,
    conversation_variables: Sequence[Variable],
) -> dict[str, Any]:
    """在节点创建时预加载系统/会话变量"""
    result: dict[str, Any] = {}
    # 系统变量
    for key in SystemVariableKey:
        result[key.value] = getattr(system_variables, key.value, None)
    # 会话变量
    for var in conversation_variables:
        result[var.name] = var.value
    return result


def inject_default_system_variable_mappings(
    graph_config: dict[str, Any],
) -> dict[str, Any]:
    """把系统变量自动注入到节点配置中"""
    ...
```

**解读**：
- 在工作流启动时，把系统变量和会话变量预加载到 pool
- 节点的 `query_variable_selector` 等字段自动指向对应的系统变量
- 简化用户配置

## 4. 关键要点总结

- 三类变量：系统（自动注入）/ 会话（跨轮次）/ 节点（节点输出）
- VariablePool 是中央存储，用 selector（路径数组）寻址
- 特殊变量有固定前缀（`sys`、`conversation` 等）
- 通过 helper 函数（`add_node_inputs_to_pool`）封装 pool 操作

## 5. 练习题

### 练习 1：基础（必做）

实现一个 VariablePool，支持 set/get/exists 方法，并用 3 个节点测试数据流转。

### 练习 2：进阶

扩展 VariablePool，增加 `get_by_prefix(prefix)` 方法，返回该前缀下所有变量。

### 练习 3：挑战（选做）

设计一个会话变量持久化方案：把 Conversation Variables 存到 Redis，每次工作流启动时自动恢复。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/variable_pool_initializer.py`
- `/Users/xu/code/github/dify/api/core/workflow/variable_prefixes.py`
- `/Users/xu/code/github/dify/api/core/workflow/system_variables.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13