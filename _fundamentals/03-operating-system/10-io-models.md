# 3.3.1 五种 IO 模型：阻塞 / 非阻塞 / IO 复用 / 信号驱动 / 异步

> 理解 IO 模型是写高性能服务器的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 5 种 IO 模型
- 理解 select/poll/epoll 的演进（详解见 [11-io-multiplexing](./11-io-multiplexing.md)）
- 知道 Linux 的 aio 和 io_uring
- 能在 dify 中识别 IO 模型的应用（asyncio + epoll；同步/异步辨析见 [13-sync-async](./13-sync-async.md)）

## 📚 前置知识

- 04-coroutine.md
- 12-async-asyncio.md

## 1. 核心概念

### 1.1 为什么需要理解 IO 模型？

Web 服务器需要处理成千上万的并发连接，IO 模型决定并发能力。

```
阻塞 IO：1 个连接 = 1 个线程
异步 IO：1 个线程 = 10000 个连接（理论）
```

### 1.2 五种 IO 模型

#### 阻塞 IO（Blocking IO）

```
read():
  1. 等待数据就绪（阻塞）
  2. 数据就绪
  3. 从内核复制到用户空间（阻塞）
```

**特点**：最简单，但效率低

#### 非阻塞 IO（Non-blocking IO）

```
read():
  1. 数据没就绪 → 返回 EAGAIN（不阻塞）
  2. 应用程序轮询调用
  3. 数据就绪
  4. 从内核复制到用户空间（阻塞）
```

**特点**：需要轮询，CPU 浪费

#### IO 复用（IO Multiplexing）

```
select():
  1. 阻塞等待多个 fd 中任何一个就绪
  2. fd 就绪
  3. 调用 read() 读数据
```

**特点**：单线程处理多连接

#### 信号驱动 IO（Signal-driven IO）

```
1. 注册 SIGIO 信号处理函数
2. 立即返回（不阻塞）
3. 内核数据就绪 → 发 SIGIO 信号
4. 信号处理函数中 read()
```

**特点**：不常用（信号开销大）

#### 异步 IO（Async IO）

```
aio_read():
  1. 立即返回（不阻塞）
  2. 内核数据就绪
  3. 内核自动复制到用户空间
  4. 通知应用程序
```

**特点**：真正异步，但 Linux 支持较弱

### 1.3 五种模型对比

| 模型 | 阻塞阶段 | 复杂度 | 性能 | 应用 |
|------|----------|--------|------|------|
| 阻塞 | 全程 | 简单 | 差 | 简单程序 |
| 非阻塞 | 数据复制 | 中 | 中 | 轮询场景 |
| IO 复用 | select + 数据复制 | 中 | **好** | 高并发服务器 |
| 信号驱动 | 数据复制 | 高 | 中 | 不常用 |
| 异步 IO | **无阻塞** | **高** | **最好** | 理想方案 |

### 1.4 实际应用

- **Java NIO** = IO 复用（Selector + Channel）
- **Node.js** = 异步 IO（libuv）
- **Python asyncio** = IO 复用（select/epoll）
- **Netty** = IO 复用（epoll）
- **Nginx** = IO 复用（epoll）
- **Django Channels** = 异步 IO + WebSocket

## 2. 代码示例

### 2.1 阻塞 IO 示例

```python
# 文件：blocking_io.py
import socket

def blocking_server():
    """阻塞 IO 服务器 - 1 连接 1 线程。"""
    server = socket.socket()
    server.bind(('127.0.0.1', 9999))
    server.listen()
    while True:
        client, addr = server.accept()  # 阻塞
        data = client.recv(1024)        # 阻塞
        if data:
            client.send(b'OK')
            client.close()
```

### 2.2 select IO 复用

```python
# 文件：select_io.py
import select
import socket

def select_server():
    """select IO 复用服务器。"""
    server = socket.socket()
    server.bind(('127.0.0.1', 9999))
    server.listen()
    inputs = [server]

    while inputs:
        readable, _, _ = select.select(inputs, [], [], 1)  # 阻塞 1 秒
        for sock in readable:
            if sock is server:
                # 新连接
                client, addr = sock.accept()
                inputs.append(client)
            else:
                # 客户端数据
                data = sock.recv(1024)
                if data:
                    sock.send(b'OK')
                else:
                    inputs.remove(sock)
                    sock.close()
```

### 2.3 epoll IO 复用（Linux）

