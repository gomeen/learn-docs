# 10.3.4 dify 的链路追踪实现

> 深入 dify 的链路追踪实现：OTEL 自动埋点 + 应用层 trace manager，理解工作流执行如何被记录。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 dify 双层追踪架构：OTEL + OpsTraceManager
- 掌握工作流执行 trace 的完整流程
- 能在 dify 中扩展自定义 trace
- 知道 dify 支持哪些第三方追踪后端

## 📚 前置知识

- 10.3.2 OpenTelemetry 标准（`12-opentelemetry.md`）
- 10.3.3 Jaeger / Zipkin 实战（`13-jaeger-zipkin.md`）
- 04-cache-and-queue Celery 任务队列

## 1. 核心概念

### 1.1 dify 的双层追踪架构

```
┌────────────────────────────────────────────────┐
│  Layer 1: OTEL 自动追踪（基础设施层）           │
│  - Flask / Celery / SQLAlchemy / Redis 自动埋点 │
│  - 输出到 OTEL Collector → Jaeger / Tempo       │
└────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────┐
│  Layer 2: OpsTraceManager（业务层）             │
│  - 工作流执行 / 消息 / 工具调用 trace           │
│  - 输出到 Langfuse / Phoenix / Arize 等         │
└────────────────────────────────────────────────┘
```

**为什么要双层？**
- **OTEL**：捕获底层调用（HTTP、DB、Redis）
- **OpsTrace**：捕获业务事件（工作流节点、LLM 调用、用户反馈）

### 1.2 OpsTraceManager 的核心职责

**文件位置**：`api/core/ops/ops_trace_manager.py`

```
OpsTraceManager（单例）
├── OpsTraceProviderConfigMap  # 第三方追踪后端注册表
├── OpsTraceManager             # trace 实例缓存 + 解密
├── TraceTask                   # 异步任务队列
└── TraceQueueManager           # 批量推送到 Celery
```

### 1.3 支持的第三方追踪后端

dify 在 `OpsTraceProviderConfigMap` 中定义了 10+ 个追踪后端：

| 后端 | 用途 | 特点 |
|------|------|------|
| **Langfuse** | LLM 专用 | 开源、自托管、UI 友好 |
| **LangSmith** | LLM 专用 | LangChain 官方 |
| **Opik** | LLM 专用 | Comet 开源 |
| **Phoenix** | Arize 开源 | LLM 可观测性 |
| **Arize** | Arize 商业版 | 企业级 |
| **Weave** | Weights & Biases | 实验追踪 |
| **MLflow** | ML 通用 | Databricks 维护 |
| **Databricks** | 企业级 | Databricks 平台 |
| **Aliyun** | 阿里云 | 国内云服务 |
| **Tencent** | 腾讯云 | 国内云服务 |

### 1.4 异步 trace 任务队列

dify 用内存队列 + 定时器把 trace 批量推送到 Celery：

```
业务事件 → TraceQueueManager.add_trace_task()
                ↓ 内存 Queue
        Timer (5s) 触发
                ↓
        TraceQueueManager.run()
                ↓ 批量
        Celery task: process_trace_tasks
                ↓
        第三方追踪后端
```

## 2. 代码示例

### 2.1 启动工作流时创建 TraceTask

```python
# 伪代码：业务调用 OpsTraceManager
from core.ops.ops_trace_manager import TraceTask, OpsTraceManager
from core.ops.entities.trace_entity import TraceTaskName

# 业务触发 trace
trace_task = TraceTask(
    trace_type=TraceTaskName.WORKFLOW_TRACE,
    workflow_execution=execution,
    conversation_id=conversation_id,
    user_id=user_id,
)

# 加入异步队列
queue_manager = TraceQueueManager(app_id=app_id, user_id=user_id)
queue_manager.add_trace_task(trace_task)
```

### 2.2 配置 dify 使用 Langfuse

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

通过 dify 控制台配置 app-level tracing，详见 5.1 LLM 调用追踪。

## 3. dify 仓库源码解读

### 3.1 第三方追踪后端注册表

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 223-339）：

