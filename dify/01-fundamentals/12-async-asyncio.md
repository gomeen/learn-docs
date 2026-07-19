# 1.1.12 Python 异步编程：`asyncio` / `async/await`

> 用最基础的方式理解：为什么要异步、`async/await` 写什么、常见坑怎么躲。能看懂 dify 里的 `async def` 即可。

## 🎯 学习目标

完成本文档后，你将能够：

- 用一句话说明：同步和异步差在哪里
- 正确写出并运行一个最简单的 `async def` + `await`
- 用 `asyncio.gather` 做「多个任务一起等」
- 识别两个最常见错误：忘记 `await`、在异步里用阻塞调用
- 对照真实业务场景，知道「什么时候该上异步」

## 📚 前置知识

- Python 函数基础（见 [02-python-functions](./02-python-functions.md)）
- 知道「函数调用会执行函数体」即可；协程会打破这个直觉

> 生成器、`yield` 能帮助理解「可暂停」，但**不是**本节必读。可选：[14-generator](./14-generator.md)

## 0. 先建立直觉（比语法更重要）

### 0.1 同步：一件事做完，再做下一件

```python
# 伪代码：同步请求 3 个 API
result_a = request("a.com")  # 等 1 秒
result_b = request("b.com")  # 再等 1 秒
result_c = request("c.com")  # 再等 1 秒
# 总耗时 ≈ 3 秒
```

等网络时，CPU 往往在**空等**，什么也干不了。

### 0.2 异步：等的时候，去干别的

```python
# 伪代码：异步并发
# 同时发出 3 个请求，谁先回来谁先处理
# 总耗时 ≈ 最慢那个 ≈ 1 秒
```

**类比**：同步像一个人排队买三杯咖啡，买完一杯再买下一杯；异步像同时点三杯，在等的时候可以干别的，三杯几乎一起好。

### 0.3 异步适合什么？不适合什么？

| 场景 | 是否适合 asyncio |
|---|---|
| 调 HTTP / 数据库 / 读网络 | ✅ 适合（大量时间在等 I/O） |
| 纯计算（加密、大循环、图像处理） | ❌ 不适合（占满 CPU，等也等不了 I/O） |
| 简单脚本、跑一次就结束 | 通常用同步就够 |

dify 的 API 层经常要并发请求外部服务、读写库，所以会大量出现 `async def`。

---

## 1. 核心概念（由浅入深）

### 1.1 最小可运行例子

先别管「协程」「事件循环」这些词，把下面代码跑通：

```python
import asyncio

async def hello():
    print("开始")
    await asyncio.sleep(1)  # 模拟「等 1 秒」（不堵死整个程序）
    print("结束")
    return "ok"

# 启动异步程序的标准写法
result = asyncio.run(hello())
print(result)  # ok
```

你只需要记住三件事：

1. **`async def`**：定义「异步函数」
2. **`await`**：在异步函数里「等另一个异步操作」
3. **`asyncio.run(...)`**：从普通（同步）代码里启动整段异步程序

### 1.2 关键误区：调用 `async def` 不会立刻执行

普通函数：

```python
def add(a, b):
    return a + b

print(add(1, 2))  # 3 —— 调用就立刻算
```

异步函数：

```python
async def add(a, b):
    return a + b

print(add(1, 2))
# <coroutine object add at 0x...>  —— 只得到「协程对象」，函数体还没跑
```

**协程对象**可以理解成：「一张待执行的任务单」，还没交给调度器。

要真正跑起来，必须二选一：

```python
# 方式 A：在另一个 async 函数里 await
async def main():
    result = await add(1, 2)
    print(result)

asyncio.run(main())

# 方式 B：最外层用 asyncio.run（只能包一层入口）
asyncio.run(add(1, 2))
```

### 1.3 `await` 到底在干什么？

`await something` 的含义是：

1. **先暂停**当前这个异步函数
2. **把控制权交出去**，让别的异步任务有机会跑
3. 等 `something` 完成后，**再从暂停处继续**，并拿到结果

