# 10.1.4 日志上下文：trace_id / tenant_id

> 把请求级别的元数据（trace ID、用户身份、租户 ID）自动注入每条日志，让分布式系统可追踪。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解日志上下文（log context）的概念和价值
- 掌握 Python `contextvars` 的使用
- 能在多线程/异步环境下正确传递上下文
- 能看懂 dify `core/logging/context.py` 和 `filters.py` 的设计

## 📚 前置知识

- 10.1.3 结构化日志（`03-structured-logging.md`）
- 10.1.2 Python logging（`02-python-logging.md`）
- Python `contextvars` 模块

## 1. 核心概念

### 1.1 为什么需要日志上下文？

**问题场景**：一个 HTTP 请求触发 50 条日志，如何快速找到"属于这次请求的所有日志"？

**解决方案**：给每条日志自动注入 `request_id` / `trace_id`：

```
[req=abc123] [INFO] User logged in
[req=abc123] [INFO] Fetching user profile
[req=abc123] [DEBUG] Cache hit
[req=abc123] [INFO] Response 200
```

通过 grep `req=abc123`，一次就能拉出完整链路。

### 1.2 上下文的三大挑战

1. **线程隔离**：每个请求一个线程？用 `threading.local`
2. **异步隔离**：asyncio 的多个 task？用 `contextvars`（async 模型详见 [async/await 与 asyncio](../01-fundamentals/12-async-asyncio.md)）
3. **自动注入**：每个 `logger.info()` 自动带上上下文？用 `logging.Filter`

### 1.3 Python `contextvars` 简介

`contextvars` 是 Python 3.7+ 提供的**协程安全的局部变量**：

```python
import contextvars
import asyncio

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)

async def handle_request(req_id: str):
    request_id_var.set(req_id)  # 设置当前 task 的值
    await step1()
    await step2()

async def step1():
    await asyncio.sleep(0.1)
    print(request_id_var.get())  # 自动获取当前 task 的值
```

**关键特性**：
- `var.get()` 总是返回当前协程/task 设置的值
- task 切换时**自动隔离**，不会串扰
- 跨 await 传递，不需要显式传参

### 1.4 Logging Filter 自动注入

```python
import logging

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()  # 从 ContextVar 读
        return True

# Formatter 模板
fmt = "[%(request_id)s] %(levelname)s - %(message)s"
```

## 2. 代码示例

### 2.1 基础：ContextVar + Filter

```python
import contextvars
import logging
import uuid
from pythonjsonlogger import jsonlogger

# 1. 定义 ContextVar
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tenant_id", default=""
)


# 2. 定义 Filter
class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.tenant_id = tenant_id_var.get()
        return True


# 3. 配置 logging
handler = logging.StreamHandler()
handler.addFilter(ContextFilter())
handler.setFormatter(logging.Formatter(
    "[%(request_id)s][%(tenant_id)s] %(levelname)s - %(message)s"
))
logger = logging.getLogger("demo")
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# 4. 在请求入口设置 ContextVar
def handle_request(req_id: str, tenant: str):
    request_id_var.set(req_id)
    tenant_id_var.set(tenant)
    process_request()


def process_request():
    # 这里任何 logger 调用都自动带上 req_id 和 tenant_id
    logger.info("开始处理")
    logger.info("查询数据库")
    logger.info("返回结果")


# 测试
handle_request(uuid.uuid4().hex[:8], "tenant-42")
# 输出：
# [abc12345][tenant-42] INFO - 开始处理
# [abc12345][tenant-42] INFO - 查询数据库
# [abc12345][tenant-42] INFO - 返回结果
```

### 2.2 异步环境下的上下文隔离

```python
import asyncio
import contextvars
import logging

request_id_var = contextvars.ContextVar("request_id", default="")

async def task(name: str, sleep: float):
    request_id_var.set(name)  # 每个 task 设置自己的值
    await asyncio.sleep(sleep)
    logger.info(f"{name} 完成")  # 自动获取自己的 req_id


async def main():
    # 并发启动 3 个 task，每个有独立的 request_id
    await asyncio.gather(
        task("task-A", 1),
        task("task-B", 1),
        task("task-C", 1),
    )
    # 输出：
    # [task-A] INFO - task-A 完成
    # [task-B] INFO - task-B 完成
    # [task-C] INFO - task-C 完成
    # 不会出现串扰！
```

