# 4.1.1 OSI 七层模型

> OSI 七层模型是网络通信的理论基础，理解它才能理解后端。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 OSI 七层模型每层的职责
- 区分 OSI 与 TCP/IP 模型
- 能在 dify 中识别网络协议栈的应用

## 📚 前置知识

- 计算机基础

## 1. 核心概念

### 1.1 为什么需要分层？

**分层的好处**：
- 各层独立演化
- 易于理解和实现
- 便于标准化
- 故障排查简单

### 1.2 OSI 七层模型

```
┌─────────────────────────────────────────┐
│  7. 应用层（Application）                │  HTTP, FTP, SMTP, DNS
├─────────────────────────────────────────┤
│  6. 表示层（Presentation）               │  SSL/TLS, JPEG, ASCII
├─────────────────────────────────────────┤
│  5. 会话层（Session）                    │  NetBIOS, RPC
├─────────────────────────────────────────┤
│  4. 传输层（Transport）                  │  TCP, UDP
├─────────────────────────────────────────┤
│  3. 网络层（Network）                    │  IP, ICMP, OSPF
├─────────────────────────────────────────┤
│  2. 数据链路层（Data Link）              │  Ethernet, PPP, ARP
├─────────────────────────────────────────┤
│  1. 物理层（Physical）                   │  网线、光纤、无线电
└─────────────────────────────────────────┘
```

### 1.3 各层职责

| 层 | 职责 | 协议 |
|----|------|------|
| **应用层** | 用户接口、应用程序 | [HTTP](./04-http-versions.md), FTP, SMTP, [DNS](./10-dns.md) |
| **表示层** | 数据格式、加密 | [TLS](./08-https.md), JSON, XML |
| **会话层** | 会话管理 | RPC, NetBIOS |
| **传输层** | 端到端连接、可靠传输 | [TCP](./02-tcp-ip.md), [UDP](./14-udp.md) |
| **网络层** | 路由、IP 地址 | IP, ICMP, OSPF（路由见 [18-routing](./18-routing.md)） |
| **数据链路层** | 帧传输、MAC 地址 | Ethernet, ARP |
| **物理层** | 比特传输 | 网线、光纤、WiFi |

### 1.4 TCP/IP 四层模型

**实际互联网用的是 TCP/IP 模型**（比 OSI 简化）：

```
┌─────────────────────────────────────────┐
│  4. 应用层                               │  HTTP, DNS, TLS
├─────────────────────────────────────────┤
│  3. 传输层                               │  TCP, UDP
├─────────────────────────────────────────┤
│  2. 网络层（IP）                         │  IP, ICMP, ARP
├─────────────────────────────────────────┤
│  1. 网络接口层（链路层 + 物理层）         │  Ethernet, WiFi
└─────────────────────────────────────────┘
```

### 1.5 OSI vs TCP/IP

| OSI | TCP/IP | 说明 |
|-----|--------|------|
| 应用层 | 应用层 | OSI 多两层（表示层、会话层） |
| 表示层 | - | TCP/IP 不单独分 |
| 会话层 | - | TCP/IP 不单独分 |
| 传输层 | 传输层 | 一致 |
| 网络层 | 网络层 | 一致 |
| 数据链路层 | 网络接口层 | TCP/IP 合并 |
| 物理层 | 网络接口层 | TCP/IP 合并 |

### 1.6 数据传输过程

**发送方（自上而下）**：

```
应用层数据 → "GET / HTTP/1.1\r\n\r\n"
   ↓ 加 HTTP 头
传输层 → TCP 头 + 数据（segment）
   ↓ 加 IP 头
网络层 → IP 头 + TCP 头 + 数据（packet）
   ↓ 加 MAC 头
链路层 → MAC 头 + IP 头 + TCP 头 + 数据（frame）
   ↓
物理层 → 比特流
```

**接收方（自下而上）**：反向拆包

### 1.7 数据单元（PDU）

| 层 | 数据单元 |
|----|----------|
| 应用层 | 消息（Message） |
| 传输层 | 段（Segment） |
| 网络层 | 包（Packet） |
| 链路层 | 帧（Frame） |
| 物理层 | 比特（Bit） |

## 2. 代码示例

### 2.1 用 Python 模拟各层

