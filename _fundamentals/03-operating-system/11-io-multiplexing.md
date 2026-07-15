# 3.3.2 select / poll / epoll 详解

> select → poll → epoll 是 IO 多路复用的演进，理解它们才能理解高并发。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 select、poll、epoll 的原理和差异
- 理解 epoll 为什么是 Linux 下的最优选择
- 能在 dify 中识别 epoll 的应用（asyncio）

## 📚 前置知识

- 10-io-models.md

## 1. 核心概念

### 1.1 IO 多路复用的核心

**单线程监控多个文件描述符（fd）**，任何一个就绪就通知。

### 1.2 select

**原理**：用**位图**记录所有 fd，调用时把位图从用户空间拷贝到内核空间，内核轮询检查。

```c
fd_set readfds;
FD_ZERO(&readfds);
FD_SET(fd1, &readfds);
FD_SET(fd2, &readfds);
select(max_fd + 1, &readfds, NULL, NULL, NULL);
```

**限制**：
- 单进程最多 1024 个 fd（FD_SETSIZE）
- 每次调用都要**拷贝 fd 集合**到内核
- 内核**轮询**所有 fd（O(n)）

### 1.3 poll

**改进**：用**链表**代替位图，突破 1024 限制。

```c
struct pollfd {
    int fd;
    short events;
    short revents;
};
poll(fds, nfds, timeout);
```

**改进点**：
- 无 1024 限制
- 仍需**轮询**所有 fd（O(n)）

### 1.4 epoll（Linux 2.6+）

**核心改进**：用**红黑树**（数据结构见 [红黑树](../01-data-structures/09-red-black-tree.md)） + **就绪链表**

```
epoll_create() → 创建 epoll 实例
epoll_ctl()    → 注册/修改/删除 fd
epoll_wait()   → 等待事件就绪（只返回就绪的 fd）
```

**三个关键函数**：

```c
int epfd = epoll_create(1024);

struct epoll_event ev;
ev.events = EPOLLIN;  // 监听读事件
ev.data.fd = fd;
epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev);

// 等待事件
struct epoll_event events[100];
int n = epoll_wait(epfd, events, 100, -1);
for (int i = 0; i < n; i++) {
    // events[i] 是就绪的 fd
}
```

**优势**：
- **无 fd 数限制**
- **回调机制**：fd 就绪时加入就绪链表（**O(1)**）
- 不需要每次都拷贝 fd 集合

### 1.5 三者对比

| 特性 | select | poll | epoll |
|------|--------|------|-------|
| fd 数限制 | 1024 | 无 | 无 |
| 时间复杂度 | O(n) | O(n) | **O(1)** |
| 数据结构 | 位图 | 链表 | 红黑树 + 链表 |
| 触发方式 | LT | LT | **LT / ET** |
| 内核版本 | 通用 | 通用 | Linux 2.6+ |

### 1.6 LT vs ET 触发模式

**LT（Level-Triggered，电平触发）**：
- fd 就绪时通知，可以多次通知
- 类似 select/poll 行为

**ET（Edge-Triggered，边沿触发）**：
- fd 就绪**只通知一次**
- 必须**一次性读完**数据
- 性能更好，但编程复杂

```
ET 模式必须非阻塞 + 一次性读完所有数据
```

### 1.7 epoll 的实现原理

```
epoll_create():
  创建 eventpoll 结构（红黑树 + 就绪链表）

epoll_ctl(ADD):
  注册 fd 时，调用 fd 的 poll 回调
  回调把 fd 加入就绪链表（如果就绪）

epoll_wait():
  直接从就绪链表取 fd（不需要轮询）
  没就绪 → 睡眠
```

**关键**：每个 fd 注册时**只注册一次**，避免重复初始化。

## 2. 代码示例

### 2.1 select 示例

```python
# 文件：select_server.py
import select
import socket

def select_echo_server():
    """select 实现 echo 服务器。"""
    server = socket.socket()
    server.setblocking(False)
    server.bind(('127.0.0.1', 9999))
    server.listen()

    inputs = [server]
    outputs = []

    while inputs:
        readable, writable, exceptional = select.select(
            inputs, outputs, inputs, 1.0
        )

        for sock in readable:
            if sock is server:
                client, addr = sock.accept()
                inputs.append(client)
            else:
                data = sock.recv(1024)
                if data:
                    if sock not in outputs:
                        outputs.append(sock)
                else:
                    inputs.remove(sock)
                    sock.close()

        for sock in writable:
            try:
                next_msg = sock.send(b"OK\n")
                outputs.remove(sock)
            except Exception:
                inputs.remove(sock)
                outputs.remove(sock)
                sock.close()
```

### 2.2 epoll 示例