```python
# 文件：epoll_io.py
import select
import socket

def epoll_server():
    """epoll IO 复用服务器（Linux only）。"""
    server = socket.socket()
    server.bind(('127.0.0.1', 9999))
    server.listen()

    epoll = select.epoll()
    epoll.register(server.fileno(), select.EPOLLIN)

    connections = {}
    while True:
        events = epoll.poll(1)  # 阻塞 1 秒
        for fileno, event in events:
            if fileno == server.fileno():
                # 新连接
                client, addr = server.accept()
                connections[client.fileno()] = client
                epoll.register(client.fileno(), select.EPOLLIN)
            else:
                client = connections[fileno]
                data = client.recv(1024)
                if data:
                    client.send(b'OK')
                else:
                    epoll.unregister(fileno)
                    connections.pop(fileno, None)
                    client.close()
```

### 2.4 异步 IO（asyncio）

```python
# 文件：async_io.py
import asyncio

async def handle_client(reader, writer):
    """异步处理客户端。"""
    data = await reader.read(1024)
    if data:
        writer.write(b'OK')
        await writer.drain()
    writer.close()

async def async_server():
    """asyncio 异步服务器（底层用 epoll）。"""
    server = await asyncio.start_server(handle_client, '127.0.0.1', 9999)
    async with server:
        await server.serve_forever()

# 启动
# asyncio.run(async_server())
```

## 3. dify 仓库源码解读

### 3.1 dify 的 asyncio + epoll

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 130-170）：

```python
import asyncio
import aiohttp

class AsyncBatchFetcher:
    """异步批量抓取器。

    dify 用 asyncio + aiohttp 做高并发 HTTP 请求。
    底层 IO 模型：
    - Python asyncio 内部用 epoll（Linux）/ kqueue（macOS）
    - aiohttp 是异步 HTTP 客户端，基于 asyncio

    处理流程（以 100 个并发请求为例）：
    1. asyncio.create_task() 创建 100 个协程
    2. 事件循环用 epoll 监听 100 个 socket
    3. 当某个 socket 就绪（数据到达），唤醒对应协程
    4. 协程继续执行，处理响应

    与阻塞模型对比：
    - 阻塞：100 个连接 = 100 个线程（内存大，切换慢）
    - epoll：100 个连接 = 1 个线程（内存小，切换快）
    """

    async def fetch_all(self, urls: list[str]) -> list[str]:
        """并发抓取所有 URL。"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_one(session, url)
                for url in urls
            ]
            return await asyncio.gather(*tasks)

    async def _fetch_one(self, session, url):
        async with session.get(url) as resp:
            return await resp.text()


# dify 的实际使用：
async def fetch_dataset_documents(urls: list[str]) -> list[str]:
    """并发抓取文档 - 用 epoll 处理 100+ 连接。"""
    fetcher = AsyncBatchFetcher()
    return await fetcher.fetch_all(urls)


# asyncio 事件循环源码（简化）：
class EventLoop:
    """事件循环：基于 epoll。"""
    def __init__(self):
        # Linux: epoll, macOS: kqueue, Windows: select
        import selectors
        self._selector = selectors.DefaultSelector()

    def run_until_complete(self, coro):
        """运行协程直到完成。"""
        # 注册协程到事件循环
        # 循环：
        #   1. epoll_wait() 等待事件
        #   2. 事件就绪 → 唤醒对应协程
        #   3. 协程执行直到再次 await
        #   4. 重复
        pass
```

**解读**：
- 第 25 行：`asyncio.gather` 并发执行所有任务
- 第 38 行：底层用 `selectors.DefaultSelector`（Linux 默认 epoll）
- **设计意图**：用 asyncio + epoll 实现高并发，单线程处理 1000+ 连接

## 4. 关键要点总结

- **5 种 IO 模型**：阻塞、非阻塞、IO 复用、信号驱动、异步
- **IO 复用**最常用：select → poll → epoll（Linux）
- **epoll** 是 Linux 高性能服务器首选
- **asyncio** 底层用 epoll
- dify 用 asyncio + aiohttp 实现高并发 HTTP

## 5. 练习题

### 练习 1：基础（必做）

用 Python 实现一个 select-based echo 服务器，能同时处理多个客户端。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 asyncio 的事件循环如何用 epoll 实现。

### 练习 3：挑战（选做）

用 `epoll` 实现一个 HTTP 服务器（不依赖框架），处理 GET 请求返回 "Hello"。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《UNIX 网络编程》第 6 章 IO 复用
- Linux epoll：man 7 epoll

---

**文档版本**：v1.0
**最后更新**：2026-07-13