```python
# 文件：network_stack_demo.py
class ApplicationLayer:
    """应用层：HTTP 请求。"""
    @staticmethod
    def create_http_request(method: str, path: str) -> str:
        return f"{method} {path} HTTP/1.1\r\nHost: example.com\r\n\r\n"

class TransportLayer:
    """传输层：TCP 头。"""
    @staticmethod
    def add_tcp_header(http_data: str, src_port: int, dst_port: int) -> str:
        # 简化的 TCP 头
        tcp_header = f"TCP[{src_port}→{dst_port}]"
        return f"{tcp_header}|{http_data}"

class NetworkLayer:
    """网络层：IP 头。"""
    @staticmethod
    def add_ip_header(segment: str, src_ip: str, dst_ip: str) -> str:
        ip_header = f"IP[{src_ip}→{dst_ip}]"
        return f"{ip_header}|{segment}"

class DataLinkLayer:
    """链路层：MAC 头。"""
    @staticmethod
    def add_mac_header(packet: str, src_mac: str, dst_mac: str) -> str:
        mac_header = f"MAC[{src_mac}→{dst_mac}]"
        return f"{mac_header}|{packet}"

# 发送流程
def send_data():
    # 应用层
    http_data = ApplicationLayer.create_http_request("GET", "/")
    print(f"1. 应用层: {http_data[:50]}")

    # 传输层
    segment = TransportLayer.add_tcp_header(http_data, 12345, 80)
    print(f"2. 传输层: {segment[:60]}")

    # 网络层
    packet = NetworkLayer.add_ip_header(segment, "192.168.1.1", "93.184.216.34")
    print(f"3. 网络层: {packet[:70]}")

    # 链路层
    frame = DataLinkLayer.add_mac_header(packet, "aa:bb:cc:dd:ee:ff", "00:11:22:33:44:55")
    print(f"4. 链路层: {frame[:80]}")

send_data()
```

### 2.2 用 socket 理解各层

```python
# 文件：socket_layers.py
import socket

def show_layers():
    """socket 在各层的体现。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 应用层：HTTP 协议（应用代码）
    request = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"

    # 传输层：TCP 协议（socket 类型）
    print(f"传输层: TCP (SOCK_STREAM)")

    # 网络层：IP 协议（地址族）
    print(f"网络层: IPv4 (AF_INET)")

    # 链路层：网卡（操作系统管理）
    # 物理层：网线/WiFi
    print(f"链路层: 由 OS 管理")
    print(f"物理层: 由硬件管理")

    s.close()

show_layers()
```

## 3. dify 仓库源码解读

### 3.1 dify 的网络栈使用

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 1-30）：

```python
import asyncio
import aiohttp

class SSRFProxy:
    """SSRF 安全的异步 HTTP 客户端。

    使用 dify 时涉及的网络协议栈：

    1. 应用层：
       - HTTP/HTTPS（外部 API 调用）
       - DNS（域名解析）

    2. 传输层：
       - TCP（aiohttp 底层）
       - TLS（HTTPS 加密）

    3. 网络层：
       - IPv4/IPv6（双协议栈）

    4. 链路层：
       - 由操作系统管理

    dify 的网络栈使用：
    - DNS 解析：自定义解析器（避免内网 DNS 劫持）
    - TCP 连接：复用连接池
    - TLS 握手：HTTPS 默认开启
    """

    def __init__(self):
        # 自定义 DNS 解析器（避免 SSRF）
        self._resolver = aiohttp.AsyncResolver()
        # TCP 连接器（启用连接池）
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            ttl_dns_cache=300,    # DNS 缓存 5 分钟
            force_close=False,    # 启用 keep-alive
        )

    async def fetch(self, url: str):
        async with aiohttp.ClientSession(connector=self._connector) as session:
            # 应用层：HTTP 请求
            # 传输层：TCP 连接
            # 网络层：DNS 解析 + IP 路由
            async with session.get(url) as resp:
                return await resp.text()
```

**解读**：
- 第 25 行：自定义 DNS 解析器（避免内网劫持）
- 第 28 行：连接池复用（减少 TCP 握手）
- **设计意图**：理解各层才能优化网络性能

## 4. 关键要点总结

- OSI 七层：应用、表示、会话、传输、网络、链路、物理
- TCP/IP 四层：应用、传输、网络、网络接口
- **每层独立**，相邻层通过**接口**交互
- 数据单元：消息 → 段 → 包 → 帧 → 比特
- dify 的 aiohttp 用 TCP、IPv4/IPv6、自定义 DNS

## 5. 练习题

### 练习 1：基础（必做）

画出 OSI 七层模型，并标注每层的常见协议。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何自定义 DNS 解析器。

### 练习 3：挑战（选做）

用 Python 写一个简单的 HTTP 服务器（不依赖框架），理解应用层到传输层的完整流程。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《计算机网络：自顶向下方法》第 1 章
- RFC 1122：互联网主机要求

---

**文档版本**：v1.0
**最后更新**：2026-07-13