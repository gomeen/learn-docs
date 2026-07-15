# 10.2.4 应用指标：QPS / 延迟 / 错误率

> 掌握三大应用层黄金信号（QPS / 延迟 / 错误率）的采集、聚合、告警，是 SRE 的核心技能。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 SRE 黄金信号的含义和计算方式
- 能在 dify 中采集 QPS、延迟、错误率
- 理解 RED 方法（Rate / Errors / Duration）
- 能用 PromQL 实现复杂的指标聚合

## 📚 前置知识

- 10.2.1 指标类型（`06-metric-types.md`）
- 10.2.2 Prometheus 基础（`07-prometheus.md`）
- 10.1 日志相关文档

## 1. 核心概念

### 1.1 SRE 黄金信号（Golden Signals）

Google SRE 提出的四大信号：

| 信号 | 含义 | 衡量 |
|------|------|------|
| **Latency** | 延迟 | 服务一个请求需要的时间 |
| **Traffic** | 流量 | 每秒请求数（QPS） |
| **Errors** | 错误 | 失败请求的速率 / 比例 |
| **Saturation** | 饱和度 | 服务接近资源极限的程度 |

### 1.2 RED 方法（Rate / Errors / Duration）

Weaveworks 提出的简化版，专为微服务设计：

| 指标 | 含义 | 公式 |
|------|------|------|
| **Rate** | 请求速率 | `rate(requests_total[5m])` |
| **Errors** | 错误率 | `rate(errors_total[5m]) / rate(requests_total[5m])` |
| **Duration** | 延迟分布 | `histogram_quantile(0.99, rate(duration_bucket[5m]))` |

### 1.3 USE 方法（Utilization / Saturation / Errors）

针对资源（CPU、内存、磁盘）的衡量方法，常与 RED 配合。

### 1.4 关键 PromQL 模式

```promql
# 1. 整体 QPS
sum(rate(http_requests_total[5m]))

# 2. 按端点分组 QPS
sum by (endpoint) (rate(http_requests_total[5m]))

# 3. 错误率（按状态码分）
sum by (status) (rate(http_requests_total{status=~"5.."}[5m]))

# 4. P99 延迟（按端点）
histogram_quantile(0.99,
  sum by (endpoint, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# 5. 平均延迟
rate(http_request_duration_seconds_sum[5m]) /
  rate(http_request_duration_seconds_count[5m])

# 6. 错误突增检测（与昨天对比）
sum(rate(http_requests_total{status=~"5.."}[5m])) /
  sum(rate(http_requests_total[5m]))
  > on() (2 * (
    sum(rate(http_requests_total{status=~"5.."}[5m] offset 1d)) /
    sum(rate(http_requests_total[5m] offset 1d))
  ))
```

## 2. 代码示例

### 2.1 dify 的 HTTP 指标采集（基于 Flask + OTEL）

```python
# api/extensions/otel/instrumentation.py
from opentelemetry.metrics import get_meter

meter = get_meter("http_metrics")

# Counter: 请求计数
request_count = meter.create_counter(
    "http.server.response.count",
    description="Total number of HTTP responses by status code, method and target",
    unit="{response}",
)

# 每次请求结束时增加
def response_hook(span, status, response_headers):
    request_count.add(1, {
        "method": flask.request.method,
        "route": str(flask.request.url_rule.rule),
        "status_code": int(status.split()[0]),
    })
```

**说明**：
- 标签 `route` 用 URL 规则（`/users/<id>`），避免基数爆炸
- 标签 `status_code` 分组为 `2xx/4xx/5xx`
- OTEL 会自动通过 Flask instrumentor 记录延迟（Histogram）

### 2.2 计算 P99 延迟（PromQL）

```promql
# 整体 P99
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# 按路由分组的 P99
histogram_quantile(0.99,
  sum by (route, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)

# 错误率
sum(rate(http_server_response_count{status_class=~"5xx"}[5m]))
  /
sum(rate(http_server_response_count[5m]))
```

### 2.3 告警规则示例

