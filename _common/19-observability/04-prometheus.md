# 10.2.2 Prometheus 基础

> 理解 Prometheus 监控系统的拉取模型、数据格式、查询语言和与 dify 的集成方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Prometheus 的 pull 模型与架构
- 掌握 PromQL 基础查询语法
- 知道如何在 dify 中导出 metrics
- 能看懂 dify 的 OTEL → Prometheus 导出路径

## 📚 前置知识

- 10.2.1 指标类型（`03-metric-types.md`）
- OpenTelemetry 基础（10.3.2）

## 1. 核心概念

### 1.1 Prometheus 架构

```
┌─────────────┐
│  Application│
│  (exporter) │ ← /metrics endpoint
└──────┬──────┘
       │ HTTP GET /metrics (pull)
       ▼
┌─────────────┐
│  Prometheus │ ← 存储 TSDB
│   server    │
└──────┬──────┘
       │ PromQL
       ▼
┌─────────────┐
│   Grafana   │ ← 可视化
└─────────────┘
```

### 1.2 Pull vs Push 模型

**Pull（Prometheus）**：
- Prometheus 主动 HTTP GET 抓取 `/metrics`
- 服务无需知道 Prometheus 在哪
- 自动检测服务下线（HTTP 失败 → 标记 down）

**Push（StatsD / OpenTelemetry）**：
- 服务主动发送数据
- 需要额外的 Pushgateway（Prometheus）或 collector（OTEL）
- 适合短生命周期任务（批处理、CronJob）

**dify 选择**：dify 用 OpenTelemetry 的 OTLP 协议 push 到 collector，再由 collector 暴露给 Prometheus。这是混合模式——应用 push，Prometheus 仍然 pull。

### 1.3 指标数据格式

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/users",status="200"} 1234
http_requests_total{method="POST",endpoint="/api/users",status="201"} 56
http_requests_total{method="GET",endpoint="/api/users",status="500"} 3

# HELP http_request_duration_seconds Request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.005"} 0
http_request_duration_seconds_bucket{le="0.01"} 12
...
http_request_duration_seconds_count 1293
http_request_duration_seconds_sum 87.234
```

格式说明：
- 第 1 行：`# HELP` 是说明文字
- 第 2 行：`# TYPE` 声明指标类型
- 第 3 行：`metric_name{label1="v1",label2="v2"} value` 时间戳隐含

### 1.4 PromQL 基础

**查询示例**：

```promql
# 1. 直接查询
http_requests_total

# 2. 按标签过滤
http_requests_total{status="500"}

# 3. 计算 QPS（每秒请求数）
rate(http_requests_total[5m])

# 4. 计算错误率
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m]))

# 5. P99 延迟
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# 6. 计算平均
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

## 2. 代码示例

### 2.1 启动一个最小的 Prometheus exporter

```python
# app.py
from prometheus_client import start_http_server, Counter, generate_latest
import time

# 定义指标
REQUESTS = Counter("app_requests_total", "Total requests", ["endpoint"])

# 启动 metrics HTTP server（默认 8000 端口）
start_http_server(8000)

# 业务代码
for i in range(1000):
    REQUESTS.labels(endpoint="/health").inc()
    time.sleep(1)
```

启动后访问 `http://localhost:8000/metrics` 即可看到输出。

### 2.2 用 Flask 暴露 /metrics

```python
from flask import Flask, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
REQUESTS = Counter("flask_requests_total", "Total requests", ["method", "endpoint"])

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/api/users")
def users():
    REQUESTS.labels(method="GET", endpoint="/api/users").inc()
    return {"users": []}

if __name__ == "__main__":
    app.run()
```

### 2.3 常见错误：忘记 /metrics 路径

```python
# ❌ 错误：把 metrics 路由放在业务路由中间
@app.route("/api/users")
def users(): ...

@app.route("/metrics")
def metrics(): ...

# Prometheus scrape config 中配了 /metrics，但应用启动后 /metrics 返回 404
# 因为 Flask 路由注册顺序问题，或者 @app.before_request 拦截了

# ✅ 正确：把 /metrics 注册在所有业务路由之前
@app.route("/metrics")
def metrics(): ...

@app.route("/api/users")
def users(): ...
```

