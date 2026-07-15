# 5.4 dify 的模型适配层：`model_runtime`

> 从统一接口、插件转发和结果归一化三个层面理解 dify 的模型运行时适配层。

## 🎯 学习目标

完成本文档后，你将能够：
- 说明模型运行时为何要隔离业务层与供应商 SDK
- 理解租户、Provider、模型、凭据和调用参数的边界
- 区分非流式结果与流式结果生成器
- 看懂 `PluginModelRuntime` 如何委托插件客户端执行模型调用

## 📚 前置知识

- [主流大模型对比](./01-llm-overview.md)
- [OpenAI API 使用](./26-openai-api.md)
- Python 抽象接口、类型注解与生成器（详见 [Protocol / Generic](../01-fundamentals/09-protocol-generic.md)、[类型注解](../01-fundamentals/07-python-typing-basics.md)、[生成器](../01-fundamentals/14-generator.md)、[dataclass](../01-fundamentals/36-dataclasses.md)）
- dify 插件系统的基本概念

## 1. 核心概念

### 1.1 为什么需要模型适配层

不同模型供应商在消息结构、凭据、流式事件、工具调用和错误码上都不同。如果工作流节点直接依赖各 SDK，增加或切换供应商会造成大量条件分支。

`model_runtime` 建立稳定边界：

```text
LLM / Embedding / Rerank 节点
              ↓ 统一调用契约
          ModelRuntime
              ↓ Provider 标识解析
      PluginModelClient / daemon
              ↓ 厂商协议
    OpenAI / Anthropic / 本地模型
```

上层只认识 `PromptMessage`、`LLMResult`、`EmbeddingResult` 等领域对象。适配层负责转换插件调用参数，并把插件结果归一化回来。

### 1.2 一次调用包含哪些上下文

- `tenant_id`：决定租户可见的插件、配置和配额。
- `user_id`：可选的调用者范围，用于插件权限或审计。
- `provider`：包含插件身份与 Provider 名称的稳定 ID。
- `model`、`credentials`：具体模型及调用凭据。
- `model_parameters`：temperature、max tokens 等运行参数。
- `prompt_messages`、`tools`、`stop`：标准化模型输入。
- `request_metadata`：如 `app_id`，不应混入提示词。

### 1.3 结果归一化与流式分派

非流式调用返回完整 `LLMResult`；流式调用返回 `Generator[LLMResultChunk, ...]`。调用者必须依据 `stream` 分支消费，不能把生成器误当成完整结果。

运行时还承担 Provider/模型凭据验证、模型 Schema 缓存、token 计数，以及 Embedding、Rerank、TTS、STT、Moderation 等能力的统一转发。

## 2. 代码示例

### 2.1 编写最小运行时接口

```python
# 文件：runtime_demo.py
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Result:
    text: str


@dataclass(frozen=True)
class Chunk:
    delta: str


class Runtime(Protocol):
    def invoke(
        self, messages: Sequence[str], *, stream: bool = False
    ) -> Result | Generator[Chunk, None, None]: ...


class DemoRuntime:
    def invoke(self, messages: Sequence[str], *, stream: bool = False):
        answer = " | ".join(messages)
        if not stream:
            return Result(answer)
        return (Chunk(word + " ") for word in answer.split())


runtime = DemoRuntime()
result = runtime.invoke(["统一", "模型接口"])
assert isinstance(result, Result)
print(result.text)
```

**说明**：业务层只依赖 `Runtime`、`Result` 和 `Chunk`，不接触任何厂商对象。正式代码可用 overload 进一步精确表达 `stream` 与返回类型的关系。

### 2.2 在边界处拆分 Provider ID

```python
# 文件：provider_id.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderID:
    plugin_id: str
    provider_name: str

    @classmethod
    def parse(cls, value: str) -> "ProviderID":
        plugin_id, separator, provider_name = value.partition("/")
        if not separator or not plugin_id or not provider_name:
            raise ValueError("provider 必须是 plugin_id/provider_name")
        return cls(plugin_id, provider_name)


def build_call(provider: str, model: str) -> dict[str, str]:
    identity = ProviderID.parse(provider)
    return {
        "plugin_id": identity.plugin_id,
        "provider": identity.provider_name,
        "model": model,
    }


print(build_call("langgenius/openai", "gpt-4o-mini"))
```