### 2.3 常见错误：用全局变量传上下文

```python
import threading

# ❌ 错误：多线程环境下会串扰
current_request_id = ""

def handle_request(req_id: str):
    global current_request_id
    current_request_id = req_id
    process()  # 在多线程下，current_request_id 可能被其他线程覆盖

# ✅ 正确：用 ContextVar
import contextvars
request_id_var = contextvars.ContextVar("request_id", default="")

def handle_request(req_id: str):
    request_id_var.set(req_id)  # 自动按 task/thread 隔离
    process()
```

## 3. dify 仓库源码解读

### 3.1 ContextVar 定义

**文件位置**：`/Users/xu/code/github/dify/api/core/logging/context.py`
**核心代码**（行 1-35）：

```python
"""Request context for logging - framework agnostic.

This module provides request-scoped context variables for logging,
using Python's contextvars for thread-safe and async-safe storage.
"""

import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("log_request_id", default="")
_trace_id: ContextVar[str] = ContextVar("log_trace_id", default="")


def get_request_id() -> str:
    """Get current request ID (10 hex chars)."""
    return _request_id.get()


def get_trace_id() -> str:
    """Get fallback trace ID when OTEL is unavailable (32 hex chars)."""
    return _trace_id.get()


def init_request_context() -> None:
    """Initialize request context. Call at start of each request."""
    req_id = uuid.uuid4().hex[:10]
    trace_id = uuid.uuid5(uuid.NAMESPACE_DNS, req_id).hex
    _request_id.set(req_id)
    _trace_id.set(trace_id)


def clear_request_context() -> None:
    """Clear request context. Call at end of request (optional)."""
    _request_id.set("")
    _trace_id.set("")
```

**解读**：
- 第 10-11 行：模块级 ContextVar，`default=""` 避免 KeyError
- 第 14-21 行：访问函数封装，便于未来切换底层实现
- 第 24-29 行：`init_request_context` 在请求开始时调用
  - `req_id` 是 10 字符短 ID（用户友好）
  - `trace_id` 是 32 字符 UUID5（兼容 OTEL 格式）
- **关键设计**：`uuid5(NAMESPACE_DNS, req_id)` 让相同 req_id 总是产生相同 trace_id，便于跨服务关联

### 3.2 TraceContextFilter：从 OTEL 或 ContextVar 取 trace

**文件位置**：`/Users/xu/code/github/dify/api/core/logging/filters.py`
**核心代码**（行 13-50）：

```python
class TraceContextFilter(logging.Filter):
    """
    Filter that adds trace_id and span_id to log records.
    Integrates with OpenTelemetry when available, falls back to ContextVar-based trace_id.
    """

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        # Get trace context from OpenTelemetry
        trace_id, span_id = self._get_otel_context()

        # Set trace_id (fallback to ContextVar if no OTEL context)
        if trace_id:
            record.trace_id = trace_id
        else:
            record.trace_id = get_trace_id()

        record.span_id = span_id or ""

        # For backward compatibility, also set req_id
        record.req_id = get_request_id()

        return True

    def _get_otel_context(self) -> tuple[str, str]:
        """Extract trace_id and span_id from OpenTelemetry context."""
        with contextlib.suppress(Exception):
            from opentelemetry.trace import get_current_span
            from opentelemetry.trace.span import INVALID_SPAN_ID, INVALID_TRACE_ID

            span = get_current_span()
            if span and span.get_span_context():
                ctx = span.get_span_context()
                if ctx.is_valid and ctx.trace_id != INVALID_TRACE_ID:
                    trace_id = f"{ctx.trace_id:032x}"
                    span_id = f"{ctx.span_id:016x}" if ctx.span_id != INVALID_SPAN_ID else ""
                    return trace_id, span_id
        return "", ""
```

