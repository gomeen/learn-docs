# 6.8 Few-Shot Prompting：让模型"看例学样"

> 理解 Few-Shot（少样本）Prompting 的原理和最佳实践，能用示例教模型完成特定格式的输出。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Zero-Shot / One-Shot / Few-Shot 的区别
- 选择合适的示例数量和典型性
- 用示例控制模型的输出格式、风格、推理过程
- 识别 Few-Shot Prompting 的局限性和陷阱

## 📚 前置知识

- Prompt 三要素（详见 [Prompt 基础](./07-prompt-basics.md)）
- 变量替换语法（详见 [Prompt 模板](./12-prompt-template.md)）

## 1. 核心概念

### 1.1 什么是 Few-Shot Prompting？

**Few-Shot Prompting** 指在 Prompt 中**给模型几个完整的"输入→输出"示例**，让模型"照着葫芦画瓢"完成新任务。

```text
# 任务：把产品评论分类为正面/负面

示例 1：
评论：这个手机壳太漂亮了！
分类：正面

示例 2：
评论：用了三天就坏了，差评。
分类：负面

示例 3：
评论：物流很慢但是质量还行。
分类：中性

现在请分类：
评论：屏幕显示效果很棒，电池也很耐用。
分类：
```

模型会"模仿"前面的格式，输出"正面"。

### 1.2 Zero-Shot / One-Shot / Few-Shot 对比

| 类型 | 示例数量 | 适用场景 | 例子 |
| --- | --- | --- | --- |
| **Zero-Shot** | 0 个 | 模型已经"会"的任务（翻译、总结） | "翻译成英文：你好" |
| **One-Shot** | 1 个 | 需要特定格式，但格式比较简单 | 给 1 个分类示例 |
| **Few-Shot** | 2-10 个 | 需要复杂格式、特殊风格、推理链 | 给 3-5 个思维链示例 |
| **Many-Shot** | 10+ 个 | 复杂决策树、特殊领域 | 需要更长的上下文窗口 |

**经验法则**：
- 简单分类、抽取：3-5 个示例足够
- 复杂推理（CoT）：5-8 个示例效果最好
- 超过 20 个示例通常**收益递减**，反而浪费 token

### 1.3 选示例的三大原则

1. **典型性**：示例应该覆盖"标准"情况，不要选冷门边界案例
2. **多样性**：示例应该覆盖不同类别/风格，避免模型只学会一种模式
3. **简洁性**：每个示例的输入输出**尽量短**，长示例占用 token 但教学效果不一定好

```text
# ❌ 反例：示例过长且无变化
示例 1：评论：......（300 字）... 分类：......（100 字解释）...

# ✅ 正例：简短典型
示例 1：评论：质量差。分类：负面
示例 2：评论：快递快。分类：正面
```

### 1.4 Few-Shot 的局限性

| 局限 | 表现 | 应对 |
| --- | --- | --- |
| **Token 消耗大** | 5 个示例可能占 1K+ tokens | 只在必要时使用，避免重复 |
| **示例偏差** | 模型"过度模仿"示例的某个偶然特征 | 多样化示例，加入反例 |
| **长度限制** | 上下文窗口装不下太多示例 | 用 embedding 检索最相关的示例（动态 Few-Shot） |
| **格式固化** | 模型只会按示例格式输出 | 输出格式用 Schema 约束而非示例 |

## 2. 代码示例

### 2.1 动态 Few-Shot：分类情感倾向

```python
# 文件：example_few_shot.py
# 用 Few-Shot Prompting 实现情感分类

# 示例库（生产环境通常从数据库加载）
EXAMPLES = [
    ("这个手机壳太漂亮了！", "正面"),
    ("用了三天就坏了，差评。", "负面"),
    ("物流很慢但是质量还行。", "中性"),
    ("价格便宜，性价比高。", "正面"),
    ("客服态度差，等了两天没人理。", "负面"),
]

def build_few_shot_prompt(user_input: str) -> str:
    """构建 Few-Shot Prompt"""
    parts = ["请对用户评论进行情感分类，输出'正面'、'负面'或'中性'。\n"]

    # 动态选择最多 3 个示例
    parts.append("示例：")
    for input_text, label in EXAMPLES[:3]:
        parts.append(f"评论：{input_text}\n分类：{label}\n")

    # 真实请求
    parts.append(f"---\n现在请分类：\n评论：{user_input}\n分类：")
    return "\n".join(parts)

# 测试
prompt = build_few_shot_prompt("屏幕显示效果很棒，电池也很耐用。")
print(prompt)
# 模型大概率输出：正面
```

