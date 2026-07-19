# 6.14 Function Calling：原理与调用流程

> 理解 LLM Function Calling（函数调用 / 工具调用）的核心原理，能追踪 dify 中从「模型返回 tool_call」到「工具执行并回填结果」的完整闭环。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 Function Calling 在 LLM 应用中的角色
- 画出一个完整的 tool-use 循环：构造请求 → 模型返回 tool_use → 执行 → 喂回 tool_result
- 区分 Chat Completions 风格的 `tool_calls` 字段与 Anthropic 风格的 `tool_use` 内容块
- 能读懂 dify 中 `fc_agent_runner.py` 的 stream/blocking 两条路径

## 📚 前置知识

- Python 基础语法（生成器详见 [生成器](../01-fundamentals/14-generator.md)；JSON 详见 [JSON](../01-fundamentals/27-json-processing.md)）
- LLM 的消息结构（system / user / assistant / tool；详见 [Prompt 基础](./07-prompt-basics.md)）
- dify 的 LLM 抽象层（详见 [主流大模型对比](./01-llm-overview.md)）

## 1. 核心概念

### 1.1 什么是 Function Calling

Function Calling（也称 Tool Use）是 LLM **不直接执行函数**、而是 **返回结构化调用请求**的能力。整个流程是：

```mermaid
sequenceDiagram
    participant U as 用户
    participant App as 业务代码 / Agent Runner
    participant LLM as LLM
    participant Tool as 工具实现
    U->>App: 1. 输入问题
    App->>LLM: 2. 构造请求：messages + tools=[{name,description,parameters}]
    LLM-->>App: 3. 返回：assistant 消息带 tool_calls/tool_use 块
    App->>Tool: 4. 解析 tool_call，分发到对应 handler
    Tool-->>App: 5. 返回执行结果
    App->>LLM: 6. 把结果作为 tool_result 消息回填，再次请求
    LLM-->>App: 7. 给出最终自然语言回答
    App-->>U: 8. 输出
```

> 📌 **Sighting**：Agent 循环与 ReAct 范式完整展开见 [Agent 概念](../07-rag-and-agent/18-agent-concepts.md)、[ReAct](./10-react.md)；工具参数 schema 见 [Tool Schema](./15-tool-schema.md)。

关键洞察：
- **模型只是"决定"调哪个函数、传什么参数**；具体执行由客户端负责
- 工具的契约写在 `tools` 数组里（name、description、JSON Schema 形式的 parameters）
- 模型永远不会直接访问文件系统、数据库、网络——只产出结构化请求

### 1.2 两种主流的 wire format

不同厂商的工具调用协议略有差异：

| 厂商 | assistant 消息里的字段 | tool 结果消息 |
| --- | --- | --- |
| OpenAI Chat Completions | `tool_calls: [{id, type:"function", function:{name, arguments}}]` | `{"role":"tool", "tool_call_id": id, "content": "..."}` |
| Anthropic Messages | `content: [{type:"tool_use", id, name, input}, ...]` | `{"role":"user", "content":[{type:"tool_result", tool_use_id, content}]}` |
| dify 内部统一 | `AssistantPromptMessage.tool_calls: list[ToolCall]` | `ToolPromptMessage(tool_call_id, content, name)` |

dify 屏蔽了厂商差异，对上层只暴露统一的 `PromptMessageTool` / `AssistantPromptMessage.ToolCall` / `ToolPromptMessage`（见 `core/model_runtime/entities/message_entities.py`）。

### 1.3 工具调用的边界

Function Calling 适合：
- 调用确定性、结果可结构化的动作（查 DB、调 API、跑计算）
- 把"自然语言意图"翻译成"参数化请求"

不适合：
- 需要流式中间步骤的（用 Workflow / Agent 而非单次 function call）
- 模型自己都不确定要不要调（用 `tool_choice="auto"` 即可；用 `tool_choice="any"` 强制至少调一次）

## 2. 代码示例

### 2.1 一个最小可运行的 agent 循环

