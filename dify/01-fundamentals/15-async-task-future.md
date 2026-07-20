# 1.1.13 协程、Task、Future 与事件循环

> 在 [12-async-asyncio](./14-async-asyncio.md) 的基础上，分清三个容易混的词：**协程 / Task / Future**，并会用 `gather`、`create_task` 做并发。

## 🎯 学习目标

完成本文档后，你将能够：

- 用自己的话区分：协程、Task、Future
- 知道「只拿到协程对象」和「已经在跑的 Task」差在哪
- 会用 `gather`、`create_task`；了解 `as_completed` 何时有用
- 避免「创建了 Task 却没人管」（任务泄漏）
- 能把 Task / 超时 / 限流 / 取消 对上真实业务场景

## 📚 前置知识

- **必读**：[12-async-asyncio](./14-async-asyncio.md)（`async` / `await` / `asyncio.run`）
- 知道「函数可以返回一个对象」即可

> 本文偏「对象关系 + 常用 API」，不要求你手写事件循环底层。

## 0. 一张图建立关系

先记这张表，再往下看例子：

| 名字 | 你怎么得到它 | 现在在跑吗？ | 一句话 |
|---|---|---|---|
| **协程（Coroutine）** | 调用 `async def` 函数 | ❌ 还没跑 | 一张「待执行任务单」 |
| **Task** | `asyncio.create_task(协程)` | ✅ 已交给事件循环 | 已调度的「正在/即将执行的任务」 |
| **Future** | 较少手写；库有时返回 | 看实现 | 「将来会有一个结果」的占位符 |

继承关系（知道即可）：

```
Future  （将来会有结果）
  └── Task  （Future 的子类 + 绑定了一个协程去跑）
```

日常业务代码里：

- 你写得最多的是 **协程** + **`await`** + **`gather`**
- **Task** 在需要「先启动、稍后取结果 / 取消」时用
- **Future** 多数时候你是「用到」，不是「自己 new」

---

## 1. 核心概念

### 1.1 协程：还没开始跑

```python
import asyncio

async def fetch() -> int:
    print("fetch 开始")
    await asyncio.sleep(1)
    print("fetch 结束")
    return 42

# 只是创建协程对象，不会打印「fetch 开始」
coro = fetch()
print(type(coro))  # <class 'coroutine'>

# 必须有人执行它，例如：
# await coro          （在 async 函数里）
# 或 asyncio.run(fetch())
```

**记忆**：`fetch()` 像「点了菜但还没上灶」——菜单写好了，厨房还没动。

### 1.2 Task：已经上灶了

```python
import asyncio

async def fetch() -> int:
    print("fetch 开始")
    await asyncio.sleep(1)
    return 42

async def main():
    # create_task：立刻把协程交给事件循环调度
    task = asyncio.create_task(fetch())
    print("task 已创建", task.done())  # 通常还是 False（还在跑或等）

    # 做一点别的事……
    await asyncio.sleep(0.1)

    result = await task  # 等它完成，拿结果
    print(result)  # 42

asyncio.run(main())
```

**记忆**：`create_task` = 把任务单交给厨房，**现在就开始做**；`await task` = 等这道菜好了再端走。

和「直接 await 协程」的差别：

```python
async def main():
    # 方式 A：await 协程 —— 从现在开始跑，跑完再继续下一行
    r1 = await fetch()

    # 方式 B：先 create_task 再 await —— 可以先启动多个，再一起等
    t1 = asyncio.create_task(fetch())
    t2 = asyncio.create_task(fetch())
    r1 = await t1
    r2 = await t2
```

### 1.3 Future：将来会有结果的盒子

Future 是更底层的概念：**一个盒子，现在可能还是空的，以后会被放进结果或异常**。

```python
import asyncio

async def main():
    fut: asyncio.Future[int] = asyncio.Future()

    # 还没结果时，await 会一直等到有人 set_result / set_exception
    async def producer():
        await asyncio.sleep(0.5)
        fut.set_result(99)  # 往盒子里放结果

    asyncio.create_task(producer())
    value = await fut
    print(value)  # 99

asyncio.run(main())
```

入门阶段你**几乎不用**自己 `asyncio.Future()`。  
知道两件事就够：

