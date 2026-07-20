# 6.10 ReAct：Reasoning + Acting 让 LLM 学会"边想边做"

> 理解 ReAct（Reason + Act）范式的工作原理，能设计让 LLM 自主调用工具的 Prompt 模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ReAct 与 Chain-of-Thought 的区别
- 写出"思考-行动-观察"循环的 Prompt 模板
- 理解 ReAct 的终止条件和错误恢复机制
- 在 dify 工具调用场景中应用 ReAct 思想

## 📚 前置知识

- Prompt 三要素（详见 [Prompt 基础](./08-prompt-basics.md)）
- Few-Shot 示例（详见 [Few-Shot](./09-few-shot.md)）
- Tool Use / Function Calling 概念（详见 [Function Calling](./17-function-calling.md)；Agent 深化见 [Agent 概念](../07-rag-and-agent/21-agent-concepts.md)、[ReAct 深入](../07-rag-and-agent/22-react-deep-dive.md)）

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

## 3. 关键要点总结

- **ReAct** = Reasoning + Acting，让 LLM 交替"思考"和"调用工具"
- 标准格式：`Thought → Action → Action Input → Observation → ... → Final Answer`
- Few-Shot 示例对 ReAct 至关重要（格式很特殊）
- 必须有**最大步数限制**，防止无限循环或工具滥用
- dify 的"代码生成+沙箱执行"模式是 ReAct 思想的应用：LLM 生成"动作"，系统执行

---

**文档版本**：v1.0
**最后更新**：2026-07-13
