# 7.4.1 Agent 概念：感知-决策-行动循环

> 理解 Agent（智能体）的本质：从被动工具到自主决策的演进。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Agent 与普通 LLM 调用的本质差异
- 描述 Agent 的"感知-决策-行动"循环（Perception → Reasoning → Action）
- 列举 Agent 的核心组件（LLM、Memory、Tools、Planning）
- 看懂 dify 中 Agent 节点的概念模型

## 📚 前置知识

- LLM 与工具调用（详见 [主流大模型对比](../06-llm-and-ai/01-llm-overview.md)、[Function Calling](../06-llm-and-ai/14-function-calling.md)、[ReAct](../06-llm-and-ai/10-react.md)）
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

## 3. dify 仓库源码解读

### 3.1 Agent 节点的实体定义

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/entities.py`
**核心代码**（节选）：

```python
class AgentEntity(BaseModel):
    """Agent 配置的实体定义"""
    agent_strategy_provider_name: str  # 策略：CoT / FunctionCall
    agent_strategy_name: str           # 具体策略：ChatAgent / CompletionAgent
    tools: list[ToolEntity]
    max_iteration: int = 10            # 最大循环次数
    memory: MemoryConfig | None = None
    prompt_template: list[PromptMessage]
```

### 3.2 Agent Runner 基类

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/base_agent_runner.py`
**核心代码**（节选）：

```python
class BaseAgentRunner(ABC):
    """Agent 运行器的抽象基类"""

    @abstractmethod
    def run(self, *args, **kwargs):
        """子类必须实现的 run 方法"""
        raise NotImplementedError
```

**解读**：
- dify 通过 `BaseAgentRunner` 抽象不同的 Agent 策略
- 具体实现：`CotAgentRunner`（Chain-of-Thought）、`FcAgentRunner`（Function Call）、`CotChatAgentRunner`、`CotCompletionAgentRunner`
- 不同 Runner 用不同的 prompt 和解析方式

### 3.3 实体接口定义

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/strategy/agent_node.py`（示意）
**核心代码**：

```python
class AgentNode:
    """工作流中的 Agent 节点"""

    node_type = BuiltinNodeTypes.AGENT

    def _run(self) -> NodeRunResult:
        # 1. 选择 Agent 策略
        runner = self._select_agent_runner()

        # 2. 初始化工具列表
        tools = self._load_tools(self.node_data.agent_strategy_tools)

        # 3. 执行 Agent 循环
        result = runner.run(
            query=self._get_input(),
            tools=tools,
            max_iterations=self.node_data.agent_parameters.max_iteration,
        )

        # 4. 返回结果
        return NodeRunResult(outputs={"text": result})
```

**解读**：
- Agent 节点是工作流中的"调用点"
- 根据用户在前端选择的策略，调用不同的 Runner
- 工具列表从工作流配置中加载

## 4. 关键要点总结

- Agent = LLM + Memory + Tools + Planning 的综合体
- 核心是"感知-决策-行动"循环
- 必须有终止条件（最大迭代次数 + 主动终止）
- dify 通过 `BaseAgentRunner` 抽象多种 Agent 策略

## 5. 练习题

### 练习 1：基础（必做）

实现一个最简 Agent：给它 3 个工具（计算、查天气、发消息），让它能完成"今天北京多少度，给妈妈发条消息"的复合任务。

### 练习 2：进阶

阅读 `base_agent_runner.py`，画出 `BaseAgentRunner` 与 `CotAgentRunner`、`FcAgentRunner` 的继承关系。

### 练习 3：挑战（选做）

思考题：Agent 与工作流（Workflow）的本质区别是什么？什么场景用 Agent、什么场景用 Workflow？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/agent/base_agent_runner.py`
- `/Users/xu/code/github/dify/api/core/agent/cot_agent_runner.py`
- `/Users/xu/code/github/dify/api/core/agent/fc_agent_runner.py`
- `/Users/xu/code/github/dify/api/core/agent/entities.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13