```python
# 文件：example_fc_loop.py
import json
from openai import OpenAI

client = OpenAI()

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气。城市名用英文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市英文名，例如 Beijing"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["city"],
            },
        }
    }
]

def get_weather(city: str, unit: str = "celsius") -> str:
    # 真实实现应该调第三方 API；这里模拟
    return f"{city} 当前 22°{unit[0].upper()}，晴"

messages = [{"role": "user", "content": "北京今天多少度？"}]

# 第一轮：让模型决定要不要调函数
resp = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
    tool_choice="auto",
)
assistant_msg = resp.choices[0].message
messages.append(assistant_msg)  # 必须把整个 assistant 消息追加回 messages

# 第二轮：把 tool_calls 转成 tool 消息
if assistant_msg.tool_calls:
    for call in assistant_msg.tool_calls:
        args = json.loads(call.function.arguments)
        if call.function.name == "get_weather":
            result = get_weather(**args)
        else:
            result = f"unknown tool: {call.function.name}"
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,  # 必须回填 id，把 call 和 result 配对
            "content": result,
        })

    # 第三轮：让模型基于 tool 结果生成自然语言
    final = client.chat.completions.create(model="gpt-4o", messages=messages)
    print(final.choices[0].message.content)
```

**说明**：
- 第 14-24 行：`tools` 数组里写好契约，模型据此判断是否要调
- 第 33 行：**整条 assistant 消息（含 tool_calls 字段）原样追加回 messages**，否则模型在下一轮会"失忆"
- 第 38-43 行：用 `tool_call_id` 把 call 和 result 配对，这是协议要求
- 第 46 行：再次请求即可拿到最终自然语言

### 2.2 常见错误：忘记把 assistant 消息追加回去

```python
# ❌ 错误：把 tool_call 拆出来直接给模型
resp = client.chat.completions.create(...)
if resp.choices[0].message.tool_calls:
    # 直接调函数
    result = call_tool(resp.choices[0].message.tool_calls[0])
    # 错误：第二轮只发 tool 结果，模型看不到自己上一轮的 tool_call，协议被破坏
    final = client.chat.completions.create(
        model="gpt-4o",
        messages=[user_msg, {"role":"tool","tool_call_id":"...","content":result}],
    )

# ✅ 正确：把 assistant 原话 + tool 结果一起发
messages.append(resp.choices[0].message)  # 关键
messages.append({"role":"tool","tool_call_id":"...","content":result})
final = client.chat.completions.create(model="gpt-4o", messages=messages)
```

## 3. dify 仓库源码解读

### 3.1 统一的工具消息结构

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/message_entities.py`
**核心代码**（行 32-49）：

```python
class PromptMessageTool(BaseModel):
    """
    Model class for prompt message tool.
    """

    name: str
    description: str
    parameters: dict


class PromptMessageFunction(BaseModel):
    """
    Model class for prompt message function.
    """

    type: str = "function"
    function: PromptMessageTool
```

**解读**：
- 第 7-10 行：`PromptMessageTool` 是 dify 内部"工具契约"的统一表示：`name + description + parameters`（其中 `parameters` 是 JSON Schema 字典）
- 第 16-19 行：`PromptMessageFunction` 是 OpenAI 风格的包装（`type:"function"` + `function: PromptMessageTool`），用于直接转给 OpenAI/兼容协议的厂商
- **关键设计**：dify 抽象了 OpenAI / Anthropic / 自研协议的差异，上层业务只看到这 3 个字段

### 3.2 Assistant 消息的 tool_calls 字段

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/message_entities.py`
**核心代码**（行 212-243）：

```python
class AssistantPromptMessage(PromptMessage):
    """
    Model class for assistant prompt message.
    """

    class ToolCall(BaseModel):
        """
        Model class for assistant prompt message tool call.
        """

        class ToolCallFunction(BaseModel):
            """
            Model class for assistant prompt message tool call function.
            """

            name: str
            arguments: str

        id: str
        type: str
        function: ToolCallFunction

        @field_validator("id", mode="before")
        @classmethod
        def transform_id_to_str(cls, value) -> str:
            if not isinstance(value, str):
                return value
            else:
                return str(value)

    role: PromptMessageRole = PromptMessageRole.ASSISTANT
    tool_calls: list[ToolCall] = []
```

**解读**：
- 第 26-28 行：内嵌的 `ToolCallFunction` 严格遵循 OpenAI 协议——`name`（函数名）+ `arguments`（**字符串**形式的 JSON）
- 第 30-32 行：每个 tool_call 自带一个 `id`（用于后续配对 tool_result）
- 第 41 行：`tool_calls: list[ToolCall] = []` 默认空列表；模型没调工具时该字段为空
- **使用提示**：上游拿到 assistant 消息后必须**原封不动**回传，否则协议被破坏