```python
import asyncio

async def task(name, seconds):
    print(f"{name} 开始")
    await asyncio.sleep(seconds)  # 暂停期间，事件循环可以跑别的 task
    print(f"{name} 结束")
    return name

async def main():
    r = await task("A", 1)
    print("拿到结果:", r)

asyncio.run(main())
```

`asyncio.sleep` 是「异步版 sleep」。  
**千万别**在 `async def` 里写 `time.sleep`——那会把整个事件循环卡住（见 2.2）。

### 1.4 事件循环：一句话版

**事件循环（Event Loop）** = 异步世界的「调度员」。

- 你写很多 `async def`
- 调度员负责：谁该继续跑、谁在等 I/O、I/O 好了再叫醒谁

日常写业务代码时，你几乎**不用手写**事件循环；`asyncio.run()` 会帮你创建、运行、关闭。

```
你写的 async 函数  →  交给事件循环调度  →  在 await 处切换到别的任务
```

### 1.5 串行 vs 并发：为什么要 `gather` / `create_task`？

只写 `await A` 再 `await B`，仍然是**一个接一个**：

```python
import asyncio
import time

async def work(name, seconds):
    print(f"{name} 开始")
    await asyncio.sleep(seconds)
    print(f"{name} 结束")
    return name

async def serial():
    start = time.perf_counter()
    await work("A", 1)
    await work("B", 1)
    print(f"串行约 {time.perf_counter() - start:.1f} 秒")  # ≈ 2 秒

asyncio.run(serial())
```

要「两个一起等」，用 `asyncio.gather`（最常用、最好记）：

```python
async def concurrent():
    start = time.perf_counter()
    results = await asyncio.gather(
        work("A", 1),
        work("B", 1),
    )
    print(results)  # ['A', 'B']
    print(f"并发约 {time.perf_counter() - start:.1f} 秒")  # ≈ 1 秒

asyncio.run(concurrent())
```

也可以先 `create_task` 再 `await`（「先启动，后取结果」）：

```python
async def with_tasks():
    t1 = asyncio.create_task(work("A", 1))  # 立刻开始调度
    t2 = asyncio.create_task(work("B", 1))
    a = await t1
    b = await t2
    return [a, b]
```

> Task / Future 的细节、`gather` 与 `wait` 的区别，见下一篇 [13-async-task-future](./13-async-task-future.md)。  
> **本节记住**：要并发，用 `gather` 或 `create_task`，不要只写一串 `await`。

---

## 2. 代码示例与常见坑

### 2.1 串行 vs 并发（完整对比）

```python
import asyncio
import time

async def slow(name: str, seconds: float) -> str:
    print(f"{name} 开始")
    await asyncio.sleep(seconds)
    print(f"{name} 完成")
    return name

async def demo():
    # ❌ 串行：总时间相加
    t0 = time.perf_counter()
    await slow("A", 1)
    await slow("B", 1)
    print(f"串行: {time.perf_counter() - t0:.2f}s")

    # ✅ 并发：总时间 ≈ 最慢那个
    t0 = time.perf_counter()
    results = await asyncio.gather(slow("A", 1), slow("B", 1))
    print(f"并发: {time.perf_counter() - t0:.2f}s, 结果={results}")

asyncio.run(demo())
```

### 2.2 坑 1：在 async 里用阻塞调用

```python
import asyncio
import time

# ❌ 错误：time.sleep 会卡住整个事件循环
# 其他任务在这 1 秒内都跑不了
async def bad():
    time.sleep(1)
    return "done"

# ✅ 正确：用异步 sleep（或异步库：aiohttp、asyncpg 等）
async def good():
    await asyncio.sleep(1)
    return "done"
```

同理：

| 同步（会堵事件循环） | 异步替代 |
|---|---|
| `time.sleep` | `await asyncio.sleep` |
| `requests.get` | `await aiohttp` / `httpx.AsyncClient` |
| 同步 DB 驱动长时间查询 | 异步驱动，或放到线程池（进阶） |

### 2.3 坑 2：忘记 `await`

```python
import asyncio

async def fetch() -> str:
    await asyncio.sleep(0.1)
    return "data"

async def main():
    # ❌ 拿到的是协程对象，不是字符串
    coro = fetch()
    print(coro)  # <coroutine object fetch ...>
    # 还会有 RuntimeWarning: coroutine was never awaited

    # ✅
    result = await fetch()
    print(result)  # data

asyncio.run(main())
```

