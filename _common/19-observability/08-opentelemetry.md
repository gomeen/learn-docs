# 10.3.2 OpenTelemetry 标准

> OpenTelemetry（OTEL）是 CNCF 主导的可观测性标准，dify 通过它统一接入 trace / metrics / logs。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 OpenTelemetry 的架构与三大信号
- 掌握 OTEL 的核心 API（Tracer / Meter / Logger）
- 能看懂 dify `extensions/ext_otel.py` 的初始化逻辑
- 能配置 OTEL 导出器（OTLP / Console）

## 📚 前置知识

- 10.3.1 链路追踪概念（`07-tracing-concepts.md`）
- 10.2.1 指标类型（`03-metric-types.md`）
- gRPC / HTTP 基础

## 1. 核心概念

### 1.1 OpenTelemetry 是什么？

OpenTelemetry（CNCF 项目）是**可观测性的统一标准**，前身是 OpenTracing 和 OpenCensus。提供：

- **API**：与后端无关的统一接口
- **SDK**：具体实现
- **数据规范**：Trace / Metric / Log 的标准格式
- **Collector**：中转服务，支持多种导出器

### 1.2 三大信号（Pillars）

| 信号 | 用途 | Python API |
|------|------|------------|
| **Trace** | 分布式链路追踪 | `opentelemetry.trace` |
| **Metrics** | 数值指标 | `opentelemetry.metrics` |
| **Logs** | 结构化日志 | `opentelemetry.sdk.logs` |

### 1.3 OTEL 架构

```
┌────────────────────────────────────────────┐
│              Application                    │
│  ┌──────────────────────────────────────┐  │
│  │  Instrumentation Library (自动埋点)  │  │
│  └────────────┬─────────────────────────┘  │
│               ↓                            │
│  ┌──────────────────────────────────────┐  │
│  │  API (Tracer / Meter / Logger)       │  │
│  └────────────┬─────────────────────────┘  │
│               ↓                            │
│  ┌──────────────────────────────────────┐  │
│  │  SDK (TracerProvider / MeterProvider)│  │
│  └────────────┬─────────────────────────┘  │
└───────────────┼────────────────────────────┘
                ↓ OTLP (gRPC / HTTP)
       ┌────────┴────────┐
       │   Collector     │ ← 数据聚合、采样、转发
       └────────┬────────┘
                ↓
   ┌────────────┴────────────┐
   ▼                         ▼
┌────────┐             ┌──────────┐
│ Jaeger │             │ Tempo    │
└────────┘             └──────────┘
```

### 1.4 OTLP 协议

OTEL 定义了 **OTLP（OpenTelemetry Protocol）** 作为传输协议：

| 传输 | 端口 | 特点 |
|------|------|------|
| gRPC | 4317 | 高性能、二进制、流式 |
| HTTP | 4318 | 兼容性好、易调试 |

### 1.5 语义约定（Semantic Conventions）

OTEL 定义了标准的字段命名规范，便于跨服务分析：

| 字段 | 含义 |
|------|------|
| `service.name` | 服务名 |
| `service.version` | 服务版本 |
| `deployment.environment.name` | 环境（dev/staging/prod） |
| `http.request.method` | HTTP 方法 |
| `http.route` | 路由模板 |
| `db.system` | 数据库类型 |
| `gen_ai.*` | LLM 相关字段 |

## 2. 代码示例

### 2.1 初始化一个最小的 OTEL Tracer

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource

# 1. 创建 Resource（描述服务信息）
resource = Resource.create({
    "service.name": "my-app",
    "service.version": "1.0.0",
})

# 2. 创建 Provider
provider = TracerProvider(resource=resource)

# 3. 添加 exporter
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

# 4. 设置全局 provider
trace.set_tracer_provider(provider)

# 5. 使用 tracer
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("hello") as span:
    span.set_attribute("greeting", "world")
    print("Hello, OTEL!")
# Span 被打印到 stdout
```

### 2.2 接入 OTLP Exporter

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 推送到 OTEL Collector（gRPC）
exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    insecure=True,
    headers={"authorization": "Bearer my-secret"},
)
provider.add_span_processor(BatchSpanProcessor(exporter))
```

### 2.3 常见错误：忘记 set_tracer_provider

