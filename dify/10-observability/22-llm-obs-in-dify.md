# 10.5.5 dify 的 LLM 监控实现

> 综合 dify 的 LLM 可观测性实现：OTEL 自动埋点 + OpsTraceManager 业务 trace + 异步批量推送 + 第三方后端集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 dify LLM 可观测性的完整架构
- 理解 TraceTask 的生命周期（从创建到第三方后端）
- 能配置 dify 的全链路 LLM 监控
- 知道如何扩展 dify 的 LLM 可观测性

## 📚 前置知识

- 10.1 ~ 10.5 所有可观测性文档
- 04-cache-and-queue Celery 任务队列
- LLM 基本概念

## 1. 核心概念

### 1.1 dify LLM 可观测性的完整架构

```
┌─────────────────────────────────────────────────────────┐
│                    LLM 应用层                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Chat / Agent / Workflow / Completion App         │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM Node (graphon/llm_generator)                │  │
│  │  - 调用 LLM SDK                                   │  │
│  │  - 把 usage 写入 outputs 列                       │  │
│  └────────────────────────┬─────────────────────────┘  │
└───────────────────────────┼──────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Trace 数据层                            │
│  ┌──────────────┐    ┌──────────────────────────────┐  │
│  │  OTEL 自动埋点│    │  OpsTraceManager             │  │
│  │  (HTTP/DB/...)│    │  - TraceTask (业务事件)       │  │
│  └──────┬───────┘    └──────────┬───────────────────┘  │
└─────────┼──────────────────────┼──────────────────────────┘
          ↓                      ↓
┌─────────────────┐    ┌─────────────────────┐
│ OTEL Collector  │    │  TraceQueueManager   │
│ → Jaeger / Tempo│    │  → Celery task       │
└─────────────────┘    └──────────┬──────────┘
                                  ↓
                    ┌─────────────────────────┐
                    │  第三方追踪后端          │
                    │  Langfuse / Phoenix     │
                    │  LangSmith / Opik ...   │
                    └─────────────────────────┘
```

### 1.2 关键组件职责

| 组件 | 位置 | 职责 |
|------|------|------|
| `LLM Node` | `graphon/nodes/llm/` | 调用 LLM SDK，记录 usage |
| `OTEL Auto-instrumentation` | `extensions/otel/instrumentation.py` | 捕获 HTTP / DB / Redis 调用 |
| `OpsTraceManager` | `core/ops/ops_trace_manager.py` | 业务 trace 数据模型 + 缓存 |
| `TraceQueueManager` | `core/ops/ops_trace_manager.py` | 异步批量推送 |
| `process_trace_tasks` | `tasks/ops_trace_task.py` | Celery 任务，处理 trace |
| `TraceTask` | `core/ops/ops_trace_manager.py` | 业务 trace 数据结构 |

### 1.3 完整的 TraceTask 生命周期

```
1. 业务代码创建 TraceTask
   ↓
2. TraceQueueManager.add_trace_task(task) 加入内存队列
   ↓
3. 定时器（5s）触发 TraceQueueManager.run()
   ↓
4. collect_tasks() 批量取任务（最多 100 个）
   ↓
5. send_to_celery() 序列化到 storage，提交 Celery
   ↓
6. process_trace_tasks.delay() 异步处理
   ↓
7. Celery worker 加载 trace 信息，调用第三方 SDK
   ↓
8. 第三方后端（Langfuse / Phoenix）接收数据
```

### 1.4 支持的 Trace 类型

dify 支持 10+ 种 trace 类型，覆盖完整业务场景：

| Trace 类型 | 含义 | 触发场景 |
|------------|------|----------|
| `CONVERSATION_TRACE` | 对话 | 完整对话 |
| `WORKFLOW_TRACE` | 工作流执行 | 工作流结束 |
| `MESSAGE_TRACE` | 消息 | 每条 LLM 响应 |
| `MODERATION_TRACE` | 内容审核 | 触发审核时 |
| `SUGGESTED_QUESTION_TRACE` | 建议问题 | 生成建议问题时 |
| `DATASET_RETRIEVAL_TRACE` | 知识库检索 | RAG 检索时 |
| `TOOL_TRACE` | 工具调用 | Agent 调用工具 |
| `GENERATE_NAME_TRACE` | 对话命名 | 自动命名时 |
| `PROMPT_GENERATION_TRACE` | Prompt 生成 | 生成 Prompt 时 |
| `NODE_EXECUTION_TRACE` | 节点执行 | 工作流节点结束 |
| `DRAFT_NODE_EXECUTION_TRACE` | 草稿节点 | 草稿模式节点 |

## 2. 代码示例

### 2.1 完整追踪一个 LLM 调用