**解读**：
- 第 9-10 行：先尝试从 OpenTelemetry 取（生产环境）
- 第 13-15 行：取不到就用 ContextVar 兜底（开发环境或未接入 OTEL）
- 第 18 行：`record.span_id = ""` 兜底空值
- 第 21 行：保留 `req_id` 字段以兼容旧版日志系统
- 第 25-32 行：`_get_otel_context` 用 `contextlib.suppress` 吞掉所有异常——日志 filter 永远不应该抛异常
- **关键设计**：OTEL 优先，ContextVar 兜底，让两套方案平滑过渡

### 3.3 IdentityContextFilter：注入租户和用户信息

**文件位置**：`/Users/xu/code/github/dify/api/core/logging/filters.py`
**核心代码**（行 53-99）：

```python
class IdentityContextFilter(logging.Filter):
    """
    Filter that adds user identity context to log records.
    Extracts tenant_id, user_id, and user_type from Flask-Login current_user.
    """

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        identity = self._extract_identity()
        record.tenant_id = identity.get("tenant_id", "")
        record.user_id = identity.get("user_id", "")
        record.user_type = identity.get("user_type", "")
        return True

    def _extract_identity(self) -> IdentityDict:
        """Extract identity from current_user if in request context."""
        try:
            if not flask.has_request_context():
                return {}
            from flask_login import current_user

            # Check if user is authenticated using the proxy
            if not current_user.is_authenticated:
                return {}

            # Access the underlying user object
            user = current_user

            from models import Account
            from models.model import EndUser

            identity: IdentityDict = {}

            match user:
                case Account():
                    if user.current_tenant_id:
                        identity["tenant_id"] = user.current_tenant_id
                    identity["user_id"] = user.id
                    identity["user_type"] = "account"
                case EndUser():
                    identity["tenant_id"] = user.tenant_id
                    identity["user_id"] = user.id
                    identity["user_type"] = user.type or "end_user"

            return identity
        except Exception:
            return {}
```

**解读**：
- 第 8-13 行：用 `match/case` 区分两种用户类型——`Account`（内部用户）和 `EndUser`（终端用户）
- 第 19-22 行：`flask.has_request_context()` 判断是否在 HTTP 请求中——后台任务（Celery）返回空 dict
- 第 24-25 行：未认证用户返回空 dict，字段会显示为空字符串
- 第 41-43 行：**整段 try/except 返回 {}**——日志 filter 不能影响业务逻辑
- **关键设计**：在 filter 内部做 lazy import，避免循环引用

## 4. 关键要点总结

- 日志上下文 = 请求级别的元数据（trace_id / user_id / tenant_id）
- Python 用 `contextvars` 解决多线程/异步隔离问题
- `logging.Filter` 自动注入上下文，无需手动传参
- **Filter 必须用 try/except 兜底**，永远不能影响业务
- dify 设计：OTEL 优先 + ContextVar 兜底，平滑过渡
- dify 通过 `match/case` 区分 Account 和 EndUser 两类身份

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `RequestContextMiddleware`：每次 HTTP 请求开始时调用 `init_request_context()`，结束时 `clear_request_context()`。需要处理异常情况（请求中途出错也要清理）。

### 练习 2：进阶

阅读 `api/core/logging/context.py` 和 `api/core/logging/filters.py`，画出完整的日志上下文流程图：HTTP 请求 → 中间件 → Filter → Formatter → JSON 输出。

### 练习 3：挑战（选做）

dify 的 `init_request_context` 用 `uuid5(NAMESPACE_DNS, req_id)` 生成 trace_id。改用真正的 OpenTelemetry API，让 request 进入时自动创建一个 root span，并把 span_id 注入到 `ContextVar` 中。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/logging/context.py`
- `/Users/xu/code/github/dify/api/core/logging/filters.py`
- `/Users/xu/code/github/dify/api/extensions/ext_logging.py`
- Python contextvars 文档：https://docs.python.org/3/library/contextvars.html
- OpenTelemetry Trace Context：https://www.w3.org/TR/trace-context/

---

**文档版本**：v1.0
**最后更新**：2026-07-13