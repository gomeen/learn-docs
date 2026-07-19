# 6.15 工具定义：JSON Schema

> 理解 LLM 工具的 JSON Schema 定义，能读懂 dify 中"工具参数 → LLM 可见的 schema"的转换流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 写出符合 LLM 工具调用规范的 JSON Schema
- 区分 `ToolParameter` 的 `form`（SCHEMA / FORM / LLM）对 schema 暴露的影响
- 理解 dify 的 `get_llm_parameters_json_schema` 怎么过滤出 LLM 可见的字段
- 能把任意业务函数包装成 LLM 可用的 tool 描述

## 📚 前置知识

- JSON Schema 基础（type / properties / required / enum；JSON 处理详见 [JSON](../01-fundamentals/27-json-processing.md)）
- Python Pydantic / TypedDict（详见 [Pydantic 基础](../02-backend/15-pydantic-basics.md)、[TypedDict](../01-fundamentals/08-typeddict.md)）
- Function Calling 协议（详见 [Function Calling](./14-function-calling.md)）

## 1. 核心概念

### 1.1 工具 schema 在协议中的位置

工具的 JSON Schema 是"模型能看到的契约"，它必须：

```mermaid
graph LR
    A[业务函数] --> B[ToolParameter 列表<br/>声明每个字段]
    B --> C[get_llm_parameters_json_schema<br/>过滤 + 转换]
    C --> D[JSON Schema 字典]
    D --> E[PromptMessageTool.parameters]
    E --> F[OpenAI: tools[].function.parameters<br/>Anthropic: tools[].input_schema]
    F --> G[LLM 看到契约]
    G --> H[模型返回 tool_call]
    H --> I[客户端按 schema 校验 + 执行]
```

每个工具包含三部分：
1. **`name`**：调用时使用的标识符（OpenAI 限制 `^[a-zA-Z0-9_-]{1,64}$`）
2. **`description`**：模型判断"什么时候该调"的唯一线索
3. **`parameters`**：JSON Schema 描述参数结构

### 1.2 三类参数 form

dify 内部把参数分成三种 form（见 `core/tools/entities/tool_entities.py` 第 329-332 行）：

```python
class ToolParameterForm(StrEnum):
    SCHEMA = auto()  # should be set while adding tool
    FORM = auto()    # should be set before invoking tool
    LLM = auto()     # will be set by LLM
```

| Form | 含义 | 是否暴露给 LLM | 典型例子 |
| --- | --- | --- | --- |
| `SCHEMA` | 工具自带的固定结构 | 否 | 工具名、URL 模板 |
| `FORM` | 用户在 UI 填一次后固定 | 否 | API Key、用户名 |
| `LLM` | 模型根据用户输入动态填 | **是** | 城市名、查询关键词 |

`get_llm_parameters_json_schema` 只把 `form == LLM` 的字段暴露给模型；`FORM` 字段由前端/调用方预先填好，不出现在 schema 里。

### 1.3 JSON Schema 最小可工作集

下面是一个最小可用的天气查询工具 schema：

```json
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string",
      "description": "城市英文名，例如 'Beijing'"
    },
    "unit": {
      "type": "string",
      "enum": ["celsius", "fahrenheit"],
      "description": "温度单位"
    }
  },
  "required": ["city"]
}
```

关键约束：
- 顶层必须是 `type: "object"`
- `properties` 里每个字段用 type 描述
- `required` 数组列出**必填**字段
- `enum` 限制取值范围（强烈推荐，比 description 里写"只能是 c/f"靠谱）

## 2. 代码示例

### 2.1 手写一个工具 + JSON Schema

```python
# 文件：example_tool_schema.py
import json
import jsonschema

# 1. 工具的 JSON Schema（这就是给模型看的契约）
weather_schema = {
    "name": "get_weather",
    "description": "查询指定城市的当前天气。仅支持英文城市名。",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市英文名，例如 'Beijing', 'Tokyo'",
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "温度单位；默认 celsius",
            },
            "include_forecast": {
                "type": "boolean",
                "description": "是否返回未来 3 天预报",
                "default": False,
            },
        },
        "required": ["city"],
        "additionalProperties": False,
    },
}

# 2. 客户端实现
def get_weather(city: str, unit: str = "celsius", include_forecast: bool = False) -> dict:
    return {
        "city": city,
        "temperature": 22,
        "unit": unit,
        "forecast": ["sunny", "cloudy", "rain"] if include_forecast else None,
    }

# 3. 模拟模型返回的 tool_call
model_call = {
    "id": "call_abc",
    "function": {
        "name": "get_weather",
        "arguments": json.dumps({"city": "Beijing", "unit": "celsius"}),
    }
}

# 4. 用 schema 校验模型返回的参数
args = json.loads(model_call["function"]["arguments"])
jsonschema.validate(args, weather_schema["parameters"])  # 合法
print("校验通过：", args)

# 5. 执行
result = get_weather(**args)
print("结果：", result)
```

