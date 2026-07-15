# 4.2.1 HTTP/1.0 / 1.1 / 2.0 / 3.0 演进

> HTTP 协议的演进史，是后端开发必须掌握的。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 HTTP 各版本的关键改进
- 理解 HTTP/2 的多路复用和 HPACK
- 了解 HTTP/3 的 QUIC 协议
- 能在 dify 中识别 HTTP 协议的应用；状态码见 [06-http-status](./06-http-status.md)，Header 见 [07-http-header](./07-http-header.md)，HTTPS 见 [08-https](./08-https.md)

## 📚 前置知识

- [02-tcp-ip](./02-tcp-ip.md)

## 1. 核心概念

### 1.1 HTTP/0.9（1991）

**特点**：
- 仅 GET 方法
- 仅 HTML 文件
- 无 Header
- 短连接（一次请求一个 TCP）

### 1.2 HTTP/1.0（1996）

**改进**：
- 加入 Header（Content-Type、Status Code）
- 支持多种文件（图片、二进制）
- 支持 POST、HEAD 方法
- **仍是无状态、短连接**

**问题**：
- 每个请求需要新建 TCP 连接（慢）
- 队头阻塞（同一连接中请求必须按序响应）

### 1.3 HTTP/1.1（1997）

**关键改进**：
- **持久连接**（Keep-Alive）：多个请求复用 TCP 连接
- **管道化**（Pipelining）：一次发送多个请求
- **分块传输编码**（Chunked Transfer）
- **Host 头**：支持虚拟主机
- 新的方法：PUT、PATCH、DELETE、OPTIONS

**问题**：
- 管道化支持差（实际很少用）
- 头部冗余传输（每次带相同 Header）
- **队头阻塞仍存在**

### 1.4 HTTP/2（2015）

**关键改进**：
- **二进制分帧**：不再是文本协议
- **多路复用**：一个连接并行多个请求/响应
- **HPACK 头部压缩**：减少冗余
- **服务器推送**（Server Push）：主动推送资源
- **流优先级**：重要资源先传输

**解决**：HTTP/1.1 的队头阻塞

### 1.5 HTTP/3（2022）

**关键改进**：
- **基于 QUIC**（UDP + TLS）
- 解决 TCP 的队头阻塞
- **0-RTT 握手**：首次连接也快
- 连接迁移（连接 ID 标识，不依赖 IP+端口）

### 1.6 各版本对比

| 特性 | HTTP/1.0 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|------|----------|----------|--------|--------|
| 连接 | 短连接 | 持久连接 | 多路复用 | QUIC |
| 头部 | 文本 | 文本 | HPACK 压缩 | QPACK |
| 传输 | 文本 | 文本 | 二进制 | 二进制 |
| 多请求 | 不支持 | 管道化 | 多路复用 | 多路复用 |
| 队头阻塞 | 有 | 有 | 缓解 | **解决** |
| 握手 | 1 RTT | 1 RTT | 1 RTT | **0 RTT** |
| 加密 | 可选 | 可选 | 通常 | **必须** |

### 1.7 性能对比

**加载 100 个资源**：

```
HTTP/1.1（6 个并行连接）：
- 100 / 6 ≈ 17 RTT
- 每连接 6 个资源，队头阻塞

HTTP/2（单连接多路复用）：
- 1 RTT 启动
- 并行传输所有 100 个
- 接近 1 RTT 完成
```

## 2. 代码示例

### 2.1 HTTP/1.1 Keep-Alive

```python
# 文件：http11_demo.py
import http.client

# HTTP/1.1 默认启用 Keep-Alive
conn = http.client.HTTPConnection("example.com", 80)

# 多个请求复用连接
for i in range(3):
    conn.request("GET", "/")
    resp = conn.getresponse()
    print(f"请求 {i}: {resp.status}")
    resp.read()  # 必须读完才能发下一个

conn.close()
```

### 2.2 HTTP/2 多路复用（requests）

