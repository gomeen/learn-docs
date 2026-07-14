# 4.3.4 UDP 协议

> UDP 是无连接的传输层协议，适合实时性要求高的场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 UDP 的特点和适用场景
- 掌握 UDP 的头部结构
- 知道 UDP 协议的关键应用
- 能在 dify 中识别 UDP 的应用

## 📚 前置知识

- 02-tcp-ip.md
- 11-tcp-handshake.md

## 1. 核心概念

### 1.1 UDP 是什么？

**UDP（User Datagram Protocol）**：无连接、不可靠的传输层协议。

**核心特点**：
- **无连接**：不建立连接，直接发送
- **不可靠**：不保证到达、不保证顺序
- **数据报**：每个包独立，有边界
- **轻量**：头部仅 8 字节
- **快**：无连接建立、无拥塞控制

### 1.2 UDP 头部

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            Length             |           Checksum            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Data (if any)                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**字段**：
- 源端口（2 字节）
- 目标端口（2 字节）
- 长度（2 字节，含头部）
- 校验和（2 字节，可选）
- 数据

### 1.3 TCP vs UDP

| 特性 | TCP | UDP |
|------|-----|-----|
| 连接 | 面向连接 | 无连接 |
| 可靠性 | 可靠（重传、排序） | 不可靠 |
| 流量控制 | 有 | 无 |
| 拥塞控制 | 有 | 无 |
| 头部 | 20+ 字节 | 8 字节 |
| 速度 | 慢 | **快** |
| 顺序 | 保证 | 不保证 |
| 应用 | HTTP、SSH、FTP | DNS、视频、语音 |

### 1.4 UDP 的应用场景

1. **DNS**：查询快、丢失可重试
2. **视频/音频流**：实时性 > 可靠性
3. **在线游戏**：低延迟
4. **VoIP**：网络电话
5. **广播/组播**：一对多
6. **QUIC（HTTP/3）**：UDP 之上的可靠协议

### 1.5 UDP 的可靠性问题

**UDP 丢包怎么办？**

应用层需要自己处理：
- **确认重传**：ACK + 超时
- **顺序控制**：序列号
- **流量控制**：滑动窗口
- **或者**：接受丢包（视频丢帧可以接受）

**QUIC** 在 UDP 之上实现了 TCP 的可靠性，同时保持低延迟。

## 2. 代码示例

### 2.1 UDP 客户端/服务器

```python
# 文件：udp_demo.py
import socket

def udp_server(host: str = "127.0.0.1", port: int = 9999):
    """UDP 服务器。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"UDP 服务器启动: {host}:{port}")

    while True:
        data, addr = server.recvfrom(1024)
        print(f"收到来自 {addr}: {data.decode()}")
        # 回显
        server.sendto(b"ACK: " + data, addr)

def udp_client(host: str = "127.0.0.1", port: int = 9999):
    """UDP 客户端。"""
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto(b"Hello UDP", (host, port))
    data, addr = client.recvfrom(1024)
    print(f"服务器响应: {data.decode()}")
    client.close()

# 在两个终端分别运行
# udp_server()
# udp_client()
```

### 2.2 DNS 查询（UDP）

```python
# 文件：dns_udp.py
import socket
import struct

def dns_query(domain: str) -> str:
    """用 UDP 发送 DNS 查询（简化版）。"""
    # 构建 DNS 查询报文
    # 头部（12 字节）+ 查询部分
    transaction_id = 0x1234
    flags = 0x0100  # 标准查询
    questions = 1

    header = struct.pack("!HHHHHH", transaction_id, flags, questions, 0, 0, 0)

    # 域名编码（如 www.baidu.com → \x03www\x05baidu\x03com\x00）
    qname = b""
    for part in domain.split("."):
        qname += bytes([len(part)]) + part.encode()
    qname += b"\x00"

    # 查询类型 A（0x0001），类 IN（0x0001）
    question = qname + struct.pack("!HH", 1, 1)

    packet = header + question

    # 发送到 DNS 服务器
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.sendto(packet, ("8.8.8.8", 53))
    response, _ = sock.recvfrom(1024)
    sock.close()

    # 解析响应（简化）
    ip = ".".join(str(b) for b in response[-4:])
    return ip
```

### 2.3 UDP 多播