### 3.3 Function-Calling 风格的 agent runner

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/fc_agent_runner.py`
**核心代码**（行 107-206）：

```python
tool_calls: list[tuple[str, str, dict[str, Any]]] = []

# save full response
response = ""

# save tool call names and inputs
tool_call_names = ""
tool_call_inputs = ""

if isinstance(chunks, Generator):
    is_first_chunk = True
    for chunk in chunks:
        # ...
        if self.check_tool_calls(chunk):
            function_call_state = True
            tool_calls.extend(self.extract_tool_calls(chunk) or [])
            tool_call_names = ";".join([tool_call[1] for tool_call in tool_calls])
            try:
                tool_call_inputs = json.dumps(
                    {tool_call[1]: tool_call[2] for tool_call in tool_calls}, ensure_ascii=False
                )
            except TypeError:
                tool_call_inputs = json.dumps({tool_call[1]: tool_call[2] for tool_call in tool_calls})
        # ... 累计 token
        yield chunk
else:
    result = chunks
    if self.check_blocking_tool_calls(result):
        function_call_state = True
        tool_calls.extend(self.extract_blocking_tool_calls(result) or [])
        # ...

assistant_message = AssistantPromptMessage(content=response, tool_calls=[])
if tool_calls:
    assistant_message.tool_calls = [
        AssistantPromptMessage.ToolCall(
            id=tool_call[0],
            type="function",
            function=AssistantPromptMessage.ToolCall.ToolCallFunction(
                name=tool_call[1], arguments=json.dumps(tool_call[2], ensure_ascii=False)
            ),
        )
        for tool_call in tool_calls
    ]
```

**解读**：
- 第 1 行：dify 把工具调用扁平化为 `(id, name, args)` 三元组
- 第 9-21 行：**流式路径**——逐 chunk 检查 `delta.message.tool_calls`，把所有片段合并
- 第 25-29 行：**阻塞路径**——一次性拿到完整响应
- 第 32-40 行：把内部三元组重新组装成对外的 `AssistantPromptMessage`，其中 `arguments` 序列化为 JSON 字符串
- **整体设计**：dify 在 stream/blocking 两条路径下都能正确还原 tool_call，再交给下游的 `ToolEngine.agent_invoke` 执行

## 4. 关键要点总结

- Function Calling = 模型产出结构化 `tool_call` 请求 + 客户端执行 + 把结果回填
- 必须把含 `tool_calls` 的整条 assistant 消息原样追加回 messages，否则协议被破坏
- `tool_call_id` 是 call 和 result 配对的唯一锚点
- dify 内部用统一的 `PromptMessageTool` / `AssistantPromptMessage.ToolCall` 屏蔽厂商差异
- 流式响应下 tool_call 是分片到达的，需要在 runner 里做合并

## 5. 练习题

### 练习 1：基础（必做）

手写一个最小 `OpenAI` 风格的 FC 循环，要求支持以下场景：
- 用户问"15 + 27 等于多少？"
- 工具 `add(a:int, b:int) -> int` 被调用
- 模型把 42 用自然语言返回

注意验证：是否把 assistant 消息的 `tool_calls` 字段原样回传了？

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/agent/fc_agent_runner.py` 第 344-388 行 `extract_tool_calls` 和 `extract_blocking_tool_calls` 的差异，画出"流式分片如何合并成最终 `tool_calls`"的流程图。

### 练习 3：挑战（选做）

把练习 1 的最小循环改造为：模型在一次响应中返回 **2 个 tool_call**（如 `add(1,2)` 和 `add(3,4)`），分别执行后**把两个 tool_result 一起**回填给模型，再让模型求和。提示：协议要求同一轮的所有 tool_result 放在 **同一**个 user 消息（多 content block）里。

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/message_entities.py`
- `/Users/xu/code/github/dify/api/core/agent/fc_agent_runner.py`
- `/Users/xu/code/github/dify/api/core/agent/cot_agent_runner.py`（非 FC 风格的对比实现）
- OpenAI Function Calling 官方文档：https://platform.openai.com/docs/guides/function-calling
- Anthropic Tool Use 官方文档：https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

---

**文档版本**：v1.0
**最后更新**：2026-07-13
