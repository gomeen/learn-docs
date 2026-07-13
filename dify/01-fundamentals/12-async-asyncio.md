# 1.1.12 Python 异步编程：`asyncio` / `async/await`

> 理解 Python 异步编程的核心机制，能看懂 dify 后端所有 `async def` 函数。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解协程、事件循环、Task、Future 的关系
- 正确使用 `async/await` 编写异步代码
- 识别并避免异步编程的常见陷阱（阻塞调用、忘记 await 等）
- 能看懂 dify 中所有异步代码（如 `services/async_workflow_service.py`）

## 📚 前置知识

- Python 基础语法（函数、装饰器）
- 生成器基础（可选）
- 01-fundamentals/08-generator.md（推荐先看）

## 1. 核心概念

### 1.1 为什么需要异步？

在 I/O 密集型场景（网络请求、数据库查询、文件读写）中，CPU 实际上大部分时间在**等待** I/O 完成。同步代码会阻塞整个线程，导致并发能力差。

**举例**：一个 Web 服务需要调用 3 个外部 API，每个 API 耗时 1 秒：
- **同步**：总耗时 3 秒
- **异步**：总耗时 ~1 秒（3 个请求并发）

### 1.2 协程（Coroutine）

协程是**可暂停和恢复**的函数。用 `async def` 定义：

```python
async def fetch_data():
    # 这里是同步代码
    return {"data": 123}

# 调用 fetch_data() 不会执行函数体，而是返回一个协程对象
coro = fetch_data()
print(type(coro))  # <class 'coroutine'>
```

要真正执行协程，必须：
- 在另一个 `async def` 中用 `await` 调用
- 或者用 `asyncio.run()` 启动事件循环

### 1.3 `await` 关键字

`await` 做了两件事：
1. **暂停**当前协程，让出控制权给事件循环
2. **等待**另一个协程完成后，**恢复**当前协程并返回结果

```python
import asyncio

async def task1():
    print("task1 start")
    await asyncio.sleep(1)  # 暂停 1 秒，期间事件循环可以执行其他任务
    print("task1 end")
    return 1
```

### 1.4 事件循环（Event Loop）

事件循环是异步代码的**调度器**，负责：
- 管理所有 Task
- 在 I/O 完成时唤醒对应的协程
- 在多个协程间切换（协作式调度）

```python
import asyncio

async def main():
    await task1()

# asyncio.run() 创建事件循环，运行 main，等待完成后关闭
asyncio.run(main())
```

### 1.5 Task 与并发

`asyncio.create_task(coro)` 把协程**包装成 Task**，使其立即开始执行（不阻塞当前协程）：

```python
import asyncio

async def fetch(url, delay):
    await asyncio.sleep(delay)
    return f"result from {url}"

async def main():
    # 并发启动 3 个任务
    task1 = asyncio.create_task(fetch("a.com", 1))
    task2 = asyncio.create_task(fetch("b.com", 2))
    task3 = asyncio.create_task(fetch("c.com", 3))

    # 等待所有任务完成
    results = await asyncio.gather(task1, task2, task3)
    print(results)

asyncio.run(main())  # 总耗时 ~3 秒（不是 6 秒）
```

## 2. 代码示例

### 2.1 基础用法：串行 vs 并发

```python
import asyncio
import time

async def slow_operation(name, seconds):
    print(f"{name} 开始")
    await asyncio.sleep(seconds)
    print(f"{name} 完成")
    return name

# ❌ 串行执行（慢）
async def serial():
    start = time.time()
    await slow_operation("A", 1)
    await slow_operation("B", 1)
    print(f"串行耗时: {time.time() - start:.2f}秒")  # ~2 秒

# ✅ 并发执行（快）
async def concurrent():
    start = time.time()
    results = await asyncio.gather(
        slow_operation("A", 1),
        slow_operation("B", 1),
    )
    print(f"并发耗时: {time.time() - start:.2f}秒")  # ~1 秒

asyncio.run(concurrent())
```

### 2.2 常见错误：阻塞调用

```python
import asyncio
import time

# ❌ 错误：在异步函数中使用同步阻塞调用
async def bad_practice():
    time.sleep(1)  # 阻塞整个事件循环！
    return "done"

# ✅ 正确：使用异步版本
async def good_practice():
    await asyncio.sleep(1)  # 不阻塞事件循环
    return "done"
```

### 2.3 常见错误：忘记 `await`

