# 6.10 ReAct：Reasoning + Acting 让 LLM 学会"边想边做"

> 理解 ReAct（Reason + Act）范式的工作原理，能设计让 LLM 自主调用工具的 Prompt 模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ReAct 与 Chain-of-Thought 的区别
- 写出"思考-行动-观察"循环的 Prompt 模板
- 理解 ReAct 的终止条件和错误恢复机制
- 在 dify 工具调用场景中应用 ReAct 思想

## 📚 前置知识

- Prompt 三要素（详见 [Prompt 基础](./07-prompt-basics.md)）
- Few-Shot 示例（详见 [Few-Shot](./08-few-shot.md)）
- Tool Use / Function Calling 概念（详见 [Function Calling](./14-function-calling.md)；Agent 深化见 [Agent 概念](../07-rag-and-agent/18-agent-concepts.md)、[ReAct 深入](../07-rag-and-agent/19-react-deep-dive.md)）

## 1. 核心概念

### 1.1 什么是 ReAct？

**ReAct**（**Re**asoning + **Act**ing）由普林斯顿和 Google 的研究者在 2022 年提出，核心思想是让 LLM 在回答问题时**交替进行"思考"和"行动"**：

```
Thought 1: 我需要先查一下北京的天气
Action 1:  search_weather(city="北京")
Observation 1: 北京今天晴，25°C

Thought 2: 用户还想知道上海
Action 2:  search_weather(city="上海")
Observation 2: 上海今天多云，22°C

Thought 3: 我已经有了两地的天气，可以回答了
Action 3:  finish(answer="北京晴 25°C，上海多云 22°C")
```

每个循环 = **一次推理（Thought）** + **一次行动（Action）** + **观察结果（Observation）**。

### 1.2 ReAct vs Chain-of-Thought

| 维度 | Chain-of-Thought (CoT) | ReAct |
| --- | --- | --- |
| **推理依据** | 仅基于模型内部知识 | 可调用外部工具/API |
| **事实性** | 可能幻觉（编造） | 用工具获取真实数据，更可靠 |
| **复杂度** | 简单推理即可 | 需要管理工具调用循环 |
| **适用场景** | 数学题、逻辑题 | 需要实时数据、操作外部系统 |
| **出错成本** | 答案错误，影响小 | 工具调用可能产生副作用（发邮件、删数据） |

**简单说**：CoT 是"闭卷考试"，ReAct 是"开卷考试 + 可以查资料"。

### 1.3 ReAct 的标准 Prompt 模板

```text
Answer the following questions as best you can. You have access to the following tools:

{tool_descriptions}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {user_question}
Thought:
```

**关键设计**：
- **格式化约束**：用 `Thought:` / `Action:` / `Observation:` 这种"结构化标签"让模型稳定输出
- **循环提示**：`...` 暗示可以重复多次
- **终止信号**：`I now know the final answer` 让模型知道何时停止循环
- **Few-Shot 必备**：通常需要给 1-2 个完整示例让模型学会这种格式

### 1.4 ReAct 的终止与错误处理

**三种终止方式**：
1. **正常终止**：模型输出 `Final Answer:`
2. **最大步数**：超过 N 步（如 5 步）强制结束，防止无限循环
3. **错误终止**：工具调用失败 N 次后回退

**常见错误模式**：

| 错误 | 表现 | 处理 |
| --- | --- | --- |
| **幻觉工具名** | 模型调用了不存在的工具 | 在 Prompt 中严格列出可用工具，解析时校验 |
| **参数错误** | 调用工具时参数格式错 | 在 Prompt 中给出工具的 JSON Schema 示例 |
| **死循环** | 模型反复调用同一工具 | 限制最大步数；检测到重复时插入"你之前已经问过这个" |
| **中途放弃** | 模型认为无法完成 | 设置兜底 Prompt："如果工具都失败，请基于已有信息给出最佳猜测" |

## 2. 代码示例

### 2.1 简化版 ReAct 循环

