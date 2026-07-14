# 4.3.5 TCP vs UDP 对比

> TCP 和 UDP 的取舍是网络编程的核心问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 TCP vs UDP 的核心差异
- 理解各自的应用场景
- 能在 dify 中识别协议选择

## 📚 前置知识

- 11-tcp-handshake.md
- 14-udp.md

## 1. 核心概念

### 1.1 核心差异

| 维度 | TCP | UDP |
|------|-----|-----|
| 连接 | 面向连接（三次握手） | 无连接 |
| 可靠性 | 可靠（ACK + 重传） | 不可靠（尽力而为） |
| 顺序 | 保证 | 不保证 |
| 流量控制 | 滑动窗口 | 无 |
| 拥塞控制 | 有（慢启动等） | 无 |
| 头部 | 20+ 字节 | 8 字节 |
| 速度 | 较慢 | **快** |
| 资源占用 | 高 | 低 |
| 适用 | 准确性优先 | 实时性优先 |

### 1.2 选择标准

**用 TCP 的场景**：
- 数据准确性 > 实时性
- 需要顺序保证
- 大数据传输
- HTTP、SSH、FTP、邮件

**用 UDP 的场景**：
- 实时性 > 准确性
- 少量数据（< 64KB）
- 大量客户端（连接数多）
- DNS、视频、游戏、VoIP

### 1.3 详细对比

#### 速度

```
TCP：
- 三次握手（1 RTT）
- TLS 握手（1-2 RTT）
- 慢启动（最初慢）
- 拥塞控制

UDP：
- 无握手
- 直接发送
- 立即达到线速
```

#### 资源占用

```
TCP：
- 服务器维护连接状态（socket、窗口、缓冲区）
- 文件描述符：1 个/连接
- 内核 TCP 控制块

UDP：
- 服务器无连接状态
- 1 个 socket 可服务多客户端
- 内核几乎无状态
```

#### 可靠性

```
TCP：
- ACK + 重传（丢包自动重发）
- 顺序保证
- 校验和

UDP：
- 仅校验和（可选）
- 丢包不重传
- 顺序不保证
```

### 1.4 应用选择

| 应用 | 协议 | 原因 |
|------|------|------|
| HTTP/HTTPS | TCP | 准确性 |
| SSH | TCP | 准确性 |
| FTP | TCP | 准确性 |
| SMTP | TCP | 准确性 |
| DNS | UDP（主） | 快速查询 |
| DHCP | UDP | 简单 |
| NTP | UDP | 简单 |
| VoIP | UDP | 实时 |
| 视频流 | UDP | 实时 |
| 在线游戏 | UDP | 低延迟 |
| HTTP/3 (QUIC) | UDP | TCP 优化 |

### 1.5 QUIC：两全其美

**QUIC（Quick UDP Internet Connections）**：
- 基于 UDP
- 在 UDP 之上实现 TCP 的可靠性
- 1 RTT 握手（甚至 0-RTT）
- 多路复用（无队头阻塞）
- 现代浏览器和 HTTP/3 默认

**应用**：HTTP/3 全部基于 QUIC

## 2. 代码示例

### 2.1 TCP vs UDP 性能对比

```python
# 文件：tcp_vs_udp.py
import socket
import time

def tcp_throughput(host: str = "127.0.0.1", port: int = 9999):
    """TCP 吞吐测试。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    # 三次握手 + 数据传输
    start = time.perf_counter()
    for _ in range(1000):
        sock.send(b"x" * 1024)
    return time.perf_counter() - start

def udp_throughput(host: str = "127.0.0.1", port: int = 9999):
    """UDP 吞吐测试。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 直接发送，无握手
    start = time.perf_counter()
    for _ in range(1000):
        sock.sendto(b"x" * 1024, (host, port))
    return time.perf_counter() - start
```

### 2.2 简单的 TCP echo 服务器

```python
# 文件：tcp_echo.py
import socket
import threading

def tcp_echo_server(host: str = "127.0.0.1", port: int = 9999):
    """TCP echo 服务器。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()

    def handle_client(conn, addr):
        print(f"新连接: {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data)
        conn.close()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
```

### 2.3 UDP echo 服务器

```python
# 文件：udp_echo.py
import socket

def udp_echo_server(host: str = "127.0.0.1", port: int = 9999):
    """UDP echo 服务器（单线程）。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"UDP 服务器: {host}:{port}")

    while True:
        data, addr = server.recvfrom(1024)
        if not data:
            continue
        print(f"收到来自 {addr}: {data}")
        server.sendto(data, addr)
```

## 3. dify 仓库源码解读

### 3.1 dify 的协议选择

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 90-120）：

```python
import socket
import aiohttp

class ProtocolSelector:
    """dify 的协议选择。

    dify 的协议选择策略：
    - HTTP/HTTPS API → TCP（准确性）
    - DNS 查询 → UDP（快速）
    - 数据库（PostgreSQL）→ TCP（准确性）
    - 缓存（Redis）→ TCP（准确性）
    - 向量数据库（Milvus gRPC）→ TCP（基于 HTTP/2）

    为什么不直接用 UDP？
    - dify 的核心是 LLM API 调用
    - LLM 响应需要准确性（不能丢字）
    - TCP 的可靠性保证是必需的

    未来可能的优化：
    - HTTP/3 (QUIC)：UDP 之上的可靠协议
    - 但目前 dify 不依赖 HTTP/3
    """

    async def fetch_external_api(self, url: str):
        """调用外部 API（HTTP） - 用 TCP。"""
        async with aiohttp.ClientSession() as session:
            # 内部用 TCP（aiohttp 默认）
            async with session.get(url) as resp:
                return await resp.text()

    async def dns_lookup(self, host: str):
        """DNS 查询 - 用 UDP（系统调用）。"""
        # asyncio 的 getaddrinfo 内部用 UDP
        loop = asyncio.get_event_loop()
        info = await loop.getaddrinfo(host, None)
        return info[0][4][0]


# 协议选择的考量：
# 1. 准确性 vs 实时性
# 2. 网络环境（公网 vs 内网）
# 3. 数据大小
# 4. 客户端数量
# 5. 防火墙兼容性（UDP 可能被屏蔽）
```

**解读**：
- 第 17 行：HTTP API 用 TCP
- 第 26 行：DNS 查询用 UDP
- **设计意图**：根据场景选择合适协议

## 4. 关键要点总结

- **TCP**：可靠、准确、慢（HTTP、文件传输）
- **UDP**：不可靠、快、实时（DNS、视频、游戏）
- **选择标准**：准确性 vs 实时性
- **QUIC**：UDP 之上的可靠协议（HTTP/3）
- dify 主要用 TCP（HTTP、数据库），UDP 仅用于 DNS

## 5. 练习题

### 练习 1：基础（必做）

对比 TCP 和 UDP 在 1000 次小包（1KB）传输中的耗时。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何所有 HTTP API 都用 TCP。

### 练习 3：挑战（选做）

调研 HTTP/3（QUIC）的优势，说明为什么未来可能用 UDP 替代 TCP。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 793（TCP）、RFC 768（UDP）
- QUIC RFC 9000

---

**文档版本**：v1.0
**最后更新**：2026-07-13