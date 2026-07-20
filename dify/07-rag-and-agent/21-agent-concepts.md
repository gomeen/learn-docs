# 7.4.1 Agent 概念：感知-决策-行动循环

> 理解 Agent（智能体）的本质：从被动工具到自主决策的演进。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Agent 与普通 LLM 调用的本质差异
- 描述 Agent 的"感知-决策-行动"循环（Perception → Reasoning → Action）
- 列举 Agent 的核心组件（LLM、Memory、Tools、Planning）
- 看懂 dify 中 Agent 节点的概念模型

## 📚 前置知识

- LLM 与工具调用（详见 [主流大模型对比](../06-llm-and-ai/01-llm-overview.md)、[Function Calling](../06-llm-and-ai/17-function-calling.md)、[ReAct](../06-llm-and-ai/11-react.md)）
- RAG 背景（详见 [RAG 概览](./01-rag-overview.md)）

## 1. 核心概念

### 1.1 什么是 Agent？

Agent 是一种能**自主感知环境、做出决策、执行行动**的系统。

```
LLM 调用：input → LLM → output（被动、一问一答）
Agent：   循环执行 → 直到任务完成（主动、多步决策）
```

### 1.2 Agent 的四大核心组件

| 组件 | 职责 |
|------|------|
| **LLM** | 大脑，做推理和决策 |
| **Memory** | 短期（context）+ 长期（向量库）记忆 |
| **Tools** | 手脚，调用外部 API/函数 |
| **Planning** | 拆解复杂任务为子步骤 |

### 1.3 感知-决策-行动循环

```
┌─────────────┐
│  Perception │  ← 观察：用户输入、工具返回结果、当前状态
└──────┬──────┘
       ↓
┌─────────────┐
│   Reasoning │  ← 思考：LLM 推理下一步该做什么
└──────┬──────┘
       ↓
┌─────────────┐
│    Action   │  ← 行动：调用工具 / 回答用户 / 等待
└──────┬──────┘
       ↓
   (回到 Perception)
```

## 2. 代码示例

### 2.1 最简 Agent 循环

```python
from typing import Callable, List, Dict


class SimpleAgent:
    def __init__(self, llm, tools: Dict[str, Callable], max_iterations: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations

    def run(self, query: str) -> str:
        history = [{"role": "user", "content": query}]

        for i in range(self.max_iterations):
            # 1. LLM 推理：决定是调用工具还是回答
            response = self.llm.invoke(
                history,
                tools=self._format_tools(),
            )
            history.append(response)

            # 2. 如果是 tool_call，执行工具
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_result = self.tools[tool_name](**tool_args)
                    history.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": str(tool_result),
                    })
                # 继续下一轮推理
                continue
            else:
                # 3. 最终答案
                return response["content"]
        return "达到最大迭代次数，任务未完成"
```

### 2.2 Tool 定义与注册

```python
import json
from datetime import datetime


# 定义工具
def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().isoformat()


def search_knowledge(query: str) -> str:
    """从知识库搜索"""
    return f"关于 {query} 的检索结果..."


def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件"""
    return f"邮件已发送至 {to}"


# 注册工具
tools = {
    "get_current_time": get_current_time,
    "search_knowledge": search_knowledge,
    "send_email": send_email,
}


# 使用 Agent
agent = SimpleAgent(llm=mock_llm, tools=tools)
print(agent.run("现在几点了？顺便查一下 Dify 是什么？"))
```

### 2.3 常见错误：没有终止条件

```python
# ❌ 错误：Agent 无限循环
while True:
    response = agent.step()
    if not response.tool_calls:
        break  # 缺这行就死循环

# ✅ 正确：显式终止条件 + 最大迭代次数保护
for i in range(max_iterations):
    response = agent.step()
    if not response.tool_calls:
        return response.content
```

## 3. 关键要点总结

- Agent = LLM + Memory + Tools + Planning 的综合体
- 核心是"感知-决策-行动"循环
- 必须有终止条件（最大迭代次数 + 主动终止）
- dify 通过 `BaseAgentRunner` 抽象多种 Agent 策略

---

**文档版本**：v1.0
**最后更新**：2026-07-13
