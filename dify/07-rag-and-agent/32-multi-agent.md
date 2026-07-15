# 7.6.1 多 Agent 架构：Supervisor / Swarm / Hierarchical

> 掌握多 Agent 协作的三种主流架构：Supervisor、Swarm、Hierarchical。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述三种多 Agent 架构的核心差异
- 选择适合业务场景的多 Agent 模式
- 实现一个 Supervisor 模式的多 Agent 系统
- 理解 dify 中多 Agent 的实现方式

## 📚 前置知识

- [Agent 概念](./18-agent-concepts.md)
- [Workflow Engine](./24-workflow-engine.md)

## 1. 核心概念

### 1.1 三种多 Agent 架构

```
Supervisor（主管模式）：
       ┌──────┐
       │ Boss │  ← 决策中心
       └──┬───┘
     ┌────┼────┐
     ↓    ↓    ↓
  Worker1 Worker2 Worker3

Swarm（群智模式）：
  Agent1 ↔ Agent2 ↔ Agent3
   ↕        ↕        ↕
  平等协作，无中心

Hierarchical（分层模式）：
       ┌──────┐
       │ Boss │  ← 总决策
       └──┬───┘
       ┌──┴───┐
       ↓      ↓
  Manager1 Manager2
       ↓      ↓
   Workers Workers
```

### 1.2 对比

| 维度 | Supervisor | Swarm | Hierarchical |
|------|------------|-------|--------------|
| 控制中心 | 有（主管） | 无（去中心化） | 有（多层） |
| 适用规模 | 小（3-10 个 worker） | 中（10-100） | 大（100+） |
| 决策路径 | 短（2 跳） | 长（多跳） | 树形 |
| 灵活性 | 中 | 高 | 低 |
| 实现难度 | 低 | 中 | 高 |

### 1.3 dify 的支持

dify 通过工作流的"Agent 节点 + 条件分支"实现多 Agent 协作，不需要复杂的 Agent 协议。

## 2. 代码示例

### 2.1 Supervisor 模式

```python
class Supervisor:
    """主管 Agent：决定调用哪个 Worker"""

    def __init__(self, llm, workers: dict):
        self.llm = llm
        self.workers = workers  # {"search": search_worker, "calc": calc_worker, ...}

    def route(self, query: str) -> str:
        """决定调用哪个 worker"""
        worker_descs = "\n".join(f"- {name}: {w.description}" for name, w in self.workers.items())
        prompt = f"""分析用户问题，调用最合适的 worker。

Workers:
{worker_descs}

用户问题：{query}

输出 JSON：{{"worker": "name", "input": {{...}}}}"""
        response = self.llm.invoke(prompt)
        return json.loads(response)["worker"]

    def run(self, query: str) -> str:
        # 1. 主管决定调用谁
        worker_name = self.route(query)
        worker = self.workers[worker_name]

        # 2. Worker 执行
        result = worker.run(query)

        # 3. 主管汇总（可选）
        final = self.llm.invoke(f"基于以下结果回答用户：{result}")
        return final
```

### 2.2 Swarm 模式（简化）

```python
class SwarmAgent:
    """群智中的一个 Agent"""

    def __init__(self, name: str, role: str, llm, peers: list):
        self.name = name
        self.role = role
        self.llm = llm
        self.peers = peers  # 其他 peer

    def run(self, query: str, context: dict = None) -> dict:
        # 1. 自己处理
        result = self.llm.invoke(f"作为 {self.role}，处理：{query}")

        # 2. 决定是否要 peer 帮忙
        peer_name = self._should_consult_peer(result)
        if peer_name:
            peer = self._find_peer(peer_name)
            peer_input = self._prepare_for_peer(result)
            peer_result = peer.run(peer_input)
            result = self._merge(result, peer_result)

        return {"agent": self.name, "result": result}
```

### 2.3 简易 Hierarchical 模式

```python
class HierarchicalAgent:
    """分层 Agent"""

    def __init__(self, llm, name: str, subordinates: list = None):
        self.llm = llm
        self.name = name
        self.subordinates = subordinates or []

    def run(self, task: str) -> str:
        if not self.subordinates:
            # 叶子节点：自己执行
            return self._execute(task)

        # 非叶子：分解任务，分配给下属
        subtasks = self._decompose(task)
        results = []
        for sub in self.subordinates:
            sub_task = subtasks.get(sub.name, "")
            if sub_task:
                results.append(sub.run(sub_task))

        # 汇总
        return self._aggregate(results)
```

### 2.4 常见错误：所有问题都走 Supervisor

```python
# ❌ 错误：每个小问题都过主管（开销大）
def run(self, query):
    decision = supervisor.route(query)  # 一次 LLM 调用
    return workers[decision].run(query)  # 一次 LLM 调用
# 总共 2 次 LLM 调用

# ✅ 正确：简单任务直接执行
def run(self, query):
    if is_simple(query):
        return direct_llm(query)  # 1 次 LLM 调用
    return supervisor.run(query)  # 复杂任务才走多 Agent
```

## 3. dify 仓库源码解读

### 3.1 多 Agent 的工作流实现

dify 通过工作流的"分支 + Agent 节点"实现多 Agent 协作，不需要专门的 MultiAgent 类。

**典型结构**：
```
LLM 节点（路由决策）
  ├── If-Else（如果分类 = A）
  │     └── Agent 节点 A
  ├── If-Else（如果分类 = B）
  │     └── Agent 节点 B
  └── Variable Aggregator（汇总结果）
```

### 3.2 Agent 节点组合

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/agent/agent_node.py`
**核心代码**：

```python
class AgentNode(Node[AgentNodeData]):
    """单个 Agent 节点

    多 Agent 通过多个 AgentNode + 条件分支组合实现
    """
    node_type = BuiltinNodeTypes.AGENT

    @override
    def _run(self) -> Generator[NodeEventBase, None, None]:
        # 1. 解析策略
        strategy = self._strategy_resolver.resolve(...)
        # 2. 执行
        result = strategy.run(...)
        # 3. 返回
        yield NodeRunResult(outputs={...})
```

**解读**：
- dify 把每个 Agent 视为工作流中的一个节点
- 多 Agent = 多个 Agent 节点 + 控制流（If-Else、Variable Aggregator）
- 这种设计让多 Agent 配置完全可视化

## 4. 关键要点总结

- 三种多 Agent 架构：Supervisor（简单）、Swarm（灵活）、Hierarchical（大规模）
- dify 通过工作流编排实现多 Agent，无需专门的 MultiAgent 类
- 简单任务应避免走多 Agent（开销大）
- 多 Agent 适合：复杂任务、角色分工明确的场景

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Supervisor 模式：3 个 worker（搜索、计算、邮件），主管根据 query 路由。

### 练习 2：进阶

设计一个 Swarm 模式：2 个 Agent（写代码、找 bug），互相协作完成编程任务。

### 练习 3：挑战（选做）

思考题：dify 为什么不实现 LangChain 的 AgentExecutor，而是用工作流编排 Agent？两种方式在 dify 中的优劣？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/agent/agent_node.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/if_else/`
- LangChain Multi-Agent 文档

---

**文档版本**：v1.0
**最后更新**：2026-07-13