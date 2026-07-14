# 4.1.2 TCP/IP 四层模型

> TCP/IP 是互联网的实际协议栈，是后端面试必考。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 TCP/IP 四层模型的协议
- 理解各层协议的职责和关系
- 能在 dify 中识别 TCP/IP 协议栈的应用

## 📚 前置知识

- 01-osi.md

## 1. 核心概念

### 1.1 TCP/IP 与 OSI 的对应

```
OSI 模型              TCP/IP 模型
┌──────────┐         ┌──────────────┐
│ 7. 应用层 │         │              │
├──────────┤         │  应用层       │  HTTP, DNS, TLS
│ 6. 表示层 │         │              │
├──────────┤         └──────────────┘
│ 5. 会话层 │         ┌──────────────┐
├──────────┤         │  传输层       │  TCP, UDP
│ 4. 传输层 │         └──────────────┘
├──────────┤         ┌──────────────┐
│ 3. 网络层 │         │  网络层（IP） │  IP, ICMP, ARP
├──────────┤         └──────────────┘
│ 2. 链路层 │         ┌──────────────┐
├──────────┤         │  网络接口层    │  Ethernet, WiFi
│ 1. 物理层 │         └──────────────┘
└──────────┘
```

### 1.2 应用层协议

| 协议 | 端口 | 说明 |
|------|------|------|
| HTTP | 80 | 超文本传输 |
| HTTPS | 443 | HTTP + TLS |
| DNS | 53 | 域名解析 |
| FTP | 21 | 文件传输 |
| SSH | 22 | 远程登录 |
| SMTP | 25 | 邮件发送 |
| POP3 | 110 | 邮件接收 |
| IMAP | 143 | 邮件接收 |
| Redis | 6379 | Redis 协议 |
| MySQL | 3306 | MySQL 协议 |

### 1.3 传输层协议

**TCP（Transmission Control Protocol）**：
- 面向连接
- 可靠传输（重传、排序、流量控制）
- 字节流
- 速度慢

**UDP（User Datagram Protocol）**：
- 无连接
- 不可靠（尽力而为）
- 数据报
- 速度快

### 1.4 网络层协议

| 协议 | 说明 |
|------|------|
| **IP** | 寻址和路由 |
| **ICMP** | 控制消息（如 ping） |
| **ARP** | IP → MAC 解析 |
| **RARP** | MAC → IP |
| **OSPF** | 路由协议 |
| **BGP** | 边界网关协议 |

### 1.5 IP 地址

**IPv4**：32 位，分 4 段（如 `192.168.1.1`）

**IPv6**：128 位，分 8 段（如 `2001:0db8:85a3:0000:0000:8a2e:0370:7334`）

### 1.6 数据封装

```
应用层数据（HTTP 请求）
   ↓
TCP 头 + 应用数据 = Segment
   ↓
IP 头 + Segment = Packet
   ↓
MAC 头 + Packet = Frame
   ↓
比特流（物理层）
```

### 1.7 端口号

**端口号**：标识主机上的进程（0-65535）

- **0-1023**：知名端口（HTTP、SSH、FTP）
- **1024-49151**：注册端口
- **49152-65535**：动态端口（客户端）

## 2. 代码示例

### 2.1 展示协议栈

```python
# 文件：protocol_stack.py
import socket

def show_protocol_stack():
    """展示 TCP/IP 协议栈。"""
    print("=== TCP/IP 协议栈 ===")
    print("应用层: HTTP, HTTPS, DNS, SSH, FTP")
    print("传输层: TCP, UDP")
    print("网络层: IPv4, IPv6, ICMP, ARP")
    print("网络接口: Ethernet, WiFi, PPP")

    # 查看本机网络信息
    hostname = socket.gethostname()
    print(f"\n本机主机名: {hostname}")

    # 通过 DNS 获取 IP（应用层）
    ip = socket.gethostbyname(hostname)
    print(f"本机 IP（IPv4）: {ip}")

    # 获取本机所有 IP
    addrs = socket.getaddrinfo(hostname, None)
    for addr in addrs[:3]:
        print(f"  {addr[0]} - {addr[4]}")

show_protocol_stack()
```

