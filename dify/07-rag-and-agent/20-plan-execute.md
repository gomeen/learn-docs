# 7.4.3 Plan-and-Execute 模式

> 理解 Plan-and-Execute Agent 模式：先规划，再执行，比 ReAct 更适合复杂任务。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Plan-and-Execute 与 ReAct 的区别
- 写出 Plan-and-Execute 的核心 Prompt
- 看懂 Plan 步骤的数据结构
- 理解 Plan-and-Execute 的优缺点

## 📚 前置知识

- 07-rag-and-agent/19-react-deep-dive.md

## 1. 核心概念

### 1.1 什么是 Plan-and-Execute？

ReAct 是"边走边想"（一步步推理 + 行动），Plan-and-Execute 是"先规划后执行"：

```
ReAct：
  Thought → Action → Observation → Thought → ...

Plan-and-Execute：
  Plan: [step1, step2, step3]  ← 一次性规划
  Execute step1 → result1
  Execute step2 → result2
  Execute step3 → result3
```

### 1.2 优缺点对比

| 维度 | ReAct | Plan-and-Execute |
|------|-------|------------------|
| 适合任务 | 短链、动态调整 | 长链、可分解 |
| Token 消耗 | 较低（每步推理） | 较高（完整规划） |
| 稳定性 | 易跑偏 | 整体方向感强 |
| 可解释性 | 逐步可读 | Plan 一目了然 |

### 1.3 进阶：Replan

执行过程中如果某步失败，**重新规划剩余步骤**：

```
Plan: [A, B, C, D]
Execute A → OK
Execute B → FAIL
Replan: [A', C', D']  ← 重新规划
```

## 2. 代码示例

### 2.1 Plan 步骤的数据结构

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanStep:
    step_id: int
    description: str  # 这一步做什么
    tool: str | None  # 用什么工具
    tool_input: dict | None  # 工具输入
    depends_on: list[int]  # 依赖哪些步骤
    status: StepStatus = StepStatus.PENDING
    result: Any = None


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
```

### 2.2 Planner：生成 Plan

```python
PLANNER_PROMPT = """你是一个任务规划助手。
给定用户的复杂任务，拆解成可顺序执行的步骤。

输出 JSON：
{{
    "goal": "原始任务",
    "steps": [
        {{"step_id": 1, "description": "...", "tool": "...", "tool_input": {{...}}, "depends_on": []}},
        ...
    ]
}}

可用工具：
{tools}

任务：{query}

输出："""


def plan(query: str, tools: list, llm) -> Plan:
    prompt = PLANNER_PROMPT.format(tools=tools, query=query)
    response = llm.invoke(prompt)
    plan_data = json.loads(response)

    steps = [PlanStep(**s) for s in plan_data["steps"]]
    return Plan(goal=plan_data["goal"], steps=steps)
```

### 2.3 Executor：按 Plan 执行

```python
def execute_plan(plan: Plan, tool_registry: dict) -> Plan:
    """按步骤执行 Plan"""
    for step in plan.steps:
        if step.status != StepStatus.PENDING:
            continue

        # 检查依赖
        deps_satisfied = all(
            plan.steps[dep - 1].status == StepStatus.COMPLETED
            for dep in step.depends_on
        )
        if not deps_satisfied:
            step.status = StepStatus.FAILED
            continue

        step.status = StepStatus.RUNNING

        # 执行工具
        if step.tool and step.tool in tool_registry:
            try:
                step.result = tool_registry[step.tool](**step.tool_input)
                step.status = StepStatus.COMPLETED
            except Exception as e:
                step.status = StepStatus.FAILED
                step.result = str(e)
        else:
            # 不用工具，LLM 直接生成
            step.result = "无需工具执行"
            step.status = StepStatus.COMPLETED
    return plan
```

### 2.4 常见错误：Plan 太粗或太细

```python
# ❌ 错误 1：Plan 太粗（只有 1 步）
plan = [{"description": "完成用户的请求"}]  # 无意义

# ❌ 错误 2：Plan 太细（每句话一步）
plan = [{"description": "读取文件第一行"}, {"description": "解析第一行"}]  # 过度拆分

# ✅ 正确：每步是一个独立可完成的目标
plan = [
    {"description": "搜索相关知识", "tool": "search"},
    {"description": "基于结果生成答案", "tool": "llm"},
]
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Planning Strategy

**文件位置**：`/Users/xu/code/github/dify/api/core/entities/agent_entities.py`（节选）
**核心代码**：

```python
class PlanningStrategy(StrEnum):
    """Agent 规划策略"""
    ROUTER = "router"               # 路由：选择哪个工具
    REACT = "react"                 # ReAct：Thought → Action → Observation
    FUNCTION_CALL = "function_call" # Function Call
    PLAN_AND_EXECUTE = "plan_and_execute"
```

### 3.2 dify 工作流中的 Agent 节点

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/agent/agent_node.py`（节选）
**核心代码**：

```python
class AgentNode(BaseNode):
    """工作流中的 Agent 节点"""

    def _run(self) -> NodeRunResult:
        # 1. 选择策略
        strategy = self.node_data.agent_strategy_provider_name

        # 2. 根据策略选择 Runner
        if strategy == "react":
            runner = CotAgentRunner(...)
        elif strategy == "function_call":
            runner = FcAgentRunner(...)

        # 3. 执行
        result = runner.run(...)
        return NodeRunResult(outputs={"text": result})
```

**解读**：
- dify 在工作流层面暴露 Agent 节点
- 用户选择策略后，后端用对应的 Runner 执行
- Plan-and-Execute 是 dify 支持的策略之一（具体实现可能在 plugin 层）

## 4. 关键要点总结

- Plan-and-Execute = 先规划再执行
- 比 ReAct 适合长链任务，但 token 消耗大
- 进阶：Replan（执行失败后重新规划）
- dify 通过 `PlanningStrategy` 枚举支持多种 Agent 策略

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Plan-and-Execute Agent：给它任务"对比北京和上海今天的天气"，让 Planner 先规划 3 步，Executor 逐步执行。

### 练习 2：进阶

为 Plan-and-Execute 增加 Replan 能力：当某步失败时，重新生成剩余步骤。

### 练习 3：挑战（选做）

设计实验：对比 ReAct 和 Plan-and-Execute 在 10 个复杂任务上的成功率、延迟、token 成本。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/entities/agent_entities.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/agent/agent_node.py`
- Plan-and-Execute 论文：https://arxiv.org/abs/2305.04091

---

**文档版本**：v1.0
**最后更新**：2026-07-13