# 10.3.1 链路追踪概念：Trace / Span / Context

> 理解分布式链路追踪的核心概念，能用 Span 把请求的全链路串联起来。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Trace / Span / SpanContext 的关系
- 掌握分布式追踪的"上下文传播"原理
- 能在 dify 中识别 Span 边界
- 为后续 OpenTelemetry 学习打基础

## 📚 前置知识

- 10.1 日志相关（理解 trace_id 的来源）
- 微服务基本概念
- 异步编程基础（详见 [async/await 与 asyncio](../01-fundamentals/12-async-asyncio.md)）

## 1. 核心概念

### 1.1 为什么需要链路追踪？

**问题场景**：一个用户请求涉及 5 个微服务、20 次数据库调用、3 次外部 API 调用。当请求变慢时，如何定位瓶颈？

**解决方案**：给请求中的每个操作打"标记"（Span），用同一个 trace_id 串联起来：

```
Trace abc123 (总耗时 1.2s)
├── Span: API Gateway (50ms)
│   ├── Span: Auth Service (20ms)
│   ├── Span: User Service (30ms)
│   └── Span: Order Service (1100ms)
│       ├── Span: DB query (50ms)
│       ├── Span: Inventory API (200ms)  ← 慢
│       └── Span: Payment API (800ms)   ← 超慢！
```

通过 trace 可视化（如 Jaeger / Tempo），一眼看出是 Payment API 卡住了。

### 1.2 核心概念

#### Trace（追踪）

一次完整的请求链路，从入口到所有相关操作结束。有一个全局唯一的 `trace_id`。

#### Span（跨度）

一个独立的操作单元（如一次 HTTP 调用、一次数据库查询）。每个 Span 有：
- `span_id`：当前 Span 的唯一 ID
- `parent_span_id`：父 Span 的 ID（构成树状结构）
- `operation_name`：操作名（如 `GET /api/users`）
- `start_time` / `end_time`：起止时间
- `attributes`：键值对属性
- `events`：时间点事件
- `status`：OK / ERROR

#### SpanContext（跨度上下文）

跨进程传递的最小信息集合：`trace_id + span_id + trace_flags`。通过 HTTP header（如 `traceparent`）传播。

### 1.3 上下文传播

跨服务调用时，需要把 trace 信息传递给下游：

```http
GET /api/orders HTTP/1.1
traceparent: 00-abc123-def456-01
user-agent: ...
```

下游服务读取 `traceparent`，作为自己 Span 的 parent。

### 1.4 Span 的属性

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order.id", "12345")
    span.set_attribute("order.amount", 99.99)
    span.add_event("payment.started", {"method": "credit_card"})
    try:
        result = process_payment()
        span.set_status(trace.StatusCode.OK)
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace.StatusCode.ERROR, str(e))
        raise
```

## 2. 代码示例

### 2.1 基础：手动创建 Span

```python
from opentelemetry import trace

tracer = trace.get_tracer("my-app")

def handle_request():
    # 创建根 Span
    with tracer.start_as_current_span("handle_request") as root_span:
        root_span.set_attribute("http.method", "GET")
        root_span.set_attribute("http.route", "/api/users")

        # 调用子操作，自动创建子 Span
        user = get_user(user_id=42)  # 子 Span: db.query
        return {"user": user}


def get_user(user_id: int):
    with tracer.start_as_current_span("db.query") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", "SELECT * FROM users WHERE id = $1")
        # 模拟数据库查询
        return {"id": user_id, "name": "Alice"}
```

### 2.2 异步环境下的 Span

```python
import asyncio
from opentelemetry import trace

tracer = trace.get_tracer("my-app")

async def fetch_all(urls):
    with tracer.start_as_current_span("fetch_all") as parent_span:
        parent_span.set_attribute("url.count", len(urls))
        # 并发执行多个请求，每个都有独立的子 Span
        tasks = [fetch_one(url) for url in urls]
        return await asyncio.gather(*tasks)


async def fetch_one(url):
    # 当前上下文会自动包含父 Span 的信息
    with tracer.start_as_current_span("http.get") as span:
        span.set_attribute("http.url", url)
        # 模拟 HTTP 请求
        await asyncio.sleep(0.1)
        return {"url": url, "status": 200}
```

### 2.3 常见错误：忘记传播上下文

```python
# ❌ 错误：跨线程时丢失上下文
import threading