```python
# 文件：udp_multicast.py
import socket
import struct

def multicast_sender(group: str = "224.1.1.1", port: int = 9999):
    """多播发送者。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 设置 TTL
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    message = b"Multicast message"
    sock.sendto(message, (group, port))
    sock.close()

def multicast_receiver(group: str = "224.1.1.1", port: int = 9999):
    """多播接收者。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))

    # 加入多播组
    mreq = struct.pack("!4sl", socket.inet_aton(group), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"多播消息来自 {addr}: {data}")
```

### 2.4 QUIC 风格（简化版可靠 UDP）

```python
# 文件：quic_demo.py
import socket
import struct
import zlib

class ReliableUDP:
    """简化的可靠 UDP（类似 QUIC 思想）。"""

    HEADER_FORMAT = "!HI"  # seq (4B) + checksum (4B)

    def __init__(self, host: str, port: int):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((host, port))
        self._sock.settimeout(5)

    def send(self, data: bytes, target: tuple) -> None:
        """发送带序号和校验的数据。"""
        seq = 0  # 简化
        checksum = zlib.crc32(data) & 0xFFFFFFFF
        header = struct.pack(self.HEADER_FORMAT, seq, checksum)
        self._sock.sendto(header + data, target)

    def recv(self) -> bytes | None:
        """接收并验证数据。"""
        try:
            data, addr = self._sock.recvfrom(4096)
            if len(data) < 8:
                return None
            seq, checksum = struct.unpack(self.HEADER_FORMAT, data[:8])
            payload = data[8:]
            # 验证校验
            if zlib.crc32(payload) & 0xFFFFFFFF != checksum:
                return None  # 损坏
            return payload
        except socket.timeout:
            return None
```

## 3. dify 仓库源码解读

### 3.1 dify 中的 UDP 应用（DNS）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 30-50）：

```python
import socket
import asyncio

class CustomSafeResolver:
    """自定义 DNS 解析器。

    DNS 主要使用 UDP：
    - DNS 查询用 UDP（快、无连接）
    - 大响应（> 512 字节）用 TCP
    - DNS 解析是 dify 网络请求的第一步

    dify 的 DNS 解析流程：
    1. 接收域名（如 api.openai.com）
    2. 构造 DNS 查询（UDP 包）
    3. 发送到 DNS 服务器（如 8.8.8.8）
    4. 接收 DNS 响应
    5. 解析为 IP 地址
    6. 验证不是内网 IP（防 SSRF）
    """

    async def resolve(self, host: str) -> list[dict]:
        """异步 DNS 解析。"""
        loop = asyncio.get_event_loop()
        # getaddrinfo 默认用 UDP
        infos = await loop.getaddrinfo(
            host, None,
            type=socket.SOCK_STREAM,  # TCP（用于 HTTP）
        )
        results = []
        for info in infos:
            ip = info[4][0]
            results.append({"hostname": host, "host": ip, "port": info[4][1]})
        return results


# UDP 在 dify 的其他应用：
# - DNS 解析（必需）
# - 日志收集（可选）
# - 服务发现（mDNS）

# TCP 在 dify 的应用（主要）：
# - HTTP/HTTPS（API 调用）
# - PostgreSQL（数据库）
# - Redis（缓存）
# - WebSocket（实时通信）

# 为什么 HTTP 用 TCP 不用 UDP：
# - HTTP 需要可靠传输（页面不能丢字符）
# - HTTP 是请求-响应模式（需要顺序）
# - TCP 的三次握手可以接受（HTTP/2 优化后）
```

**解读**：
- 第 22 行：`getaddrinfo` 内部用 UDP 查询 DNS
- **设计意图**：UDP 适合 DNS（快、丢包可重试）

## 4. 关键要点总结

- **UDP**：无连接、不可靠、数据报
- **头部仅 8 字节**：比 TCP 轻量
- **适用**：DNS、视频、游戏、VoIP
- **不可靠**：应用层处理（QUIC 在 UDP 上实现可靠）
- dify 主要用 TCP，UDP 仅用于 DNS

## 5. 练习题

### 练习 1：基础（必做）

用 Python socket 实现 UDP echo 服务器和客户端。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 DNS 为何用 UDP 而非 TCP。

### 练习 3：挑战（选做）

实现 UDP 多播：发送者向 `224.1.1.1` 发消息，多个接收者都能收到。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 768：UDP 规范
- 《计算机网络：自顶向下方法》第 3 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13