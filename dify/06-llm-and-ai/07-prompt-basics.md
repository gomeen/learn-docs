# 6.7 Prompt 工程基础：指令、上下文、输出格式

> 理解 Prompt 的三个基本要素（Instruction / Context / Output Format），能写出清晰可控的 Prompt 模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Prompt 的三个核心要素：指令、上下文、输出格式
- 用 XML 标签或结构化分块的方式组织多部分 Prompt
- 写出能稳定产出 JSON / Markdown / 列表的输出格式指令
- 理解 dify 高级 Prompt 模板（`advanced_prompt_templates.py`）的组成

## 📚 前置知识

- 了解 LLM 的基本调用方式（参见 `01-llm-overview.md`）
- Python 基础语法
- 06-llm-and-ai/12-prompt-template.md（推荐先看，了解 `{{}}` 变量语法）

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

1. **自然语言描述**："请用 JSON 格式返回，字段包括 name、age" —— 最简单但模型可能不严格遵守
2. **Schema 约束**：用 JSON Schema 描述输出结构（dify 的 `SYSTEM_STRUCTURED_OUTPUT_GENERATE`）
3. **工具调用**（Function Calling）：把输出绑定到函数签名，模型只能按签名填充

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
- 这是 RAG（检索增强生成）场景的标准范式

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

## 3. dify 仓库源码解读

### 3.1 dify 的标准 RAG 上下文模板

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py`
**核心代码**（行 1-3）：

```python
CONTEXT = "Use the following context as your learned knowledge, inside <context></context> XML tags.\n\n<context>\n{{#context#}}\n</context>\n\nWhen answer to user:\n- If you don't know, just say that you don't know.\n- If you don't know when you are not sure, ask for clarification.\nAvoid mentioning that you obtained the information from the context.\nAnd answer according to the language of the user's question.\n"
```

**解读**：
- 第 1 行：把上下文**明确地包在 `<context></context>` XML 标签中**——这是 dify RAG 流程的标准做法
- 关键指令 "If you don't know, just say that you don't know" —— 强制模型在知识不足时拒绝回答，**减少幻觉**
- "Avoid mentioning that you obtained the information from the context" —— 避免模型暴露"我看到了 XX 文档"这种元信息
- "answer according to the language of the user's question" —— **多语言自适应**，但要靠模型自行判断（容易出错，更稳的方案是显式传入语言变量）

### 3.2 完整 Chat App Prompt 配置

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py`
**核心代码**（行 4-14）：

```python
CHAT_APP_COMPLETION_PROMPT_CONFIG = {
    "completion_prompt_config": {
        "prompt": {
            "text": "{{#pre_prompt#}}\nHere are the chat histories between human and assistant, inside <histories></histories> XML tags.\n\n<histories>\n{{#histories#}}\n</histories>\n\n\nHuman: {{#query#}}\n\nAssistant: "
        },
        "conversation_histories_role": {"user_prefix": "Human", "assistant_prefix": "Assistant"},
    },
    "stop": ["Human:"],
}
```

**解读**：
- 第 5-7 行：完整呈现了**三要素 + 历史 + Query**的 Prompt 结构
  - `{{#pre_prompt#}}`（用户自定义的系统指令，相当于 Instruction）
  - `<histories>{{#histories#}}</histories>`（Context：历史对话）
  - `Human: {{#query#}}`（用户当前输入）
  - `Assistant: `（暗示模型开始回答）
- 第 8 行：定义历史对话中两个角色分别用 "Human" / "Assistant" 前缀
- 第 9 行：`stop: ["Human:"]` —— **告诉模型看到 "Human:" 就停止生成**，避免模型自己伪造用户输入
- **整体设计意图**：dify 用"补全式"（Completion）而非"对话式"（Chat）调用方式来获得对老模型（如 text-davinci-003）的兼容性，用 stop 序列模拟多轮对话

## 4. 关键要点总结

- Prompt 由**指令（Instruction）**、**上下文（Context）**、**输出格式（Output Format）**三大要素构成
- **XML 标签**是隔离上下文和指令的行业标准，能显著降低幻觉
- 输出格式要**明确到字段级别**，最好附 JSON Schema 或具体示例
- 指令要"动词开头、列出具体要求、给出反例"
- dify 的 RAG 模板用 `<context>` 标签包裹检索结果，并强制"不知道就说不知道"

## 5. 练习题

### 练习 1：基础（必做）

为"代码审查助手"写一个三要素 Prompt，要求：
- Instruction：检查 Python 代码的命名规范、类型注解、可能的空指针
- Context：传入用户提供的代码
- Output Format：JSON，包含 `issues` 数组（每项有 `line`、`severity`、`suggestion`）

### 练习 2：进阶

阅读 `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py` 的 `CHAT_APP_COMPLETION_PROMPT_CONFIG` 和 `CHAT_APP_CHAT_PROMPT_CONFIG`，对比两者：
- 哪种是"补全模式"？哪种是"对话模式"？
- 补全模式用 `stop: ["Human:"]` 的目的是什么？对话模式为什么不需要？

### 练习 3：挑战（选做）

设计一个"多语言翻译 + 风格迁移" Prompt，要求：
- 把英文翻译成中文
- 同时把翻译结果的"正式度"调整为"商务邮件"风格
- 输出 JSON：`{"translation": "...", "style_notes": "..."}`
- 用 XML 标签组织 Context（包含待翻译文本、风格要求文档）
- 添加"反例"指令，禁止直译、避免机翻味

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py`
- Anthropic Prompt Engineering Guide：https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- 06-llm-and-ai/12-prompt-template.md（Prompt 模板变量语法）
- 06-llm-and-ai/13-prompt-in-dify.md（dify 完整 Prompt 体系）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
