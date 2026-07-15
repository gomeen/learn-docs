# 7.5.5 工作流的执行与状态管理

> 理解工作流执行的全生命周期：启动、执行、暂停、恢复、终止、状态查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述工作流执行的完整生命周期
- 理解 GraphRuntimeState 的状态管理
- 看懂 dify 中工作流执行的入口与核心类
- 理解暂停/恢复的实现原理

## 📚 前置知识

- [Workflow Engine](./24-workflow-engine.md)
- [Workflow Nodes](./25-workflow-nodes.md)
- 异步执行与任务队列（Celery 背景详见 [Celery 架构](../04-cache-and-queue/14-celery-architecture.md)）

## 1. 核心概念

### 1.1 工作流的执行生命周期

```
触发 → 初始化 → 图构建 → 节点调度
  ├─ 同步执行（正常路径）
  ├─ 异步执行（Celery worker）
  ├─ 暂停（等待人工/外部输入）
  ├─ 恢复（继续执行）
  └─ 终止（异常/用户取消）
       ↓
   状态持久化 + 结果返回
```

### 1.2 GraphRuntimeState

工作流执行时的运行时状态：

```python
@dataclass
class GraphRuntimeState:
    variable_pool: VariablePool       # 变量池
    start_at: float                   # 启动时间
    execution_context: Context        # 上下文（trace ID、用户 ID 等）
    paused_nodes: list[str]           # 暂停的节点
    failed_nodes: list[str]           # 失败的节点
    finished_nodes: list[str]         # 已完成的节点
```

### 1.3 命令通道（Command Channel）

dify 用命令通道控制工作流：

```python
class CommandChannel:
    """外部控制工作流的通道"""

    def pause(self): ...
    def resume(self): ...
    def stop(self): ...
```

## 2. 代码示例

### 2.1 工作流执行入口

```python
import asyncio
from dataclasses import dataclass, field


@dataclass
class WorkflowExecution:
    workflow_id: str
    status: str = "pending"  # pending / running / paused / completed / failed
    current_nodes: list[str] = field(default_factory=list)
    variable_pool: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)


class WorkflowRunner:
    def __init__(self, workflow_def):
        self.def_ = workflow_def

    async def run(self, inputs: dict) -> WorkflowExecution:
        exec_ = WorkflowExecution(workflow_id="run_123", status="running")
        exec_.variable_pool.update(inputs)

        try:
            # 按拓扑顺序执行
            ready = self._initial_ready_nodes()
            while ready:
                # 并发执行所有 ready 节点
                results = await asyncio.gather(*[
                    self._run_node(n, exec_) for n in ready
                ])
                # 更新状态
                exec_.current_nodes = [n.id for n in ready]
                # 找出下一批 ready
                ready = self._next_ready_nodes()

            exec_.status = "completed"
        except Exception as e:
            exec_.status = "failed"
            exec_.result["error"] = str(e)

        return exec_
```

### 2.2 暂停与恢复

```python
class PausableWorkflowRunner(WorkflowRunner):
    """支持暂停/恢复的工作流"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 默认允许执行

    async def pause(self):
        self._pause_event.clear()

    async def resume(self):
        self._pause_event.set()

    async def _run_node(self, node, exec_):
        # 在执行关键节点前检查暂停
        await self._pause_event.wait()
        return await super()._run_node(node, exec_)
```

### 2.3 状态持久化

```python
class WorkflowStatePersistence:
    """把工作流状态存到数据库，支持跨进程恢复"""

    @classmethod
    def save(cls, workflow_run_id: str, state: dict):
        db.execute(
            "INSERT INTO workflow_runs (id, state, updated_at) VALUES (%s, %s, NOW())",
            (workflow_run_id, json.dumps(state)),
        )

    @classmethod
    def load(cls, workflow_run_id: str) -> dict | None:
        row = db.execute(
            "SELECT state FROM workflow_runs WHERE id = %s", (workflow_run_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None
```

### 2.4 常见错误：执行状态不持久化

```python
# ❌ 错误：进程崩溃后所有状态丢失
async def run(self):
    state = {}  # 只在内存
    await execute(state)  # 崩溃就丢

# ✅ 正确：关键状态写入数据库
async def run(self):
    state = {}
    save_to_db("run_123", state)
    await execute(state)
    save_to_db("run_123", state)  # 定期保存
```

## 3. dify 仓库源码解读

### 3.1 GraphEngine 的构建

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`（行 210-240）
**核心代码**：

```python
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
- `GraphEngine` 是 dify 工作流执行的真正驱动者（在 graphon 库）
- `command_channel` 是外部控制通道（暂停/恢复/停止）
- `min_workers` 是并发执行的最小工作线程数

### 3.2 子工作流构建器

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`（行 72-100）
**核心代码**：

```python
class _WorkflowChildEngineBuilder:
    """构建子工作流引擎（用于嵌套调用）"""

    tenant_id: str

    def __init__(self, *, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    @staticmethod
    def _has_node_id(graph_config: Mapping[str, Any], node_id: str) -> bool | None:
        """检查 graph_config 中是否包含指定节点 ID"""
        nodes = graph_config.get("nodes")
        if not isinstance(nodes, list):
            return None

        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            current_id = node.get("id")
            if isinstance(current_id, str) and current_id == node_id:
                return True
        return False

    def build_child_engine(
        self,
        *,
        workflow_id: str,
        graph_init_params: GraphInitParams,
        parent_graph_runtime_state: GraphRuntimeState,
        root_node_id: str,
        variable_pool: VariablePool | None = None,
    ) -> GraphEngine:
        """Build a child engine with a fresh runtime state and only child-safe layers."""
```

**解读**：
- 支持工作流嵌套调用（子工作流）
- 子工作流有独立的 `runtime_state`，避免污染父状态
- 通过 `LLMQuotaLayer` 等 layer 做配额管理

### 3.3 ResponseStreamFilter

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`（行 49-69）
**核心代码**：

```python
def iter_dify_graph_engine_events(
    engine: GraphEngine,
    response_stream_filter: ResponseStreamFilter | None = None,
) -> Generator[GraphEngineEvent, None, None]:
    """
    Apply Dify's response streaming compatibility filter to GraphEngine events.

    Graphon v0.5.0 emits raw variable stream chunks and requires callers to opt
    into the legacy response-ordered stream behavior that Dify exposes to its
    workflow runners and tests.
    """
    yield from filter_graph_events(
        engine.run(),
        context=GraphEventFilterContext.from_engine(engine),
        filters=[response_stream_filter or ResponseStreamFilter()],
    )
```

**解读**：
- 工作流事件流式返回（Generator）
- `ResponseStreamFilter` 过滤并排序事件，让前端能按用户预期的顺序展示
- 这是 dify 与 graphon 库的兼容层

## 4. 关键要点总结

- 工作流执行入口：`WorkflowEntry` → `GraphEngine`
- GraphRuntimeState 管理运行时状态
- CommandChannel 支持暂停/恢复/停止
- 支持子工作流嵌套（`_WorkflowChildEngineBuilder`）
- 状态需要持久化以支持跨进程恢复

## 5. 练习题

### 练习 1：基础（必做）

实现一个 WorkflowRunner，支持按拓扑顺序执行节点，并把状态存到 dict。

### 练习 2：进阶

扩展你的 Runner，支持暂停/恢复：用 asyncio.Event 控制执行流。

### 练习 3：挑战（选做）

设计一个工作流状态持久化方案：每个节点执行完都写入 Redis，支持崩溃后从 Redis 恢复。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
- `/Users/xu/code/github/dify/api/core/workflow/graph_topology.py`
- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13