```python
# 文件：example_react.py
# 模拟 ReAct 循环：用 2 个工具（计算器、查天气）回答"上海 5 天后温度 × 2 = ?"

import json
import re
from typing import Callable

# 模拟工具
def calculator(expression: str) -> str:
    """安全计算器"""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"

def get_weather(city: str, days_ahead: int) -> str:
    return "28"  # 模拟：上海 5 天后 28°C

TOOLS = {
    "calculator": calculator,
    "get_weather": get_weather,
}

# ReAct Prompt 模板
REACT_PROMPT = """Answer the question using the tools below. Use this format:

Question: <question>
Thought: <reasoning>
Action: <tool_name>
Action Input: <json_arguments>
Observation: <result>
... (repeat as needed)
Thought: I now know the final answer
Final Answer: <answer>

Available tools:
- calculator(expression: str) -> str
- get_weather(city: str, days_ahead: int) -> str

Begin!

Question: {question}
Thought:"""

def run_react(question: str, mock_llm=None, max_steps: int = 5) -> str:
    """模拟一个 ReAct 循环"""
    # 实际中这里要调用真实的 LLM；这里用预定义的"模型响应"演示
    # 为了简洁，这里手动定义期望的轨迹
    trace = [
        "I need to find the weather in Shanghai 5 days from now.",
        "Action: get_weather",
        'Action Input: {"city": "上海", "days_ahead": 5}',
        "Shanghai 5 days from now is 28°C.",
        "Now I need to multiply 28 by 2.",
        "Action: calculator",
        'Action Input: {"expression": "28 * 2"}',
        "Result is 56.",
        "I now know the final answer.\nFinal Answer: 28°C × 2 = 56",
    ]

    for step in range(max_steps):
        # 实际：response = mock_llm(...)
        # 实际：解析 response，提取 Action 和 Action Input
        # 实际：调用 TOOLS[action](**args)
        # 实际：把 Observation 拼回 prompt
        if "Final Answer:" in trace[step * 3]:
            return trace[step * 3].split("Final Answer:")[-1].strip()

    return "Exceeded max steps"

# 简化运行
question = "上海 5 天后的温度乘以 2 等于多少？"
print(f"Question: {question}")
print("Final answer: 28°C × 2 = 56")
```

**说明**：
- 第 27-40 行：标准的 ReAct Prompt 模板结构
- 第 47-58 行：核心循环——LLM 生成 → 解析 Action → 执行工具 → 把 Observation 拼回 Prompt → 再次调用 LLM
- 真实实现里"解析模型输出"是最复杂的部分（用正则或结构化输出）

### 2.2 Few-Shot ReAct 示例

```python
# 文件：example_react_few_shot.py
# Few-Shot ReAct —— 给模型 2 个完整示例，让它学会格式

FEW_SHOT_EXAMPLES = """
Example 1:
Question: 法国的首都是什么？
Thought: 我需要查一下法国的首都是什么。这是一个事实性问题。
Action: search_wikipedia
Action Input: {"query": "法国首都"}
Observation: 法国首都是巴黎。
Thought: 我已经知道答案了。
Final Answer: 巴黎

Example 2:
Question: 100 美元换成人民币是多少？
Thought: 我需要查汇率。这是一个计算任务。
Action: get_exchange_rate
Action Input: {"from": "USD", "to": "CNY"}
Observation: 1 USD = 7.25 CNY
Thought: 100 × 7.25 = 725
Action: calculator
Action Input: {"expression": "100 * 7.25"}
Observation: 725.0
Thought: 我已经知道答案了。
Final Answer: 100 美元约等于 725 人民币
"""

PROMPT = FEW_SHOT_EXAMPLES + "\n\nNow solve:\nQuestion: {question}\nThought:"

# 模型会模仿"Thought/Action/Observation/Final Answer"的格式继续生成
```

**说明**：
- 第 3-23 行：**完整的"思考-行动-观察"循环示例**，让模型学会"看到 Observation 后如何继续推理"
- 第 26 行：把 Few-Shot 示例 + 真实问题拼起来给模型
- Few-Shot 比 Zero-Shot 在 ReAct 上**效果显著更好**，因为格式很特殊

### 2.3 常见错误

```python
# ❌ 错误 1：没有终止条件，导致无限循环
def bad_react_loop(question):
    while True:
        response = llm(question)
        if "Final Answer" in response:
            return response
        # 忘记执行工具！模型会一直生成"Thought"但没真正行动

# ✅ 正确：每步都执行工具，把 Observation 拼回 Prompt
def good_react_loop(question, max_steps=5):
    prompt = build_prompt(question)
    for step in range(max_steps):
        response = llm(prompt)
        action, args = parse_action(response)
        if action == "finish":
            return args["answer"]
        observation = execute_tool(action, args)
        prompt += f"\nObservation: {observation}\nThought:"
    return "Exceeded max steps"

# ❌ 错误 2：工具描述不清晰
prompt_bad = "你可以用工具。"  # 模型不知道有哪些工具

# ✅ 正确：明确列出工具及其签名
prompt_good = """
Available tools:
- calculator(expression: str) -> str: 计算数学表达式
- search_wikipedia(query: str) -> str: 搜索维基百科
- get_weather(city: str) -> str: 查询天气
"""
```

## 3. dify 仓库源码解读

### 3.1 dify 工作流中的 Agent 节点

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`
**核心代码**（行 203-216）：

```python
@classmethod
def generate_suggested_questions_after_answer(
    cls,
    tenant_id: str,
    histories: str,
    *,
    instruction_prompt: str | None = None,
    model_config: object | None = None,
) -> Sequence[str]:
    output_parser = SuggestedQuestionsAfterAnswerOutputParser(instruction_prompt=instruction_prompt)
    format_instructions = output_parser.get_format_instructions()

    prompt_template = PromptTemplateParser(template="{{histories}}\n{{format_instructions}}\nquestions:\n")

    prompt = prompt_template.format({"histories": histories, "format_instructions": format_instructions})
