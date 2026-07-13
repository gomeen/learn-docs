# 5.5 dify 的供应商系统：ModelProvider 抽象

> 理解 Provider 元数据、插件发现、凭据校验与模型类型实例化如何组成 dify 的供应商系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Provider、模型和模型类型三个概念
- 说明 `ModelProviderFactory` 如何发现、缓存和排序插件 Provider
- 理解 Provider 级凭据与模型级凭据的校验边界
- 看懂工厂如何为不同 `ModelType` 构造统一实现

## 📚 前置知识

- [dify 的模型适配层](./28-model-runtime.md)
- Python 工厂模式、Pydantic 和枚举基础
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

## 3. dify 仓库源码解读

### 3.1 发现并缓存租户可见 Provider

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/model_providers/model_provider_factory.py`  
**核心代码**（行 74-101）：

```python
    def get_plugin_model_providers(self) -> Sequence["PluginModelProviderEntity"]:
        """
        Get all plugin model providers
        :return: list of plugin model providers
        """
        # check if context is set
        try:
            contexts.plugin_model_providers.get()
        except LookupError:
            contexts.plugin_model_providers.set(None)
            contexts.plugin_model_providers_lock.set(Lock())

        with contexts.plugin_model_providers_lock.get():
            plugin_model_providers = contexts.plugin_model_providers.get()
            if plugin_model_providers is not None:
                return plugin_model_providers

            plugin_model_providers = []
            contexts.plugin_model_providers.set(plugin_model_providers)

            # Fetch plugin model providers
            plugin_providers = self.plugin_model_manager.fetch_model_providers(self.tenant_id)

            for provider in plugin_providers:
                provider.declaration.provider = provider.plugin_id + "/" + provider.declaration.provider
                plugin_model_providers.append(provider)

            return plugin_model_providers
```

**解读**：
- 行 79-83 初始化上下文变量和锁，适应尚未建立缓存的调用环境。
- 行 85-88 在锁内检查缓存，已有结果直接返回。
- 行 94 按租户从插件客户端拉取 Provider。
- 行 97 将插件 ID 加入 Provider 标识，形成全局不易冲突的复合 ID。

### 3.2 按模型类型构造实现

**文件位置**：同上  
**核心代码**（行 289-315）：

```python
    def get_model_type_instance(self, provider: str, model_type: ModelType) -> AIModel:
        """
        Get model type instance by provider name and model type
        :param provider: provider name
        :param model_type: model type
        :return: model type instance
        """
        plugin_id, provider_name = self.get_plugin_id_and_provider_name_from_provider(provider)
        init_params = {
            "tenant_id": self.tenant_id,
            "plugin_id": plugin_id,
            "provider_name": provider_name,
            "plugin_model_provider": self.get_plugin_model_provider(provider),
        }

        if model_type == ModelType.LLM:
            return LargeLanguageModel(**init_params)  # type: ignore
        elif model_type == ModelType.TEXT_EMBEDDING:
            return TextEmbeddingModel(**init_params)  # type: ignore
        elif model_type == ModelType.RERANK:
            return RerankModel(**init_params)  # type: ignore
        elif model_type == ModelType.SPEECH2TEXT:
            return Speech2TextModel(**init_params)  # type: ignore
        elif model_type == ModelType.MODERATION:
            return ModerationModel(**init_params)  # type: ignore
        elif model_type == ModelType.TTS:
            return TTSModel(**init_params)  # type: ignore
```

**解读**：工厂先解析 Provider，再复用相同初始化参数构造各模型类型适配器。业务层因此只需提供 `ModelType`，不需要 import 具体实现类。

## 4. 关键要点总结

- Provider 是能力与凭据容器，不等同于一个具体模型。
- dify 通过插件动态发现 Provider，并用租户 ID 限定可见范围。
- 复合 Provider ID 把插件身份与声明名组合起来，减少命名冲突。
- 凭据先做 Schema 过滤，再由插件做真实连通性和授权校验。
- 工厂根据 `ModelType` 返回 LLM、Embedding、Rerank 等统一适配器。

## 5. 练习题

### 练习 1：基础（必做）

为 `Provider` 示例增加 `supports(model_type)` 方法，并分别测试 LLM、Embedding 和未支持的 Rerank。

**参考答案**：对 `models` 使用 `any(model.model_type == model_type for model in self.models)`。

### 练习 2：进阶

设计一个 Provider 凭据 Schema，包含必填 API Key、可选 Endpoint 和 Region；实现过滤未知字段并隐藏日志中的 API Key。

### 练习 3：挑战（选做）

沿 `ModelProviderFactory.get_plugin_model_providers()` 追踪到插件 daemon，画出租户安装插件后 Provider 出现在模型配置页面的完整时序图。

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/model_providers/model_provider_factory.py`
- `/Users/xu/code/github/dify/api/core/plugin/impl/model_runtime.py`
- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- dify 插件开发文档：https://docs.dify.ai/plugins/quick-start/develop-plugins

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