**说明**：
- 第 3-4 行：description 写得越具体，模型判断得越准
- 第 7-21 行：`additionalProperties: False` 显式拒绝未声明字段（强烈建议加上）
- 第 30-31 行：用 `jsonschema.validate` 在执行前校验，捕获模型幻觉
- 第 33 行：只有通过校验的 `args` 才进入业务函数

### 2.2 常见错误：把后端密钥写进 schema

```python
# ❌ 错误：把数据库连接串等机密信息写到工具 schema
api_key_schema = {
    "name": "query_db",
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
            "db_password": {"type": "string", "description": "数据库密码"},  # 灾难
        },
        "required": ["sql", "db_password"],
    }
}
# 问题：模型看到 db_password 字段，可能在对话中"创造"虚假的密码；密码也随每次请求进 LLM token

# ✅ 正确：敏感信息放 FORM form，由用户在 dify UI 配一次，不进 schema
# LLM 只能看到 sql
```

## 3. dify 仓库源码解读

### 3.1 dify 内部的 ToolParameter 实体

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/entities/tool_entities.py`
**核心代码**（行 293-340）：

```python
class ToolParameter(PluginParameter):
    """
    Overrides type
    """

    class ToolParameterType(StrEnum):
        STRING = PluginParameterType.STRING
        NUMBER = PluginParameterType.NUMBER
        BOOLEAN = PluginParameterType.BOOLEAN
        SELECT = PluginParameterType.SELECT
        SECRET_INPUT = PluginParameterType.SECRET_INPUT
        FILE = PluginParameterType.FILE
        FILES = PluginParameterType.FILES
        APP_SELECTOR = PluginParameterType.APP_SELECTOR
        MODEL_SELECTOR = PluginParameterType.MODEL_SELECTOR
        ARRAY = MCPServerParameterType.ARRAY
        OBJECT = MCPServerParameterType.OBJECT
        # ...

    class ToolParameterForm(StrEnum):
        SCHEMA = auto()
        FORM = auto()
        LLM = auto()

    type: ToolParameterType = Field(..., description="The type of the parameter")
    human_description: I18nObject | None = None
    form: ToolParameterForm = Field(..., description="The form of the parameter, schema/form/llm")
    llm_description: str | None = None
    # MCP object/array 用这个字段存 raw JSON schema
    input_schema: dict[str, Any] | None = None
```

**解读**：
- 第 4-19 行：`ToolParameterType` 列举了所有合法类型，包括 `FILE`/`SECRET_INPUT`/`APP_SELECTOR` 等 dify 特有类型
- 第 21-25 行：**核心字段 `form`**：决定这个参数是否会被传给 LLM
- 第 27-29 行：`llm_description` 是给模型看的描述；`human_description` 是给前端用户看的（多语言）
- 第 30 行：`input_schema` 是给 `OBJECT`/`ARRAY` 等复杂类型用——存 raw JSON Schema

### 3.2 把 ToolParameter 列表转成 LLM 可见的 JSON Schema

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/__base/tool.py`
**核心代码**（行 166-215）：

```python
def get_llm_parameters_json_schema(
    self,
    conversation_id: str | None = None,
    app_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Build the model-visible JSON schema from effective tool parameters.

    Hidden/manual parameters stay available for invocation preparation on the
    API side, but are intentionally omitted from the LLM-facing schema.
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for parameter in self.get_merged_runtime_parameters(
        conversation_id=conversation_id,
        app_id=app_id,
        message_id=message_id,
    ):
        if parameter.form != ToolParameter.ToolParameterForm.LLM:
            continue

        if parameter.type in {
            ToolParameter.ToolParameterType.SYSTEM_FILES,
            ToolParameter.ToolParameterType.FILE,
            ToolParameter.ToolParameterType.FILES,
        }:
            continue

        parameter_schema: dict[str, Any] = (
            {
                "type": parameter.type.as_normal_type(),
                "description": parameter.llm_description or "",
            }
            if parameter.input_schema is None
            else deepcopy(parameter.input_schema)
        )
        parameter_schema.setdefault("description", parameter.llm_description or "")

        if parameter.type == ToolParameter.ToolParameterType.SELECT and parameter.options:
            parameter_schema["enum"] = [option.value for option in parameter.options]

        schema["properties"][parameter.name] = parameter_schema
        if parameter.required:
            schema["required"].append(parameter.name)

    return schema
```

