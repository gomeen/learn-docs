# 6.25 Anthropic Claude API（Messages API）

> 掌握 Anthropic Messages API 的核心用法：请求结构、消息角色、流式输出、工具调用、Prompt Caching，能在 dify 之外独立集成 Claude。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Python SDK 或 curl 调用 Anthropic Messages API
- 正确构造多轮对话、工具调用、流式响应
- 理解 Prompt Caching 的成本优化机制
- 在 dify 中识别 `anthropic` 供应商对应的请求结构

## 📚 前置知识

- HTTP / JSON 基础（详见 [HTTP 协议](../../_common/14-api-protocols/01-http-protocol.md)、[JSON](../01-fundamentals/27-json-processing.md)）
- MCP vs Function Calling（详见 [MCP vs Function Calling](./23-mcp-vs-function-calling.md)）
- Anthropic 模型家族（详见 [主流大模型对比](./01-llm-overview.md)）

## 1. 核心概念

### 1.1 Messages API 是什么？

Anthropic Messages API 是 Claude 对外的统一接口，所有 Claude 模型（Opus / Sonnet / Haiku）都通过它访问：

```
POST https://api.anthropic.com/v1/messages
Headers:
  x-api-key: <ANTHROPIC_API_KEY>
  anthropic-version: 2023-06-01
  content-type: application/json

Body:
  {
    "model": "claude-sonnet-5-20251001",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "..."}]
  }
```

### 1.2 关键概念

| 概念 | 含义 |
| --- | --- |
| `model` | 模型 ID（如 `claude-sonnet-5-20251001`） |
| `max_tokens` | **必填**，限制输出长度 |
| `messages` | 对话历史，role 必须是 `user` / `assistant`（不能 `system`！） |
| `system` | 系统提示，独立字段（不在 messages 里） |
| `tools` | 工具定义（Function Calling，详见 [Function Calling](./14-function-calling.md)） |
| `stream` | true 时返回 SSE 流（协议详见 [SSE](../../_common/14-api-protocols/04-sse.md)；实践见 [流式输出](./27-streaming-sse.md)） |
| `temperature` / `top_p` / `top_k` | 采样参数 |
| `stop_sequences` | 自定义停止符 |

### 1.3 Prompt Caching 原理

Claude 支持**显式 prompt caching**，可以缓存 prompt 前缀降低费用（完整策略详见 [Prompt Caching](./31-prompt-caching.md)）：

```json
{
  "model": "claude-sonnet-5-20251001",
  "max_tokens": 1024,
  "system": [
    {
      "type": "text",
      "text": "You are a helpful assistant...",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "<large context>", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "question"}
      ]
    }
  ]
}
```

`cache_control: ephemeral` 标记**该位置之前的所有内容**会被缓存（5 分钟 TTL）。读取缓存价格低约 90%，写入价格高约 25%——适合"长 prompt + 多轮/多次请求"场景。

### 1.4 dify 与 Anthropic API 的关系

dify 不直接用 `anthropic` Python SDK，而是通过 plugin daemon 进程转发调用：
- 好处：插件崩溃不影响主进程
- 坏处：调试多一层（dify → plugin daemon → Anthropic API）

`dify` 在 `api/core/model_runtime/model_providers/` 下原本有 anthropic 目录，新版改为由外部 plugin 提供。ModelProviderFactory 通过 `PluginModelClient` 拉取供应商配置。

## 2. 代码示例

### 2.1 用 Python SDK 发最简请求

```python
# 文件：hello_claude.py
import anthropic

client = anthropic.Anthropic()  # 读 ANTHROPIC_API_KEY 环境变量

message = client.messages.create(
    model="claude-sonnet-5-20251001",
    max_tokens=1024,
    system="You are a helpful assistant.",
    messages=[
        {"role": "user", "content": "用一句话介绍 Python 异步编程"},
    ],
)
print(message.content[0].text)
print(f"input tokens: {message.usage.input_tokens}, output: {message.usage.output_tokens}")
```