### 2.4 坑 3：在普通函数里直接 `await`

```python
# ❌ 语法错误：await 只能写在 async def 里面
def normal():
    await asyncio.sleep(1)

# ✅ 普通代码入口用 asyncio.run
async def entry():
    await asyncio.sleep(1)

asyncio.run(entry())
```

### 2.5 最小「并发请求」骨架（模拟 dify 调外部 API）

真实项目会用 `aiohttp` / `httpx`；这里用 `sleep` 模拟网络等待：

```python
import asyncio

async def fetch_url(url: str, delay: float) -> dict:
    await asyncio.sleep(delay)  # 假装在等网络
    return {"url": url, "status": 200}

async def fetch_all(urls: list[str]) -> list[dict]:
    # 每个 URL 假装延迟 0.5 秒；并发后总时间仍约 0.5 秒
    tasks = [fetch_url(u, 0.5) for u in urls]
    return await asyncio.gather(*tasks)

async def main():
    urls = ["https://a.com", "https://b.com", "https://c.com"]
    results = await fetch_all(urls)
    print(results)

asyncio.run(main())
```

---

## 3. 实际开发中的应用场景

语法会了还不够——**什么时候该写 async** 才是日常决策。下面都是后端里很常见的落地场景（含 dify 一类 LLM 应用）。

### 3.1 一张表：场景 → 怎么用

| 业务场景 | 为什么用异步 | 典型写法 |
|---|---|---|
| Web 接口要同时调多个下游 | 等网络时不堵死当前请求处理 | `await asyncio.gather(...)` |
| 异步 Web 框架路由（FastAPI / Sanic 等） | 一个进程扛更多并发连接 | `async def` 路由 + 异步库 |
| 聊天 / Agent：并行查知识库 + 调工具 + 调模型 | 总延迟 ≈ 最慢那一步，而不是相加 | 多个 `create_task` / `gather` |
| 对外 HTTP 代理、webhook、插件调用 | 高并发 I/O | `aiohttp` / `httpx.AsyncClient` |
| 流式输出（SSE / WebSocket 推 token） | 边生成边推，连接要长时间挂着 | `async for` + 异步写响应 |
| 批量健康检查、多租户配置拉取 | 同样是「大量等待」 | `gather` + 可选超时 |
| 纯 CPU 重计算、一次性小脚本 | 异步帮不上忙，还增加复杂度 | 同步即可；重活用进程/队列 |

### 3.2 场景 A：接口聚合——一次请求，多个下游

用户打开「应用详情」页，后端往往要：查库拿配置、调计费服务、拉最近运行记录。三步都是 I/O，**没有数据依赖**时就该并发：

```python
import asyncio

async def get_app_detail(app_id: str) -> dict:
    # 三个 I/O 同时发出，总耗时 ≈ max(各下游)，不是 sum
    config, usage, runs = await asyncio.gather(
        load_app_config(app_id),      # 读 DB / Redis
        fetch_quota_usage(app_id),    # 调内部 HTTP
        list_recent_runs(app_id, 10), # 再读一次存储
    )
    return {"config": config, "usage": usage, "recent_runs": runs}
```

**开发注意**：有依赖时不能乱并行（例如必须先拿到 `model_id` 才能调模型）。先画依赖，再决定哪些 `gather`。

### 3.3 场景 B：LLM / Agent 链路（dify 最典型）

一次对话可能同时需要：

1. 向量检索知识库  
2. 调用外部工具（HTTP 插件）  
3. 最后把结果塞进 prompt 调模型  

检索和工具调用彼此独立时，用并发能明显压低首 token 前的等待：

```python
async def prepare_context(query: str, tools: list) -> dict:
    knowledge, tool_results = await asyncio.gather(
        search_knowledge_base(query),
        run_tools_parallel(tools),  # 内部再 gather 多个工具
    )
    return {"knowledge": knowledge, "tools": tool_results}

async def chat(query: str) -> str:
    ctx = await prepare_context(query, tools=[...])
    # 有上下文之后再调模型（这一步依赖上面结果，必须串在后面）
    return await call_llm(query, context=ctx)
```