```python
# ❌ 错误：直接使用 tracer 但没设置全局 provider
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("test") as span:
    print(span)  # 不会报错，但 span 不会被导出

# ✅ 正确：先 set_tracer_provider
from opentelemetry.sdk.trace import TracerProvider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
```

## 3. dify 仓库源码解读

### 3.1 dify 的 OTEL 初始化完整流程

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_otel.py`
**核心代码**（行 14-99）：

```python
def init_app(app: DifyApp):
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
    from opentelemetry.metrics import set_meter_provider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
    from opentelemetry.semconv._incubating.attributes.deployment_attributes import (
        DEPLOYMENT_ENVIRONMENT_NAME,
    )
    from opentelemetry.semconv._incubating.attributes.host_attributes import (
        HOST_ARCH,
        HOST_ID,
        HOST_NAME,
    )
    from opentelemetry.semconv._incubating.attributes.os_attributes import (
        OS_DESCRIPTION,
        OS_TYPE,
        OS_VERSION,
    )
    from opentelemetry.semconv._incubating.attributes.process_attributes import (
        PROCESS_PID,
    )
    from opentelemetry.semconv.attributes.service_attributes import (
        SERVICE_NAME,
        SERVICE_VERSION,
    )
    from opentelemetry.trace import set_tracer_provider

    from extensions.otel.instrumentation import init_instruments
    from extensions.otel.runtime import setup_context_propagation, shutdown_tracer

    setup_context_propagation()
    # Initialize OpenTelemetry
    # Follow Semantic Convertions 1.32.0 to define resource attributes
    resource = Resource(
        attributes={
            SERVICE_NAME: dify_config.APPLICATION_NAME,
            SERVICE_VERSION: f"dify-{dify_config.project.version}-{dify_config.COMMIT_SHA}",
            PROCESS_PID: os.getpid(),
            DEPLOYMENT_ENVIRONMENT_NAME: f"{dify_config.DEPLOY_ENV}-{dify_config.EDITION}",
            HOST_NAME: socket.gethostname(),
            HOST_ARCH: platform.machine(),
            "custom.deployment.git_commit": dify_config.COMMIT_SHA,
            HOST_ID: platform.node(),
            OS_TYPE: platform.system().lower(),
            OS_DESCRIPTION: platform.platform(),
            OS_VERSION: platform.version(),
        }
    )
    sampler = ParentBasedTraceIdRatio(dify_config.OTEL_SAMPLING_RATE)
    provider = TracerProvider(resource=resource, sampler=sampler)

    set_tracer_provider(provider)
```

**解读**：
- 第 2-49 行：完整导入所有需要的 OTEL 模块
- 第 53 行：先调用 `setup_context_propagation()` 设置全局 propagator
- 第 55-72 行：定义 Resource（服务标识）+ 主机/进程信息
- 第 73 行：`ParentBasedTraceIdRatio` 采样器——基于父级决定是否采样（避免在链路中间突然断掉）
- 第 74 行：创建 TracerProvider
- 第 76 行：设置为全局 provider
- **关键设计**：dify 把所有 OTEL 资源信息都注入到 Resource，后端可以直接看到版本、git commit、部署环境

### 3.2 dify 的 OTLP 协议选择

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_otel.py`
**核心代码**（行 76-117）：

```python
exporter: Union[GRPCSpanExporter, HTTPSpanExporter, ConsoleSpanExporter]
metric_exporter: Union[GRPCMetricExporter, HTTPMetricExporter, ConsoleMetricExporter]
protocol = (dify_config.OTEL_EXPORTER_OTLP_PROTOCOL or "").lower()
if dify_config.OTEL_EXPORTER_TYPE == "otlp":
    if protocol == "grpc":
        # Auto-detect TLS: https:// uses secure, everything else is insecure
        endpoint = dify_config.OTLP_BASE_ENDPOINT
        insecure = not endpoint.startswith("https://")

        # Header field names must consist of lowercase letters, check RFC7540
        grpc_headers = (
            (("authorization", f"Bearer {dify_config.OTLP_API_KEY}"),) if dify_config.OTLP_API_KEY else ()
        )

        exporter = GRPCSpanExporter(
            endpoint=endpoint,
            headers=grpc_headers,
            insecure=insecure,
        )
        metric_exporter = GRPCMetricExporter(
            endpoint=endpoint,
            headers=grpc_headers,
            insecure=insecure,
        )
    else:
        headers = {"Authorization": f"Bearer {dify_config.OTLP_API_KEY}"} if dify_config.OTLP_API_KEY else None

        trace_endpoint = dify_config.OTLP_TRACE_ENDPOINT
        if not trace_endpoint:
            trace_endpoint = dify_config.OTLP_BASE_ENDPOINT + "/v1/traces"
        exporter = HTTPSpanExporter(
            endpoint=trace_endpoint,
            headers=headers,
        )

        metric_endpoint = dify_config.OTLP_METRIC_ENDPOINT
        if not metric_endpoint:
            metric_endpoint = dify_config.OTLP_BASE_ENDPOINT + "/v1/metrics"
        metric_exporter = HTTPMetricExporter(
            endpoint=metric_endpoint,
            headers=headers,
        )
else:
    exporter = ConsoleSpanExporter()
    metric_exporter = ConsoleMetricExporter()
```

