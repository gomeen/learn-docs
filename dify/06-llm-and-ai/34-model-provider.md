# 5.5 dify 的供应商系统：ModelProvider 抽象

> 理解 Provider 元数据、插件发现、凭据校验与模型类型实例化如何组成 dify 的供应商系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Provider、模型和模型类型三个概念
- 说明 `ModelProviderFactory` 如何发现、缓存和排序插件 Provider
- 理解 Provider 级凭据与模型级凭据的校验边界
- 看懂工厂如何为不同 `ModelType` 构造统一实现

## 📚 前置知识

- [dify 的模型适配层](./33-model-runtime.md)
- Python 工厂模式、Pydantic 和枚举（详见 [Pydantic 基础](../02-backend/12-pydantic-basics.md)、[dataclass](../01-fundamentals/26-dataclasses.md)）
- dify 插件系统基本概念

## 1. 核心概念

### 1.1 Provider 不是单个模型

Provider 表示一个模型能力来源，例如 OpenAI、Azure OpenAI 或某个本地推理服务；一个 Provider 可以暴露多个模型和多种能力：

```text
Provider
├── 元数据：名称、图标、帮助链接
├── 凭据 Schema：API Key、Endpoint、Region
├── 支持的 ModelType
│   ├── LLM
│   ├── TEXT_EMBEDDING
│   ├── RERANK
│   └── TTS / STT / MODERATION
└── 模型清单与动态 Schema
```

因此，“选 Provider”与“选模型”是两步。Provider 负责连接和能力声明，模型负责具体上下文长度、参数和价格。

### 1.2 插件发现与租户隔离

`ModelProviderFactory` 以 `tenant_id` 构造，通过插件客户端读取该租户可见的 Provider。返回结果带有插件 ID，避免不同插件声明同名 Provider 时发生冲突。

工厂还读取位置映射，为 UI 提供稳定排序。发现结果可以在请求上下文中缓存，并用锁避免同一上下文重复拉取。

### 1.3 两级凭据与 Schema 校验

- **Provider 凭据**：多个模型共享，例如统一 API Key。
- **模型凭据**：某个部署或模型独享，例如 Azure deployment endpoint。

校验分两步：先按声明的 Schema 过滤和验证字段，再请求插件执行真实凭据校验。前者阻止字段缺失和多余输入，后者发现密钥无效、权限不足或端点不可达。

## 2. 代码示例

### 2.1 定义 Provider 元数据并过滤模型类型

```python
# 文件：provider_catalog.py
from dataclasses import dataclass
from enum import StrEnum


class ModelType(StrEnum):
    LLM = "llm"
    EMBEDDING = "text-embedding"


@dataclass(frozen=True)
class Model:
    name: str
    model_type: ModelType


@dataclass(frozen=True)
class Provider:
    name: str
    models: tuple[Model, ...]

    def models_of(self, model_type: ModelType) -> list[Model]:
        return [model for model in self.models if model.model_type == model_type]


provider = Provider(
    name="demo",
    models=(Model("chat-large", ModelType.LLM), Model("embed-small", ModelType.EMBEDDING)),
)
print(provider.models_of(ModelType.LLM))
```

**说明**：Provider 持有能力目录，业务按照 `ModelType` 查询，不需要猜测模型名是否属于 LLM。

### 2.2 分离结构校验与远端校验

```python
# 文件：credential_validation.py
from collections.abc import Callable


def validate_credentials(
    credentials: dict[str, str],
    remote_validator: Callable[[dict[str, str]], None],
) -> dict[str, str]:
    allowed = {"api_key", "endpoint"}
    filtered = {key: value.strip() for key, value in credentials.items() if key in allowed}

    if not filtered.get("api_key"):
        raise ValueError("api_key 不能为空")
    if "endpoint" in filtered and not filtered["endpoint"].startswith("https://"):
        raise ValueError("endpoint 必须使用 HTTPS")

    remote_validator(filtered)
    return filtered


def ping_provider(credentials: dict[str, str]) -> None:
    if credentials["api_key"] == "invalid":
        raise PermissionError("远端拒绝凭据")


print(validate_credentials({"api_key": "demo", "ignored": "x"}, ping_provider))
```

**说明**：返回过滤后的凭据，而不是原始输入，避免未知字段继续流入插件调用。

## 3. 关键要点总结

- Provider 是能力与凭据容器，不等同于一个具体模型。
- dify 通过插件动态发现 Provider，并用租户 ID 限定可见范围。
- 复合 Provider ID 把插件身份与声明名组合起来，减少命名冲突。
- 凭据先做 Schema 过滤，再由插件做真实连通性和授权校验。
- 工厂根据 `ModelType` 返回 LLM、Embedding、Rerank 等统一适配器。

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