```

**解读**：
- 第 14 行：先用 `SuggestedQuestionsAfterAnswerOutputParser` 拿到**结构化的输出格式说明**（相当于 ReAct 里的"工具说明"）
- 第 16 行：用 `PromptTemplateParser` 拼接 Prompt 模板
- 第 18 行：把历史对话和格式说明注入 Prompt
- **设计意图**：虽然 dify 这里的"建议问题"是单步任务（不是完整 ReAct 循环），但它**用 OutputParser 把输出格式固化**，相当于 ReAct 中"明确 Action 的格式"

### 3.2 dify 的代码生成：隐式 ReAct

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`
**核心代码**（行 588-623）：

```python
@classmethod
def generate_code(
    cls,
    tenant_id: str,
    args: RuleCodeGeneratePayload,
) -> CodeGenerateResultDict:
    if args.code_language == "python":
        prompt_template = PromptTemplateParser(PYTHON_CODE_GENERATOR_PROMPT_TEMPLATE)
    else:
        prompt_template = PromptTemplateParser(JAVASCRIPT_CODE_GENERATOR_PROMPT_TEMPLATE)

    prompt = prompt_template.format(
        inputs={
            "INSTRUCTION": args.instruction,
            "CODE_LANGUAGE": args.code_language,
        },
        remove_template_variables=False,
    )

    model_manager = ModelManager.for_tenant(tenant_id=tenant_id)
    model_instance = model_manager.get_model_instance(
        tenant_id=tenant_id,
        model_type=ModelType.LLM,
        provider=args.model_config_data.provider,
        model=args.model_config_data.name,
    )

    prompt_messages: list[PromptMessage] = [UserPromptMessage(content=prompt)]
    model_parameters = args.model_config_data.completion_params
    try:
        response: LLMResult = model_instance.invoke_llm(
            prompt_messages=list(prompt_messages), model_parameters=model_parameters, stream=False
        )

        generated_code = response.message.get_text_content()
        return {"code": generated_code, "language": args.code_language, "error": ""}
    ...
```

**解读**：
- 第 3-7 行：选择 Python 或 JavaScript 模板（不同的"工具"对应不同的 Prompt）
- 第 9-14 行：**通过模板变量注入用户指令**（`{{INSTRUCTION}}` 被替换为用户的自然语言需求）
- 第 25-31 行：调用 LLM 单步生成代码
- **隐式 ReAct 模式**：dify 实际上做了"自然语言 → 代码 → 执行 → 拿到结果"的两步循环：
  1. LLM 生成代码（ReAct 的"行动"）
  2. dify 在沙箱里 `exec` 这段代码（相当于"执行"）
  3. 把代码运行结果作为最终答案返回
- **与 ReAct 的区别**：dify 这里不需要"思考-行动-观察"循环，因为代码生成+执行是原子操作；但**核心理念相似**——LLM 生成可执行的"动作"，由外部系统执行

## 4. 关键要点总结

- **ReAct** = Reasoning + Acting，让 LLM 交替"思考"和"调用工具"
- 标准格式：`Thought → Action → Action Input → Observation → ... → Final Answer`
- Few-Shot 示例对 ReAct 至关重要（格式很特殊）
- 必须有**最大步数限制**，防止无限循环或工具滥用
- dify 的"代码生成+沙箱执行"模式是 ReAct 思想的应用：LLM 生成"动作"，系统执行

## 5. 练习题

### 练习 1：基础（必做）

写一个简化 ReAct 模板，要求：
- 工具：`get_stock_price(symbol: str) -> str`（模拟返回股价）
- 工具：`calculator(expression: str) -> str`
- 任务："苹果公司股价 × 100 = ?"
- 给出完整的 Thought/Action/Observation 轨迹

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py` 的 `generate_conversation_name` 方法（行 142-200），回答：
- 这个方法是 ReAct 吗？为什么？
- 它如何处理"模型输出不是合法 JSON"的情况？（看 `json.JSONDecodeError` 的处理）
- `query[:300] + "...[TRUNCATED]..." + query[-300:]` 这一步的设计意图是什么？

### 练习 3：挑战（选做）

为 dify 设计一个"工作流自动修复"功能：
- 输入：一个出错的工作流节点（包括错误信息、节点输入、节点配置）
- 工具：`read_workflow_node` / `modify_node_config` / `validate_workflow`
- 让 LLM 通过 ReAct 循环自动诊断并修复错误
- 写出 Prompt 模板和终止条件
- 考虑：如果修改 3 次仍未修复，应该怎么办？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`（dify 的 LLM 调用和 Prompt 注入）
- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py`
- Yao et al. 2022 "ReAct: Synergizing Reasoning and Acting in Language Models"（原始论文）
- LangChain ReAct Agent：https://python.langchain.com/docs/modules/agents/agent_types/react

---

**文档版本**：v1.0
**最后更新**：2026-07-13
