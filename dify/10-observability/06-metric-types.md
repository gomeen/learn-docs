# 10.2.1 指标类型：Counter / Gauge / Histogram / Summary

> 理解 Prometheus 四大指标类型的语义、适用场景和选型准则。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Counter / Gauge / Histogram / Summary 四种指标类型
- 掌握每种类型的适用场景和陷阱
- 能在代码中正确选择指标类型
- 能看懂 dify `extensions/otel/instrumentation.py` 中的指标定义

## 📚 前置知识

- 统计学基础（平均数、分位数）
- 10.2.2 Prometheus 基础（`07-prometheus.md`）

## 1. 核心概念

### 1.1 四大指标类型对比

| 类型 | 语义 | 单调递增？ | 重置？ | 典型用例 |
|------|------|-----------|--------|----------|
| **Counter** | 累计计数 | 是 | 可被重置（重启时归 0） | 请求数、错误数、字节数 |
| **Gauge** | 瞬时值 | 否 | 否 | CPU 使用率、并发连接数、队列长度 |
| **Histogram** | 分布统计 | 否 | 否 | 请求延迟、响应大小 |
| **Summary** | 分布统计 | 否 | 否 | 同 Histogram，但分位数在客户端计算 |

### 1.2 Counter（计数器）

**特点**：只能增加或重置为 0，适合累计事件。

```python
from prometheus_client import Counter

# 命名规范：<应用>_<对象>_<动作>_<单位>
http_requests_total = Counter(
    "http_requests_total",          # 指标名
    "Total HTTP requests",          # 帮助文本
    ["method", "endpoint", "status"] # 标签
)

# 使用
http_requests_total.labels(method="GET", endpoint="/api/users", status="200").inc()
http_requests_total.labels(method="POST", endpoint="/api/users", status="500").inc()
```

**注意**：
- Prometheus 喜欢 `_total` 后缀（Counter 的惯例）
- 客户端只在本地计数，不主动 reset（服务重启时 Prometheus 仍能通过 `rate()` 检测到 reset）

### 1.3 Gauge（仪表盘）

**特点**：可增可减，反映"当前状态"。

```python
from prometheus_client import Gauge

active_connections = Gauge(
    "active_connections",
    "Current number of active WebSocket connections"
)

# 连接建立时
active_connections.inc()
# 连接断开时
active_connections.dec()
# 也可直接设置
active_connections.set(42)
```

**典型用例**：
- 当前在线用户数
- 内存/CPU 使用率
- 队列积压长度
- 服务是否存活（up=1 / down=0）

### 1.4 Histogram（直方图）

**特点**：把样本值分桶（bucket），统计每个桶的计数。Prometheus 端可计算分位数。

```python
from prometheus_client import Histogram

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# 使用：自动记录执行时长
@http_request_duration_seconds.labels(method="GET", endpoint="/api/users").time()
def handle_request():
    ...
```

**桶（buckets）的选择**：
- 默认桶是 Prometheus 推荐值（适用于一般 HTTP）
- 自定义时要包含业务关键 SLA（如 P99 目标值）

### 1.5 Summary（汇总）

**特点**：在客户端预计算分位数，直接发送到 Prometheus。

```python
from prometheus_client import Summary

request_latency = Summary(
    "request_latency_seconds",
    "Request latency",
    ["endpoint"]
)

# 或指定分位数
request_latency = Summary(
    "request_latency_seconds",
    "Request latency",
    ["endpoint"],
    quantiles=(0.5, 0.9, 0.95, 0.99)  # P50/P90/P95/P99
)
```

**Histogram vs Summary**：

| 维度 | Histogram | Summary |
|------|-----------|---------|
| 分位数计算 | 服务端（`histogram_quantile`） | 客户端 |
| 跨实例聚合 | ✅ 可以 | ❌ 不能 |
| 灵活性 | 高（任意分位数） | 低（固定分位数） |
| 性能 | 高 | 低（每次都要算） |

**推荐**：能用 Histogram 就用 Histogram（特别是需要跨实例聚合时）。

## 2. 代码示例

### 2.1 基础：四种指标的使用

