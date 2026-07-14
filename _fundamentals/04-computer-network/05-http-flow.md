# 4.2.2 HTTP 完整流程（DNS → TCP → HTTP）

> 一个完整的 HTTP 请求背后经历了什么？

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握从 URL 输入到页面渲染的完整流程
- 理解每一步耗时的影响
- 能在 dify 中识别 HTTP 处理的各阶段

## 📚 前置知识

- 03-packet-flow.md
- 04-http-versions.md

## 1. 核心概念

### 1.1 完整时序

```
浏览器                     DNS                  服务器
  │                          │                     │
  ├── DNS 查询 ──────────────→                     │
  │←────── IP 地址 ──────────┤                     │
  │                                                │
  ├── TCP 三次握手 ──────────────────────────────→ │
  │←────────── 连接建立 ──────────────────────────┤ │
  │                                                │
  ├── HTTP 请求 ──────────────────────────────────→│
  │                                                │
  │←────────────── HTTP 响应 ────────────────────┤ │
  │                                                │
  ├── 浏览器解析、渲染                            │
```

### 1.2 详细流程

#### Step 1: DNS 解析

```
URL: https://www.example.com:443/path?query=1

浏览器解析 URL：
- 协议：https
- 主机：www.example.com
- 端口：443（默认）
- 路径：/path
- 查询：?query=1

DNS 解析（按序）：
1. 浏览器缓存（Chrome 缓存 60 秒）
2. 系统缓存（/etc/hosts）
3. 路由器缓存
4. ISP DNS（递归）
5. 根 DNS → .com DNS → example.com DNS
6. 返回 IP
```

#### Step 2: TCP 握手

```
客户端 → SYN seq=x → 服务器
客户端 ← SYN-ACK seq=y, ack=x+1 ← 服务器
客户端 → ACK ack=y+1 → 服务器
[连接建立]
```

#### Step 3: TLS 握手（HTTPS）

```
TLS 1.2（2 RTT）：
客户端 → ClientHello
服务器 → ServerHello + 证书
客户端 → Key Exchange + Change Cipher Spec + Finished
服务器 → Change Cipher Spec + Finished

TLS 1.3（1 RTT）：
客户端 → ClientHello + Key Share
服务器 → ServerHello + 证书 + Finished
[握手完成]
```

#### Step 4: HTTP 请求

```http
GET /path?query=1 HTTP/1.1
Host: www.example.com
User-Agent: Mozilla/5.0
Accept: text/html
Cookie: session=abc123
Connection: keep-alive
```

#### Step 5: HTTP 响应

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Content-Length: 1234
Set-Cookie: session=xyz789
Date: Mon, 13 Jul 2026 12:00:00 GMT

<!DOCTYPE html>
<html>...</html>
```

### 1.3 时延分析

**输入 URL 到页面渲染**：

| 阶段 | 时延 | 优化 |
|------|------|------|
| DNS 解析 | 0-100ms | DNS 缓存、预解析 |
| TCP 握手 | 1 RTT | 长连接 |
| TLS 握手 | 1-2 RTT | TLS 1.3、0-RTT |
| HTTP 请求/响应 | 几 ms | HTTP/2 |
| 资源加载 | 多个 RTT | 并发、HTTP/2 |
| 浏览器渲染 | 几十 ms | 优化 CSS/JS |

### 1.4 浏览器渲染流程

```
1. 解析 HTML → DOM 树
2. 解析 CSS → CSSOM 树
3. 合并 → 渲染树
4. 布局（Layout）
5. 绘制（Paint）
6. 合成（Composite）
```

### 1.5 优化策略

1. **DNS 预解析**：`<link rel="dns-prefetch" href="//example.com">`
2. **TCP 连接池**：浏览器限制（6 个/域名）
3. **HTTP/2**：多路复用
4. **资源压缩**：gzip、br
5. **缓存**：强缓存、协商缓存
6. **CDN**：就近访问

## 2. 代码示例

### 2.1 完整 HTTP 请求

```python
# 文件：http_full_flow.py
import socket
import ssl
import time

def full_http_request(host: str, path: str = "/"):
    """完整 HTTP 请求（应用层 + 传输层 + 网络层）。"""
    timings = {}

    # Step 1: DNS 解析
    start = time.perf_counter()
    ip = socket.gethostbyname(host)
    timings["dns"] = time.perf_counter() - start
    print(f"DNS: {host} → {ip} ({timings['dns']*1000:.1f}ms)")

    # Step 2: TCP 连接
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((ip, 80))
    timings["tcp"] = time.perf_counter() - start
    print(f"TCP 握手: {timings['tcp']*1000:.1f}ms")

    # Step 3: HTTP 请求
    start = time.perf_counter()
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    sock.send(request.encode())

    # Step 4: 接收响应
    response = b""
    while True:
        data = sock.recv(4096)
        if not data:
            break
        response += data
    timings["http"] = time.perf_counter() - start
    print(f"HTTP 请求/响应: {timings['http']*1000:.1f}ms")

    sock.close()

    # Step 5: 解析响应
    headers, _, body = response.partition(b"\r\n\r\n")
    print(f"\n响应头:\n{headers.decode()[:200]}")
    print(f"\n响应体（前 200 字符）:\n{body.decode()[:200]}")

    print(f"\n总耗时: {sum(timings.values())*1000:.1f}ms")
    return timings

