# 2.1.7 DDD 在 dify 中的实践：Workflow 执行链路分析

> 通过 Workflow 执行链路深入理解 DDD 在 dify 中的具体落地。

## 🎯 学习目标

完成本文档后，你将能够：
- 跟踪 dify 中 Workflow 执行的完整调用链路
- 识别每个层级（Controller → Service → Domain）的核心类
- 理解 Workflow 聚合根、Node 实体、Repository 三者的协作
- 通过阅读实际代码巩固 DDD 概念

## 📚 前置知识

- [实体、值对象、聚合根](../../_common/22-architecture/01-ddd-concepts.md)
- [分层架构](../../_common/22-architecture/02-layered-architecture.md)
- [Repository 模式](../../_common/22-architecture/03-repository-pattern.md)
- [领域服务 vs 应用服务](../../_common/22-architecture/04-domain-service.md)
- [领域事件](../../_common/22-architecture/06-domain-event.md)

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
| 工厂 | `DifyNodeFactory`、`WorkflowAppGenerator`（详见 [策略与工厂](./21-strategy-factory.md)） |
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

## 3. 关键要点总结

- **WorkflowExecution 是聚合根**：`WorkflowRun` 表 + `WorkflowNodeExecution` 表通过 `workflow_run_id` 关联
- **`WorkflowEntry` 是编排入口**：负责构建图、启动 GraphEngine、流式输出事件
- **`DifyNodeFactory` 是工厂**：根据 node_type 创建对应节点（Strategy + Factory 模式）
- **节点执行 = 调用领域服务**：每个节点的 `_run` 方法都按"取变量 → 拼 prompt → 审核 → 调用模型"顺序执行
- **领域服务集中在 `api/core/`**：提示词、内容审核、RAG 检索都是纯业务规则
- dify 用 `graphon` 库（图执行引擎）做底层编排，自己在上层封装 DDD 友好的接口

---

**文档版本**：v1.0
**最后更新**：2026-07-13