和 dify 的关系：工作流节点里「HTTP 请求节点」「知识库节点」等，底层经常是异步 HTTP / 异步 I/O；编排层再决定串行还是并行边。

### 3.4 场景 C：异步 Web 框架里的路由

```python
# FastAPI 风格示意
from fastapi import FastAPI

app = FastAPI()

@app.get("/apps/{app_id}")
async def app_detail(app_id: str):
    # 框架在事件循环里调用你的协程
    return await get_app_detail(app_id)
```

**容易踩坑**：

- 路由是 `async def`，里面却写 `requests.get` / 同步 ORM 长时间查询 → 堵事件循环，QPS 反而崩  
- 需要同步库时：要么换异步驱动，要么 `asyncio.to_thread(...)` 丢到线程池（进阶），要么把重活丢 Celery

### 3.5 场景 D：流式响应（聊天打字机效果）

产品要求「模型一边生成，前端一边显示」。连接会挂很久，适合异步 + 流式协议（SSE 见 [24-sse](../../_common/14-api-protocols/04-sse.md)）：

```python
async def stream_chat(query: str):
    async for chunk in llm_stream(query):  # 异步生成器
        yield chunk  # 框架写成 SSE / WebSocket 帧
```

这里重点不是 `gather`，而是：**长时间占用的连接不能用同步阻塞读**，否则一个聊天就占死一个 worker 线程。

### 3.6 场景 E：批量任务——脚本与运维

例如：给 50 个 webhook 做连通性探测、给 100 个租户刷缓存。

```python
async def ping_all(urls: list[str]) -> list[tuple[str, bool]]:
    async def one(url: str) -> tuple[str, bool]:
        try:
            await http_get(url, timeout=2)
            return url, True
        except Exception:
            return url, False

    return await asyncio.gather(*[one(u) for u in urls])
```

**开发注意**：批量时往往要**限流**（别一次打爆对方），限流用 `Semaphore`，见 [13-async-task-future](./13-async-task-future.md)。

### 3.7 场景 F：什么时候别用 asyncio

| 情况 | 更合适的做法 |
|---|---|
| 接口只查一次本地 DB，逻辑简单 | 同步框架 / 同步函数，代码更直观 |
| PDF 解析、大矩阵运算、视频转码 | 多进程、专用 worker、Celery |
| 任务要跨机器、可重试、可延时 | 任务队列（Celery / RQ），不是单进程协程 |
| 团队不熟异步，工期紧且 QPS 不高 | 先同步跑通，瓶颈再改 |

**经验法则**：瓶颈是「等网络 / 等磁盘」且单机要扛很多并发连接 → 考虑 asyncio；瓶颈是「算得慢」→ 进程或队列。

### 3.8 和「队列异步」怎么配合（产品里两种异步）

真实系统（含 dify）经常是组合拳：

```
用户请求
  → API（asyncio）：快速校验、写库、返回 run_id
  → Celery worker：真正跑长工作流、调模型、写结果
  → 前端轮询 / WebSocket：拿状态
```

| 你想做的事 | 用 asyncio | 用 Celery 等队列 |
|---|---|---|
| 同一个请求里并发调 3 个 HTTP | ✅ | 一般不用 |
| 工作流跑 10 分钟、要重试、要隔离 | 不适合独占 API 进程 | ✅ |
| 高并发短连接 API | ✅ | 可选，看架构 |

读 dify 源码时：看到 `async def` 多半是 **进程内 I/O**；看到 `.delay()` / `AsyncResult` 是 **跨进程任务**。

---

## 4. dify 仓库源码解读（先抓主线）

> 路径以你本机 dify 仓库为准，常见在 `dify/api/...`。

### 4.1 `async def` 不等于「里面全是 await」

**参考**：`api/services/async_workflow_service.py` 一类服务

思路示意（简化，非逐字源码）：

