# 7.5.7 自定义节点开发

> 学习如何为 dify 开发自定义节点，扩展工作流能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述自定义节点的开发流程
- 实现一个最小的自定义节点
- 理解节点与引擎的交互接口
- 了解 dify 的插件化架构

## 📚 前置知识

- [Workflow Nodes](./29-workflow-nodes.md)
- [Workflow Engine](./28-workflow-engine.md)
- Pydantic 基础（详见 [Pydantic 基础](../02-backend/12-pydantic-basics.md)）

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

## 3. 关键要点总结

- 自定义节点实现 `BaseNode._run()` 接口
- 节点配置用 Pydantic 定义
- 通过 VariablePool 与引擎交互
- dify 支持 Plugin 节点（第三方扩展）
- 节点异常应该捕获并返回 `failed` 状态

---

**文档版本**：v1.0
**最后更新**：2026-07-13