**解读**：
- 第 4 行：从配置读取协议类型（`grpc` 或 `http`）
- 第 5 行：判断 OTEL exporter 类型（`otlp` 或 `console`）
- 第 7-10 行：gRPC 模式下自动检测 TLS（`https://` 自动启用 secure）
- 第 13-15 行：**HTTP/2 规范要求 header 名小写**
- 第 17-23 行：trace 和 metric 共用 gRPC endpoint 和 headers
- 第 26-33 行：HTTP 模式下允许分别配置 trace 和 metric endpoint（拼上 `/v1/traces` 或 `/v1/metrics`）
- 第 42-44 行：非 OTLP 模式用 Console（开发调试用）
- **关键设计**：dify 自动适配多种部署环境（gRPC / HTTP / Console）

### 3.3 dify 的 OTEL 自动埋点

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 155-163）：

```python
def init_instruments(app: DifyApp) -> None:
    if not is_celery_worker():
        init_flask_instrumentor(app)
        _new_celery_instrumentor().instrument()

    instrument_exception_logging()
    init_sqlalchemy_instrumentor(app)
    init_redis_instrumentor()
    init_httpx_instrumentor()
```

**解读**：
- 第 2-5 行：Flask + Celery 互相独立（Celery worker 不需要 Flask 路由）
- 第 7 行：异常日志 hook
- 第 8 行：SQLAlchemy 自动埋点（数据库查询）
- 第 9 行：Redis 自动埋点（缓存调用；Redis 本身详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 第 10 行：HTTPX 自动埋点（外部 HTTP 请求）
- **关键设计**：通过 OTEL instrumentor，dify 无需手动给每个调用加埋点

## 4. 关键要点总结

- OpenTelemetry 是可观测性的统一标准
- 三大信号：**Trace** / **Metrics** / **Logs**
- 通过 **OTLP** 协议（gRPC 4317 / HTTP 4318）推送到 collector
- 遵循 **语义约定**（Semantic Conventions）便于跨服务分析
- dify 用 `ParentBasedTraceIdRatio` 采样器，避免链路中间断掉
- dify 自动检测 TLS、按协议切换 exporter

## 5. 练习题

### 练习 1：基础（必做）

启动一个本地 OTEL Collector（用 Docker，详见 [Docker 核心概念](../../_common/09-containerization/01-concepts.md)），把 dify 配置为 gRPC 模式（`OTEL_EXPORTER_TYPE=otlp`、`OTEL_EXPORTER_OTLP_PROTOCOL=grpc`），观察 trace 是否成功推送。

### 练习 2：进阶

阅读 `api/extensions/ext_otel.py` 的全部代码，画出 dify OTEL 初始化的完整调用流程图（包含 Provider、Exporter、Sampler、Resource）。

### 练习 3：挑战（选做）

扩展 dify 的 OTEL Resource，新增 `custom.tenant_id` 和 `custom.environment` 字段，让 Grafana 可以按租户和环境分组分析 trace。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
- OpenTelemetry 官方文档：https://opentelemetry.io/docs/
- OTLP 协议规范：https://opentelemetry.io/docs/specs/otlp/
- 语义约定：https://opentelemetry.io/docs/specs/semconv/

---

**文档版本**：v1.0
**最后更新**：2026-07-13