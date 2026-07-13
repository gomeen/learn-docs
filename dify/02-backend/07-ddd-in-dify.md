# 2.1.7 DDD 在 dify 中的实践：Workflow 执行链路分析

> 通过 Workflow 执行链路深入理解 DDD 在 dify 中的具体落地。

## 🎯 学习目标

完成本文档后，你将能够：
- 跟踪 dify 中 Workflow 执行的完整调用链路
- 识别每个层级（Controller → Service → Domain）的核心类
- 理解 Workflow 聚合根、Node 实体、Repository 三者的协作
- 通过阅读实际代码巩固 DDD 概念

## 📚 前置知识

- 02-backend/01-ddd-concepts.md（实体、值对象、聚合根）
- 02-backend/02-layered-architecture.md（分层架构）
- 02-backend/03-repository-pattern.md（Repository 模式）
- 02-backend/04-domain-service.md（领域服务 vs 应用服务）
- 02-backend/06-domain-event.md（领域事件）

## 1. 核心概念

### 1.1 Workflow 执行链路的全貌

一次 Workflow 执行涉及多个 DDD 元素：

```
用户触发 (HTTP POST /v1/workflows/run)
  ↓
[Controller 层]  api/controllers/service_api/app/workflow.py
  WorkflowRunApi.post()
  ↓
[Service 层]  api/services/workflow_service.py
  WorkflowService.run()
  ↓
[Domain 层]   api/core/workflow/workflow_entry.py
  WorkflowEntry.run()  ← 聚合根
  ├─ 构建 Graph（图结构）
  ├─ 启动 GraphEngine
  └─ 逐节点执行（Node 实体）
      ├─ Start Node
      ├─ LLM Node  ← 调用 LLM Provider
      ├─ Code Node  ← 执行 Python 代码
      ├─ HTTP Request Node
      └─ End Node
  ↓
[Repository 层]  api/core/repositories/
  ├─ WorkflowExecutionRepository.save()
  └─ WorkflowNodeExecutionRepository.save()
  ↓
[事件] app_was_published / app_was_run
```

### 1.2 关键 DDD 元素对照

| DDD 概念 | dify 实现 |
|---------|-----------|
| 聚合根 | `WorkflowExecution`、`Workflow` |
| 实体 | `WorkflowNodeExecution`（聚合内实体） |
| 值对象 | `RetrievalSourceMetadata`、`FileReference`、`MessageFile` |
| 领域服务 | `SimplePromptTransform`、`InputModeration` |
| 应用服务 | `WorkflowService`、`AppService` |
| Repository | `WorkflowExecutionRepository` (Protocol) |
| 工厂 | `DifyNodeFactory`、`WorkflowAppGenerator` |
| 事件 | `app_was_created`、`app_was_published` |

### 1.3 执行模式

dify 的 Workflow 执行有两种模式：

1. **Streaming（流式）**：逐节点返回事件（`message` → `message_end`），用于 WebApp
2. **Blocking（阻塞）**：等待整个 workflow 完成后一次性返回，用于 API

dify 用 **Queue + Worker 模式** 把节点执行结果异步推送给客户端（参见 `api/core/app/entities/queue_entities.py`）。

## 2. 代码示例

### 2.1 Workflow 执行的核心结构

```python
# 简化的 Workflow 执行流程（伪代码）

class WorkflowExecution:  # 聚合根
    def __init__(self, workflow_id, tenant_id, inputs):
        self.id = str(uuid.uuid4())
        self.workflow_id = workflow_id
        self.tenant_id = tenant_id
        self.inputs = inputs
        self.status = "running"
        self.node_executions = []  # 聚合内实体集合
        self.outputs = None

    def add_node_execution(self, node_id: str, node_type: str, status: str):
        """添加节点执行记录"""
        node_exe = WorkflowNodeExecution(
            id=str(uuid.uuid4()),
            workflow_run_id=self.id,  # 引用聚合根
            node_id=node_id,
            node_type=node_type,
            status=status,
        )
        self.node_executions.append(node_exe)
        return node_exe

    def complete(self, outputs: dict):
        self.status = "succeeded"
        self.outputs = outputs


class WorkflowExecutionService:  # 应用服务
    def __init__(self, repo: WorkflowExecutionRepository, queue: EventQueue):
        self._repo = repo
        self._queue = queue

    def run(self, workflow_id: str, inputs: dict) -> WorkflowExecution:
        # 1. 创建聚合根
        execution = WorkflowExecution(workflow_id, tenant_id="...", inputs=inputs)

        # 2. 持久化初始状态
        self._repo.save(execution)

        # 3. 异步执行（实际用 Celery）
        for node in self._topological_sort(workflow_id):
            # 4. 执行节点
            result = node.execute(execution.inputs)
            node_exe = execution.add_node_execution(node.id, node.type, "succeeded")
            self._queue.publish(QueueNodeSucceededEvent(node_exe))

        # 5. 完成聚合根
        execution.complete({"result": "..."})
        self._repo.save(execution)
        return execution
```