```python
# 业务代码示例（伪代码）
from core.ops.ops_trace_manager import TraceTask, TraceQueueManager
from core.ops.entities.trace_entity import TraceTaskName


def handle_chat_message(message_id: str, user_id: str, app_id: str):
    """处理用户聊天消息，完整追踪"""
    timer = {"start": datetime.now()}

    # 1. 调用 LLM
    response = llm_client.chat(messages=...)
    timer["end"] = datetime.now()

    # 2. 创建 TraceTask（消息级别）
    msg_trace = TraceTask(
        trace_type=TraceTaskName.MESSAGE_TRACE,
        message_id=message_id,
        user_id=user_id,
        timer=timer,
    )

    # 3. 加入异步队列
    queue_manager = TraceQueueManager(app_id=app_id, user_id=user_id)
    queue_manager.add_trace_task(msg_trace)

    return response
```

### 2.2 为自定义场景添加 trace

```python
# 自定义场景：批量 LLM 调用追踪
from core.ops.ops_trace_manager import TraceTask
from core.ops.entities.trace_entity import TraceTaskName


def batch_llm_call(tenant_id: str, user_id: str, app_id: str, items: list):
    """批量调用 LLM，每个 item 单独追踪"""
    queue_manager = TraceQueueManager(app_id=app_id, user_id=user_id)

    for item in items:
        timer = {"start": datetime.now()}
        response = llm_client.chat(messages=item["messages"])
        timer["end"] = datetime.now()

        # 创建 trace
        trace = TraceTask(
            trace_type=TraceTaskName.PROMPT_GENERATION_TRACE,
            tenant_id=tenant_id,
            user_id=user_id,
            app_id=app_id,
            instruction=item["prompt"],
            generated_output=response.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model_provider="openai",
            model_name=response.model,
            latency=(timer["end"] - timer["start"]).total_seconds(),
            timer=timer,
        )

        queue_manager.add_trace_task(trace)
```

### 2.3 通过 OTEL 协议追踪 LLM（自动）

```python
# dify 的 OTEL 集成自动捕获 LLM 调用的 Span
# 不需要手动编写，业务代码调用 LLM SDK 时自动记录

# 在 api/extensions/otel/instrumentation.py 中：
def init_instruments(app: DifyApp) -> None:
    if not is_celery_worker():
        init_flask_instrumentor(app)  # Flask HTTP 请求
        _new_celery_instrumentor().instrument()  # Celery 任务

    instrument_exception_logging()  # 异常日志
    init_sqlalchemy_instrumentor(app)  # 数据库
    init_redis_instrumentor()  # Redis
    init_httpx_instrumentor()  # 外部 HTTP
```

## 3. dify 仓库源码解读

### 3.1 TraceTask：业务 trace 的核心数据结构

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 737-797）：

```python
def __init__(
    self,
    trace_type: Any,
    message_id: str | None = None,
    workflow_execution: "WorkflowExecution | None" = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
    timer: Any | None = None,
    **kwargs,
):
    self.trace_type = trace_type
    self.message_id = message_id
    self.workflow_run_id = workflow_execution.id_ if workflow_execution else None
    self.workflow_total_tokens: int | None = workflow_execution.total_tokens if workflow_execution else None
    self.conversation_id = conversation_id
    self.user_id = user_id
    self.timer = timer
    self.file_base_url = os.getenv("FILES_URL", "http://127.0.0.1:5001")
    self.app_id = None
    self.trace_id = None
    self.kwargs = kwargs
    if user_id is not None and "user_id" not in self.kwargs:
        self.kwargs["user_id"] = user_id
    external_trace_id = kwargs.get("external_trace_id")
    if external_trace_id:
        self.trace_id = external_trace_id

def execute(self):
    return self.preprocess()

def preprocess(self):
    preprocess_map = {
        TraceTaskName.CONVERSATION_TRACE: lambda: self.conversation_trace(**self.kwargs),
        TraceTaskName.WORKFLOW_TRACE: lambda: self.workflow_trace(
            workflow_run_id=self.workflow_run_id,
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            total_tokens_override=self.workflow_total_tokens,
        ),
        TraceTaskName.MESSAGE_TRACE: lambda: self.message_trace(message_id=self.message_id, **self.kwargs),
        TraceTaskName.MODERATION_TRACE: lambda: self.moderation_trace(
            message_id=self.message_id, timer=self.timer, **self.kwargs
        ),
        TraceTaskName.SUGGESTED_QUESTION_TRACE: lambda: self.suggested_question_trace(
            message_id=self.message_id, timer=self.timer, **self.kwargs
        ),
        TraceTaskName.DATASET_RETRIEVAL_TRACE: lambda: self.dataset_retrieval_trace(
            message_id=self.message_id, timer=self.timer, **self.kwargs
        ),
        TraceTaskName.TOOL_TRACE: lambda: self.tool_trace(
            message_id=self.message_id, timer=self.timer, **self.kwargs
        ),
        TraceTaskName.GENERATE_NAME_TRACE: lambda: self.generate_name_trace(
            conversation_id=self.conversation_id, timer=self.timer, **self.kwargs
        ),
        TraceTaskName.PROMPT_GENERATION_TRACE: lambda: self.prompt_generation_trace(**self.kwargs),
        TraceTaskName.NODE_EXECUTION_TRACE: lambda: self.node_execution_trace(**self.kwargs),
        TraceTaskName.DRAFT_NODE_EXECUTION_TRACE: lambda: self.draft_node_execution_trace(**self.kwargs),
    }

    return preprocess_map.get(self.trace_type, lambda: None)()
```

