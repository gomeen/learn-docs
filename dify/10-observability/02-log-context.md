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
- 10.1.2 Python logging（`01-python-logging.md`）
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
2. **异步隔离**：asyncio 的多个 task？用 `contextvars`（async 模型详见 [async/await 与 asyncio](../01-fundamentals/14-async-asyncio.md)）
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

## 3. 关键要点总结

- 日志上下文 = 请求级别的元数据（trace_id / user_id / tenant_id）
- Python 用 `contextvars` 解决多线程/异步隔离问题
- `logging.Filter` 自动注入上下文，无需手动传参
- **Filter 必须用 try/except 兜底**，永远不能影响业务
- dify 设计：OTEL 优先 + ContextVar 兜底，平滑过渡
- dify 通过 `match/case` 区分 Account 和 EndUser 两类身份

---

**文档版本**：v1.0
**最后更新**：2026-07-13