1. **Task 是 Future 的一种**（所以 Task 也能 `await`、也能有结果/异常）
2. 很多库返回的「异步结果对象」思路和 Future 类似——例如 Celery 的 `AsyncResult`（见第 3 节）

### 1.4 事件循环在干什么？（仍用白话）

事件循环大致重复：

```
1. 跑当前「就绪」的 Task，直到它遇到 await（自己让出）
2. 去看哪些 I/O / 定时器已经好了
3. 把对应 Task 标为就绪，回到 1
```

你不需要实现这个循环；只要理解：

- **没有 await 的纯计算**会一直占着调度员，别人插不进队
- **await I/O** 才会让出，并发才有意义

### 1.5 三个常用 API：`gather` / `as_completed` / `wait`

#### `gather`：一起跑，一起收结果（首选）

```python
import asyncio

async def work(n: int) -> int:
    await asyncio.sleep(n * 0.1)
    return n

async def main():
    # 返回值顺序与传入顺序一致，不是完成顺序
    results = await asyncio.gather(work(3), work(1), work(2))
    print(results)  # [3, 1, 2]

asyncio.run(main())
```

适合：**全部都要**，且关心「按输入顺序的结果列表」。

#### `as_completed`：谁先完成先处理谁

```python
async def main():
    aws = [work(3), work(1), work(2)]
    for coro in asyncio.as_completed(aws):
        result = await coro
        print("先完成的:", result)  # 可能先打印 1，再 2，再 3

asyncio.run(main())
```

适合：流式展示进度、先到先处理。

#### `wait`：更细的控制（进阶，知道即可）

```python
async def main():
    tasks = [asyncio.create_task(work(i)) for i in (1, 2, 3)]
    done, pending = await asyncio.wait(
        tasks,
        timeout=0.25,
        return_when=asyncio.FIRST_COMPLETED,  # 或 ALL_COMPLETED 等
    )
    print("已完成数量:", len(done))
    print("还在跑数量:", len(pending))
    # 注意：pending 里的任务若不再需要，应 cancel，避免泄漏

asyncio.run(main())
```

入门优先 **`gather`**；需要超时/部分完成再查 `wait`。

### 1.6 Task 的常见操作

```python
task = asyncio.create_task(some_coro())

# 等待完成并拿结果（推荐）
result = await task

# 取消
task.cancel()
try:
    await task
except asyncio.CancelledError:
    print("被取消了")

# 状态查询
task.done()       # 是否结束（成功/失败/取消都算 done）
task.cancelled()  # 是否因取消而结束
task.exception()  # 若失败，返回异常对象（需在 done 后调用）
```

---

## 2. 代码示例

### 2.1 并排对比三种对象

```python
import asyncio

async def slow(n: float) -> float:
    await asyncio.sleep(n)
    return n * 2

async def main():
    # 1) 协程：创建了但没跑
    c = slow(0.1)
    print("协程类型:", type(c))
    # 若不 await / create_task，函数体不会执行
    # 这里演示完要关掉，避免 "never awaited" 警告：
    c.close()

    # 2) Task：已调度
    t = asyncio.create_task(slow(0.2))
    print("task.done() 刚创建时:", t.done())
    print(await t)  # 0.4

    # 3) Future：手动填结果
    f: asyncio.Future[int] = asyncio.Future()
    f.set_result(99)
    print(await f)  # 99

asyncio.run(main())
```

### 2.2 `gather` 遇到异常时

```python
import asyncio

async def ok() -> str:
    await asyncio.sleep(0.1)
    return "ok"

async def boom() -> str:
    await asyncio.sleep(0.05)
    raise ValueError("boom")

async def main():
    # 默认：任意一个失败，gather 整体抛错
    try:
        await asyncio.gather(ok(), boom())
    except ValueError as e:
        print("捕获:", e)

    # 不想整组失败：把异常放进结果列表
    results = await asyncio.gather(ok(), boom(), return_exceptions=True)
    print(results)
    # ['ok', ValueError('boom')]

asyncio.run(main())
```

### 2.3 坑：任务泄漏（创建了 Task 却没人管）