```python
class OpsTraceProviderConfigMap(collections.UserDict[str, TracingProviderConfigEntry]):
    @override
    def __getitem__(self, key: str) -> TracingProviderConfigEntry:
        try:
            match key:
                case TracingProviderEnum.LANGFUSE:
                    from dify_trace_langfuse.config import LangfuseConfig
                    from dify_trace_langfuse.langfuse_trace import LangFuseDataTrace

                    return {
                        "config_class": LangfuseConfig,
                        "secret_keys": ["public_key", "secret_key"],
                        "other_keys": ["host", "project_key"],
                        "trace_instance": LangFuseDataTrace,
                    }

                case TracingProviderEnum.LANGSMITH:
                    from dify_trace_langsmith.config import LangSmithConfig
                    from dify_trace_langsmith.langsmith_trace import LangSmithDataTrace

                    return {
                        "config_class": LangSmithConfig,
                        "secret_keys": ["api_key"],
                        "other_keys": ["project", "endpoint"],
                        "trace_instance": LangSmithDataTrace,
                    }

                case TracingProviderEnum.OPIK:
                    from dify_trace_opik.config import OpikConfig
                    from dify_trace_opik.opik_trace import OpikDataTrace

                    return {
                        "config_class": OpikConfig,
                        "secret_keys": ["api_key"],
                        "other_keys": ["project", "url", "workspace"],
                        "trace_instance": OpikDataTrace,
                    }

                case TracingProviderEnum.WEAVE:
                    from dify_trace_weave.config import WeaveConfig
                    from dify_trace_weave.weave_trace import WeaveDataTrace

                    return {
                        "config_class": WeaveConfig,
                        "secret_keys": ["api_key"],
                        "other_keys": ["project", "entity", "endpoint", "host"],
                        "trace_instance": WeaveDataTrace,
                    }
                # ... 还有 ARIZE / PHOENIX / ALIYUN / MLFLOW / DATABRICKS / TENCENT

                case _:
                    raise KeyError(f"Unsupported tracing provider: {key}")
        except ImportError:
            raise ImportError(f"Provider {key} is not installed.")


provider_config_map = OpsTraceProviderConfigMap()
```

**解读**：
- 第 1 行：继承 `UserDict`，实现 `__getitem__` 时按需导入（lazy import）
- 第 4-5 行：用 `match/case` 实现分发，比 `if/elif` 更清晰
- 第 7-15 行：每个 provider 返回统一的 4 字段结构（config_class / secret_keys / other_keys / trace_instance）
- 第 8-10 行：用 lazy import，避免加载未使用的 provider
- 第 11-12 行：`secret_keys` 标记需要加密的字段，`other_keys` 是非敏感字段
- **关键设计**：插件化架构——新增追踪后端只需要添加一个 `case`

### 3.2 trace 实例缓存 + 配置解密

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 343-540）：

```python
class OpsTraceManager:
    ops_trace_instances_cache: LRUCache = LRUCache(maxsize=128)
    decrypted_configs_cache: LRUCache = LRUCache(maxsize=128)
    _decryption_cache_lock = threading.RLock()

    # ... 省略 encrypt/decrypt 方法 ...

    @classmethod
    def get_ops_trace_instance(
        cls,
        app_id: UUID | str | None = None,
    ):
        """
        Get ops trace through model config
        """
        if isinstance(app_id, UUID):
            app_id = str(app_id)

        if app_id is None:
            return None

        # Handle storage_id format (tenant-{uuid}) - not a real app_id
        if isinstance(app_id, str) and app_id.startswith("tenant-"):
            return None

        app = db.session.get(App, app_id)

        if app is None:
            return None

        app_ops_trace_config = _app_tracing_config_adapter.validate_json(app.tracing) if app.tracing else None
        if app_ops_trace_config is None:
            return None
        if not app_ops_trace_config.get("enabled"):
            return None

        tracing_provider = app_ops_trace_config.get("tracing_provider")
        if tracing_provider is None:
            return None
        try:
            provider_config_map[tracing_provider]
        except KeyError:
            return None

        # decrypt_token
        decrypt_trace_config = cls.get_decrypted_tracing_config(app_id, tracing_provider)
        if not decrypt_trace_config:
            return None

        trace_instance, config_class = (
            provider_config_map[tracing_provider]["trace_instance"],
            provider_config_map[tracing_provider]["config_class"],
        )
        decrypt_trace_config_key = json.dumps(decrypt_trace_config, sort_keys=True)
        tracing_instance = cls.ops_trace_instances_cache.get(decrypt_trace_config_key)
        if tracing_instance is None:
            # create new tracing_instance and update the cache if it absent
            tracing_instance = trace_instance(config_class(**decrypt_trace_config))
            cls.ops_trace_instances_cache[decrypt_trace_config_key] = tracing_instance
            logger.info("new tracing_instance for app_id: %s", app_id)
        return tracing_instance
```

