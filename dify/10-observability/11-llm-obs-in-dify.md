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

## 3. 关键要点总结

- dify LLM 可观测性：**OTEL 自动埋点** + **OpsTraceManager 业务 trace**
- **10+ 种 trace 类型**：消息、工作流、节点、工具调用、知识库检索等
- **异步批量推送**：业务线程入队 → 定时器批量 → Celery 异步
- **LRU 缓存**：避免重复创建 SDK client
- **多后端插件化**：通过 `OpsTraceProviderConfigMap` 支持 Langfuse 等 10+ 后端
- **异常安全**：未知 trace 类型返回 None，filter / handler 永不抛异常
- **跨系统关联**：支持 `external_trace_id` 与 OTEL trace 关联

---

**文档版本**：v1.0
**最后更新**：2026-07-13