**说明**：复合 ID 的解析集中在边界层，可避免业务代码到处切割字符串，并能尽早拒绝非法输入。

## 3. dify 仓库源码解读

### 3.1 租户绑定的插件运行时

**文件位置**：`/Users/xu/code/github/dify/api/core/plugin/impl/model_runtime.py`  
**核心代码**（行 104-130）：

```python
class PluginModelRuntime(ModelRuntime):
    """Plugin-backed runtime adapter bound to tenant context and optional caller scope.

    Provider discovery goes through ``PluginService`` so the plugin lifecycle
    methods and provider reads share one tenant-scoped cache owner.
    """

    tenant_id: str
    user_id: str | None
    client: PluginModelClient
    _plugin_service: type[PluginService]

    def __init__(
        self,
        tenant_id: str,
        user_id: str | None,
        client: PluginModelClient,
        plugin_service: type[PluginService],
    ) -> None:
        if client is None:
            raise ValueError("client is required.")
        if plugin_service is None:
            raise ValueError("plugin_service is required.")
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.client = client
        self._plugin_service = plugin_service
```

**解读**：
- 类继承 `ModelRuntime`，表明它是领域协议的一种插件实现。
- 租户和用户在构造时绑定，后续调用无需重新猜测调用范围。
- 客户端与插件服务从外部注入，便于测试，也避免内部创建不可替换的依赖。
- 显式空值检查让配置错误在构造阶段暴露。

### 3.2 调用插件并归一化非流式结果

**文件位置**：`/Users/xu/code/github/dify/api/core/plugin/impl/model_runtime.py`  
**核心代码**（行 323-345）：

```python
        plugin_id, provider_name = self._split_provider(provider)
        if app_id is None:
            result = self.client.invoke_llm(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                plugin_id=plugin_id,
                provider=provider_name,
                model=model,
                credentials=credentials,
                model_parameters=model_parameters,
                prompt_messages=list(prompt_messages),
                tools=tools,
                stop=list(stop) if stop else None,
                stream=stream,
            )
        else:
            result = self.client.invoke_llm(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                plugin_id=plugin_id,
                provider=provider_name,
                model=model,
                credentials=credentials,
```

**解读**：
- 行 322 将复合 Provider ID 拆成插件路由字段。
- 调用参数显式携带租户、用户、凭据与标准化消息，插件边界清晰。
- `Sequence` 在传输前转为列表，适配客户端序列化需求。
- 实际文件随后依据 `stream` 直接返回流，或调用 `normalize_non_stream_runtime_result` 归一化完整结果。

## 4. 关键要点总结

- `model_runtime` 是领域层与具体模型供应商之间的反腐层。
- 运行时统一输入实体、凭据验证、结果类型、流式语义与多种模型能力。
- `PluginModelRuntime` 绑定租户上下文，并通过注入的客户端转发调用。
- 非流式与流式返回类型不同，调用方必须明确分支消费。
- Provider ID 拆分和结果归一化应留在适配边界，不泄露到业务节点。

## 5. 练习题

### 练习 1：基础（必做）

给 `runtime_demo.py` 增加 `model` 和 `temperature` 参数，并保证业务层仍不引用具体供应商名称。

**参考答案**：把参数加入统一 `invoke` 签名，由 `DemoRuntime` 在内部解释，不在调用者中写厂商分支。

### 练习 2：进阶

为示例运行时增加一个适配器，把厂商返回的 `{content, input_tokens, output_tokens}` 转成你定义的 `Result`，并对缺失字段给出领域异常。

### 练习 3：挑战（选做）

阅读 `PluginModelRuntime` 的所有 `invoke_*` 方法，画出 LLM、Embedding、Rerank、TTS、STT、Moderation 的共同参数与特有参数，设计一个不使用 `Any` 的 Protocol 体系。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/plugin/impl/model_runtime.py`
- `/Users/xu/code/github/dify/api/core/plugin/impl/model.py`
- `/Users/xu/code/github/dify/api/core/model_manager.py`
- [dify 的供应商系统](./29-model-provider.md)

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
