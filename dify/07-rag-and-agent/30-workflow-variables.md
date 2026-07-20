# 7.5.3 变量系统：全局 / 会话 / 节点变量

> 理解 dify 工作流的变量系统：节点的"血液"，在节点之间传递数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分三类变量：系统变量 / 会话变量 / 节点变量
- 理解 VariablePool 的数据结构
- 用变量选择器引用变量
- 看懂 dify 中变量系统的实现

## 📚 前置知识

- [Workflow Engine](./28-workflow-engine.md)
- [Workflow Nodes](./29-workflow-nodes.md)

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

## 3. 关键要点总结

- 三类变量：系统（自动注入）/ 会话（跨轮次）/ 节点（节点输出）
- VariablePool 是中央存储，用 selector（路径数组）寻址
- 特殊变量有固定前缀（`sys`、`conversation` 等）
- 通过 helper 函数（`add_node_inputs_to_pool`）封装 pool 操作

---

**文档版本**：v1.0
**最后更新**：2026-07-13