**说明**：
- 第 12-15 行：示例选择——这里用"前 3 个"，实际可基于关键词检索（动态 Few-Shot）
- 第 18 行：`---` 分隔示例和真实请求，让模型明确"现在轮到它答了"
- 第 19 行：问题+`分类：`提示词，暗示模型"接着写"

### 2.2 Chain-of-Thought（CoT）Few-Shot

```python
# 文件：example_cot_few_shot.py
# 带推理链的 Few-Shot —— 适合数学、逻辑题

EXAMPLES_WITH_REASONING = [
    {
        "q": "小明有 5 个苹果，吃了 2 个，又买了 3 个，现在有几个？",
        "a": "小明一开始有 5 个。吃了 2 个后剩 3 个。又买了 3 个，3 + 3 = 6。所以现在有 6 个苹果。",
    },
    {
        "q": "一本书原价 100 元，打 8 折后再用 10 元优惠券，实付多少？",
        "a": "原价 100 元。打 8 折后是 100 × 0.8 = 80 元。用 10 元优惠券后是 80 - 10 = 70 元。所以实付 70 元。",
    },
]

def build_cot_prompt(question: str) -> str:
    parts = ["请一步步推理后回答数学问题。\n"]
    for ex in EXAMPLES_WITH_REASONING:
        parts.append(f"问题：{ex['q']}\n推理：{ex['a']}\n")
    parts.append(f"---\n问题：{question}\n推理：")
    return "\n".join(parts)

# 测试
prompt = build_cot_prompt("一个水池有两根管子，A 管 4 小时注满，B 管 6 小时放空，同时打开多久注满？")
print(prompt)
```

**说明**：
- 第 5-13 行：**关键技巧是示例里写明"推理步骤"** 而不是直接给答案
- 模型的"推理"可以是它自己编造的（不一定对），但**过程展示出来**能极大提高最终答案的准确率
- CoT 在 GPT-3 论文中被首次提出，是 Few-Shot 的"高阶玩法"

### 2.3 常见错误

```python
# ❌ 错误 1：示例带偏见（"模板"）
examples_bad = [
    ("产品质量差", "差评"),
    ("服务态度差", "差评"),
    ("包装很糟糕", "差评"),
]
# 模型会学到"只要是负面词都算差评"，对模糊案例判断失误

# ❌ 错误 2：示例太长，浪费 token
example_bad_long = (
    "请看这条评论：'我今天买了这个产品，用了一天后感觉非常棒，屏幕清晰，电池耐用，"
    "手感也好，总之非常满意，五颗星！'，请分析它表达了什么情感，"
    "这种情感在心理学上属于什么范畴，在商业评论中通常代表什么意义...分类是：正面"
)
# 30 字的输入却配 100 字的解释，模型只学到"啰嗦"

# ✅ 正确做法
examples_good = [
    ("质量差", "负面"),
    ("物流快", "正面"),
    ("还行吧", "中性"),  # 边界案例
]
```

## 3. dify 仓库源码解读

### 3.1 dify 的代码生成 Prompt 模板

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/prompts.py`
**核心代码**（行 23-64）：

```python
PYTHON_CODE_GENERATOR_PROMPT_TEMPLATE = (
    "You are an expert programmer. Generate code based on the following instructions:\n\n"
    "Instructions: {{INSTRUCTION}}\n\n"
    "Write the code in {{CODE_LANGUAGE}}.\n\n"
    "Please ensure that you meet the following requirements:\n"
    "1. Define a function named 'main'.\n"
    "2. The 'main' function must return a dictionary (dict).\n"
    "3. You may modify the arguments of the 'main' function, but include appropriate type hints.\n"
    "4. The returned dictionary should contain at least one key-value pair.\n\n"
    "5. You may ONLY use the following libraries in your code: \n"
    "- json\n"
    "- datetime\n"
    "- math\n"
    "...\n\n"
    "Example:\n"
    "def main(arg1: str, arg2: int) -> dict:\n"
    "    return {\n"
    '        "result": arg1 * arg2,\n'
    "    }\n\n"
    "IMPORTANT:\n"
    "- Provide ONLY the code without any additional explanations, comments, or markdown formatting.\n"
    "- DO NOT use markdown code blocks (``` or ``` python). Return the raw code directly.\n"
    "- The code should start immediately after this instruction, without any preceding newlines or spaces.\n"
    "- The code should be complete, functional, and follow best practices for {{CODE_LANGUAGE}}.\n\n"
    "- Always use the format return {'result': ...} for the output.\n\n"
    "Generated Code:\n"
)
```

**解读**：
- 第 1-6 行：指令部分（Instruction）—— 告诉模型"做专家程序员、写什么语言"
- 第 8-12 行：**5 条具体要求** —— 比单纯"请写好代码"更可控
- 第 14-21 行：**One-Shot 示例** —— 给出一个"main 函数返回字典"的标准模式
- 第 24-29 行：**反面指令**（IMPORTANT 段）—— 禁止 markdown、禁止注释、禁止多余文字
- 第 30 行："Always use the format `return {'result': ...}`" —— **固定输出 Schema**，下游解析时直接 `result` 字段取结果
- **整体设计**：dify 让用户在前端写自然语言需求，后端用这个模板把需求转成可在沙箱执行的 Python 代码，再用 `exec` 跑代码拿结果

### 3.2 dify 的对话标题生成 Prompt

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/prompts.py`
**核心代码**（行 2-21）：