## 3. dify 仓库源码解读

### 3.1 dify 的 OTEL Metrics 导出配置

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_otel.py`
**核心代码**（行 131-140）：

```python
    reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=dify_config.OTEL_METRIC_EXPORT_INTERVAL,
        export_timeout_millis=dify_config.OTEL_METRIC_EXPORT_TIMEOUT,
    )
    set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    init_instruments(app)

    atexit.register(shutdown_tracer)
```

**解读**：
- 第 1-5 行：`PeriodicExportingMetricReader` 周期性推送指标到 exporter
- 第 4 行：`export_interval_millis` 控制推送频率（默认 60 秒）
- 第 6 行：全局设置 MeterProvider，OTEL 内部所有 `get_meter()` 都从这里取
- **关键设计**：dify 不直接用 prometheus_client，而是 OTEL → Prometheus collector → Prometheus

### 3.2 MeterProvider 初始化（完整 OTEL 栈）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_otel.py`
**核心代码**（行 73-99）：

```python
sampler = ParentBasedTraceIdRatio(dify_config.OTEL_SAMPLING_RATE)
provider = TracerProvider(resource=resource, sampler=sampler)

set_tracer_provider(provider)
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
```

**解读**：
- 第 1-3 行：`TracerProvider` 用 `ParentBasedTraceIdRatio` 采样器（基于父级决定采样率）
- 第 5-6 行：OTEL 支持 gRPC 和 HTTP 两种协议
- 第 9-13 行：自动检测 TLS（`https://` 前缀自动启用 secure）
- 第 16-19 行：HTTP/2 规范要求 header 名小写
- 第 21-32 行：分别创建 trace 和 metric 的 gRPC exporter
- **关键设计**：dify 的 OTEL 配置统一由 `OTEL_*` 环境变量控制

### 3.3 HTTP 响应计数器（已在 10.2.1 详解）

见 `extensions/otel/instrumentation.py:104-131`，通过 OTEL Meter 创建 Counter，OTEL 推送到 collector。

> 注意：dify 中暂未直接使用 `prometheus_client`，而是通过 OpenTelemetry 间接实现 Prometheus 集成。如果你需要直接暴露 `/metrics` 端点，需要额外配置 OTEL collector 的 Prometheus exporter。

## 4. 关键要点总结

- Prometheus 用 **pull 模型**：定期 HTTP GET `/metrics`
- 数据格式：`metric_name{labels} value`，可选 `# HELP` 和 `# TYPE`
- 核心函数：`rate()`、`histogram_quantile()`、`sum()`、`avg()`
- **Histogram > Summary**：Histogram 可服务端聚合分位数
- dify 通过 OpenTelemetry → collector → Prometheus 导出
- 配置项：`OTEL_EXPORTER_TYPE`（otlp/console）、`OTEL_EXPORTER_OTLP_PROTOCOL`（grpc/http）

## 5. 练习题

### 练习 1：基础（必做）

写一个 Flask 应用，定义 3 个 Prometheus 指标（请求 Counter、在线用户 Gauge、延迟 Histogram），并暴露 `/metrics` 端点。

### 练习 2：进阶

阅读 `api/extensions/ext_otel.py`，画出 OTEL Metrics 导出链路图：dify 应用 → OTEL Meter → PeriodicExportingMetricReader → OTLP Exporter → Collector → Prometheus → Grafana。

### 练习 3：挑战（选做）

实现一个 `prometheus.yml` scrape 配置，从 dify 部署中抓取 metrics，包括：
- scrape_interval: 15s
- 静态配置 + 服务发现
- relabel_config 过滤无用指标

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- Prometheus 官方文档：https://prometheus.io/docs/introduction/overview/
- PromQL 教程：https://prometheus.io/docs/prometheus/latest/querying/basics/
- OpenTelemetry Prometheus 集成：https://opentelemetry.io/docs/collector/exporters/prometheus/

---

**文档版本**：v1.0
**最后更新**：2026-07-13