```python
import asyncio

async def background():
    await asyncio.sleep(2)
    print("后台做完了")

# ❌ 危险：函数返回后，task 可能还在跑；
# 事件循环结束时会警告 Task was destroyed but it is pending
async def bad():
    asyncio.create_task(background())
    return "立刻返回"

# ✅ 方案 1：保存引用并 await（或 gather）
async def good_await():
    task = asyncio.create_task(background())
    await task
    return "等后台结束再返回"

# ✅ 方案 2：明确「后台任务」时，至少保留引用 + 在退出前统一 await/cancel
async def good_track():
    tasks = set()

    def _track(t: asyncio.Task):
        tasks.add(t)
        t.add_done_callback(tasks.discard)

    _track(asyncio.create_task(background()))
    # ... 主逻辑 ...
    if tasks:
        await asyncio.gather(*tasks)

asyncio.run(good_await())
```

**原则**：每个 Task 都要有「归宿」——要么被 `await` / `gather`，要么在程序退出前取消并处理。

### 2.4 限制并发数量：`Semaphore`（实用进阶）

一次启动 1000 个 HTTP 请求容易打爆对方或本机连接。用信号量限制「同时最多 N 个」：

```python
import asyncio

async def fetch(i: int, sem: asyncio.Semaphore) -> int:
    async with sem:  # 最多 N 个协程同时进入
        await asyncio.sleep(0.1)
        return i

async def main():
    sem = asyncio.Semaphore(5)  # 最多 5 个并发
    results = await asyncio.gather(*[fetch(i, sem) for i in range(20)])
    print(len(results))

asyncio.run(main())
```

---

## 3. 实际开发中的应用场景

12 讲「要不要异步」；本节讲 **Task / Future 相关 API 在业务里具体干什么**——超时、取消、限流、部分失败、后台任务。

### 3.1 一张表：需求 → API

| 你在产品里遇到的需求 | 优先用什么 | 为什么 |
|---|---|---|
| 多个独立 I/O，全部结果都要，顺序与输入一致 | `asyncio.gather` | 写法短、结果好对 |
| 谁先返回先展示（进度条、部分结果） | `as_completed` | 按完成顺序处理 |
| 先启动、中间还能干别的，最后再取结果 | `create_task` + 稍后 `await` | Task 已在跑 |
| 下游最多等 3 秒，超时就失败/降级 | `asyncio.wait_for` / `timeout` | 保护接口延迟 |
| 用户取消请求 / 连接断开 | `task.cancel()` | 别继续烧模型配额 |
| 批量调第三方，QPS 不能超限 | `Semaphore` | 控制同时飞行中的请求数 |
| 一个失败不要拖死整组 | `gather(..., return_exceptions=True)` | 部分成功也可返回 |
| 任务要跨机器、可重试、跑很久 | Celery `AsyncResult` 等 | 不是单进程 Task 的职责 |

### 3.2 场景 A：接口超时与降级

调外部模型 / 插件时，不能无限等。超时后返回缓存或错误提示，比拖垮整站更好：

```python
import asyncio

async def call_plugin(url: str) -> dict:
    await asyncio.sleep(5)  # 假装很慢
    return {"ok": True}

async def safe_call(url: str) -> dict:
    try:
        return await asyncio.wait_for(call_plugin(url), timeout=2.0)
    except asyncio.TimeoutError:
        return {"ok": False, "error": "plugin timeout", "fallback": True}
```

**开发注意**：超时后若底层 HTTP 还在飞，最好配合可取消的客户端（或关闭 session），否则连接仍可能占着资源。

### 3.3 场景 B：用户取消 / 连接断开

聊天生成中途用户点「停止」，或网关断开 SSE。若继续 `await` 模型流，会浪费钱和算力：

```python
async def generate_with_cancel(prompt: str, cancel_event: asyncio.Event):
    task = asyncio.create_task(llm_generate(prompt))
    cancel_waiter = asyncio.create_task(cancel_event.wait())

    done, pending = await asyncio.wait(
        {task, cancel_waiter},
        return_when=asyncio.FIRST_COMPLETED,
    )
    if cancel_waiter in done:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return {"status": "cancelled"}
    cancel_waiter.cancel()
    return {"status": "ok", "text": task.result()}
```

简化理解：**Task 的价值是「能取消」**；只 `await` 一个协程时，中途打断会麻烦很多。

### 3.4 场景 C：批量插件 / webhook，必须限流