**解读**：
- 第 17-21 行：构造空 schema，固定顶层 `type: "object"`
- 第 23-26 行：调用 `get_merged_runtime_parameters` 拿到合并后的"实际参数"（包含运行时注入）
- 第 27-28 行：**关键过滤**——`form != LLM` 的参数被跳过，**不会**进入 schema
- 第 30-33 行：FILE/FILES 类型也被排除（文件由 dify 内部处理，不让 LLM 看见文件名变量）
- 第 35-40 行：构造单个字段的 schema：基础类型用 `as_normal_type()` 转 `string/number/boolean`；复杂类型（`input_schema` 不为空）直接深拷贝其 JSON Schema
- 第 42-43 行：**SELECT 类型**自动添加 `enum`，比 description 限制更可靠
- 第 45-46 行：填入 `properties`，按 `required` 标志累加到 `required` 数组
- **整体设计意图**：把所有业务参数（API key、用户名等 FORM 字段）在 schema 层就过滤掉，模型**永远**只看到 LLM 字段，从而避免机密泄露

### 3.3 fc_agent_runner 把 schema 喂给 LLM

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/base_agent_runner.py`
**核心代码**（行 138-156）：

```python
def _convert_tool_to_prompt_message_tool(self, tool: AgentToolEntity) -> tuple[PromptMessageTool, Tool]:
    """
    convert tool to prompt message tool
    """
    tool_entity = ToolManager.get_agent_tool_runtime(
        tenant_id=self.tenant_id,
        app_id=self.app_config.app_id,
        agent_tool=tool,
        user_id=self.user_id,
        invoke_from=self.application_generate_entity.invoke_from,
    )
    assert tool_entity.entity.description
    message_tool = PromptMessageTool(
        name=tool.tool_name,
        description=tool_entity.entity.description.llm,
        parameters=tool_entity.get_llm_parameters_json_schema(),
    )

    return message_tool, tool_entity
```

**解读**：
- 第 9-14 行：先 `ToolManager.get_agent_tool_runtime` 拿到运行时实体（已注入凭据）
- 第 16-20 行：构造 `PromptMessageTool`：
  - `name`：工具名
  - `description`：从 `ToolEntity.description.llm` 取（即"给模型看的描述"）
  - `parameters`：调 `get_llm_parameters_json_schema` 拿到过滤后的 schema
- **整体设计意图**：这一步是"工具 → 模型"的关键桥接——把运行时实体里的"业务参数"和"LLM 参数"分开处理

## 4. 关键要点总结

- 工具 schema = `name + description + JSON Schema parameters`
- **写好 description** 是工具被正确调用的关键（模型只能根据 description 判断何时调）
- dify 用 `form` 字段把参数分成 SCHEMA/FORM/LLM 三类，**只有 LLM 类的字段会进 schema**
- FILE/SECRET_INPUT 等类型在 schema 层就被过滤，避免敏感信息泄露给 LLM
- SELECT 类型会自动派生 `enum`，比纯文本描述更可靠
- 复杂类型（ARRAY/OBJECT）通过 `input_schema` 字段直接塞 raw JSON Schema

## 5. 练习题

### 练习 1：基础（必做）

为一个"汇率换算"工具写 JSON Schema：
- 必需参数：`from_currency`（3 字母枚举：`USD/CNY/EUR/JPY`）、`amount`（数字，> 0）
- 可选参数：`to_currency`（默认 `CNY`）、`include_chart`（布尔，默认 false）

写完后用 `jsonschema.validate` 校验两个示例：
- `{"from_currency":"USD","amount":100}` ✓
- `{"from_currency":"usd","amount":-5}` ✗（应当失败：枚举 + 数值范围）

### 练习 2：进阶

阅读 `core/tools/__base/tool.py` 第 127-164 行 `get_merged_runtime_parameters`，解释：
- 什么是 "runtime parameters"？它们从哪来？
- 为什么要 deepcopy？
- `parameter_indexes` 字典的用途是什么？

### 练习 3：挑战（选做）

仿照 dify 的 `get_llm_parameters_json_schema`，写一个 `filter_form_params(params, form)` 函数：
- 输入：`params: list[ToolParameter]`、`form: ToolParameterForm`
- 输出：仅保留 `form` 匹配的参数
- 思考：如果同一工具既有 LLM 字段又有 SECRET_INPUT 字段，调用方需要哪一层来脱敏？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/entities/tool_entities.py`
- `/Users/xu/code/github/dify/api/core/tools/__base/tool.py`
- `/Users/xu/code/github/dify/api/core/agent/base_agent_runner.py`
- JSON Schema 官方规范：https://json-schema.org/
- OpenAI Function Calling 文档：https://platform.openai.com/docs/guides/function-calling
- Anthropic Tool Use 文档：https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

---

**文档版本**：v1.0
**最后更新**：2026-07-13