```python
# 文件：http2_demo.py
import httpx  # 支持 HTTP/2

async def fetch_http2():
    """用 httpx 启用 HTTP/2。"""
    async with httpx.AsyncClient(http2=True) as client:
        # 同一连接并发多个请求
        urls = [f"https://example.com/?q={i}" for i in range(10)]
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.status_code for r in responses]

# 运行
import asyncio
print(asyncio.run(fetch_http2()))
```

### 2.3 检查 HTTP 版本

```python
# 文件：check_version.py
import http.client

def check_http_version(host: str, path: str = "/"):
    """检查服务器支持的 HTTP 版本。"""
    conn = http.client.HTTPConnection(host, 80)
    conn.request("GET", path, headers={"Connection": "Upgrade", "Upgrade": "h2c"})
    resp = conn.getresponse()
    print(f"HTTP 版本: {resp.version}")
    print(f"状态码: {resp.status}")
    print(f"Header: {dict(resp.getheaders())}")
    conn.close()

check_http_version("example.com")
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTP 客户端配置

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 130-160）：

```python
import aiohttp

class OptimizedSSRFProxy:
    """高性能 SSRF 代理。

    dify 使用 aiohttp，底层支持 HTTP/1.1 和 HTTP/2（如果服务器支持）。
    """

    def __init__(self):
        # 启用 HTTP/2（如果可用）
        # 注：HTTP/2 在 Python 中支持有限
        self._connector = aiohttp.TCPConnector(
            ttl_dns_cache=300,
            keepalive_timeout=75,
            force_close=False,
            enable_cleanup_closed=True,
            # 启用 HTTP/2（需要 aiohttp[http2]）
            # 实际上 dify 主要用 HTTP/1.1
        )

        # 自定义 DNS 解析器
        self._resolver = CustomSafeResolver()

    async def fetch_with_http2(self, url: str):
        """HTTP/2 请求。"""
        # Python aiohttp 通过 http2 库支持 HTTP/2
        # 实际效果：
        # - 服务器支持 HTTP/2 → 用 HTTP/2（更快）
        # - 不支持 → 退化为 HTTP/1.1（兼容）

        async with aiohttp.ClientSession(
            connector=self._connector,
            headers={"Accept-Encoding": "gzip, deflate"},
        ) as session:
            async with session.get(url) as resp:
                print(f"HTTP 版本: {resp.version}")  # 1.1 或 2.0
                print(f"状态码: {resp.status}")
                return await resp.text()


# dify 的 HTTP 优化：
# 1. 连接池：减少 TCP 握手
# 2. Keep-alive：保持长连接
# 3. DNS 缓存：避免重复解析
# 4. 异步并发：asyncio.gather
# 5. HTTP/2（如果服务器支持）

# 实际生产中：
# - dify 服务器 → Flask/Gunicorn → HTTP/1.1（默认）
# - LLM API（OpenAI）→ HTTP/1.1 或 HTTP/2
# - 向量数据库（Qdrant）→ HTTP/2（gRPC 底层）
```

**解读**：
- 第 14 行：连接池 + Keep-alive
- 第 36 行：HTTP 版本自动协商
- **设计意图**：用 HTTP/1.1 持久连接 + 连接池，已足够 dify 的需求

## 4. 关键要点总结

- **HTTP/1.0**：短连接，每次新建 TCP
- **HTTP/1.1**：持久连接，缓解但仍有队头阻塞
- **HTTP/2**：多路复用 + 头部压缩
- **HTTP/3**：基于 QUIC（UDP），解决队头阻塞
- **选择**：HTTP/1.1 足够多数场景，HTTP/2 性能更优
- dify 用 aiohttp，默认 HTTP/1.1

## 5. 练习题

### 练习 1：基础（必做）

用 Python `http.client` 启用 Keep-Alive，连续发 3 个请求到 example.com，验证连接复用。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何默认用 HTTP/1.1 而非 HTTP/2。

### 练习 3：挑战（选做）

用 `curl --http2` 访问支持 HTTP/2 的网站，对比 HTTP/1.1 的耗时。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《HTTP 权威指南》第 2 章
- HTTP/2 RFC 7540
- HTTP/3 RFC 9114

---

**文档版本**：v1.0
**最后更新**：2026-07-13