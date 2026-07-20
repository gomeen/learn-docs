# 6.25 Anthropic Claude API（Messages API）

> 掌握 Anthropic Messages API 的核心用法：请求结构、消息角色、流式输出、工具调用、Prompt Caching，能在 dify 之外独立集成 Claude。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Python SDK 或 curl 调用 Anthropic Messages API
- 正确构造多轮对话、工具调用、流式响应
- 理解 Prompt Caching 的成本优化机制
- 在 dify 中识别 `anthropic` 供应商对应的请求结构

## 📚 前置知识

- HTTP / JSON 基础（详见 [HTTP 协议](../../_common/14-api-protocols/01-http-protocol.md)、[JSON](../01-fundamentals/20-json-processing.md)）
- MCP vs Function Calling（详见 [MCP vs Function Calling](./27-mcp-vs-function-calling.md)）
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
| `tools` | 工具定义（Function Calling，详见 [Function Calling](./17-function-calling.md)） |
| `stream` | true 时返回 SSE 流（协议详见 [SSE](../../_common/14-api-protocols/04-sse.md)；实践见 [流式输出](./32-streaming-sse.md)） |
| `temperature` / `top_p` / `top_k` | 采样参数 |
| `stop_sequences` | 自定义停止符 |

### 1.3 Prompt Caching 原理

Claude 支持**显式 prompt caching**，可以缓存 prompt 前缀降低费用（完整策略详见 [Prompt Caching](./37-prompt-caching.md)）：

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

## 3. 关键要点总结

- Anthropic Messages API 端点：`POST https://api.anthropic.com/v1/messages`
- `max_tokens` 是**必填**字段，`system` 是**顶层字段**（不在 messages 里）
- 支持 stream（`"stream": true`）、tools（Function Calling）、Prompt Caching（`cache_control`）
- Prompt Caching 适合长 prompt + 多轮场景，读取价低 ~90%
- dify 通过 plugin daemon（Go 进程）转发 Anthropic 调用，Python 端不直接用 SDK
- 上层业务只看到 `invoke_llm(...)` 一个方法，模型无关

---

**文档版本**：v1.0
**最后更新**：2026-07-13