```python
import asyncio

async def fetch():
    await asyncio.sleep(1)
    return "data"

async def main():
    # ❌ 错误：coro 是协程对象，不是结果
    coro = fetch()
    print(coro)  # <coroutine object>

    # ✅ 正确：用 await 获取结果
    result = await fetch()
    print(result)  # "data"
```

## 3. dify 仓库源码解读

### 3.1 异步任务分发服务

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 1-50）：

```python
import asyncio
from typing import Any

from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.account import Account
from models.workflow import Workflow
from tasks.workflow import run_workflow_task  # Celery 任务（同步）

class AsyncWorkflowService:
    """异步工作流服务：负责触发工作流的执行。

    这里"异步"有两层含义：
    1. Python 层面的 async/await（I/O 异步）
    2. 任务队列层面的 Celery（CPU 密集型任务分发）

    两者配合使用：API 请求快速响应，重活交给 Celery worker。
    """

    async def trigger_workflow_async(
        self,
        tenant_id: str,
        workflow_id: str,
        user: Account,
        inputs: dict[str, Any],
    ) -> str:
        """触发工作流执行，立即返回 run_id。

        Returns:
            workflow_run_id，可用于查询执行状态
        """
        # Step 1: 同步检查前置条件（数据库查询）
        with Session(db.engine, expire_on_commit=False) as session:
            workflow = session.query(Workflow).filter_by(
                tenant_id=tenant_id,
                id=workflow_id,
            ).first()

            if workflow is None:
                raise WorkflowNotFoundError(workflow_id)

        # Step 2: 提交到 Celery（同步操作）
        run_id = run_workflow_task.delay(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            user_id=user.id,
            inputs=inputs,
        )

        return str(run_id)
```

**解读**：
- 第 33 行：`async def` 函数，但内部没有 `await`——这是合法的，async 函数可以包含纯同步代码
- 第 37 行：使用 `with Session(...)` 上下文管理器管理数据库连接
- 第 50 行：`.delay()` 是 Celery 的同步方法，把任务推到 Redis 队列
- **关键设计**：API 层快速响应（不阻塞），实际工作流执行由 Celery worker 异步处理

### 3.2 异步上下文管理器

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 100-130）：

```python
import aiohttp

class SSRFProxy:
    """SSRF 安全的异步 HTTP 客户端。

    通过代理转发外部请求，避免服务端请求伪造攻击。
    """

    async def get(self, url: str, **kwargs) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.text()

    async def post(self, url: str, data: dict, **kwargs) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
```

**解读**：
- 第 13 行：`async with aiohttp.ClientSession() as session`——异步上下文管理器
- 第 14 行：`await response.text()`——异步读取响应体
- **为什么用 aiohttp 而不是 requests？** 因为 dify 需要并发请求多个外部 API，requests 是同步的会阻塞事件循环

## 4. 关键要点总结

- `async def` 定义协程函数，调用时不执行函数体，只返回协程对象
- `await` 暂停当前协程并等待另一个协程完成
- `asyncio.create_task()` 把协程包装成 Task 实现并发
- `asyncio.gather()` 并发执行多个协程并收集结果
- **绝不能在 async 函数中使用同步阻塞调用**（`time.sleep` / `requests.get` / `open()`）
- dify 中：`async def` 用于 API 层 I/O 密集操作，CPU 密集型任务用 Celery

## 5. 练习题

### 练习 1：基础（必做）

写一个异步函数 `fetch_all(urls: list[str])`，并发请求所有 URL 并返回结果列表（模拟 dify 的 SSRFProxy）。

```python
import asyncio
import aiohttp

async def fetch_all(urls):
    # TODO: 实现并发请求
    pass

# 测试
urls = ["https://api1.com", "https://api2.com", "https://api3.com"]
results = asyncio.run(fetch_all(urls))
```

### 练习 2：进阶

阅读 `api/services/async_workflow_service.py`，理解 `trigger_workflow_async` 的完整执行流程，并画出调用时序图（用户 → API → Celery → Worker → DB）。

### 练习 3：挑战（选做）

修改 `AsyncWorkflowService`，让 `trigger_workflow_async` 支持**批量触发**：一次性提交 100 个工作流，要求总耗时 < 2 秒（提示：用 `asyncio.gather` + Celery 的 `apply_async`）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- `/Users/xu/code/github/dify/api/tasks/workflow.py`
- Python 官方文档：https://docs.python.org/3/library/asyncio.html
- Real Python 异步教程：https://realpython.com/async-io-python/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