```python
from prometheus_client import Counter, Gauge, Histogram, Summary
import time

# 1. Counter：请求计数
request_count = Counter(
    "api_requests_total", "Total API requests",
    ["method", "endpoint", "status"]
)

# 2. Gauge：在线连接数
active_users = Gauge("active_users", "Current active users")

# 3. Histogram：请求延迟
latency = Histogram(
    "api_latency_seconds", "API request latency",
    ["endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
)

# 4. Summary：自定义分位数
custom_latency = Summary(
    "api_custom_latency", "Custom latency",
    ["endpoint"],
    quantiles=(0.5, 0.95, 0.99)
)


def handle_request(endpoint: str):
    start = time.time()
    try:
        # 业务逻辑
        result = do_work()
        request_count.labels(method="GET", endpoint=endpoint, status="200").inc()
        return result
    except Exception:
        request_count.labels(method="GET", endpoint=endpoint, status="500").inc()
        raise
    finally:
        duration = time.time() - start
        latency.labels(endpoint=endpoint).observe(duration)
        custom_latency.labels(endpoint=endpoint).observe(duration)
        active_users.inc()  # 进入时 +1（伪代码）
```

### 2.2 常见错误：用 Counter 记录"当前值"

```python
# ❌ 错误：Counter 只能递增，不能表达"当前"
current_users = Counter("current_users_total", "Current users")
current_users.inc()  # 进入 +1
current_users.dec()  # 退出 -1
# Counter 是允许 dec 的，但语义不对——重启后值会变，不能用 rate() 算 QPS

# ✅ 正确：用 Gauge
current_users_gauge = Gauge("current_users", "Current users")
current_users_gauge.inc()
current_users_gauge.dec()
```

### 2.3 常见错误：Histogram 桶设计不合理

```python
# ❌ 错误：桶过大，无法区分快慢请求
latency = Histogram("api_latency_seconds", "...", buckets=(0.1, 1, 10, 100))

# ✅ 正确：桶覆盖目标 P99 附近的细粒度
latency = Histogram(
    "api_latency_seconds", "...",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)
# 在 1s 附近细分，便于计算 P99
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTP 响应计数器

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 104-131）：

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
```

**解读**：
- 第 2 行：`get_meter("http_metrics", version=...)` 从 OTEL 全局 provider 获取 meter
- 第 3-7 行：用 `create_counter` 创建 Counter 类型的指标
- 第 10-13 行：设置 span 状态（2xx = OK，其他 = ERROR）
- 第 14-19 行：把 status_code 拆为 `200` 和 `2xx` 两个维度，便于聚合（看 5xx 比例）
- 第 25 行：`_http_response_counter.add(1, attributes)` 等价于 Counter 的 `inc()`
- 第 28-29 行：**整个 response_hook 用 try/except 包裹**——指标采集绝不能影响业务
- **关键设计**：用 OTEL Meter（而不是 prometheus_client）——同一套指标可以导出到多种后端

### 3.2 异常日志处理器（间接统计）

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
- 第 8 行：`contextlib.suppress(Exception)` 让整个方法永不抛异常
- 第 10 行：没有异常信息直接返回
- 第 15-16 行：必须 span 正在 recording 才操作（避免性能浪费）
- 第 21-23 行：把 span 标记为 ERROR，让 OTEL 后端可以统计错误数
- 第 25-32 行：用 `add_event` 把异常记录为 span 的事件，保留完整堆栈
- **关键设计**：错误统计不是单独的 Counter，而是通过 span status 间接计算

## 4. 关键要点总结

| 类型 | 何时用 |
|------|--------|
| **Counter** | 累计事件（请求数、错误数、字节数） |
| **Gauge** | 当前状态（在线人数、CPU%、队列长度） |
| **Histogram** | 延迟/大小分布，需要跨实例聚合分位数 |
| **Summary** | 单一实例的分位数计算 |

- **Histogram > Summary**：Histogram 更灵活，可以服务端聚合
- 桶的设计要覆盖目标 SLA 附近
- dify 用 OTEL Meter 而不是 prometheus_client，便于多后端导出
- 指标采集代码必须 try/except 兜底

## 5. 练习题

### 练习 1：基础（必做）

为一个"用户登录"功能设计 4 类指标：
- Counter：登录成功/失败次数
- Gauge：当前在线用户
- Histogram：登录响应时间
- Summary：登录流程各阶段耗时（输入校验、密码校验、Session 创建）

### 练习 2：进阶

阅读 `api/extensions/otel/instrumentation.py` 的 `init_flask_instrumentor`，解释为什么 dify 选择 `http.server.response.count` 这个指标名（而不是 `http_requests_total`）？

### 练习 3：挑战（选做）

设计一个 `WorkflowMetrics`：用 OTEL Meter 为工作流引擎实现 4 类指标——工作流执行总数（Counter）、当前并发工作流数（Gauge）、执行时长（Histogram）、Token 用量分布（Histogram）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- Prometheus 指标类型文档：https://prometheus.io/docs/concepts/metric_types/
- OpenTelemetry Metrics API：https://opentelemetry.io/docs/specs/otel/metrics/api/

---

**文档版本**：v1.0
**最后更新**：2026-07-13