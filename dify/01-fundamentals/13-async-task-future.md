# 1.1.13 协程、Task、Future 与事件循环

> 深入理解 asyncio 的三大核心对象：协程（Coroutine）、Task、Future，以及事件循环的调度机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分协程、Task、Future 三个概念
- 理解事件循环的调度原理
- 掌握 `asyncio.gather` / `asyncio.wait` / `asyncio.create_task` 的适用场景
- 能调试异步代码中的常见问题（任务泄漏、回调异常）

## 📚 前置知识

- 01-fundamentals/06-async-asyncio.md
- Python 基础：函数、闭包

## 1. 核心概念

### 1.1 协程 vs Task vs Future

| 对象 | 创建方式 | 是否正在执行 | 关键特性 |
|---|---|---|---|
| **Coroutine** | 调用 `async def` 函数 | 否，只是"可执行对象" | 必须被 await 或包装为 Task |
| **Task** | `asyncio.create_task(coro)` | 是，立即调度 | Future 的子类，可以取消、添加回调 |
| **Future** | `asyncio.Future()` 或库返回 | 取决于实现 | 低层"未来某个时刻有结果"的占位符 |

```python
import asyncio

async def fetch():
    await asyncio.sleep(1)
    return 42

# 1. 协程对象（未执行）
coro = fetch()                # <coroutine object>
# coro 不会自动执行

# 2. Task（已调度到事件循环）
task = asyncio.create_task(coro)
# task 已经"在后台跑"

# 3. Future（低层占位符）
future = asyncio.Future()
future.set_result(42)         # 显式设置结果
```

### 1.2 事件循环的工作原理

事件循环维护一个**就绪队列**和**I/O 回调列表**，不断循环执行：

```
事件循环 tick:
1. 执行就绪队列中所有 Task 直到它们 await
2. 收集 I/O 完成的回调
3. 把因 I/O 完成而被唤醒的 Task 重新加入就绪队列
4. 回到 1
```

### 1.3 `gather` vs `wait` vs `as_completed`

```python
import asyncio

# gather：并发执行，全部成功才返回（一个失败全部失败）
results = await asyncio.gather(coro1(), coro2(), coro3())

# wait：更灵活的控制（可以指定超时、部分完成）
done, pending = await asyncio.wait(
    [coro1(), coro2()],
    timeout=5,
    return_when=asyncio.FIRST_COMPLETED,
)

# as_completed：按完成顺序产出结果
for coro in asyncio.as_completed([coro1(), coro2(), coro3()]):
    result = await coro
    print(result)
```

### 1.4 Task 的生命周期

```python
task = asyncio.create_task(coro)
# 状态：PENDING → RUNNING → FINISHED（或 CANCELLED）

# 取消任务
task.cancel()

# 检查是否取消
if task.cancelled():
    ...

# 获取异常（如果有）
try:
    await task
except asyncio.CancelledError:
    ...
except Exception as e:
    print(task.exception())
```

## 2. 代码示例

### 2.1 演示三种对象的差异

```python
import asyncio

async def slow_op(n):
    await asyncio.sleep(n)
    return n * 2

async def main():
    # 1. 协程：未执行
    c = slow_op(1)
    print(type(c))  # <class 'coroutine'>
    # 不打印任何东西，因为没人执行它

    # 2. Task：立即调度
    t = asyncio.create_task(slow_op(2))
    print(t.done())  # False
    print(t.get_name())  # 默认 Task-1

    # 3. Future：手动控制
    f: asyncio.Future = asyncio.Future()
    f.set_result(99)
    print(await f)  # 99

    # 等待 task 完成
    result = await t
    print(result)  # 4

asyncio.run(main())
```

### 2.2 `gather` 的错误处理

```python
import asyncio

async def success():
    await asyncio.sleep(1)
    return "ok"

async def fail():
    await asyncio.sleep(0.5)
    raise ValueError("boom")

async def main():
    # 默认行为：任何一个失败，gather 抛异常
    try:
        results = await asyncio.gather(success(), fail())
    except ValueError as e:
        print(f"Caught: {e}")
    # 成功的结果会被丢弃！

    # return_exceptions=True：把异常放进结果列表
    results = await asyncio.gather(success(), fail(), return_exceptions=True)
    print(results)  # ['ok', ValueError('boom')]

asyncio.run(main())
```

