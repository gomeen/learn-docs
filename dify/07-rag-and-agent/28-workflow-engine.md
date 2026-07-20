# 7.5.1 工作流引擎原理：节点 + 边 + 状态机

> 深入理解工作流引擎的核心原理：图（Graph）数据结构、节点执行、状态机驱动。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述工作流引擎的三大核心：Graph / Node / Engine
- 理解节点执行的"有向无环图"（DAG）模型
- 看懂 dify 中 `workflow_entry.py` 与 GraphEngine 的协作
- 理解工作流的拓扑结构与调度

## 📚 前置知识

- [RAG 概览](./01-rag-overview.md)（工作流常组合检索与生成）
- Python 异步编程（详见 [async/asyncio](../01-fundamentals/14-async-asyncio.md)）
- 图执行 / 控制流直觉（节点与边将在后文展开，详见 [Workflow Nodes](./29-workflow-nodes.md)）

## 1. 核心概念

### 1.1 工作流引擎是什么？

工作流引擎是 dify 最核心的能力：让用户通过拖拽节点编排复杂流程。

```
触发 → 开始 → LLM → 条件判断 → [分支1: 工具 / 分支2: 知识检索] → 结束
```

引擎负责：
1. 解析 DSL（图配置 JSON/YAML）
2. 构建有向图
3. 按拓扑顺序调度节点
4. 管理变量池
5. 处理分支、循环、并行

### 1.2 核心数据结构

```python
@dataclass
class Node:
    id: str
    type: str          # "start", "llm", "tool", "if-else", "loop", ...
    data: dict         # 节点配置
    next_nodes: list[str]  # 后继节点 ID


@dataclass
class Graph:
    nodes: dict[str, Node]
    edges: list[Edge]
    start_node_id: str
    end_node_ids: list[str]


class GraphEngine:
    """驱动 Graph 执行的引擎"""
    graph: Graph
    variable_pool: VariablePool
    state: GraphRuntimeState

    def run(self) -> Generator[GraphEvent]:
        while not self.state.is_finished():
            node = self.state.next_ready_node()
            yield from self.execute_node(node)
```

### 1.3 拓扑调度

```
     A
    / \
   B   C
   |   |
   D   E
    \ /
     F
```

调度顺序：A → B/C（并行） → D/E（依赖 B/C） → F

## 2. 代码示例

### 2.1 极简工作流引擎

```python
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class Node:
    id: str
    execute: Callable[[dict], dict]
    next_ids: list[str] = field(default_factory=list)


@dataclass
class Graph:
    nodes: dict[str, Node]
    start_id: str


class MiniWorkflowEngine:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.variables: dict = {}
        self.finished = False

    def run(self) -> dict:
        current_id = self.graph.start_id
        while current_id:
            node = self.graph.nodes[current_id]
            print(f"执行节点: {node.id}")

            # 执行节点
            output = node.execute(self.variables)
            self.variables.update(output)

            # 简单场景：取第一个后继
            current_id = node.next_ids[0] if node.next_ids else None
        return self.variables


# 定义节点
def echo_node(name: str):
    def _run(vars):
        print(f"  [{name}] vars={vars}")
        return {"last": name}
    return Node(id=name, execute=_run, next_ids=[])


graph = Graph(
    nodes={
        "start": echo_node("start"),
        "middle": echo_node("middle"),
        "end": echo_node("end"),
    },
    start_id="start",
)
graph.nodes["start"].next_ids = ["middle"]
graph.nodes["middle"].next_ids = ["end"]

engine = MiniWorkflowEngine(graph)
engine.run()
```

### 2.2 处理分支

```python
class BranchingEngine:
    """支持条件分支的工作流引擎"""

    def run(self):
        current_id = self.graph.start_id
        while current_id:
            node = self.graph.nodes[current_id]
            output = node.execute(self.variables)

            # 根据条件选择下一个节点
            condition_key = output.get("__next__")
            next_ids = [nid for nid, cond in node.next_ids.items() if cond == condition_key]
            current_id = next_ids[0] if next_ids else None
```

### 2.3 处理循环

```python
class LoopingEngine:
    """支持循环的工作流引擎"""

    def run(self, max_iterations: int = 10):
        for _ in range(max_iterations):
            current_id = self.graph.start_id
            while current_id:
                node = self.graph.nodes[current_id]
                output = node.execute(self.variables)

                # 循环退出条件
                if output.get("__exit_loop__"):
                    return
                current_id = node.next_ids[0] if node.next_ids else None
```

## 3. 关键要点总结

- 工作流引擎核心：Graph（图）+ Node（节点）+ Engine（执行器）
- 用有向图描述节点和边的关系
- 用 BFS/DFS 做拓扑分析、上下游判断
- dify 通过 `WorkflowEntry` + `GraphEngine` 驱动执行
- 用系统变量（SystemVariable）注入运行时信息

---

**文档版本**：v1.0
**最后更新**：2026-07-13
