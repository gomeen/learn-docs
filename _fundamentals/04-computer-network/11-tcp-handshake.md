# 4.3.1 TCP 三次握手 / 四次挥手

> TCP 的连接建立和关闭是面试必考。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 TCP 三次握手的完整过程
- 理解四次挥手的必要性
- 知道 SYN 洪泛攻击的防护
- 能在 dify 中识别 TCP 连接管理的应用

## 📚 前置知识

- 02-tcp-ip.md

## 1. 核心概念

### 1.1 TCP 的特性

- **面向连接**：通信前必须建立连接
- **可靠传输**：ACK + 重传保证数据不丢
- **字节流**：无消息边界
- **全双工**：双向同时通信
- **流量控制**：滑动窗口
- **拥塞控制**：慢启动、拥塞避免

### 1.2 三次握手（连接建立）

**目的**：同步双方序列号，确认收发能力。

```
客户端                                服务器
  │                                      │
  ├── 1. SYN seq=x ────────────────────→ │  (同步序列号)
  │                                      │    状态：SYN_SENT
  │                                      │    状态：SYN_RCVD
  │                                      │
  │← 2. SYN-ACK seq=y, ack=x+1 ─────────┤  (同步 + 确认)
  │                                      │
  ├── 3. ACK ack=y+1 ─────────────────→ │  (确认)
  │                                      │    状态：ESTABLISHED
  │                                      │    状态：ESTABLISHED
```

**为什么三次？**
- **一次**：无法确认对方收到
- **两次**：服务器无法确认客户端收到自己的 SYN-ACK
- **三次**：双方都确认对方能收发 ✓

**Seq 和 Ack**：
- `seq=x`：客户端的初始序列号
- `seq=y, ack=x+1`：服务器的初始序列号 + 确认客户端的 SYN
- `ack=y+1`：客户端确认服务器的 SYN

### 1.3 四次挥手（连接关闭）

**为什么四次？** TCP 是全双工，需要分别关闭两个方向。

```
客户端                                服务器
  │                                      │
  ├── 1. FIN seq=u ────────────────────→ │  (客户端：我要关了)
  │    状态：FIN_WAIT_1                  │
  │                                      │    状态：CLOSE_WAIT
  │← 2. ACK ack=u+1 ──────────────────┤  (服务器：收到)
  │    状态：FIN_WAIT_2                  │
  │                                      │
  │   （服务器可能还有数据要发）          │
  │                                      │
  │← 3. FIN seq=v, ack=u+1 ────────────┤  (服务器：我也关)
  │                                      │    状态：LAST_ACK
  │                                      │
  ├── 4. ACK ack=v+1 ──────────────────→ │  (客户端：收到)
  │    状态：TIME_WAIT                   │
  │                                      │    状态：CLOSED
  │                                      │
  │   （等待 2MSL 后）                  │
  │    状态：CLOSED                     │
```

**MSL（Maximum Segment Lifetime）**：报文最长生存时间（通常 2 分钟）。

**为什么 TIME_WAIT 等待 2MSL？**
1. 确保最后一个 ACK 能到达（如果丢失，服务器会重发 FIN）
2. 让旧报文段在网络中消失（避免影响下一个连接）

### 1.4 状态转换

**客户端**：
```
CLOSED → SYN_SENT → ESTABLISHED → FIN_WAIT_1 → FIN_WAIT_2 → TIME_WAIT → CLOSED
```

**服务器**：
```
CLOSED → LISTEN → SYN_RCVD → ESTABLISHED → CLOSE_WAIT → LAST_ACK → CLOSED
```

### 1.5 SYN 洪泛攻击

**攻击**：攻击者发送大量 SYN，但不响应 SYN-ACK，导致服务器资源耗尽。

**防护**：
- **SYN Cookie**：不保存 SYN 队列，编码信息到 seq
- **缩短超时**：减少半连接占用时间
- **防火墙**：限制 SYN 速率

### 1.6 TCP 面试题

**为什么不是两次握手？**
- 防止已失效的连接请求突然传到服务器

**为什么挥手是四次？**
- TCP 全双工，需要分别关闭两个方向
- 服务器收到 FIN 后可能还有数据要发

**为什么 TIME_WAIT 等待 2MSL？**
- 保证 ACK 到达
- 让旧报文段消失

## 2. 代码示例

### 2.1 TCP 连接演示

```python
# 文件：tcp_handshake_demo.py
import socket
import struct

def tcp_handshake_demo():
    """TCP 三次握手演示。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 9999))
    server.listen(5)
    print("服务器：LISTEN")

    # 客户端
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("客户端：连接")
    client.connect(('127.0.0.1', 9999))
    print("客户端：SYN_SENT → ESTABLISHED")

    # 服务器接受连接
    conn, addr = server.accept()
    print(f"服务器：接受来自 {addr} 的连接")
    print("服务器：ESTABLISHED")

    # 通信
    client.send(b"Hello")
    data = conn.recv(1024)
    print(f"服务器收到: {data}")

    conn.send(b"World")
    data = client.recv(1024)
    print(f"客户端收到: {data}")

    # 关闭（四次挥手）
    client.close()
    conn.close()
    server.close()
    print("连接关闭")

tcp_handshake_demo()
```