### 2.2 节点（Node）的多态执行

```python
from abc import ABC, abstractmethod

class Node(ABC):  # 节点抽象
    @abstractmethod
    def execute(self, inputs: dict) -> dict: ...


class LLMNode(Node):
    def __init__(self, model_config, prompt_template):
        self._model_config = model_config
        self._prompt_template = prompt_template

    def execute(self, inputs: dict) -> dict:
        # 调用 LLM
        prompt = self._prompt_template.render(inputs)
        result = self._model_config.invoke(prompt)
        return {"text": result}


class CodeNode(Node):
    def __init__(self, code: str, language: str):
        self._code = code
        self._language = language

    def execute(self, inputs: dict) -> dict:
        # 执行 Python 代码（沙箱）
        result = sandbox.execute(self._code, inputs)
        return result
```

## 3. dify 仓库源码解读

### 3.1 聚合根：`WorkflowExecution`

**文件位置**：`/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py`
**核心代码**（行 1-40）：

```python
from graphon.entities import WorkflowExecution, WorkflowNodeExecution
from graphon.enums import WorkflowExecutionStatus, WorkflowType

class SQLAlchemyWorkflowExecutionRepository(WorkflowExecutionRepository):
    """
    SQLAlchemy implementation of the WorkflowExecutionRepository interface.

    WorkflowExecution 是 Workflow 执行的聚合根：
    - 每次执行创建一条 WorkflowExecution 记录
    - 每个节点执行创建一条 WorkflowNodeExecution 记录（聚合内实体）
    - 通过 workflow_execution_id 关联，确保一致性边界
    """
    def save(self, execution: WorkflowExecution):
        """保存聚合根到 WorkflowRun 表"""
        run = WorkflowRun(
            id=execution.id_,
            tenant_id=execution.tenant_id,
            app_id=execution.app_id,
            workflow_id=execution.workflow_id,
            status=execution.status.value,
            inputs=execution.inputs_dump(),
            outputs=execution.outputs_dump() if execution.outputs else None,
        )
        self._session.merge(run)
        self._session.commit()
```

**解读**：
- 第 14 行：导入 `WorkflowExecution`、`WorkflowNodeExecution`（领域对象，由 graphon 提供）
- 第 16-19 行：注释说明这是聚合根 + 聚合内实体的关系
- 第 20-25 行：`save` 方法负责持久化聚合根到 `WorkflowRun` 表
- 第 28-29 行：`execution.inputs_dump()` 把领域对象转为 JSON 字符串存储

