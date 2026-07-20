# 7.4.2 ReAct 模式深入

> 深入理解 ReAct（Reasoning + Acting）模式，看懂 dify 的 Chain-of-Thought Agent 实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ReAct 的核心思想：Thought → Action → Observation
- 写出标准的 ReAct Prompt
- 对比 ReAct 与 Function Call 两种 Agent 实现
- 看懂 dify 中 `CotAgentRunner` 的代码

## 📚 前置知识

- [Agent 概念](./21-agent-concepts.md)
- Prompt 与 ReAct 入门（详见 [Prompt 基础](../06-llm-and-ai/08-prompt-basics.md)、[ReAct](../06-llm-and-ai/11-react.md)）
- Function Calling 对比（详见 [Function Calling](../06-llm-and-ai/17-function-calling.md)）

## 1. 核心概念

### 1.1 什么是 ReAct？

ReAct（Reason + Act）是一种 Agent 推理模式，通过让 LLM **显式输出思考过程**来提升决策能力：

```
Thought 1: 用户问 Dify 是什么，我需要先搜索
Action 1: search_knowledge("Dify 是什么")
Observation 1: Dify 是开源 LLM 平台...
Thought 2: 信息足够，可以回答了
Action 2: Finish(answer="Dify 是...")
```

### 1.2 ReAct vs Function Call

| 维度 | ReAct | Function Call |
|------|-------|---------------|
| 输出格式 | 文本（Thought/Action/Observation） | 结构化 JSON（tool_calls） |
| 模型要求 | 任何 chat 模型 | 必须支持 function calling |
| 可读性 | 高（看到思考过程） | 低（结构化） |
| 可靠性 | 依赖解析（可能解析失败） | 模型原生支持，可靠 |

### 1.3 ReAct 的 Prompt 结构

```
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
```

## 2. 代码示例

### 2.1 简单的 ReAct Prompt

```python
REACT_PROMPT = """Answer the following questions as best you can. You have access to the following tools:

{tool_descriptions}

Use the following format:

Question: the input question
Thought: think about what to do
Action: tool name from [{tool_names}]
Action Input: input for the tool
Observation: result of the tool
Thought: I now know the final answer
Final Answer: the answer

Begin!

Question: {query}
Thought:"""


def build_react_prompt(query: str, tools: list) -> str:
    tool_descriptions = "\n".join(
        f"- {t['name']}: {t['description']}" for t in tools
    )
    tool_names = ", ".join(t["name"] for t in tools)
    return REACT_PROMPT.format(
        query=query,
        tool_descriptions=tool_descriptions,
        tool_names=tool_names,
    )
```

### 2.2 ReAct 输出解析器

```python
import re
from typing import Tuple


def parse_react_output(text: str) -> Tuple[str, str, str]:
    """解析 ReAct 输出，提取 Thought/Action/Action Input"""
    thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|$)", text, re.DOTALL)
    action_match = re.search(r"Action:\s*(.+?)(?=Action Input:|$)", text, re.DOTALL)
    action_input_match = re.search(r"Action Input:\s*(.+?)(?=Observation:|$)", text, re.DOTALL)

    thought = thought_match.group(1).strip() if thought_match else ""
    action = action_match.group(1).strip() if action_match else ""
    action_input = action_input_match.group(1).strip() if action_input_match else ""

    return thought, action, action_input


def parse_final_answer(text: str) -> str | None:
    """检查是否是 Final Answer"""
    match = re.search(r"Final Answer:\s*(.+?)$", text, re.DOTALL)
    return match.group(1).strip() if match else None
```

### 2.3 完整的 ReAct Agent 循环

```python
def react_agent_loop(query: str, tools: dict, llm, max_iter=5):
    """完整的 ReAct 循环"""
    prompt = build_react_prompt(query, list(tools.values()))
    scratchpad = ""

    for i in range(max_iter):
        # 1. LLM 生成 Thought/Action
        response = llm.invoke(prompt + scratchpad + "Thought:")
        scratchpad += f"Thought:{response}\n"

        # 2. 检查是否是最终答案
        final = parse_final_answer(response)
        if final:
            return final

        # 3. 解析 Action
        action, action_input = parse_action(response)
        if action not in tools:
            scratchpad += "Observation: 工具不存在\n"
            continue

        # 4. 执行 Action
        try:
            observation = tools[action].func(action_input)
        except Exception as e:
            observation = f"Error: {e}"

        scratchpad += f"Observation: {observation}\n"

    return "达到最大迭代次数"
```

### 2.4 常见错误：Thought 没有意义

```python
# ❌ 错误：Thought 只是无意义重复
# Thought: 我需要查一下
# Action: search
# Action Input: query

# ✅ 正确：Thought 体现推理过程
# Thought: 用户问 Dify 是什么，但我没把握，需要查知识库。
#          应该用 search_knowledge 工具，关键词用"dify"。
# Action: search_knowledge
# Action Input: dify
```

## 3. 关键要点总结

- ReAct = Thought + Action + Observation 三段式
- 比 Function Call 更通用（不需要支持 function calling 的模型）
- dify 用 `CotAgentRunner` 实现 ReAct
- 关键技巧：用 stop token 控制 LLM 输出格式

---

**文档版本**：v1.0
**最后更新**：2026-07-13