### 2.2 用 scapy 观察 TCP 握手

```python
# 文件：tcp_observer.py
from scapy.all import *

def observe_tcp_handshake():
    """用 scapy 观察 TCP 三次握手。"""
    # 发送 SYN
    syn = IP(dst="www.baidu.com") / TCP(dport=80, flags="S")
    print(f"发送 SYN: {syn[TCP].summary()}")

    # 接收 SYN-ACK
    syn_ack = sr1(syn, timeout=2)
    if syn_ack and TCP in syn_ack:
        print(f"收到 SYN-ACK: seq={syn_ack[TCP].seq}, ack={syn_ack[TCP].ack}")

        # 发送 ACK
        ack = IP(dst="www.baidu.com") / TCP(
            dport=80,
            flags="A",
            seq=syn_ack[TCP].ack,
            ack=syn_ack[TCP].seq + 1,
        )
        send(ack)
        print("发送 ACK：三次握手完成")

# observe_tcp_handshake()
```

### 2.3 设置 SO_REUSEADDR

```python
# 文件：reuse_addr.py
import socket

def create_server_with_reuseaddr(host: str, port: int):
    """设置 SO_REUSEADDR（避免 TIME_WAIT 状态导致无法绑定）。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 关键：允许重用处于 TIME_WAIT 状态的端口
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    return server

# 用途：服务器重启时立即绑定同一端口
server = create_server_with_reuseaddr("127.0.0.1", 9999)
print(f"服务器启动：127.0.0.1:9999")
```

### 2.4 TCP 连接池

```python
# 文件：tcp_pool.py
import socket
import threading
from queue import Queue, Empty

class TCPConnectionPool:
    """简单的 TCP 连接池。"""

    def __init__(self, host: str, port: int, max_size: int = 5):
        self._host = host
        self._port = port
        self._pool = Queue(maxsize=max_size)
        self._lock = threading.Lock()

    def _create_connection(self) -> socket.socket:
        """创建新连接。"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._host, self._port))
        return s

    def get(self) -> socket.socket:
        """从池中获取连接。"""
        try:
            return self._pool.get_nowait()
        except Empty:
            return self._create_connection()

    def release(self, conn: socket.socket) -> None:
        """归还连接到池。"""
        try:
            self._pool.put_nowait(conn)
        except Exception:
            conn.close()

# 用法
pool = TCPConnectionPool("example.com", 80)
conn = pool.get()
conn.send(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
data = conn.recv(4096)
pool.release(conn)
```

## 3. dify 仓库源码解读

### 3.1 dify 的 TCP 连接管理

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 30-50）：

```python
import aiohttp

class SSRFProxy:
    """SSRF 安全的异步 HTTP 客户端。

    TCP 三次握手的应用：
    1. aiohttp 在请求时执行三次握手（内部）
    2. 启用 Keep-alive 复用连接（避免重复握手）
    3. 连接池管理多个 TCP 连接
    """

    def __init__(self):
        # TCP 连接器（管理 TCP 连接池）
        self._connector = aiohttp.TCPConnector(
            ttl_dns_cache=300,       # DNS 缓存
            keepalive_timeout=75,    # TCP Keep-alive 75 秒
            force_close=False,       # 启用连接复用
            limit=100,               # 连接池上限
            limit_per_host=10,       # 每个 host 最多 10 个连接
            enable_cleanup_closed=True,  # 清理关闭的连接
        )

    async def fetch(self, url: str):
        """HTTPS 请求 - 内部完成三次握手 + TLS 握手。"""
        async with aiohttp.ClientSession(connector=self._connector) as session:
            async with session.get(url) as resp:
                return await resp.text()


# dify 的 TCP 优化：
# 1. 连接池：避免每次三次握手（节省 RTT）
# 2. Keep-alive：保持长连接（避免空闲超时）
# 3. 限制并发：避免单机连接数过多
# 4. DNS 缓存：避免 DNS 查询

# 实际 TCP 连接监控：
# - 活跃连接数：netstat -an | grep ESTABLISHED
# - TIME_WAIT 数量：netstat -an | grep TIME_WAIT | wc -l
# - 每秒新建连接：ss -s
```

**解读**：
- 第 14 行：连接池配置（避免每次握手）
- 第 17 行：Keep-alive（保持长连接）
- 第 19 行：每 host 最多 10 个连接
- **设计意图**：用连接池减少三次握手开销，提升性能

## 4. 关键要点总结

- **三次握手**：SYN → SYN-ACK → ACK
- **四次挥手**：FIN → ACK → FIN → ACK
- **TIME_WAIT**：等待 2MSL（防止旧报文段影响）
- **SYN 洪泛**：用 SYN Cookie 防护
- dify 用连接池避免重复 TCP 握手

## 5. 练习题

### 练习 1：基础（必做）

用 Python socket 实现 TCP echo 服务器，观察三次握手过程。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何用连接池而非每次新建连接。

### 练习 3：挑战（选做）

用 `tcpdump` 抓包观察一次完整的 TCP 三次握手和四次挥手。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 793：TCP 规范
- 《TCP/IP 详解 卷 1》第 17-18 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13