**解读**：
- 第 3-5 行：两个 LRU 缓存（最大 128）+ 线程锁
- 第 18-22 行：app_id 是 UUID 时转为字符串
- 第 25-28 行：处理 `tenant-{uuid}` 这种 storage_id 格式（不是真实 app_id）
- 第 38-41 行：从 `App.tracing` 字段读取配置（JSON 格式）
- 第 43-44 行：未启用 trace 直接返回 None（性能优化）
- 第 48-50 行：未注册的 provider 返回 None，不抛异常
- 第 53-55 行：获取解密的 trace 配置（API key 等敏感字段）
- 第 57-59 行：从配置 map 获取 trace instance class
- 第 60-65 行：**LRU 缓存**——相同配置复用同一个 instance
- **关键设计**：缓存避免每次都解密 + 创建 SDK client，节省 ~100ms

### 3.3 TraceTask：业务 trace 的数据结构

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 651-797）：

```python
class TraceTask:
    _workflow_run_repo = None
    _repo_lock = threading.Lock()

    # ... 省略 _calculate_workflow_token_split / _get_user_id_from_metadata ...

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
- 第 16-37 行：`__init__` 接收各种业务参数（message_id / workflow_execution / 等）
- 第 33-36 行：`trace_id` 可以从外部传入（如 OTEL 上游），用于跨系统关联
- 第 39-41 行：`execute()` 是入口方法，调用 `preprocess()`
- 第 43-78 行：`preprocess_map` 是 dispatch 表（10+ 种 trace 类型）
- 第 79 行：未知类型返回 None（不抛异常，避免影响业务）
- **关键设计**：用 dispatch table 而不是 if/elif，新增 trace 类型只需要加一个 case

### 3.4 异步队列 + 批量推送

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
        self.flask_app = current_app._get_current_object()  # type: ignore

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
                process_trace_tasks.delay(file_info)  # type: ignore
```

**解读**：
- 第 1-4 行：模块级全局状态——queue、timer、间隔、批量大小
- 第 11-23 行：构造时获取 trace instance（LRU 缓存）
- 第 19 行：`_get_current_object()` 获取真实 Flask app（不是 proxy）
- 第 26-33 行：业务调用 `add_trace_task` 时，把 task 加入队列
- 第 35-43 行：定时器触发时，批量取任务（最多 100 个）
- 第 50-58 行：用 `threading.Timer` 重新调度下一次执行
- 第 60-83 行：**序列化 task 到 storage，然后通过 Celery 异步处理**——避免阻塞请求
- 第 73-76 行：用 UUID 作为文件名，保证唯一性
- **关键设计**：业务线程 → 内存 queue → Celery 异步任务 → 第三方 SDK

## 4. 关键要点总结

- dify 双层追踪：**OTEL 自动埋点** + **OpsTraceManager 业务 trace**
- 支持 10+ 第三方追踪后端（Langfuse / LangSmith / Phoenix 等）
- `OpsTraceProviderConfigMap` 用 `match/case` 实现插件化注册
- `OpsTraceManager` 用 LRU 缓存避免重复创建 SDK client
- `TraceQueueManager` 用内存队列 + Celery 异步批量推送
- dify 通过 `dispatch map` 支持 10+ 种 trace 类型

## 5. 练习题

### 练习 1：基础（必做）

为 dify 配置 Langfuse 作为追踪后端（参考 https://langfuse.com/docs），在控制台触发一次工作流执行，在 Langfuse UI 中查看完整 trace。

### 练习 2：进阶

阅读 `api/core/ops/ops_trace_manager.py` 的 `TraceTask` 类和 `TraceQueueManager` 类，画出业务 trace 的完整数据流图：业务事件 → TraceQueueManager → Celery task → 第三方后端。

### 练习 3：挑战（选做）

扩展 dify 的 OpsTraceProviderConfigMap，新增一个自定义追踪后端（假设有 `MyCustomTrace` 类）。需要实现：
1. Config 类（包含 api_key / endpoint）
2. Trace instance 类（实现 `api_check()` / `trace()` 方法）
3. 在 `OpsTraceProviderConfigMap` 中注册

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- Langfuse 文档：https://langfuse.com/docs
- Arize Phoenix 文档：https://docs.arize.com/phoenix
- Opik 文档：https://www.comet.com/docs/opik/

---

**文档版本**：v1.0
**最后更新**：2026-07-13