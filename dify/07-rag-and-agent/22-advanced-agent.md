# 7.4.5 Toolformer / ReWOO 等前沿模式

> 了解 Agent 的前沿研究：Toolformer、ReWOO、OpenFunctions 等扩展模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 Toolformer、ReWOO、OpenFunctions 的核心思想
- 对比这些前沿方法与传统 ReAct 的差异
- 思考前沿方法在 dify 中的潜在落地

## 📚 前置知识

- Agent 基础到 Reflection（详见 [Agent 概念](./18-agent-concepts.md)、[ReAct 深入](./19-react-deep-dive.md)、[Plan-and-Execute](./20-plan-execute.md)、[Reflection](./21-reflection.md)）

## 1. 核心概念

### 1.1 主流前沿 Agent 模式

| 模式 | 出处 | 核心思想 |
|------|------|----------|
| **ReAct** | Yao et al. 2022 | Thought → Action → Observation 循环 |
| **Toolformer** | Meta 2023 | 模型在训练时学习调用 API |
| **ReWOO** | Xu et al. 2023 | Planner 先规划，Worker 并行执行 |
| **OpenFunctions** | Salesforce 2023 | 把所有工具统一为函数 |
| **AutoGPT** | 社区 2023 | 长期目标 + 自我提示 |
| **BabyAGI** | 社区 2023 | 任务列表 + 优先级排序 |

### 1.2 Toolformer 的核心

Toolformer 把工具调用**融入训练过程**：

1. 自动标注训练数据：在文本中插入工具调用
2. 模型学习"在合适位置调用工具"
3. 推理时模型自主决定何时调用

**优点**：模型原生具备工具调用能力，无需复杂 Prompt。
**缺点**：需要大量标注和训练。

### 1.3 ReWOO 的核心

ReWOO = Reason Without Observation：

```
Planner: 生成完整 Plan（包含所有步骤的工具调用）
Worker: 并行执行所有工具调用
Solver: 基于所有结果生成最终答案
```

**优点**：并行执行节省时间。
**缺点**：没有中间观察，错误累积。

## 2. 代码示例

### 2.1 ReWOO 实现框架

```python
class ReWOOAgent:
    """ReWOO: Planner + Worker + Solver"""

    def __init__(self, llm, tools: dict):
        self.llm = llm
        self.tools = tools

    def run(self, query: str) -> str:
        # Step 1: Planner 生成完整 Plan
        plan = self._plan(query)
        # plan = [
        #     {"step": 1, "tool": "search", "input": "weather beijing"},
        #     {"step": 2, "tool": "search", "input": "weather shanghai"},
        #     {"step": 3, "tool": "compare", "input": "#1 and #2"},
        # ]

        # Step 2: Worker 并行执行所有步骤
        results = {}
        for step in plan:
            results[step["step"]] = self._execute(step, results)

        # Step 3: Solver 综合所有结果
        return self._solve(query, results)

    def _plan(self, query: str) -> list:
        prompt = f"""为以下任务生成执行计划。
每步格式：Step [id]: [tool]([input])

工具：{list(self.tools.keys())}
任务：{query}
计划："""
        response = self.llm.invoke(prompt)
        return self._parse_plan(response)
```

### 2.2 OpenFunctions 风格的统一接口

```python
from typing import Callable


def make_tool(name: str, description: str, func: Callable) -> dict:
    """OpenFunctions 风格：所有工具都包装成统一格式"""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "the input"}
                },
                "required": ["input"],
            },
        },
        "callable": func,
    }


# 使用
tools = [
    make_tool("search", "Search the knowledge base", search_func),
    make_tool("calculator", "Perform calculation", calc_func),
]
```

### 2.3 BabyAGI 风格的任务列表

```python
class BabyAGI:
    """任务列表 + 优先级"""

    def __init__(self, llm, tools, max_tasks: int = 10):
        self.llm = llm
        self.tools = tools
        self.task_list = []

    def add_task(self, task: dict):
        """添加到任务列表"""
        self.task_list.append(task)

    def run(self) -> list:
        results = []
        for _ in range(self.max_tasks):
            if not self.task_list:
                break

            # 1. 按优先级排序
            self.task_list.sort(key=lambda x: x["priority"], reverse=True)

            # 2. 执行第一个
            task = self.task_list.pop(0)
            result = self._execute_task(task)
            results.append(result)

            # 3. 基于结果生成新任务
            new_tasks = self._create_new_tasks(task, result)
            self.task_list.extend(new_tasks)
        return results
```

### 2.4 常见错误：盲目追前沿

```python
# ❌ 错误：项目都用最新最复杂的 Agent 模式
# 实际上 80% 的场景 ReAct + Function Call 就够用了

# ✅ 正确：根据任务复杂度选择模式
# 简单任务（1-3 步） → Function Call
# 中等任务（4-10 步） → ReAct
# 复杂任务（10+ 步） → Plan-and-Execute 或 ReWOO
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Agent 策略可扩展性

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/strategy/strategy_protocols.py`（节选）
**核心代码**：

```python
class AgentStrategy(Protocol):
    """Agent 策略的 Protocol，新策略只需实现这个接口"""

    def run(self, *args, **kwargs) -> Generator:
        ...
```

**解读**：
- dify 用 Protocol 而不是 ABC 来定义 Agent 策略接口
- 任何实现了 `run` 方法的类都可以作为 Agent 策略
- 第三方开发者可以贡献新的 Agent 策略（ReWOO、Toolformer 等）

### 3.2 工具统一抽象

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/tool_engine.py`
**核心代码**：

```python
class ToolEngine:
    """工具引擎：统一管理所有工具"""

    @classmethod
    def invoke_tool(cls, tool_name: str, tool_input: dict, ...) -> Any:
        # 1. 根据 tool_name 找到 tool 实现
        tool = cls.get_tool(tool_name)
        # 2. 鉴权
        # 3. 调用工具
        return tool.invoke(tool_input)
```

**解读**：
- dify 的 ToolEngine 把所有工具统一成一个调用接口
- 这就是 OpenFunctions 风格的设计
- 工具可以是内置的，也可以是用户自定义的（plugin）

## 4. 关键要点总结

- 前沿 Agent 模式各有侧重：Toolformer（训练时学习）、ReWOO（并行执行）
- 生产环境 80% 场景用 ReAct + Function Call 就够了
- 复杂任务才需要 Plan-and-Execute
- dify 用 Protocol 让 Agent 策略可扩展

## 5. 练习题

### 练习 1：基础（必做）

调研 Toolformer 论文，列出它的三个核心贡献。

### 练习 2：进阶

实现 ReWOO 的最小版本：Planner → 3 个并行 Worker → Solver，对比 ReAct 的延迟。

### 练习 3：挑战（选做）

思考题：哪种 Agent 模式最适合 dify？为什么 dify 目前主推 Function Call + 工作流？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/agent/strategy/strategy_protocols.py`
- `/Users/xu/code/github/dify/api/core/tools/tool_engine.py`
- Toolformer 论文：https://arxiv.org/abs/2302.04761
- ReWOO 论文：https://arxiv.org/abs/2305.18323

---

**文档版本**：v1.0
**最后更新**：2026-07-13