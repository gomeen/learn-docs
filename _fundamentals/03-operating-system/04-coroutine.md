# 3.1.4 协程（Coroutine）：用户态线程

> 协程是用户态的"轻量级线程"，性能远高于线程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解协程与线程的区别
- 掌握 Python asyncio 的使用
- 了解协程的实现原理（事件循环 + 调度器）
- 能在 dify 中识别协程的应用（async/await）

## 📚 前置知识

- 02-thread.md
- 12-async-asyncio.md（推荐）

## 1. 核心概念

### 1.1 协程 vs 线程

| 维度 | 线程 | 协程 |
|------|------|------|
| 调度方 | **内核** | **用户程序** |
| 切换开销 | 大（系统调用） | **极小** |
| 并行 | ✓ | ✗（并发非并行） |
| 数量 | 几百到几千 | **几十万** |
| 同步问题 | 需要锁 | **不需要**（协作式） |

### 1.2 协程的特点

1. **协作式调度**：协程主动让出控制权（`await`），不被抢占
2. **用户态**：不经过内核，切换快
3. **轻量**：单个协程栈空间几 KB（线程是几 MB）

### 1.3 协程的实现模型

**对称协程**（Go goroutine）：
- 协程之间平等，无主从
- 用 `go` 关键字启动

**非对称协程**（Python asyncio）：
- 有调度器（事件循环）
- 用 `async def` + `await`

### 1.4 asyncio 事件循环

```
┌─────────────────────────┐
│   事件循环（Event Loop）  │
│                          │
│   ┌─── Task 队列 ──┐     │
│   │                │     │
│   ↓                ↓     │
│ Task 1          Task 2    │
│   ↓                ↓     │
│ I/O 等待        I/O 等待  │
└─────────────────────────┘
```

### 1.5 协程的应用场景

1. **高并发 I/O**：Web 服务器、爬虫
2. **WebSocket**：实时通信
3. **微服务**：gRPC、Kafka 客户端
4. **流式处理**：日志、消息
5. **数据库驱动**：asyncpg、aiomysql

## 2. 代码示例

### 2.1 Python asyncio 基础

```python
# 文件：async_demo.py
import asyncio
import time

async def fetch_data(n: int) -> str:
    """模拟 I/O 操作。"""
    await asyncio.sleep(1)  # 异步等待 1 秒
    return f"data-{n}"

async def main():
    # ❌ 串行（慢）
    start = time.perf_counter()
    for i in range(5):
        result = await fetch_data(i)  # 每次等 1 秒
    print(f"串行耗时: {time.perf_counter() - start:.2f}秒")  # ~5 秒

    # ✅ 并发（快）
    start = time.perf_counter()
    tasks = [fetch_data(i) for i in range(5)]
    results = await asyncio.gather(*tasks)  # 并发执行
    print(f"并发耗时: {time.perf_counter() - start:.2f}秒")  # ~1 秒
    print(f"结果: {results}")

asyncio.run(main())
```

### 2.2 aiohttp 异步 HTTP 客户端

```python
# 文件：aiohttp_demo.py
import asyncio
import aiohttp
import time

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# 对比同步版本
import requests

def fetch_all_sync(urls):
    return [requests.get(url).text for url in urls]

urls = ["https://api1.com", "https://api2.com", "https://api3.com"]

# 异步：~0.5 秒
start = time.perf_counter()
asyncio.run(fetch_all(urls))
print(f"异步: {time.perf_counter() - start:.2f}秒")

# 同步：~1.5 秒
start = time.perf_counter()
fetch_all_sync(urls)
print(f"同步: {time.perf_counter() - start:.2f}秒")
```

### 2.3 异步上下文管理器

```python
# 文件：async_context.py
import asyncio

class AsyncResource:
    """模拟异步资源（如数据库连接）。"""

    async def __aenter__(self):
        print("异步打开资源")
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("异步关闭资源")
        await asyncio.sleep(0.1)

    async def query(self, sql):
        await asyncio.sleep(0.1)
        return f"result of: {sql}"

async def main():
    async with AsyncResource() as res:
        result = await res.query("SELECT 1")
        print(result)

asyncio.run(main())
```

## 3. dify 仓库源码解读

### 3.1 dify 的 SSRF 异步 HTTP 客户端

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 80-130）：

```python
import asyncio
import aiohttp

class SSRFProxy:
    """SSRF 安全的异步 HTTP 客户端。

    dify 用 aiohttp 而不是 requests：
    - aiohttp 是异步的，配合 asyncio 实现高并发
    - requests 是同步的，会阻塞事件循环

    协程的实现：
    1. async def 定义协程函数
    2. await 暂停协程
    3. 事件循环调度其他协程
    4. I/O 完成后恢复协程
    """

    async def get(self, url: str, **kwargs) -> str:
        """异步 GET 请求。"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.text()

    async def post(self, url: str, data: dict, **kwargs) -> dict:
        """异步 POST 请求。"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

    async def batch_get(self, urls: list[str]) -> list[str]:
        """并发批量 GET。"""
        tasks = [self.get(url) for url in urls]
        return await asyncio.gather(*tasks)


# dify 的实际使用：
async def fetch_dataset_documents(urls: list[str]) -> list[str]:
    """从多个 URL 抓取文档 - 用协程并发。"""
    proxy = SSRFProxy()
    # 并发请求所有 URL
    results = await proxy.batch_get(urls)
    return results
```

**解读**：
- 第 24 行：`async with` 异步上下文管理器
- 第 26 行：`await response.text()` 异步读取响应
- 第 36 行：`asyncio.gather` 并发执行多个请求
- **设计意图**：dify 需要并发请求多个外部 API，协程是最合适的方式

## 4. 关键要点总结

- 协程：用户态线程，**轻量**（切换快、占用小）
- **协作式调度**：`await` 让出控制权，无锁问题
- 适合 **I/O 密集** 场景，**不适合 CPU 密集**
- Python `asyncio` + `aiohttp` 是经典组合
- dify 用 aiohttp 做异步 HTTP 请求

## 5. 练习题

### 练习 1：基础（必做）

写一个异步爬虫：并发请求 10 个 URL，统计总耗时（对比同步版本）。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何用 aiohttp 而不是 requests。

### 练习 3：挑战（选做）

用 `asyncio.Queue` 实现异步生产者-消费者：3 个协程生产数据，5 个协程消费数据。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- Python asyncio 文档：https://docs.python.org/3/library/asyncio.html
- 《操作系统概念》第 4 章 多线程和并发

---

**文档版本**：v1.0
**最后更新**：2026-07-13