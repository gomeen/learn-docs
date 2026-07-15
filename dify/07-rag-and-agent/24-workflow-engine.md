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
- Python 异步编程（详见 [async/asyncio](../01-fundamentals/12-async-asyncio.md)）
- 图执行 / 控制流直觉（节点与边将在后文展开，详见 [Workflow Nodes](./25-workflow-nodes.md)）

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

## 3. dify 仓库源码解读

### 3.1 WorkflowEntry 入口

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
**核心代码**（行 163-220）：

```python
class WorkflowEntry:
    def __init__(
        self,
        tenant_id: str,
        app_id: str,
        workflow_id: str,
        graph_config: Mapping[str, Any],
        graph: Graph,
        user_id: str,
        user_from: UserFrom,
        invoke_from: InvokeFrom,
        call_depth: int,
        variable_pool: VariablePool,
        graph_runtime_state: GraphRuntimeState,
        command_channel: CommandChannel | None = None,
        response_stream_filter: ResponseStreamFilter | None = None,
    ) -> None:
        # 检查调用深度（防止无限嵌套）
        workflow_call_max_depth = dify_config.WORKFLOW_CALL_MAX_DEPTH
        if call_depth > workflow_call_max_depth:
            raise ValueError(f"Max workflow call depth {workflow_call_max_depth} reached.")

        # 设置命令通道
        if command_channel is None:
            command_channel = InMemoryChannel()

        self.command_channel = command_channel
        self._response_stream_filter = response_stream_filter or ResponseStreamFilter()
        execution_context = capture_current_context()
        graph_runtime_state.execution_context = execution_context
        self._child_engine_builder = _WorkflowChildEngineBuilder(tenant_id=tenant_id)
        self.graph_engine = GraphEngine(
            workflow_id=workflow_id,
            graph=graph,
            graph_runtime_state=graph_runtime_state,
            command_channel=command_channel,
            config=GraphEngineConfig(
                min_workers=dify_config.GRAPH_ENGINE_MIN_WORKERS,
                ...
            ),
        )
```

**解读**：
- `WorkflowEntry` 是工作流的入口类
- `call_depth` 防止无限递归调用子工作流
- `GraphEngine` 实际驱动图执行，`WorkflowEntry` 负责包装和配置
- `command_channel` 是外部控制通道（如暂停、恢复）

### 3.2 Graph 拓扑分析

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`
**核心代码**（行 16-50）：

```python
class WorkflowGraphTopology:
    def __init__(self, *, node_ids: set[str], incoming: Mapping[str, Sequence[str]]) -> None:
        self._node_ids = node_ids
        self._incoming = incoming

    @classmethod
    def from_graph(cls, graph: Mapping[str, Any]) -> WorkflowGraphTopology:
        node_ids = cls._node_ids_from_graph(graph)
        incoming: dict[str, list[str]] = defaultdict(list)
        edges = graph.get("edges")
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, Mapping):
                    continue
                source = edge.get("source")
                target = edge.get("target")
                if isinstance(source, str) and isinstance(target, str):
                    incoming[target].append(source)
        return cls(node_ids=node_ids, incoming=incoming)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._node_ids

    def is_upstream(self, *, source_node_id: str, target_node_id: str) -> bool:
        if source_node_id == target_node_id:
            return False
        visited: set[str] = set()
        queue: deque[str] = deque(self._incoming.get(target_node_id, ()))
        while queue:
            candidate = queue.popleft()
            if candidate == source_node_id:
                return True
            if candidate in visited:
                continue
            visited.add(candidate)
```

**解读**：
- `WorkflowGraphTopology` 把图的 JSON 结构解析成拓扑结构
- `incoming` 字典：`target → [source1, source2, ...]`（反向索引）
- `is_upstream` 用 BFS 判断两个节点的上下游关系（用于校验 DAG）
- 这是图论算法的标准应用

### 3.3 系统变量定义

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/system_variables.py`
**核心代码**（行 22-40）：

```python
class SystemVariableKey(StrEnum):
    """系统级变量键"""
    QUERY = "query"
    FILES = "files"
    CONVERSATION_ID = "conversation_id"
    USER_ID = "user_id"
    DIALOGUE_COUNT = "dialogue_count"
    APP_ID = "app_id"
    WORKFLOW_ID = "workflow_id"
    WORKFLOW_EXECUTION_ID = "workflow_run_id"
    TIMESTAMP = "timestamp"
    DOCUMENT_ID = "document_id"
    ORIGINAL_DOCUMENT_ID = "original_document_id"
    BATCH = "batch"
    DATASET_ID = "dataset_id"
    DATASOURCE_TYPE = "datasource_type"
    DATASOURCE_INFO = "datasource_info"
    INVOKE_FROM = "invoke_from"
```

**解读**：
- 系统变量由引擎自动注入，所有节点都能访问
- 如 `query`（用户输入）、`conversation_id`（会话 ID）、`timestamp`（时间戳）
- 用 `StrEnum` 防止拼写错误，IDE 自动补全

## 4. 关键要点总结

- 工作流引擎核心：Graph（图）+ Node（节点）+ Engine（执行器）
- 用有向图描述节点和边的关系
- 用 BFS/DFS 做拓扑分析、上下游判断
- dify 通过 `WorkflowEntry` + `GraphEngine` 驱动执行
- 用系统变量（SystemVariable）注入运行时信息

## 5. 练习题

### 练习 1：基础（必做）

实现一个 MiniWorkflowEngine，支持顺序执行的 3 个节点，每个节点打印自己并把变量往下传。

### 练习 2：进阶

扩展你的引擎，支持条件分支：节点 A 输出 `__next__=B or C`，引擎根据条件选下一个节点。

### 练习 3：挑战（选做）

实现一个支持并行执行的引擎：当多个节点都满足依赖条件时，并发执行它们。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
- `/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`
- `/Users/xu/code/github/dify/api/core/workflow/system_variables.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13