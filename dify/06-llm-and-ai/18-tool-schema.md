# 6.15 工具定义：JSON Schema

> 理解 LLM 工具的 JSON Schema 定义，能读懂 dify 中"工具参数 → LLM 可见的 schema"的转换流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 写出符合 LLM 工具调用规范的 JSON Schema
- 区分 `ToolParameter` 的 `form`（SCHEMA / FORM / LLM）对 schema 暴露的影响
- 理解 dify 的 `get_llm_parameters_json_schema` 怎么过滤出 LLM 可见的字段
- 能把任意业务函数包装成 LLM 可用的 tool 描述

## 📚 前置知识

- JSON Schema 基础（type / properties / required / enum；JSON 处理详见 [JSON](../01-fundamentals/20-json-processing.md)）
- Python Pydantic / TypedDict（详见 [Pydantic 基础](../02-backend/12-pydantic-basics.md)、[TypedDict](../01-fundamentals/09-typeddict.md)）
- Function Calling 协议（详见 [Function Calling](./17-function-calling.md)）

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

## 3. 关键要点总结

- 工具 schema = `name + description + JSON Schema parameters`
- **写好 description** 是工具被正确调用的关键（模型只能根据 description 判断何时调）
- dify 用 `form` 字段把参数分成 SCHEMA/FORM/LLM 三类，**只有 LLM 类的字段会进 schema**
- FILE/SECRET_INPUT 等类型在 schema 层就被过滤，避免敏感信息泄露给 LLM
- SELECT 类型会自动派生 `enum`，比纯文本描述更可靠
- 复杂类型（ARRAY/OBJECT）通过 `input_schema` 字段直接塞 raw JSON Schema

---

**文档版本**：v1.0
**最后更新**：2026-07-13