### 3.2 领域编排：`WorkflowEntry`

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
**核心代码**（行 49-70）：

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

    ``response_stream_filter``, when supplied, must be the same instance a
    caller intends to persist on pause (see ``PauseStatePersistenceLayer``) so
    the filter's ``paths_map`` reflects everything the engine has actually
    streamed for this run.
    """
    yield from filter_graph_events(
        engine.run(),
        context=GraphEventFilterContext.from_engine(engine),
        filters=[response_stream_filter or ResponseStreamFilter()],
    )
```

**解读**：
- 第 1-5 行：`iter_dify_graph_engine_events` 是一个生成器，把 GraphEngine 的事件流过滤后逐个产出
- 第 17-20 行：`filter_graph_events` 是关键的过滤层——dify 在 Graphon（底层图执行引擎）之上增加了响应流兼容过滤
- **设计意图**：把"领域执行"和"对外暴露的事件流"解耦，GraphEngine 不需要知道 dify 的 streaming 协议

### 3.3 节点工厂：`DifyNodeFactory`

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/node_factory.py`
**核心代码**（行 70-110）：

```python
@dataclass(frozen=True, slots=True)
class DifyGraphInitContext:
    """初始化上下文：构造节点所需的全部依赖。"""
    tenant_id: str
    app_id: str
    user_id: str
    invoke_from: InvokeFrom
    ...


class DifyNodeFactory:
    """节点工厂：根据 node_type 创建对应的 Node 实例。"""
    def create_node(self, node_config: NodeConfigDict, ...) -> Node:
        """工厂方法：根据配置创建不同类型的节点。"""
        node_type = node_config.get("data", {}).get("type")
        if node_type == "start":
            return StartNode(...)
        elif node_type == "llm":
            return LLMNode(...)
        elif node_type == "code":
            return CodeNode(...)
        ...
```

**解读**：
- 第 4-10 行：`DifyGraphInitContext` 封装构造节点所需的全部依赖（tenant、app、user、invoke_from）
- 第 14-26 行：`DifyNodeFactory` 是**工厂模式**：根据 `node_type` 字符串创建不同节点
- **DDD 意义**：把节点的"构造"和"执行"分离，工厂聚合根（Graph）负责组装各个节点

### 3.4 节点执行的领域服务：`LLMNode`

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/llm/`
**核心代码**（节点伪代码）：

```python
# 伪代码，展示 LLM 节点的执行逻辑
class LLMNode(Node):
    def __init__(self, data: LLMNodeData, context: DifyGraphInitContext):
        self._data = data  # 节点配置（prompt、model、temperature 等）
        self._context = context

    def _run(self) -> NodeRunResult:
        """节点执行入口"""
        # 1. 解析变量
        variables = self._graph_runtime_state.variable_pool.get_all()

        # 2. 调用领域服务：拼装 prompt（SimplePromptTransform / AdvancedPromptTransform）
        prompt_messages = SimplePromptTransform(
            prompt_template=self._data.prompt_template,
            inputs=variables,
        ).get_prompt()

        # 3. 调用领域服务：内容审核（InputModeration / OutputModeration）
        InputModeration(...).check()

        # 4. 调用 ModelInstance（基础设施）
        model_instance = ModelInstance(...)
        result = model_instance.invoke_llm(
            prompt_messages=prompt_messages,
            model_parameters=self._data.model_parameters,
        )

        # 5. 构造输出
        return NodeRunResult(
            outputs={"text": result.content},
            usage=result.usage,
        )
```

**解读**：
- 第 6 行：`_run` 是节点执行入口（被 GraphEngine 调用）
- 第 9 行：从变量池取所有变量（值对象集合）
- 第 12 行：调用**领域服务** `SimplePromptTransform` 拼装 prompt
- 第 15 行：调用**领域服务** `InputModeration` 做内容审核
- 第 18-22 行：调用 `ModelInstance` 调用 LLM（基础设施层）
- 第 25-28 行：构造 `NodeRunResult`（领域对象的执行结果）

## 4. 关键要点总结

- **WorkflowExecution 是聚合根**：`WorkflowRun` 表 + `WorkflowNodeExecution` 表通过 `workflow_run_id` 关联
- **`WorkflowEntry` 是编排入口**：负责构建图、启动 GraphEngine、流式输出事件
- **`DifyNodeFactory` 是工厂**：根据 node_type 创建对应节点（Strategy + Factory 模式）
- **节点执行 = 调用领域服务**：每个节点的 `_run` 方法都按"取变量 → 拼 prompt → 审核 → 调用模型"顺序执行
- **领域服务集中在 `api/core/`**：提示词、内容审核、RAG 检索都是纯业务规则
- dify 用 `graphon` 库（图执行引擎）做底层编排，自己在上层封装 DDD 友好的接口

## 5. 练习题

### 练习 1：基础（必做）

画出"用户调用 `/v1/workflows/run`"的完整调用时序图，包含：
- Controller 层（哪个文件？）
- Service 层（哪个方法？）
- Domain 层（`WorkflowEntry`、`GraphEngine`）
- Repository 层（保存执行记录）

### 练习 2：进阶

阅读 `api/core/workflow/nodes/code/` 目录下的代码：
1. `CodeNode` 的执行流程是什么？
2. 它如何保证 Python 代码执行的安全性？（沙箱？）
3. 它调用了哪些领域服务？

### 练习 3：挑战（选做）

在 dify 中新增一个节点类型 `TranslateNode`（翻译节点），要求：
1. 定义节点配置（`TranslateNodeData`）
2. 实现 `TranslateNode._run()`：调用 LLM 进行翻译
3. 在 `DifyNodeFactory` 中注册新节点类型
4. 在前端配置面板中添加翻译节点（可选）

完成后说明：哪些是 Domain 层？哪些是 Infrastructure 层？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py` — Workflow 入口
- `/Users/xu/code/github/dify/api/core/workflow/node_factory.py` — 节点工厂
- `/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py` — Repository 实现
- `/Users/xu/code/github/dify/api/core/app/apps/workflow_app_runner.py` — 应用层编排
- `/Users/xu/code/github/dify/api/services/workflow_service.py` — 应用服务
- `/Users/xu/code/github/dify/api/core/workflow/nodes/` — 各节点实现

---

**文档版本**：v1.0
**最后更新**：2026-07-13