**解读**：
- 第 12-27 行：构造函数接收各种业务参数
- 第 21-25 行：**外部 trace_id 支持**——可与上游 OTEL trace 关联
- 第 30-31 行：`execute()` 是入口
- 第 33-69 行：**dispatch map**——10+ 种 trace 类型映射到对应方法
- 第 70 行：未知类型返回 None（不抛异常）
- **关键设计**：
  - 单一数据结构支持多种业务场景
  - 外部 trace_id 支持跨系统关联
  - 异常安全（未知类型不报错）

### 3.2 异步批量推送的实现

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1485-1568）：

```python
trace_manager_timer: threading.Timer | None = None
trace_manager_queue: queue.Queue = queue.Queue()
trace_manager_interval = int(os.getenv("TRACE_QUEUE_MANAGER_INTERVAL", 5))
trace_manager_batch_size = int(os.getenv("TRACE_QUEUE_MANAGER_BATCH_SIZE", 100))


class TraceQueueManager:
    def __init__(self, app_id=None, user_id=None):
        global trace_manager_timer

        self.app_id = app_id
        self.user_id = user_id
        self.trace_instance = OpsTraceManager.get_ops_trace_instance(app_id)
        self.flask_app = current_app._get_current_object()

        from core.telemetry.gateway import is_enterprise_telemetry_enabled

        self._enterprise_telemetry_enabled = is_enterprise_telemetry_enabled()
        if trace_manager_timer is None:
            self.start_timer()

    def add_trace_task(self, trace_task: TraceTask):
        global trace_manager_timer, trace_manager_queue
        try:
            if self._enterprise_telemetry_enabled or self.trace_instance:
                trace_task.app_id = self.app_id
                trace_manager_queue.put(trace_task)
        except Exception:
            logger.exception("Error adding trace task, trace_type %s", task.trace_type)
        finally:
            self.start_timer()

    def collect_tasks(self):
        global trace_manager_queue
        tasks: list[TraceTask] = []
        while len(tasks) < trace_manager_batch_size and not trace_manager_queue.empty():
            task = trace_manager_queue.get_nowait()
            tasks.append(task)
            trace_manager_queue.task_done()
        return tasks

    def run(self):
        try:
            tasks = self.collect_tasks()
            if tasks:
                self.send_to_celery(tasks)
        except Exception:
            logger.exception("Error processing trace tasks")

    def start_timer(self):
        global trace_manager_timer
        if trace_manager_timer is None or not trace_manager_timer.is_alive():
            trace_manager_timer = threading.Timer(trace_manager_interval, self.run)
            trace_manager_timer.name = f"trace_manager_timer_{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
            trace_manager_timer.daemon = False
            trace_manager_timer.start()

    def send_to_celery(self, tasks: list[TraceTask]):
        with self.flask_app.app_context():
            for task in tasks:
                storage_id = task.app_id
                if storage_id is None:
                    tenant_id = task.kwargs.get("tenant_id")
                    if tenant_id:
                        storage_id = f"tenant-{tenant_id}"
                    else:
                        logger.warning("Skipping trace without app_id or tenant_id, trace_type: %s", task.trace_type)
                        continue

                file_id = uuid4().hex
                trace_info = task.execute()

                task_data = TaskData(
                    app_id=storage_id,
                    trace_info_type=type(trace_info).__name__,
                    trace_info=trace_info.model_dump() if trace_info else None,
                )
                file_path = f"{OPS_FILE_PATH}{storage_id}/{file_id}.json"
                storage.save(file_path, task_data.model_dump_json().encode("utf-8"))
                file_info = {
                    "file_id": file_id,
                    "app_id": storage_id,
                }
                process_trace_tasks.delay(file_info)
```