运营一次给 200 个客户推 webhook。`gather` 200 个没问题，但对方会限流你：

```python
async def deliver_all(urls: list[str], max_concurrent: int = 10) -> list:
    sem = asyncio.Semaphore(max_concurrent)

    async def one(url: str):
        async with sem:
            return await post_webhook(url)

    # 单个失败不影响其它：把异常收进列表
    return await asyncio.gather(
        *[one(u) for u in urls],
        return_exceptions=True,
    )
```

这是 **Task 数量可以很大，但同时执行的要封顶**——`Semaphore` 的日常用法。

### 3.5 场景 D：先完成先处理（进度与流式汇总）

导入 100 个文档做向量化：UI 要显示「已完成 37/100」，而不是全部结束才动：

```python
async def embed_all(docs: list[str]) -> None:
    total = len(docs)
    finished = 0
    for coro in asyncio.as_completed([embed(d) for d in docs]):
        await coro
        finished += 1
        await publish_progress(finished, total)  # 推给前端
```

和 `gather` 对比：`gather` 适合「最后一次性返回」；`as_completed` 适合「过程可见」。

### 3.6 场景 E：请求内的「后台小任务」

例如：接口主路径先返回结果，同时异步写审计日志、刷新缓存。**短生命周期、同进程**可以用 Task；**必须可靠投递**应上消息队列。

```python
async def update_profile(user_id: str, data: dict) -> dict:
    profile = await save_profile(user_id, data)

    # 同进程后台：注意保存引用，并在应用关闭时 drain
    asyncio.create_task(write_audit_log(user_id, "profile_update"))

    return profile
```

| 后台工作 | 用 `create_task` | 用 Celery / 队列 |
|---|---|---|
| 写一条无关紧要的日志（丢了可接受） | 可以（仍建议处理异常） | 可选 |
| 扣费、发邮件、跑工作流 | 不推荐 | ✅ |
| 进程重启后还要继续 | 不行 | ✅ |

### 3.7 场景 F：部分失败的聚合接口

仪表盘要拼 5 个服务的状态，允许个别挂掉：

```python
async def dashboard() -> dict:
    names = ["billing", "vector", "model", "storage", "plugin"]
    raw = await asyncio.gather(
        *[check_service(n) for n in names],
        return_exceptions=True,
    )
    services = {}
    for name, item in zip(names, raw):
        if isinstance(item, Exception):
            services[name] = {"up": False, "error": str(item)}
        else:
            services[name] = {"up": True, "detail": item}
    return {"services": services}
```

默认 `gather`（一错全错）适合「事务式全部成功」；监控、聚合、批量导入更常 `return_exceptions=True`。

### 3.8 场景 G：和 dify 产品功能的对应关系

| dify / 同类产品能力 | 更接近哪种机制 |
|---|---|
| 对话时并行检索 + 调工具 | 进程内 `gather` / Task |
| 工作流「运行中」可停止 | 取消（协程 cancel 或 worker 撤销） |
| 触发工作流立刻返回 `run_id` | Celery `AsyncResult`（分布式 Future） |
| 批量执行、队列优先级 | 队列 + worker，不是单机 `gather` 无限开 |
| 插件 HTTP 超时 | `wait_for` / HTTP client timeout |
| 高并发调外部 API | `Semaphore` + 连接池 |

**选型一句话**：

- 还在**当前这次 HTTP 请求**的生命周期里 → asyncio Task / gather  
- 要**跨请求、跨进程、可重试** → 队列 Future（Celery 等）

---

## 4. 关键要点总结

1. **协程** = 还没跑的任务单；**Task** = 已交给事件循环；**Future** = 将来装结果的盒子（Task 是其子类）
2. 并发优先用 **`asyncio.gather`**；要「先完成先处理」用 **`as_completed`**
3. **`create_task` 后必须有归宿**，否则任务泄漏
4. `gather` 默认「一错全错」；需要收集异常时用 `return_exceptions=True`
5. **落地场景**：超时降级、取消生成、批量限流、进度回调、部分失败聚合；长任务用队列 Future
6. dify 里常同时出现：**asyncio（进程内 I/O）** 与 **Celery AsyncResult（跨进程任务）**——概念相似，运行位置不同

---

**文档版本**：v1.2  
**最后更新**：2026-07-17
