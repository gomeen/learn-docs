# 10.3.3 Jaeger / Zipkin 实战

> 掌握两个最流行的开源链路追踪后端：Jaeger（Uber 开源）和 Zipkin（Twitter 开源），能在本地部署并接入 dify。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Jaeger 和 Zipkin 的架构与差异
- 能用 Docker 启动本地的 Jaeger / Zipkin
- 能配置 OTEL Collector 转发 trace 到这两个后端
- 知道 dify 中暂未直接使用 Jaeger / Zipkin

## 📚 前置知识

- 10.3.2 OpenTelemetry 标准（`12-opentelemetry.md`）
- 10.3.1 链路追踪概念（`11-tracing-concepts.md`）
- Docker 基础

## 1. 核心概念

### 1.1 Jaeger 简介

**Jaeger**（Uber 开源，CNCF 毕业项目）是分布式链路追踪平台，特点：
- 高性能（基于 Go）
- 原生支持 OpenTelemetry / Jaeger / Zipkin 协议
- 提供 UI（依赖图、Span 列表、时间轴）
- 支持 Cassandra / Elasticsearch / Kafka 存储

### 1.2 Zipkin 简介

**Zipkin**（Twitter 开源）是较早的分布式追踪系统，特点：
- 基于 Java，资源占用较低
- 协议基于 Thrift / JSON / Protobuf
- UI 简洁，适合小规模部署
- 支持多种存储后端（MySQL / Cassandra / ES）

### 1.3 Jaeger vs Zipkin

| 维度 | Jaeger | Zipkin |
|------|--------|--------|
| 出身 | Uber（2015） | Twitter（2012） |
| 语言 | Go | Java |
| UI | 现代化、依赖图 | 简洁、时间轴 |
| 协议 | OTLP / Jaeger / Zipkin | Zipkin / OTLP（新版） |
| 性能 | 高 | 中 |
| 适用规模 | 大型微服务 | 中小型系统 |
| 生态 | CNCF、与 OTEL 深度整合 | 稳定、独立 |

### 1.4 OTEL Collector 作为中转

```
dify → OTEL Collector → Jaeger / Zipkin / Tempo / ...
```

dify 通过 OTEL Collector 推送 trace，Collector 可以路由到多个后端：

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  zipkin:
    endpoint: http://zipkin:9411/api/v2/spans

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [jaeger, zipkin]
```

## 2. 代码示例

### 2.1 Docker 启动 Jaeger

```bash
# 启动 Jaeger（全功能模式，含 UI）
docker run -d --name jaeger \
  -p 16686:16686 \  # UI
  -p 4317:4317 \    # OTLP gRPC
  -p 4318:4318 \    # OTLP HTTP
  -p 14250:14250 \  # jaeger thrift
  jaegertracing/all-in-one:latest

# 访问 UI
open http://localhost:16686
```

### 2.2 Docker 启动 Zipkin

```bash
# 启动 Zipkin
docker run -d --name zipkin \
  -p 9411:9411 \
  openzipkin/zipkin:latest

# 访问 UI
open http://localhost:9411
```

### 2.3 启动 OTEL Collector（同时转发到 Jaeger 和 Zipkin）

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  zipkin:
    endpoint: http://zipkin:9411/api/v2/spans
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger, zipkin, debug]
```

```bash
docker run -d --name otel-collector \
  -p 4317:4317 -p 4318:4318 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel/config.yaml \
  otel/opentelemetry-collector-contrib:latest
```

### 2.4 配置 dify 推送到 Collector

```bash
# .env
ENABLE_OTEL=true
OTEL_EXPORTER_TYPE=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTLP_BASE_ENDPOINT=http://localhost:4317
OTEL_SAMPLING_RATE=1.0  # 开发环境 100% 采样
```

### 2.5 常见错误：协议端口混淆

```bash
# ❌ 错误：OTLP gRPC 用 4318 端口（HTTP 的）
OTLP_BASE_ENDPOINT=http://localhost:4318
# gRPC exporter 会连接失败

# ✅ 正确：gRPC 用 4317，HTTP 用 4318
OTLP_BASE_ENDPOINT=http://localhost:4317  # gRPC
# 或
OTLP_BASE_ENDPOINT=http://localhost:4318  # HTTP
```

## 3. dify 仓库源码解读

### 3.1 dify 与 Jaeger / Zipkin 的集成方式