# 运行
# full_http_request("example.com")
```

### 2.2 HTTPS 请求（含 TLS）

```python
# 文件：https_request.py
import socket
import ssl
import time

def https_request(host: str, path: str = "/"):
    """HTTPS 请求（应用层 + TLS + 传输层）。"""
    timings = {}

    # Step 1: DNS
    start = time.perf_counter()
    ip = socket.gethostbyname(host)
    timings["dns"] = time.perf_counter() - start

    # Step 2: TCP 握手
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, 443))
    timings["tcp"] = time.perf_counter() - start

    # Step 3: TLS 握手
    start = time.perf_counter()
    context = ssl.create_default_context()
    sock = context.wrap_socket(sock, server_hostname=host)
    timings["tls"] = time.perf_counter() - start
    print(f"TLS 版本: {sock.version()}")

    # Step 4: HTTP 请求
    start = time.perf_counter()
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    sock.send(request.encode())

    response = b""
    while True:
        data = sock.recv(4096)
        if not data:
            break
        response += data
    timings["http"] = time.perf_counter() - start

    sock.close()

    print(f"DNS: {timings['dns']*1000:.1f}ms")
    print(f"TCP: {timings['tcp']*1000:.1f}ms")
    print(f"TLS: {timings['tls']*1000:.1f}ms")
    print(f"HTTP: {timings['http']*1000:.1f}ms")
    print(f"总耗时: {sum(timings.values())*1000:.1f}ms")

# https_request("www.baidu.com")
```

### 2.3 用 curl 展示各阶段

```bash
# 用 curl 显示时延
$ curl -w '\nDNS: %{time_namelookup}\nTCP: %{time_connect}\nTLS: %{time_appconnect}\nHTTP: %{time_pretransfer}\nTotal: %{time_total}\n' \
       -o /dev/null -s https://www.baidu.com

# 输出：
# DNS: 0.005s
# TCP: 0.025s
# TLS: 0.080s
# HTTP: 0.082s
# Total: 0.150s
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTP 请求工具

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 160-200）：

```python
import aiohttp
import time
import logging

class MonitoredSSRFProxy:
    """带监控的 SSRF 代理。

    dify 的每个外部请求都会记录各阶段耗时：
    - DNS 解析
    - TCP 连接
    - TLS 握手
    - HTTP 请求/响应
    """

    async def fetch_with_metrics(self, url: str):
        metrics = {}

        # 创建 ClientSession（带连接池）
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(
                ttl_dns_cache=300,  # DNS 缓存
                keepalive_timeout=75,  # Keep-alive
            ),
        ) as session:

            # 发起请求（aiohttp 内部处理 DNS、TCP、TLS、HTTP）
            start = time.perf_counter()
            async with session.get(url) as resp:
                # 直到收到响应头的时间
                metrics["http_headers"] = time.perf_counter() - start

                # 读取响应体
                start = time.perf_counter()
                body = await resp.read()
                metrics["http_body"] = time.perf_counter() - start

                metrics["status"] = resp.status
                metrics["size"] = len(body)

        # 记录指标（用于监控）
        logging.info(f"HTTP fetch: {url}, metrics: {metrics}")
        return body


# dify 的 HTTP 请求监控：
# 1. Prometheus 指标：每次请求的耗时
# 2. 慢请求日志：超过阈值的请求
# 3. 错误率统计：超时、5xx 错误
# 4. 连接池监控：活跃连接数

# 性能瓶颈分析：
# - DNS 慢 → 检查 DNS 配置或启用缓存
# - TCP 慢 → 网络延迟（用 CDN）
# - TLS 慢 → 启用 TLS 1.3 / 0-RTT
# - HTTP 慢 → 检查服务器响应
```

**解读**：
- 第 30 行：DNS 缓存（避免重复解析）
- 第 33 行：Keep-alive（复用连接）
- 第 38-46 行：记录各阶段耗时
- **设计意图**：监控 HTTP 各阶段耗时，便于性能调优

## 4. 关键要点总结

- **完整流程**：DNS → TCP → TLS → HTTP → 渲染
- **DNS**：缓存优化
- **TCP**：持久连接（HTTP/1.1）
- **TLS**：1.3 / 0-RTT 加速
- **HTTP**：HTTP/2 多路复用
- dify 监控 HTTP 各阶段耗时

## 5. 练习题

### 练习 1：基础（必做）

用 `curl -w` 访问 `https://www.baidu.com`，记录 DNS、TCP、TLS、HTTP 各阶段耗时。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何使用连接池而非每次新建连接。

### 练习 3：挑战（选做）

用 Wireshark 抓包，分析一次 HTTPS 请求的完整过程（包括 TLS 握手）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《HTTP 权威指南》第 4 章 连接管理
- 《计算机网络：自顶向下方法》第 2 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13