```yaml
# alerts.yml
groups:
  - name: api_golden_signals
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_server_response_count{status_class=~"5xx"}[5m]))
            /
          sum(rate(http_server_response_count[5m]))
            > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API 错误率超过 5%"
          description: "过去 5 分钟错误率 {{ $value | humanizePercentage }}"

      - alert: HighP99Latency
        expr: |
          histogram_quantile(0.99,
            sum by (route, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 延迟超过 2 秒 ({{ $labels.route }})"

      - alert: TrafficDrop
        expr: |
          sum(rate(http_server_response_count[15m]))
            <
          sum(rate(http_server_response_count[15m] offset 1d)) * 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "流量比昨天同时段下降 50%"
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTP 响应采集

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 104-138）：

```python
def init_flask_instrumentor(app: DifyApp) -> None:
    meter = get_meter("http_metrics", version=dify_config.project.version)
    _http_response_counter = meter.create_counter(
        "http.server.response.count",
        description="Total number of HTTP responses by status code, method and target",
        unit="{response}",
    )

    def response_hook(span: Span, status: str, response_headers: list) -> None:
        if span and span.is_recording():
            try:
                if status.startswith("2"):
                    span.set_status(StatusCode.OK)
                else:
                    span.set_status(StatusCode.ERROR, status)

                status = status.split(" ")[0]
                status_code = int(status)
                status_class = f"{status_code // 100}xx"
                attributes: dict[str, str | int] = {"status_code": status_code, "status_class": status_class}
                request = flask.request
                if request and request.url_rule:
                    attributes[HTTP_ROUTE] = str(request.url_rule.rule)
                if request and request.method:
                    attributes[HTTP_REQUEST_METHOD] = str(request.method)
                _http_response_counter.add(1, attributes)
            except Exception:
                logger.exception("Error setting status and attributes")

    from opentelemetry.instrumentation.flask import FlaskInstrumentor

    instrumentor = cast(SupportsFlaskInstrumentor, FlaskInstrumentor())
    if dify_config.DEBUG:
        logger.info("Initializing Flask instrumentor")
    instrumentor.instrument_app(app, response_hook=response_hook)
```

**解读**：
- 第 16-20 行：2xx → OK，其他 → ERROR（同时设置 span 状态）
- 第 23-24 行：状态码分为 `200`、`2xx` 两个标签，方便 PromQL 分组聚合
- 第 26-27 行：`HTTP_ROUTE` 标签用路由模板（`/users/<id>`），避免基数爆炸
- 第 30 行：用 `cast` 做类型断言，兼容 OpenTelemetry 宽松的 typing
- 第 32-33 行：`DEBUG` 模式下打印日志，避免生产噪音
- **关键设计**：通过 `response_hook` 把 Flask 的响应状态注入到 OTEL 指标

### 3.2 dify 的数据库/Redis/HTTP 客户端自动埋点

> 📌 **Sighting**：Redis 客户端与数据结构本身见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)；此处只关心 OTEL 自动埋点。

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 141-163）：

```python
def init_sqlalchemy_instrumentor(app: DifyApp) -> None:
    with app.app_context():
        engines = list(app.extensions["sqlalchemy"].engines.values())
        _new_sqlalchemy_instrumentor().instrument(enable_commenter=True, engines=engines)


def init_redis_instrumentor() -> None:
    _new_redis_instrumentor().instrument()


def init_httpx_instrumentor() -> None:
    _new_httpx_instrumentor().instrument()


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
- 第 4 行：`enable_commenter=True` 让 SQL 自动添加 trace_id 注释，便于关联
- 第 7-13 行：Redis / HTTPX / SQLAlchemy 都自动埋点
- 第 16-18 行：Flask 路由 + Celery worker 互相独立
- 第 20 行：`instrument_exception_logging` 把异常关联到 span
- **关键设计**：通过 OTEL 自动埋点，dify 不需要手动给每个函数加监控

### 3.3 异常埋点：让错误率可统计

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 58-97）：

```python
class ExceptionLoggingHandler(logging.Handler):
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
- 第 7-9 行：用 `contextlib.suppress` 包裹整个方法，绝不抛异常
- 第 14-18 行：把 span 标记为 ERROR（让 OTEL 后端可统计）
- 第 21-29 行：用 `add_event` 把异常信息追加到 span，便于在 Tempo/Jaeger 查看
- 第 31-33 行：调用 `record_exception` 记录完整堆栈
- **关键设计**：错误日志自动转化为 span 状态，无须额外的 `errors_total` 计数器

## 4. 关键要点总结

- SRE 四大黄金信号：Latency / Traffic / Errors / Saturation
- RED 方法（Rate / Errors / Duration）适合微服务
- P99 比平均值更能反映真实用户体验
- 标签基数控制：用路由模板而非实际 URL
- 错误统计：通过 span 状态（ERROR）而非独立 Counter
- OTEL 自动埋点 SQLAlchemy / Redis / HTTPX，无需手写

## 5. 练习题

### 练习 1：基础（必做）

为 dify 设计 3 个告警规则：
1. 5xx 错误率超过 5% 持续 2 分钟
2. P99 延迟超过 3 秒持续 5 分钟
3. 流量突降（与昨天同时段相比下降 70%）持续 10 分钟

### 练习 2：进阶

阅读 `api/extensions/otel/instrumentation.py`，解释 dify 为什么在 `response_hook` 中既设置 span status 又调用 `_http_response_counter.add()`？两者能否互相替代？

### 练习 3：挑战（选做）

实现一个 `SaturationMetric`：用 OTEL Gauge 监控 dify 工作流的并发执行数和 Celery 队列长度，超过阈值时触发告警。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- Google SRE Book：https://sre.google/sre-book/monitoring-distributed-systems/
- RED 方法：https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/
- Prometheus 实践：https://prometheus.io/docs/practices/instrumentation/

---

**文档版本**：v1.0
**最后更新**：2026-07-13