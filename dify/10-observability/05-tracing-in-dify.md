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

## 3. 关键要点总结

- dify 双层追踪：**OTEL 自动埋点** + **OpsTraceManager 业务 trace**
- 支持 10+ 第三方追踪后端（Langfuse / LangSmith / Phoenix 等）
- `OpsTraceProviderConfigMap` 用 `match/case` 实现插件化注册
- `OpsTraceManager` 用 LRU 缓存避免重复创建 SDK client
- `TraceQueueManager` 用内存队列 + Celery 异步批量推送
- dify 通过 `dispatch map` 支持 10+ 种 trace 类型

---

**文档版本**：v1.0
**最后更新**：2026-07-13