> **dify 中暂未直接使用 Jaeger 或 Zipkin**。dify 通过 OpenTelemetry 协议（OTLP）推送 trace，需要通过 OTEL Collector 转发到 Jaeger / Zipkin。

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_otel.py`
**核心代码**（行 76-99）：

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
```

**解读**：
- 第 5 行：通过 `OTEL_EXPORTER_TYPE=otlp` 选择 OTLP 模式（与 Collector 通信）
- 第 6 行：根据 `OTEL_EXPORTER_OTLP_PROTOCOL` 选择 gRPC 或 HTTP
- 第 9-10 行：dify **不直接连接 Jaeger**，而是通过 Collector 中转
- **集成方法**：通过 OTEL Collector 的 `jaeger` / `zipkin` exporter 转发

### 3.2 dify 的上下文传播（兼容 Jaeger B3）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
**核心代码**（行 22-30）：

```python
def setup_context_propagation() -> None:
    set_global_textmap(
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
                B3MultiFormat(),
            ]
        )
    )
```

**解读**：
- 第 4 行：`TraceContextTextMapPropagator` 支持 W3C TraceContext（OTEL 标准）
- 第 5 行：`B3MultiFormat` 支持 B3 格式（Zipkin / 早期 Jaeger）
- **关键设计**：dify 同时支持两种 propagator，可以与已有的 Jaeger / Zipkin 系统无缝集成

### 3.3 dify 的 trace 关闭清理

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
**核心代码**（行 33-56）：

```python
def shutdown_tracer() -> None:
    flush_telemetry()


def flush_telemetry() -> None:
    """
    Best-effort flush for telemetry providers.

    This is mainly used by short-lived command processes (e.g. Kubernetes CronJob)
    so counters/histograms are exported before the process exits.
    """
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        try:
            provider.force_flush()
        except Exception:
            logger.exception("otel: failed to flush trace provider")

    metric_provider = metrics.get_meter_provider()
    if hasattr(metric_provider, "force_flush"):
        try:
            metric_provider.force_flush()
        except Exception:
            logger.exception("otel: failed to flush metric provider")
```

**解读**：
- 第 1-2 行：`shutdown_tracer` 在 `atexit` 时调用，确保数据不丢失
- 第 3-12 行：`flush_telemetry` 主要用于短生命周期任务（K8s CronJob）
- 第 14-20 行：先 flush trace provider
- 第 22-28 行：再 flush metric provider
- 第 17-18 行 / 第 26-27 行：用 try/except 兜底，flush 失败不影响进程退出
- **关键设计**：通过 `atexit.register(shutdown_tracer)` 注册退出钩子（见 `ext_otel.py:140`）

## 4. 关键要点总结

- **Jaeger**（Uber / CNCF）：Go 实现，UI 现代化，性能高
- **Zipkin**（Twitter）：Java 实现，UI 简洁，适合中小规模
- dify 通过 **OTEL Collector 中转**，不直接连 Jaeger / Zipkin
- 部署架构：dify → OTEL Collector（4317 gRPC / 4318 HTTP）→ Jaeger / Zipkin
- dify 同时支持 **W3C TraceContext** 和 **B3** propagator，兼容旧系统
- dify 通过 `atexit.register` 注册 flush，避免短任务数据丢失

## 5. 练习题

### 练习 1：基础（必做）

本地启动 Jaeger（Docker），配置 dify 通过 OTEL Collector 推送 trace，然后在 Jaeger UI 中查看一次工作流执行的完整 trace。

### 练习 2：进阶

阅读 `api/extensions/ext_otel.py` 和 `api/extensions/otel/runtime.py`，画出 dify OTEL 数据的完整流向图：dify 应用 → OTLP → Collector → Jaeger → 浏览器 UI。

### 练习 3：挑战（选做）

搭建一个完整的 OTEL 监控栈：
- dify 应用（OTLP gRPC 输出）
- OTEL Collector（接收 + 批量处理）
- Jaeger（trace 存储）
- Prometheus（metric 存储）
- Grafana（统一可视化）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- `/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
- Jaeger 官方文档：https://www.jaegertracing.io/docs/
- Zipkin 官方文档：https://zipkin.io/pages/architecture.html
- OTEL Collector 配置：https://opentelemetry.io/docs/collector/configuration/
- Docker Hub Jaeger：https://hub.docker.com/r/jaegertracing/all-in-one

---

**文档版本**：v1.0
**最后更新**：2026-07-13