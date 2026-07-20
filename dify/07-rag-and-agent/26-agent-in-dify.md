# 7.4.6 dify 的 Agent 节点实现

> 深度解读 dify 中 Agent 节点的实现：从工作流节点到具体 Runner 的调用链。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出 dify Agent 节点的端到端调用链
- 理解 Agent 节点的配置数据结构
- 看懂 `AgentNode._run()` 的实现
- 区分 Agent 节点与工作流节点的关系

## 📚 前置知识

- Agent 系列（详见 [Agent 概念](./21-agent-concepts.md)、[ReAct 深入](./22-react-deep-dive.md)、[Advanced Agent](./25-advanced-agent.md)）
- 工作流引擎（详见 [Workflow Engine](./28-workflow-engine.md)）
- dify Function Calling Agent（详见 [Function Calling](../06-llm-and-ai/17-function-calling.md)、[工具系统](../06-llm-and-ai/22-tools-in-dify.md)）

## 1. 核心概念

### 1.1 dify 中 Agent 的形态

在 dify 中，Agent 有两种存在形式：

1. **独立 Agent 应用**：单独的 Agent 应用，只有一个 Agent 节点
2. **工作流中的 Agent 节点**：嵌入在 Workflow/Chatflow 中的子模块

### 1.2 Agent 节点的配置

```
Agent 节点
  ├── agent_strategy_provider_name: 策略提供方（如 "langchain"、"dify"）
  ├── agent_strategy_name: 具体策略（如 "ChatAgent"、"CompletionAgent"）
  ├── agent_parameters: Agent 参数（max_iteration、memory 等）
  ├── agent_tools: 工具列表（每个工具一个配置）
  ├── agent_prompt: Prompt 模板
  └── memory: 记忆配置
```

### 1.3 端到端调用链

```
工作流引擎调度
  → AgentNode._run()
    → AgentStrategyResolver 解析策略
    → AgentRuntimeSupport 准备运行时
    → 具体 AgentRunner.run()
      → LLM 调用 + 工具执行循环
      → 返回结果 + 思考链
    → AgentMessageTransformer 转换消息
    → 返回 NodeRunResult
```

## 2. 代码示例

### 2.1 简化的 Agent 节点

```python
class SimpleAgentNode:
    """工作流中的一个 Agent 节点（简化版）"""

    def __init__(self, config: dict):
        self.strategy_name = config["strategy"]
        self.tools = config["tools"]
        self.max_iteration = config.get("max_iteration", 10)
        self.prompt = config["prompt"]

    def run(self, query: str, llm, tool_registry) -> dict:
        # 1. 根据策略选择 Runner
        runner = self._create_runner(llm, tool_registry)

        # 2. 执行 Agent
        result = runner.run(query=query, max_iteration=self.max_iteration)

        # 3. 返回结构化结果
        return {
            "answer": result.answer,
            "thought_chain": result.thoughts,  # 给前端展示
            "iterations": result.iterations,
        }

    def _create_runner(self, llm, tool_registry):
        if self.strategy_name == "react":
            return CotAgentRunner(llm=llm, tools=tool_registry)
        elif self.strategy_name == "function_call":
            return FcAgentRunner(llm=llm, tools=tool_registry)
```

### 2.2 Agent 配置的数据类

```python
from pydantic import BaseModel
from typing import Optional


class AgentToolConfig(BaseModel):
    """工具配置"""
    tool_name: str
    enabled: bool = True
    params: dict = {}


class AgentNodeConfig(BaseModel):
    """Agent 节点配置"""
    strategy_provider: str  # "langchain" 或 "dify"
    strategy_name: str      # "ChatAgent"、"CompletionAgent"
    max_iteration: int = 10
    memory_enabled: bool = False
    memory_window: int = 10
    prompt_template: list[dict]  # [{role: "system", content: "..."}]
    tools: list[AgentToolConfig] = []
```

## 3. 关键要点总结

- dify 的 Agent 节点嵌入在工作流中
- 通过 `AgentStrategyResolver` 解析具体策略
- 支持多种策略：langchain、dify 内置、第三方插件
- 返回结果包含 answer 和 thought_chain（前端可展示思考过程）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