**解读**：
- 第 1-4 行：模块级全局状态
- 第 9-23 行：构造时获取 trace_instance + flask app + 启动定时器
- 第 25-34 行：业务调用——把 task 加入队列
- 第 36-44 行：定时器触发时批量取任务（最多 100 个）
- 第 46-52 行：处理任务，失败时记录异常
- 第 54-61 行：用 `threading.Timer` 调度下一次
- 第 63-95 行：**序列化到 storage + 提交 Celery**
  - 第 71-79 行：app_id 为空时用 tenant_id 兜底
  - 第 81-86 行：执行 task 获取 trace info，构造 TaskData
  - 第 87-88 行：写入 storage（JSON 文件）
  - 第 89-95 行：提交 Celery 异步任务
- **关键设计**：
  - 业务线程快速返回（只入队）
  - 后台定时器批量处理
  - storage 中转（避免 Celery 参数过大）
  - 全程异常安全

### 3.3 dify 的 OTEL 自动埋点

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 58-97）：

```python
class ExceptionLoggingHandler(logging.Handler):
    """
    Handler that records exceptions to the current OpenTelemetry span.

    Unlike creating a new span, this records exceptions on the existing span
    to maintain trace context consistency throughout the request lifecycle.
    """

    @override
    def emit(self, record: logging.LogRecord) -> None:
        with contextlib.suppress(Exception):
            if not record.exc_info:
                return

            from opentelemetry.trace import get_current_span

            span = get_current_span()
            if not span or not span.is_recording():
                return

            # Record exception on the current span instead of creating a new one
            span.set_status(StatusCode.ERROR, record.getMessage())

            # Add log context as span events/attributes
            span.add_event(
                "log.exception",
                attributes={
                    "log.level": record.levelname,
                    "log.message": record.getMessage(),
                    "log.logger": record.name,
                    "log.file.path": record.pathname,
                    "log.file.line": record.lineno,
                },
            )

            if record.exc_info[1]:
                span.record_exception(record.exc_info[1])
            if record.exc_info[0]:
                span.set_attribute("exception.type", record.exc_info[0].__name__)
```

**解读**：
- 第 8 行：用 `contextlib.suppress(Exception)` 让整个方法永不抛异常
- 第 14-18 行：把 span 标记为 ERROR，让 OTEL 后端可统计
- 第 21-29 行：用 `add_event` 把异常记录为 span 的事件
- 第 31-35 行：调用 `record_exception` 记录完整堆栈
- **关键设计**：日志异常自动转化为 span 状态，无须额外的 `errors_total` 计数器

### 3.4 dify 的工作流 Token 用量聚合

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 850-852）：

```python
prompt_tokens, completion_tokens = self._calculate_workflow_token_split(
    session, workflow_run_id=workflow_run_id, tenant_id=tenant_id
)
```

**解读**：
- dify 在每次工作流 trace 时，自动调用 `_calculate_workflow_token_split`
- 聚合所有节点的 prompt/completion token
- 写入 `WorkflowTraceInfo`，便于第三方后端展示成本

## 4. 关键要点总结

- dify LLM 可观测性：**OTEL 自动埋点** + **OpsTraceManager 业务 trace**
- **10+ 种 trace 类型**：消息、工作流、节点、工具调用、知识库检索等
- **异步批量推送**：业务线程入队 → 定时器批量 → Celery 异步
- **LRU 缓存**：避免重复创建 SDK client
- **多后端插件化**：通过 `OpsTraceProviderConfigMap` 支持 Langfuse 等 10+ 后端
- **异常安全**：未知 trace 类型返回 None，filter / handler 永不抛异常
- **跨系统关联**：支持 `external_trace_id` 与 OTEL trace 关联

## 5. 练习题

### 练习 1：基础（必做）

为 dify 配置完整的 LLM 监控栈：
1. 启用 OTEL（推送到 Collector → Jaeger）
2. 配置 Langfuse 作为 OpsTrace 后端
3. 触发一次工作流执行，在两个后端查看 trace
4. 验证 trace_id 关联是否正确

### 练习 2：进阶

阅读 `api/core/ops/ops_trace_manager.py` 的全部核心代码，画出 dify LLM trace 的完整数据流图：业务事件 → TraceTask → 内存队列 → 定时器 → storage → Celery → 第三方后端。

### 练习 3：挑战（选做）

实现一个 `TraceAnalyzer`：从 `WorkflowNodeExecutionModel.outputs` 表中读取 LLM 用量数据，按租户、模型、应用、时间维度聚合，生成可视化报告。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- `/Users/xu/code/github/dify/api/tasks/ops_trace_task.py`
- Langfuse 文档：https://langfuse.com/docs
- OpenTelemetry GenAI 语义约定：https://opentelemetry.io/docs/specs/semconv/gen-ai/

---

**文档版本**：v1.0
**最后更新**：2026-07-13