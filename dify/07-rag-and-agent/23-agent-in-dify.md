# 7.4.6 dify 的 Agent 节点实现

> 深度解读 dify 中 Agent 节点的实现：从工作流节点到具体 Runner 的调用链。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出 dify Agent 节点的端到端调用链
- 理解 Agent 节点的配置数据结构
- 看懂 `AgentNode._run()` 的实现
- 区分 Agent 节点与工作流节点的关系

## 📚 前置知识

- 07-rag-and-agent/18-agent-concepts.md 至 22-advanced-agent.md
- 07-rag-and-agent/24-workflow-engine.md（推荐先看）

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

## 3. dify 仓库源码解读

### 3.1 AgentNode 类骨架

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/agent/agent_node.py`
**核心代码**（行 27-90）：

```python
class AgentNode(Node[AgentNodeData]):
    """工作流中的 Agent 节点"""

    node_type = BuiltinNodeTypes.AGENT

    _strategy_resolver: AgentStrategyResolver
    _presentation_provider: AgentStrategyPresentationProvider
    _runtime_support: AgentRuntimeSupport
    _message_transformer: AgentMessageTransformer

    def __init__(
        self,
        node_id: str,
        data: AgentNodeData,
        *,
        graph_init_params: GraphInitParams,
        graph_runtime_state: GraphRuntimeState,
        strategy_resolver: AgentStrategyResolver,
        presentation_provider: AgentStrategyPresentationProvider,
        runtime_support: AgentRuntimeSupport,
        message_transformer: AgentMessageTransformer,
    ) -> None:
        super().__init__(
            node_id=node_id,
            data=data,
            graph_init_params=graph_init_params,
            graph_runtime_state=graph_runtime_state,
        )
        self._strategy_resolver = strategy_resolver
        self._presentation_provider = presentation_provider
        self._runtime_support = runtime_support
        self._message_transformer = message_transformer

    @classmethod
    @override
    def version(cls) -> str:
        return "1"

    @override
    def populate_start_event(self, event) -> None:
        dify_ctx = DifyRunContext.model_validate(self.require_run_context_value(DIFY_RUN_CONTEXT_KEY))
        event.extras["agent_strategy"] = {
            "name": self.node_data.agent_strategy_name,
            "icon": self._presentation_provider.get_icon(
                tenant_id=dify_ctx.tenant_id,
                agent_strategy_provider_name=self.node_data.agent_strategy_provider_name,
            ),
        }
```

**解读**：
- `AgentNode` 继承自 `Node[AgentNodeData]`，遵守工作流节点的统一接口
- 通过依赖注入传入 4 个 helper：策略解析器、运行时支持、消息转换器
- `populate_start_event` 在节点开始执行时设置元信息（策略名、图标）给前端展示

### 3.2 AgentNodeData 实体

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/agent/entities.py`
**核心代码**（节选）：

```python
class AgentNodeData(BaseModel):
    """Agent 节点的数据模型，对应前端表单"""

    agent_strategy_provider_name: str  # langchain / dify
    agent_strategy_name: str           # 具体策略
    agent_parameters: AgentParameters  # Agent 参数（max_iteration 等）
    agent_tools: list[AgentToolEntity] = []  # 工具列表
    memory: MemoryConfig | None = None
    # 各种 prompt 配置
```

**解读**：
- Pydantic 模型，与前端 JSON 一一对应
- `agent_strategy_provider_name` + `agent_strategy_name` 唯一确定一个 Agent 策略

### 3.3 Strategy Resolver

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/agent/strategy_protocols.py`
**核心代码**（节选）：

```python
class AgentStrategyResolver(Protocol):
    """根据配置解析出具体的 Agent 策略"""

    def resolve(
        self,
        *,
        tenant_id: str,
        agent_strategy_provider_name: str,
        agent_strategy_name: str,
    ) -> AgentStrategy:
        ...


class AgentStrategyPresentationProvider(Protocol):
    """提供 Agent 策略的展示信息（名称、图标、描述）"""

    def get_icon(self, *, tenant_id: str, agent_strategy_provider_name: str) -> str:
        ...
```

**解读**：
- 通过 Protocol（结构化子类型）解耦：AgentNode 不需要知道具体策略的实现
- `Resolver` 负责把 `(provider, name)` 解析成具体的策略对象
- dify 支持 langchain、dify 内置、第三方插件等多种 Agent 策略

### 3.4 与工作流节点的对比

| 维度 | Agent 节点 | LLM 节点 | 工具节点 |
|------|-----------|---------|---------|
| 内部循环 | 多步（ReAct） | 1 步 | 1 步 |
| 是否调用工具 | 是 | 否 | N/A |
| 输出 | 文本 + 思考链 | 文本 | 工具结果 |
| 复杂度 | 高 | 低 | 中 |

## 4. 关键要点总结

- dify 的 Agent 节点嵌入在工作流中
- 通过 `AgentStrategyResolver` 解析具体策略
- 支持多种策略：langchain、dify 内置、第三方插件
- 返回结果包含 answer 和 thought_chain（前端可展示思考过程）

## 5. 练习题

### 练习 1：基础（必做）

阅读 `agent_node.py` 的 `_run` 方法完整实现（行 75-150），画出内部的调用顺序。

### 练习 2：进阶

设计一个工作流：用户输入 → 知识检索节点 → Agent 节点（带计算器工具）→ LLM 节点（润色）→ 输出。

### 练习 3：挑战（选做）

实现一个自定义的 Agent 策略插件（按 `AgentStrategyResolver` 接口），比如 ReWOO。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/agent/agent_node.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/agent/entities.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/agent/strategy_protocols.py`
- `/Users/xu/code/github/dify/api/core/agent/base_agent_runner.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13