### 2.3 常见错误：任务泄漏

```python
import asyncio

async def fire_and_forget():
    # ❌ 错误：创建的 task 没被 await，事件循环结束后会被警告
    asyncio.create_task(slow_op(2))
    return "done"

# 修复 1：保存并 await
async def correct_v1():
    task = asyncio.create_task(slow_op(2))
    return await task

# 修复 2：add_done_callback
async def correct_v2():
    task = asyncio.create_task(slow_op(2))
    task.add_done_callback(lambda t: print(f"done: {t.result()}"))
    return "done"
```

## 3. dify 仓库源码解读

### 3.1 Celery 异步结果（与 asyncio.Future 类似的概念）

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 161-172）：

```python
from celery.result import AsyncResult

# 9. Dispatch to appropriate queue
task_data_dict = task_data.model_dump(mode="json")

try:
    task: AsyncResult[Any] | None = None
    if queue_name == QueuePriority.PROFESSIONAL:
        task = execute_workflow_professional.delay(task_data_dict)
    elif queue_name == QueuePriority.TEAM:
        task = execute_workflow_team.delay(task_data_dict)
    else:  # SANDBOX
        task = execute_workflow_sandbox.delay(task_data_dict)
    quota_charge.commit()
except Exception:
    quota_charge.refund()
    raise
```

**解读**：
- 第 5-9 行：`execute_workflow_*.delay()` 返回 `AsyncResult`，是 Celery 的 Future-like 对象
- `AsyncResult` 提供 `task.id`（任务 ID）、`task.status`（状态）、`task.get()`（阻塞获取结果）等接口
- **关键设计**：dify 把"Future 模式"应用到分布式任务队列——API 调用立即返回 task id，前端轮询或 WebSocket 推送获取结果

### 3.2 异步工作流的错误处理

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 138-152）：

```python
# 7. Reserve quota (commit after successful dispatch)
quota_charge = unlimited()
try:
    quota_charge = QuotaService.reserve(QuotaType.WORKFLOW, trigger_data.tenant_id)
except QuotaExceededError as e:
    # Update trigger log status
    trigger_log.status = WorkflowTriggerStatus.RATE_LIMITED
    trigger_log.error = f"Quota limit reached: {e}"
    trigger_log_repo.update(trigger_log)
    session.commit()

    raise WorkflowQuotaLimitError(
        f"Workflow execution quota limit reached for tenant {trigger_data.tenant_id}"
    ) from e
```

**解读**：
- 第 4-5 行：先"预留"配额，配额服务可能抛 `QuotaExceededError`
- 第 6-12 行：捕获后**回滚状态**——记录到 trigger_log，重新抛出
- 第 13 行：`raise ... from e` 保留异常链（Python 3 `from` 语法），便于调试
- **关键设计**：异步任务链路中的错误必须被记录到数据库，否则事后无法追溯

## 4. 关键要点总结

- **Coroutine**：未执行的协程对象，必须被 await 或包装成 Task
- **Task**：包装好的"可执行单元"，由事件循环调度，支持 `cancel()` 和回调
- **Future**：低层占位符，Task 是 Future 的子类
- `gather` 适合"全部成功"的场景，`as_completed` 适合"流式处理"场景
- 异步任务必须有"归宿"——要么 await，要么 add_done_callback，否则会泄漏
- dify 用 Celery 的 `AsyncResult` 在分布式场景下复用 Future 模式

## 5. 练习题

### 练习 1：基础（必做）

写一个程序并发执行 3 个 sleep(1) 的协程，测量总耗时。然后分别用 `gather`、`as_completed` 改写，对比差异。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/services/async_workflow_service.py` 的 `trigger_workflow_async`，画出"配额预留→任务派发→状态更新"的完整时序图。

### 练习 3：挑战（选做）

实现一个 `pool` 装饰器：用信号量（`asyncio.Semaphore`）限制并发任务数不超过 N，所有任务排队进入。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
- Python 官方文档：https://docs.python.org/3/library/asyncio-task.html
- Celery 文档：https://docs.celeryq.dev/en/stable/reference/celery.result.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13