```python
# 文件：epoll_server.py
import select
import socket

def epoll_echo_server():
    """epoll 实现 echo 服务器（Linux）。"""
    server = socket.socket()
    server.setblocking(False)
    server.bind(('127.0.0.1', 9999))
    server.listen()

    epoll = select.epoll()
    epoll.register(server.fileno(), select.EPOLLIN)

    connections = {}

    try:
        while True:
            events = epoll.poll(1)
            for fileno, event in events:
                if fileno == server.fileno():
                    # 新连接
                    client, addr = server.accept()
                    client.setblocking(False)
                    connections[client.fileno()] = client
                    epoll.register(client.fileno(), select.EPOLLIN)
                elif event & select.EPOLLIN:
                    # 可读
                    client = connections[fileno]
                    data = client.recv(1024)
                    if data:
                        client.send(b"OK\n")
                    else:
                        epoll.unregister(fileno)
                        connections.pop(fileno, None)
                        client.close()
    finally:
        epoll.unregister(server.fileno())
        epoll.close()
        server.close()
```

### 2.3 性能对比

```python
# 文件：benchmark.py
import time
import socket
import threading

def benchmark(name, server_func, num_clients=100, requests_per_client=100):
    """简单的 select vs epoll 性能对比。"""
    # 启动服务器
    server_thread = threading.Thread(target=server_func, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # 模拟客户端
    start = time.perf_counter()

    def client():
        for _ in range(requests_per_client):
            try:
                s = socket.socket()
                s.connect(('127.0.0.1', 9999))
                s.send(b'hi')
                s.recv(1024)
                s.close()
            except Exception:
                pass

    threads = [threading.Thread(target=client) for _ in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    elapsed = time.perf_counter() - start
    print(f"{name}: {elapsed:.3f}s")
```

## 3. dify 仓库源码解读

### 3.1 dify 的 asyncio 底层（epoll）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 40-70）：

```python
import asyncio
import selectors
import socket

# Python asyncio 的事件循环在不同平台：
# - Linux: epoll
# - macOS: kqueue
# - Windows: IOCP（I/O Completion Port）

# dify 的高并发依赖 epoll：
# - 单线程处理数千个 HTTP 请求
# - 每个请求是一个协程
# - 当 socket 数据就绪时，epoll 通知

class SSRFProxy:
    """SSRF 安全的异步 HTTP 代理。

    底层：asyncio → selectors → epoll (Linux)
    """

    def __init__(self):
        # 自动选择最优的 selector（Linux 下是 epoll）
        self._selector: selectors.BaseSelector = selectors.DefaultSelector()
        self._loop = asyncio.new_event_loop()

    async def get(self, url: str, **kwargs) -> str:
        """异步 HTTP 请求。"""
        # 创建一个 socket 连接
        reader, writer = await asyncio.open_connection(url.split('/')[2], 80)
        # 写入请求
        writer.write(f"GET {url} HTTP/1.1\r\nHost: ...\r\n\r\n".encode())
        # 等待响应（事件循环在这里切换到其他协程）
        data = await reader.read(4096)
        writer.close()
        return data

    def _epoll_insight(self) -> dict:
        """epoll 的内部信息（调试用）。"""
        # Linux epoll 用红黑树 + 就绪链表
        # - 红黑树：管理所有注册的 fd（O(log n)）
        # - 就绪链表：就绪的 fd（O(1) 取出）
        return {
            "platform": "linux",
            "backend": "epoll",
            "max_fd": 2**32,  # epoll 无 1024 限制
            "trigger_modes": ["LT", "ET"],
        }
```

**解读**：
- 第 14 行：`selectors.DefaultSelector()` 自动选最优（Linux 选 epoll）
- 第 38 行：`max_fd = 2^32`：epoll 无 1024 限制
- **设计意图**：用 epoll 实现 C10K（单进程处理 1 万连接）

## 4. 关键要点总结

- **select**：1024 限制，O(n) 轮询
- **poll**：无限制，仍 O(n) 轮询
- **epoll**：无限制，**O(1) 回调**，LT/ET 模式
- ET 模式性能好但编程复杂
- Linux 高性能服务器首选 epoll
- dify 的 asyncio 在 Linux 下用 epoll

## 5. 练习题

### 练习 1：基础（必做）

用 select 实现一个简单的回显服务器，演示多客户端并发处理。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 Python 的 `DefaultSelector` 在 Linux 下选 epoll 的原因。

### 练习 3：挑战（选做）

用 epoll 的 ET 模式实现高性能服务器（非阻塞 + 一次性读完数据）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《UNIX 网络编程》第 6 章 IO 复用
- Linux epoll 文档：man 7 epoll

---

**文档版本**：v1.0
**最后更新**：2026-07-13