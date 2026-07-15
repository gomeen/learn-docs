# 7.5.7 自定义节点开发

> 学习如何为 dify 开发自定义节点，扩展工作流能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述自定义节点的开发流程
- 实现一个最小的自定义节点
- 理解节点与引擎的交互接口
- 了解 dify 的插件化架构

## 📚 前置知识

- [Workflow Nodes](./25-workflow-nodes.md)
- [Workflow Engine](./24-workflow-engine.md)
- Pydantic 基础（详见 [Pydantic 基础](../02-backend/15-pydantic-basics.md)）

## 1. 核心概念

### 1.1 自定义节点的两种形态

| 形态 | 适用 | 实现难度 |
|------|------|----------|
| **Python 内置节点** | dify 内部扩展 | 中（修改 dify 源码） |
| **Plugin 节点** | 第三方扩展 | 低（用 Plugin SDK） |

dify 现在主推 Plugin 化：所有节点都通过 Plugin 机制提供。

### 1.2 自定义节点的接口

```python
class CustomNode(BaseNode):
    """自定义节点必须实现的接口"""

    node_type = "my_custom_node"  # 唯一标识

    def _run(self) -> NodeRunResult:
        # 节点逻辑
        ...
        return NodeRunResult(outputs={...})
```

### 1.3 节点的输入输出

通过 `NodeRunResult` 把结果写入 VariablePool：

```python
return NodeRunResult(outputs={
    "result_var_name": value,
})
```

通过 `self.graph_runtime_state.variable_pool` 读输入：

```python
input_value = self.graph_runtime_state.variable_pool.get(selector)
```

## 2. 代码示例

### 2.1 最简单的自定义节点

```python
from pydantic import BaseModel


class UppercaseNodeData(BaseModel):
    """节点配置"""
    input_variable: str = "input_text"


class UppercaseNode(BaseNode):
    """大写转换节点：把输入文本转大写"""

    node_type = "uppercase"

    def _run(self) -> NodeRunResult:
        # 1. 读输入
        input_text = self.graph_runtime_state.variable_pool.get(
            ["start", self.node_data.input_variable]
        )

        # 2. 处理
        output_text = input_text.upper()

        # 3. 写输出
        return NodeRunResult(outputs={
            "text": output_text,
        })
```

### 2.2 节点调用外部 API

```python
import httpx


class WeatherNode(BaseNode):
    """天气查询节点"""

    node_type = "weather"

    def _run(self) -> NodeRunResult:
        # 1. 读城市名
        city = self.graph_runtime_state.variable_pool.get(["start", "city"])

        # 2. 调用 API
        response = httpx.get(
            f"https://api.weather.com/v1/current?city={city}",
            timeout=10,
        )
        weather_data = response.json()

        # 3. 返回
        return NodeRunResult(outputs={
            "temperature": weather_data["temperature"],
            "description": weather_data["description"],
        })
```

### 2.3 节点带鉴权

```python
class AuthenticatedNode(BaseNode):
    """需要鉴权的节点"""

    def _run(self) -> NodeRunResult:
        # 1. 读 API Key（从配置）
        api_key = self.node_data.api_key

        # 2. 调用鉴权 API
        headers = {"Authorization": f"Bearer {api_key}"}
        response = httpx.get("https://api.example.com/data", headers=headers)
        return NodeRunResult(outputs={"data": response.json()})
```

### 2.4 常见错误：节点抛异常导致工作流崩溃

```python
# ❌ 错误：节点抛异常，引擎崩溃
def _run(self):
    result = external_api()  # 可能失败
    return NodeRunResult(outputs={"data": result})

# ✅ 正确：节点内部 try-except，返回错误状态
def _run(self):
    try:
        result = external_api()
        return NodeRunResult(status="success", outputs={"data": result})
    except Exception as e:
        return NodeRunResult(status="failed", error=str(e))
```

## 3. dify 仓库源码解读

### 3.1 Node 基类

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/base.py`（节选）
**核心代码**（示意）：

```python
from abc import ABC, abstractmethod


class BaseNode(ABC, Generic[T]):
    """所有节点的基类"""

    def __init__(
        self,
        node_id: str,
        data: T,
        *,
        graph_init_params: GraphInitParams,
        graph_runtime_state: GraphRuntimeState,
    ):
        self.node_id = node_id
        self.node_data = data  # 节点配置
        self.graph_init_params = graph_init_params
        self.graph_runtime_state = graph_runtime_state

    @abstractmethod
    def _run(self) -> NodeRunResult | Generator[NodeEventBase, None, None]:
        """子类必须实现：节点执行逻辑"""
        raise NotImplementedError
```

**解读**：
- 泛型 `T` 是节点数据类型（每个节点有自己的 Pydantic 数据模型）
- 通过依赖注入传入 `graph_init_params` 和 `graph_runtime_state`
- `_run` 是核心方法，子类必须实现

### 3.2 节点注册机制

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/node_factory.py`（节选）
**核心代码**（示意）：

```python
def resolve_workflow_node_class(node_type: str) -> type[Node]:
    """根据 node_type 找到节点类"""
    # 1. 查找 dify 自定义节点
    if node_type in DIFY_NODE_TYPES:
        return DIFY_NODE_TYPES[node_type]

    # 2. 查找 plugin 节点
    plugin_node = plugin_registry.get_node(node_type)
    if plugin_node:
        return plugin_node

    # 3. 查找内置节点（graphon）
    return BuiltinNodeTypes[node_type].get_node_class()
```

**解读**：
- dify 用三段式查找：自定义 → plugin → 内置
- plugin 节点是第三方扩展，dify 通过 `plugin_registry` 动态加载
- 内置节点在 graphon 库

### 3.3 KnowledgeRetrievalNode 实例

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/knowledge_retrieval_node.py`（节选）
**核心代码**：

```python
class KnowledgeRetrievalNode(BaseNode):
    """知识检索节点（dify 自定义节点）"""

    node_type = BuiltinNodeTypes.KNOWLEDGE_RETrieval

    @override
    def _run(self) -> Generator[NodeEventBase, None, None]:
        # 1. 读 query 变量
        query = self._get_query_from_pool()

        # 2. 调用 DatasetRetrieval
        documents = DatasetRetrieval.retrieve(
            retrieval_method=self.node_data.retrieval_mode,
            dataset_id=self.node_data.dataset_ids[0],
            query=query,
            top_k=self.node_data.top_k,
            ...
        )

        # 3. 流式返回结果
        yield NodeRunResult(outputs={
            "result": [doc.page_content for doc in documents],
        })
```

**解读**：
- 这是 dify 自定义节点的典型实现
- 通过 `self.node_data` 访问配置（Pydantic 模型）
- 通过 `self.graph_runtime_state.variable_pool` 读写变量

## 4. 关键要点总结

- 自定义节点实现 `BaseNode._run()` 接口
- 节点配置用 Pydantic 定义
- 通过 VariablePool 与引擎交互
- dify 支持 Plugin 节点（第三方扩展）
- 节点异常应该捕获并返回 `failed` 状态

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `ReverseNode`：读 `text` 变量，输出 `reversed` 变量 = text[::-1]。

### 练习 2：进阶

实现一个 `CountWordsNode`：读 `text` 变量，输出 `word_count` 变量 = len(text.split())。

### 练习 3：挑战（选做）

阅读 dify 的 plugin 文档，实现一个第三方 plugin 节点（HTTP 调用外部 API）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/base.py`
- `/Users/xu/code/github/dify/api/core/workflow/node_factory.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/`
- dify 官方：自定义节点开发指南

---

**文档版本**：v1.0
**最后更新**：2026-07-13