### 2.2 TCP Socket 示例

```python
# 文件：tcp_demo.py
import socket

def tcp_server():
    """TCP 服务器。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 9999))
    server.listen(5)
    print("TCP 服务器启动")

    while True:
        client, addr = server.accept()
        print(f"连接来自: {addr}")
        data = client.recv(1024)
        if data:
            client.send(b"OK")
        client.close()

def tcp_client():
    """TCP 客户端。"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 9999))
    client.send(b"Hello")
    data = client.recv(1024)
    print(f"收到: {data.decode()}")
    client.close()
```

### 2.3 UDP Socket 示例

```python
# 文件：udp_demo.py
import socket

def udp_server():
    """UDP 服务器。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('127.0.0.1', 9999))
    print("UDP 服务器启动")

    while True:
        data, addr = server.recvfrom(1024)
        print(f"收到来自 {addr}: {data.decode()}")
        server.sendto(b"OK", addr)

def udp_client():
    """UDP 客户端。"""
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto(b"Hello", ('127.0.0.1', 9999))
    data, addr = client.recvfrom(1024)
    print(f"收到: {data.decode()}")
    client.close()
```

## 3. dify 仓库源码解读

### 3.1 dify 的网络协议栈使用

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 20-60）：

```python
import aiohttp

class SSRFProxy:
    """SSRF 安全的异步 HTTP 客户端。

    dify 的网络通信涉及完整 TCP/IP 协议栈：

    应用层：
    - HTTP/HTTPS（调用外部 LLM API）
    - DNS（域名解析，自定义解析器）
    - TLS（HTTPS 加密）

    传输层：
    - TCP（HTTP 底层）
    - 默认禁用 UDP（HTTP 不需要）

    网络层：
    - IPv4 / IPv6 双协议栈
    - 自定义 DNS 解析（防止 SSRF）

    网络接口层：
    - 由操作系统管理
    """

    def __init__(self):
        # 自定义 DNS 解析器（SSRF 防护）
        # 关键：避免解析到内网 IP
        self._resolver = CustomSafeResolver()

        # TCP 连接器（启用连接池）
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            ttl_dns_cache=300,    # DNS 缓存 5 分钟
            keepalive_timeout=75,  # Keep-alive 75 秒
            force_close=False,    # 启用 keep-alive
            enable_cleanup_closed=True,
        )

    async def fetch(self, url: str):
        async with aiohttp.ClientSession(connector=self._connector) as session:
            async with session.get(url) as resp:
                return await resp.text()


# 性能优化：
# 1. 连接池：复用 TCP 连接（避免每次握手）
# 2. DNS 缓存：避免每次解析
# 3. Keep-alive：保持长连接
# 4. HTTP/2：多路复用（一个连接多个请求）
```

**解读**：
- 第 26 行：自定义 DNS 解析（SSRF 防护）
- 第 28-34 行：连接池配置（TCP 复用）
- **设计意图**：理解协议栈各层才能优化网络性能

## 4. 关键要点总结

- **TCP/IP 四层**：应用、传输、网络、网络接口
- **TCP**：可靠、面向连接、字节流
- **UDP**：不可靠、无连接、数据报
- **IP**：寻址和路由
- 端口号：0-65535，标识进程
- dify 用自定义 DNS + TCP 连接池

## 5. 练习题

### 练习 1：基础（必做）

用 TCP Socket 实现 echo 服务器和客户端，用 UDP Socket 实现简单消息传递。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何禁用 UDP 而只支持 TCP。

### 练习 3：挑战（选做）

用 `tcpdump` 或 `wireshark` 抓包，分析一次 HTTP 请求的完整 TCP/IP 协议栈。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《TCP/IP 详解 卷 1：协议》
- RFC 793（TCP）、RFC 768（UDP）、RFC 791（IP）

---

**文档版本**：v1.0
**最后更新**：2026-07-13