### 2.2 用 curl 发流式请求

```bash
# 文件：stream_claude.sh
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-5-20251001",
    "max_tokens": 1024,
    "stream": true,
    "messages": [{"role": "user", "content": "讲个笑话"}]
  }'
```

返回 SSE 流：

```
event: message_start
data: {"type":"message_start","message":{"id":"msg_...","role":"assistant",...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"为"}}

...

event: message_stop
data: {"type":"message_stop"}
```

### 2.3 工具调用（Function Calling）

```python
# 文件：tool_use_claude.py
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather",
        "description": "查询城市天气",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }
]

response = client.messages.create(
    model="claude-sonnet-5-20251001",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
)

# 处理 tool_use 块
for block in response.content:
    if block.type == "tool_use":
        tool_name = block.name
        tool_input = block.input
        print(f"调工具 {tool_name}, 参数 {tool_input}")
        # 真正执行工具（这里是伪代码）
        tool_result = {"temp": 25, "unit": "c"}
        # 把结果追加到 messages，调第二次
        messages = [
            {"role": "user", "content": "北京今天天气怎么样？"},
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result),
                    }
                ],
            },
        ]
        final = client.messages.create(
            model="claude-sonnet-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        print(final.content[0].text)
```

### 2.4 常见错误：忘记 max_tokens

```python
# ❌ 错误：不传 max_tokens 会返回 400
client.messages.create(model="claude-sonnet-5-20251001", messages=[...])
# APIError: 400 missing required field "max_tokens"

# ✅ 正确：max_tokens 是必填
client.messages.create(model="claude-sonnet-5-20251001", max_tokens=1024, messages=[...])
```

### 2.5 常见错误：把 system 放 messages 里

```python
# ❌ 错误：system 必须是顶层字段，不能在 messages 里
messages = [
    {"role": "system", "content": "You are helpful"},  # API 会报 invalid role
    {"role": "user", "content": "hi"},
]

# ✅ 正确：system 放顶层
client.messages.create(
    model="claude-sonnet-5-20251001",
    max_tokens=1024,
    system="You are helpful",
    messages=[{"role": "user", "content": "hi"}],
)
```

## 3. dify 仓库源码解读

### 3.1 ModelProviderFactory 通过 plugin daemon 调用 Anthropic

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/model_providers/model_provider_factory.py`
**核心代码**（行 34-72）：

```python
class ModelProviderFactory:
    provider_position_map: dict[str, int]

    def __init__(self, tenant_id: str) -> None:
        from core.plugin.impl.model import PluginModelClient

        self.provider_position_map = {}

        self.tenant_id = tenant_id
        self.plugin_model_manager = PluginModelClient()

        if not self.provider_position_map:
            # get the path of current classes
            current_path = os.path.abspath(__file__)
            model_providers_path = os.path.dirname(current_path)

            # get _position.yaml file path
            self.provider_position_map = get_provider_position_map(model_providers_path)

    def get_providers(self) -> Sequence[ProviderEntity]:
        """
        Get all providers
        :return: list of providers
        """
        # Fetch plugin model providers
        plugin_providers = self.get_plugin_model_providers()
        ...
