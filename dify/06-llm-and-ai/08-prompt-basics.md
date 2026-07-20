# 6.7 Prompt 工程基础：指令、上下文、输出格式

> 理解 Prompt 的三个基本要素（Instruction / Context / Output Format），能写出清晰可控的 Prompt 模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Prompt 的三个核心要素：指令、上下文、输出格式
- 用 XML 标签或结构化分块的方式组织多部分 Prompt
- 写出能稳定产出 JSON / Markdown / 列表的输出格式指令
- 理解 dify 高级 Prompt 模板（`advanced_prompt_templates.py`）的组成

## 📚 前置知识

- 了解 LLM 的基本调用方式（详见 [主流大模型对比](./01-llm-overview.md)）
- Python 基础语法
- Prompt 模板变量语法（详见 [Prompt 模板](./14-prompt-template.md)）

## 1. 核心概念

### 1.1 Prompt 三要素

一个**有效的 Prompt** 由三类内容组成，缺一不可：

| 要素 | 作用 | 常见位置 | 缺失的后果 |
| --- | --- | --- | --- |
| **Instruction（指令）** | 告诉模型"做什么、怎么做" | Prompt 头部 / System 消息 | 模型自由发挥，结果不可控 |
| **Context（上下文）** | 提供模型完成任务所需的背景信息 | 中间段落、`<context>` 标签 | 模型幻觉、答非所问 |
| **Output Format（输出格式）** | 指定模型回答的"形状" | Prompt 尾部、JSON Schema | 输出难以解析，下游处理困难 |

```
┌────────────────────────────────────────────┐
│ Instruction（指令）                          │  ← "请基于以下上下文回答问题"
├────────────────────────────────────────────┤
│ Context（上下文）                            │  ← <context> ... </context>
├────────────────────────────────────────────┤
│ Question（用户问题）                          │  ← "什么是 RAG？"
├────────────────────────────────────────────┤
│ Output Format（输出格式）                    │  ← "请用 JSON 回答，schema: ..."
└────────────────────────────────────────────┘
```

### 1.2 指令的设计原则

**好的指令要满足 4 个要求**：
1. **明确任务**：动词开头（"总结"、"翻译"、"分类"），不要用"我想知道..."
2. **限定范围**：说明哪些情况下该答、哪些不该答
3. **指定风格**：语气、长度、专业程度
4. **给出反例**（可选）：禁止出现的输出模式

**对比示例**：

```text
# ❌ 模糊指令
帮我看看这段代码

# ✅ 明确指令
请审查以下 Python 代码，重点检查：
1. 是否有空指针/None 引用风险
2. 函数参数是否有类型注解
3. 是否有重复的逻辑可以抽取
请逐项输出，每项标注"通过"或"建议修改"以及具体位置。
```

### 1.3 上下文的注入方式

**三种常见的上下文注入模式**：

| 方式 | 适用场景 | 优缺点 |
| --- | --- | --- |
| **直接拼接** | 上下文很短（< 1K tokens） | 简单，但模型容易把上下文和指令混淆 |
| **XML 标签包裹** | 检索增强（RAG）、多文档 | 模型能清晰区分"指令"和"数据"，是行业最佳实践 |
| **多轮对话** | 需要追问、改写 | 自然，但上下文窗口受限 |

**XML 标签模板**：

```xml
<context>
{{#context#}}
</context>

<question>
{{#query#}}
</question>

请基于 <context> 中的信息回答 <question>，不要使用其他知识。
```

这种写法让模型"知道哪些是事实、哪些是问题、哪些是格式要求"，极大降低幻觉。

### 1.4 输出格式控制

**三种粒度**：

1. **自然语言描述**："请用 JSON 格式返回，字段包括 name、age" —— 最简单但模型可能不严格遵守（JSON 处理详见 [JSON](../01-fundamentals/20-json-processing.md)）
2. **Schema 约束**：用 JSON Schema 描述输出结构（dify 的 `SYSTEM_STRUCTURED_OUTPUT_GENERATE`）
3. **工具调用**（Function Calling，详见 [Function Calling](./17-function-calling.md)）：把输出绑定到函数签名，模型只能按签名填充

```text
请按以下 JSON Schema 输出：
{
  "name": "string",
  "age": "number",
  "hobbies": ["string"]
}
仅输出 JSON，不要包含解释文字。
```

## 2. 代码示例

### 2.1 完整的三要素 Prompt 模板

```python
# 文件：example_prompt_basics.py
# 演示"指令 + 上下文 + 输出格式"三要素的标准组织方式

prompt_template = """
<instruction>
你是一个客服助手。请根据 <context> 中的产品文档回答用户问题。
要求：
1. 只使用 <context> 中出现的信息，不要编造
2. 如果 <context> 中没有答案，回答"我不清楚"
3. 回答要简洁，不超过 100 字
</instruction>

<context>
{{#context#}}
</context>

<question>
{{#query#}}
</question>

<output_format>
请按以下 JSON 格式输出：
{
  "answer": "你的回答",
  "confidence": "high | medium | low",
  "source": "引用的文档片段原文"
}
</output_format>
"""

# 实际数据注入（dify 的 PromptTemplateParser 风格）
def render(template: str, context: str, query: str) -> str:
    return template.replace("{{#context#}}", context).replace("{{#query#}}", query)

final_prompt = render(
    prompt_template,
    context="Dify 是一个开源 LLM 应用平台。核心功能包括可视化工作流编排、知识库管理、Agent 构建。",
    query="Dify 有什么功能？"
)
print(final_prompt)
```

**说明**：
- 第 7-12 行：明确指令（做什么、不能做什么）
- 第 14-16 行：用 `<context>` 标签把检索结果隔离，避免模型直接当指令执行
- 第 24-30 行：明确 JSON 输出结构，下游可直接 `json.loads()` 解析
- 这是 RAG（检索增强生成，详见 [RAG 概览](../07-rag-and-agent/01-rag-overview.md)）场景的标准范式

### 2.2 常见错误

```python
# ❌ 错误 1：指令和上下文混在一起
bad_prompt = f"请回答问题：{context}\n问题：什么是 Dify？"
# 问题：模型可能误把"context"的开头当作指令的一部分

# ❌ 错误 2：输出格式不明确
bad_prompt2 = "请列出 Dify 的核心功能"
# 问题：模型可能用 bullet 列表、可能用表格、可能用一段话，下游难以解析

# ❌ 错误 3：上下文缺少边界，模型可能引用未提供的知识
bad_prompt3 = "请基于下面的信息回答：Dify 是一个 LLM 应用平台"
# 问题：模型可能回答"它还支持 XXX..."，但 XXX 不在提供的上下文里
```

```python
# ✅ 正确做法：指令、上下文、格式清晰分离
good_prompt = """
<instruction>
你是一个严格基于上下文回答问题的助手。
不要使用 <context> 之外的知识。
</instruction>

<context>
{{#context#}}
</context>

<question>{{#query#}}</question>

<output_format>
仅返回 JSON: {"answer": "string", "confidence": "high|medium|low"}
</output_format>
"""
```

## 3. 关键要点总结

- Prompt 由**指令（Instruction）**、**上下文（Context）**、**输出格式（Output Format）**三大要素构成
- **XML 标签**是隔离上下文和指令的行业标准，能显著降低幻觉
- 输出格式要**明确到字段级别**，最好附 JSON Schema 或具体示例
- 指令要"动词开头、列出具体要求、给出反例"
- dify 的 RAG 模板用 `<context>` 标签包裹检索结果，并强制"不知道就说不知道"

---

**文档版本**：v1.0
**最后更新**：2026-07-13