def handle_request():
    with tracer.start_as_current_span("main"):
        # 在新线程中执行，上下文丢失！
        t = threading.Thread(target=process_async)
        t.start()

def process_async():
    # 这里 trace_id 是新的，没有关联到主 Span
    with tracer.start_as_current_span("background"):
        ...

# ✅ 正确：手动传递上下文
from opentelemetry.context import attach, detach

def handle_request():
    with tracer.start_as_current_span("main") as span:
        ctx = trace.set_span_in_context(span)
        token = attach(ctx)
        try:
            t = threading.Thread(target=process_async)
            t.start()
        finally:
            detach(token)
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Span 边界识别

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 58-79）：

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
```

**解读**：
- 第 22 行：`get_current_span()` 获取当前活跃 Span（由 Flask instrumentor 自动创建）
- 第 23 行：`is_recording()` 判断 Span 是否在采样中
- 第 26 行：`set_status(ERROR, ...)` 把异常标记到当前 Span
- **关键设计**：日志和 Span 联动——`logger.exception()` 自动把异常关联到当前 Span

### 3.2 dify 的上下文传播设置

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
- 第 2-7 行：组合 propagator，同时支持 W3C TraceContext 和 B3
- **W3C TraceContext**：标准协议，通过 `traceparent` header 传递
- **B3**：Zipkin 协议（早期业界标准）
- **关键设计**：兼容多种 propagator，避免与已有系统冲突

### 3.3 dify 的用户身份注入到 Span

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
**核心代码**（行 63-80）：

```python
@user_logged_in.connect
@user_loaded_from_request.connect
def on_user_loaded(_sender, user: Union["Account", "EndUser"]):
    if dify_config.ENABLE_OTEL:
        from opentelemetry.trace import get_current_span

        if user:
            try:
                current_span = get_current_span()
                tenant_id = extract_tenant_id(user)
                if not tenant_id:
                    return
                if current_span:
                    current_span.set_attribute(DifySpanAttributes.TENANT_ID, tenant_id)
                    current_span.set_attribute(GenAIAttributes.USER_ID, user.id)
            except Exception:
                logger.exception("Error setting tenant and user attributes")
                pass
```

**解读**：
- 第 1-2 行：Flask-Login 信号——用户登录或从请求加载时触发
- 第 4 行：只在 OTEL 启用时执行
- 第 9 行：获取当前 Span（由 Flask instrumentor 创建）
- 第 10 行：提取 tenant_id（多租户系统的关键字段）
- 第 13-14 行：把 tenant_id 和 user_id 作为 Span 属性
- 第 16-18 行：异常处理——业务失败不能影响登录流程
- **关键设计**：通过业务信号（user_loaded）注入业务属性，让 Span 包含租户/用户维度

## 4. 关键要点总结

- **Trace**：一次完整请求链路，全局唯一 `trace_id`
- **Span**：一个操作单元，有 `span_id` 和 `parent_span_id`
- **SpanContext**：跨进程传递的最小信息，通过 HTTP header 传播
- **W3C TraceContext** 是当前业界标准（`traceparent` header）
- Span 通过 `attributes` 携带业务属性（tenant_id、user_id）
- 日志和 Span 联动：`logger.exception()` 自动记录到当前 Span

## 5. 练习题

### 练习 1：基础（必做）

为"用户下单"流程设计 Span 结构：
- 入口：API Gateway
- 子操作：Auth、库存检查、支付、订单创建
- 每个 Span 标注耗时、状态、关键属性

### 练习 2：进阶

阅读 `api/extensions/otel/runtime.py` 的 `setup_context_propagation`，解释 W3C TraceContext 和 B3 协议的区别。dify 为什么同时支持两者？

### 练习 3：挑战（选做）

实现一个 `TraceContextMiddleware`：解析请求 header 中的 `traceparent`，如果是新请求就创建根 Span，否则 attach 到上游 Span。同时把 Span 关闭时的状态记录到日志。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
- OpenTelemetry Trace 规范：https://opentelemetry.io/docs/specs/otel/trace/api/
- W3C TraceContext：https://www.w3.org/TR/trace-context/
- OpenTelemetry Python 文档：https://opentelemetry.io/docs/languages/python/

---

**文档版本**：v1.0
**最后更新**：2026-07-13