```

**解读**：
- 第 37-43 行：构造函数初始化 `PluginModelClient`——这是 dify 调 Anthropic / OpenAI 等的统一入口
- 第 45-51 行：读取 `_position.yaml` 来控制 UI 上供应商的显示顺序（Anthropic 通常排在 OpenAI 之前）
- 第 53-72 行：`get_providers` 通过 plugin daemon 进程（Go 写的）拉取所有供应商信息，排序后返回
- **整体设计意图**：dify 把每个 LLM 供应商都做成"外部插件"，由 Go daemon 进程执行实际 API 调用，Python 端只负责转发。这样做的好处：①插件崩溃不影响主进程；②插件可以用任何语言；③不同租户可以加载不同版本的插件

### 3.2 PluginModelClient.invoke_llm 入口

**文件位置**：`/Users/xu/code/github/dify/api/core/plugin/impl/model_runtime.py`
**核心代码**（行 1-50）：

```python
class PluginModelClient:
    def fetch_model_providers(self, tenant_id: str) -> Sequence[PluginModelProviderEntity]:
        """
        Fetch model providers for a tenant.
        """
        try:
            resp = self._request(
                method="GET",
                path="plugin/model/providers",
                params={"tenant_id": tenant_id},
            )
            return [PluginModelProviderEntity(**provider) for provider in resp["data"]]
        except Exception:
            raise PluginDaemonClientSideError(code=...) from None

    def invoke_llm(self, tenant_id, provider, model, credentials, prompt_messages, ...):
        # 通过 plugin daemon 进程转发调用，统一鉴权/限流/审计
        ...
```

**解读**：
- 第 5-15 行：`fetch_model_providers` 通过 HTTP GET 调 plugin daemon，路径 `plugin/model/providers`
- 第 18-21 行：`invoke_llm` 把 `tenant_id` / `provider` / `model` / `credentials` / `prompt_messages` 等参数转发给 daemon
- `credentials` 是用户在 dify UI 填的 API Key，daemon 端会用它直接调 Anthropic API
- **整体设计意图**：上层 Python 业务（Agent/Workflow）只看到 `invoke_llm` 这一个方法，完全不知道下面用的是 Anthropic / OpenAI / Gemini。这就是 dify"模型无关"的抽象基础

## 4. 关键要点总结

- Anthropic Messages API 端点：`POST https://api.anthropic.com/v1/messages`
- `max_tokens` 是**必填**字段，`system` 是**顶层字段**（不在 messages 里）
- 支持 stream（`"stream": true`）、tools（Function Calling）、Prompt Caching（`cache_control`）
- Prompt Caching 适合长 prompt + 多轮场景，读取价低 ~90%
- dify 通过 plugin daemon（Go 进程）转发 Anthropic 调用，Python 端不直接用 SDK
- 上层业务只看到 `invoke_llm(...)` 一个方法，模型无关

## 5. 练习题

### 练习 1：基础（必做）

写一个 Python 脚本：调 Anthropic Messages API 生成 3 句话讲清楚"什么是 MCP"，用 SSE 流式输出，每收到一个 token 就打印一次（不要等全部内容）。

提示：用 `client.messages.stream(...)` 或 `client.messages.create(stream=True)` 加 `for chunk in response:`。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/model_runtime/model_providers/model_provider_factory.py` 第 135-198 行 `provider_credentials_validate` 和 `model_credentials_validate`，理解 dify 怎么校验用户在 UI 填的 Anthropic API Key——它是直接调 Anthropic 验证，还是只看格式？

### 练习 3：挑战（选做）

实现一个 Anthropic API 的轻量级 Python 客户端（不依赖 `anthropic` SDK），要求：
1. 用 `httpx` 发请求，支持 SSE 流式响应解析
2. 支持 `messages` / `tools` / `system` 字段
3. 正确处理 401（无效 API Key）、429（限流）、529（过载）状态码
4. 在 429 时自动按 `Retry-After` header 等候后重试（最多 3 次）

提示：参考 `dify` 的 `api/core/helper/ssrf_proxy.py` 风格，用 async context manager 管理 httpx Client。

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/model_providers/model_provider_factory.py`
- `/Users/xu/code/github/dify/api/core/plugin/impl/model_runtime.py`
- Anthropic Messages API 文档：https://docs.anthropic.com/en/api/messages
- Prompt Caching 文档：https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Tool Use 文档：https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- Streaming 文档：https://docs.anthropic.com/en/api/messages-streaming
- Anthropic Python SDK：https://github.com/anthropics/anthropic-sdk-python

---

**文档版本**：v1.0
**最后更新**：2026-07-13