```python
CONVERSATION_TITLE_PROMPT = """You are asked to generate a concise chat title by decomposing the user's input into two parts: "Intention" and "Subject".

1. Detect Input Language
Automatically identify the language of the user's input (e.g. English, Chinese, Italian, Español, Arabic, Japanese, French, and etc.).

2. Generate Title
- Combine Intention + Subject into a single, as-short-as-possible phrase.
- The title must be natural, friendly, and in the same language as the input.
- If the input is a direct question to the model, you may add an emoji at the end.

3. Output Format
Return **only** a valid JSON object with these exact keys and no additional text:
{
  "Language Type": "<Detected language>",
  "Your Reasoning": "<Brief explanation in that language>",
  "Your Output": "<Intention + Subject>"
}

User Input:
"""
```

**解读**：
- 第 1-7 行：把任务**拆解为 3 步**（识别语言 → 生成标题 → 输出 JSON）—— 这是隐式的 Chain-of-Thought
- 第 9-16 行：**明确 JSON 输出 Schema**，且用 "Language Type" / "Your Reasoning" / "Your Output" 这种"自描述"字段名
- 第 18 行：`User Input:` 后留空，让用户 query 拼接到 Prompt 末尾
- **注意**：这个 Prompt 没有给具体示例（Zero-Shot），靠的是"明确的步骤拆解 + 严格的 JSON Schema"——当任务定义清晰时，Zero-Shot 也可以很稳

## 4. 关键要点总结

- **Few-Shot** = 在 Prompt 中给 2-10 个"输入→输出"示例，让模型"照着做"
- 示例要**典型、多样、简洁**，避免长篇大论
- **Chain-of-Thought Few-Shot**（带推理过程的示例）能极大提升数学/逻辑题准确率
- 当 Schema 清晰时，Zero-Shot 也可能比 Few-Shot 更好（节省 token）
- dify 的代码生成、对话标题生成都是**指令 + 约束 + Schema** 的范式

## 5. 练习题

### 练习 1：基础（必做）

写一个 Few-Shot Prompt，要求把英文产品名翻译成"地道的中文营销文案"。给 3 个示例，每个示例的"输入→输出"控制在 50 字以内。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/llm_generator/prompts.py` 中的 `PYTHON_CODE_GENERATOR_PROMPT_TEMPLATE`，回答：
- 哪个部分是 **Instruction**？哪个是 **One-Shot 示例**？哪个是 **反例约束**？
- 如果把第 53-56 行的 `Example` 删掉，模型还能按要求输出吗？为什么？
- 如果只给 "main 函数返回字典" 这一点约束（去掉第 14-21 行的库限制），可能会出什么问题？

### 练习 3：挑战（选做）

为 dify 的"工作流指令建议"功能设计 Few-Shot Prompt。需求：
- 输入：用户当前工作流已有的节点列表（如 `["知识库检索", "LLM", "HTTP 请求"]`）
- 输出：3-5 条"可以尝试的应用场景"（如"基于知识库的客服问答"）
- 给出 3 个高质量示例，**每个示例的"输入"长度接近真实场景**（约 3-4 个节点）
- 思考：为什么用"节点列表→场景"而不是"场景→节点列表"？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/llm_generator/prompts.py`（dify 的 Few-Shot 范式）
- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py`
- Brown et al. 2020 "Language Models are Few-Shot Learners"（GPT-3 论文，Few-Shot 概念首次提出）
- Wei et al. 2022 "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"

---

**文档版本**：v1.0
**最后更新**：2026-07-13