```python
class AsyncWorkflowService:
    async def trigger_workflow_async(
        self,
        tenant_id: str,
        workflow_id: str,
        user: Account,
        inputs: dict[str, Any],
    ) -> str:
        # 1) 查库、校验（可能是同步 ORM）
        workflow = load_workflow(tenant_id, workflow_id)

        # 2) 把重活丢给 Celery 队列（.delay 是同步 API）
        run_id = run_workflow_task.delay(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            user_id=user.id,
            inputs=inputs,
        )
        return str(run_id)
```

**怎么读**：

- 函数是 `async def`，所以可以挂在异步 Web 框架（如 Sanic / Quart / FastAPI）的路由上
- 内部可以**暂时没有** `await`——合法；只是没有在「等 I/O 时让出控制权」
- 这里的「异步」还有第二层含义：**Celery 后台任务**——API 立刻返回 `run_id`，真正跑工作流在 worker 里

两层「异步」别混：

| 层级 | 技术 | 作用 |
|---|---|---|
| 进程内 | `async/await` | 一个进程里高效处理大量 I/O 等待 |
| 跨进程 | Celery 等队列 | 把重任务丢给 worker，API 快速响应 |

### 4.2 异步 HTTP：`async with` + `await`

**参考**：`api/core/helper/ssrf_proxy.py` 一类代理客户端

```python
import aiohttp

async def get_text(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
```

**怎么读**：

- `async with`：异步版 `with`，离开时正确关闭连接（上下文管理器见 [11-context-manager](./11-context-manager.md)）
- `await response.text()`：读 body 也是异步的
- 为什么不用 `requests`？`requests` 是同步的，在事件循环线程里会堵死其他请求

---

## 5. 关键要点总结

1. **异步解决的是「等 I/O 时浪费」**，不是让 CPU 算得更快
2. **`async def` 调用 → 协程对象**；必须 `await` 或 `asyncio.run` 才会执行
3. **`await` = 暂停自己 + 让别人跑 + 回来拿结果**
4. **并发用 `gather` / `create_task`**；一串 `await` 仍是串行
5. **禁止**在 async 里用 `time.sleep` / 同步 `requests` 等阻塞调用
6. **落地场景**：多下游聚合、LLM 并行准备上下文、异步 Web、流式连接、批量探测；CPU 重活和长任务用进程/队列
7. dify 里：`async` 管 API 侧 I/O；重工作流常交给 Celery

## 6. 练习题

### 练习 1：基础（必做）

1. 写一个 `async def greet(name: str) -> str`，`await asyncio.sleep(0.5)` 后返回 `f"hi, {name}"`
2. 用 `asyncio.run` 打印结果
3. 故意去掉 `await`，观察输出和警告

### 练习 2：巩固（必做）

写 `async def fetch_all(names: list[str])`：对每个 name 调用上面的 `greet`，用 `gather` 并发，打印总耗时。  
对比：不用 `gather`、逐个 `await` 的耗时。

### 练习 3：场景题（推荐）

模拟「应用详情聚合」：三个异步函数 `load_config` / `load_usage` / `load_runs` 各 `sleep` 0.5 秒。  
分别用串行和 `gather` 实现 `get_app_detail`，对比耗时，并想一下：若 `load_runs` 依赖 `load_config` 里的字段，代码该怎么改？

### 练习 4：进阶（选做）

在本机 dify 仓库中搜索 `async def` 与 `aiohttp`，找一处真实调用，说明：

1. 对应本文哪类场景（聚合 / 代理 HTTP / 流式等）？
2. 入口是谁调用了这个 `async def`？
3. 有没有混用同步 I/O？

### 练习 5：挑战（选做）

用 `aiohttp` 或 `httpx.AsyncClient` 实现真正的 `fetch_all(urls)`，并发请求多个 URL，收集状态码。

## 7. 参考资料

- 下一篇（Task / Future / 调度细节）：[13-async-task-future](./13-async-task-future.md)
- 并发模型总览：[23-concurrency](./23-concurrency.md)
- 流式响应：[24-sse](../../_common/14-api-protocols/04-sse.md)
- Python 官方：https://docs.python.org/3/library/asyncio.html
- Real Python 入门：https://realpython.com/async-io-python/
- dify 参考目录（按你本机路径调整）：`api/services/`、`api/core/helper/`

---

**文档版本**：v1.2  
**最后更新**：2026-07-17
