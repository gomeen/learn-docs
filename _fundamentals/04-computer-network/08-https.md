# 4.2.5 HTTPS 握手：TLS 1.2 / 1.3

> HTTPS 通过 TLS 加密保证传输安全，是现代 Web 的标配。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 TLS 1.2 和 TLS 1.3 的握手过程
- 理解证书验证和密钥交换
- 知道 0-RTT 等性能优化
- 能在 dify 中识别 HTTPS 的应用

## 📚 前置知识

- 05-http-flow.md
- 04-http-versions.md

## 1. 核心概念

### 1.1 HTTPS = HTTP + TLS

```
HTTP → 明文传输
HTTPS → HTTP + TLS 加密传输
```

**TLS（Transport Layer Security）**（握手细节亦见 [_fundamentals 编码与加密 12-tls](../07-encoding-and-crypto/12-tls.md)）：
- 在 TCP 之上、应用层之下
- 提供加密、认证、完整性

### 1.2 TLS 的三大目标

1. **加密**：防止窃听
2. **认证**：验证服务器身份（证书）
3. **完整性**：防止篡改（MAC）

### 1.3 TLS 1.2 握手（2 RTT）

```
客户端                                服务器
  │                                      │
  ├── 1. ClientHello ─────────────────→ │  (TLS 版本、加密套件、随机数)
  │                                      │
  │← 2. ServerHello ──────────────────┤  (选择 TLS 版本、加密套件)
  │← 3. Certificate ──────────────────┤  (服务器证书)
  │← 4. ServerKeyExchange ────────────┤  (可选，密钥交换参数)
  │← 5. ServerHelloDone ──────────────┤
  │                                      │
  ├── 6. ClientKeyExchange ──────────→ │  (用服务器公钥加密 pre-master secret)
  ├── 7. ChangeCipherSpec ───────────→ │  (后续消息加密)
  ├── 8. Finished ───────────────────→ │  (握手完成，加密)
  │                                      │
  │← 9. ChangeCipherSpec ────────────┤
  │← 10. Finished ──────────────────┤
  │                                      │
  [加密通道建立]
  │                                      │
  ├── 11. HTTP Request (加密) ──────→ │
  │←─── 12. HTTP Response (加密) ───┤
```

### 1.4 TLS 1.3 握手（1 RTT）

```
客户端                                服务器
  │                                      │
  ├── 1. ClientHello + Key Share ─────→ │  (推测的密钥共享)
  │                                      │
  │← 2. ServerHello + Key Share ──────┤  (选择的密钥共享)
  │← 3. EncryptedExtensions ──────────┤  (加密的扩展)
  │← 4. Certificate ──────────────────┤  (证书，加密)
  │← 5. CertificateVerify ────────────┤  (证书验证)
  │← 6. Finished ─────────────────────┤  (握手完成)
  │                                      │
  [加密通道建立]
```

**TLS 1.3 改进**：
- **1 RTT**（vs TLS 1.2 的 2 RTT）
- **0-RTT**（恢复连接时，0 个 RTT 即可发送数据）
- 移除不安全算法（RC4、SHA-1、3DES 等）
- 强制前向保密（PFS）

### 1.5 加密算法

**密钥交换**：
- RSA（TLS 1.2）
- ECDHE（椭圆曲线，TLS 1.3 默认）
- X25519（现代曲线）

**对称加密**：
- AES-GCM（最常用）
- ChaCha20-Poly1305

**消息认证**：
- SHA-256
- SHA-384

### 1.6 证书（X.509）

**证书内容**：
- 颁发给（Subject）
- 颁发者（Issuer）
- 公钥
- 有效期
- 签名

**证书链**：
```
根证书（CA）→ 中间证书 → 服务器证书
```

### 1.7 HTTPS 性能优化

1. **TLS 1.3**：1 RTT 握手
2. **0-RTT**：恢复连接无 RTT
3. **Session Ticket**：避免重复握手
4. **OCSP Stapling**：服务器代查证书状态
5. **False Start**：提前发送数据

## 2. 代码示例

### 2.1 Python HTTPS 客户端

```python
# 文件：https_client.py
import ssl
import socket
import time

def https_request(host: str, path: str = "/"):
    """HTTPS 请求 - 手动控制各阶段。"""
    timings = {}

    # 1. DNS 解析
    start = time.perf_counter()
    ip = socket.gethostbyname(host)
    timings["dns"] = time.perf_counter() - start

    # 2. TCP 握手
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, 443))
    timings["tcp"] = time.perf_counter() - start

    # 3. TLS 握手
    start = time.perf_counter()
    context = ssl.create_default_context()
    # 支持 TLS 1.3
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    sock = context.wrap_socket(sock, server_hostname=host)
    timings["tls"] = time.perf_counter() - start
    print(f"TLS 版本: {sock.version()}")
    print(f"加密套件: {sock.cipher()}")

    # 4. HTTP 请求
    start = time.perf_counter()
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    sock.send(request.encode())
    response = sock.recv(4096)
    timings["http"] = time.perf_counter() - start

    sock.close()

    print(f"DNS: {timings['dns']*1000:.1f}ms")
    print(f"TCP: {timings['tcp']*1000:.1f}ms")
    print(f"TLS: {timings['tls']*1000:.1f}ms")
    print(f"HTTP: {timings['http']*1000:.1f}ms")

# https_request("www.baidu.com")
```

### 2.2 启用 TLS 1.3

```python
# 文件：tls13_demo.py
import ssl

def create_tls13_context():
    """创建支持 TLS 1.3 的上下文。"""
    context = ssl.create_default_context()

    # 仅允许 TLS 1.3
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    # 设置加密套件（TLS 1.3 自动协商）
    context.set_ciphers("TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256")

    return context

# 检查 TLS 版本
context = create_tls13_context()
print(f"最低 TLS 版本: {context.minimum_version}")
```

### 2.3 检查证书

```python
# 文件：check_cert.py
import ssl
import socket

def get_cert_info(host: str) -> dict:
    """获取服务器证书信息。"""
    context = ssl.create_default_context()
    with socket.create_connection((host, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()

    return {
        "subject": dict(x[0] for x in cert["subject"]),
        "issuer": dict(x[0] for x in cert["issuer"]),
        "version": cert["version"],
        "serial": cert["serialNumber"],
        "not_before": cert["notBefore"],
        "not_after": cert["notAfter"],
        "san": cert.get("subjectAltName", []),
    }

# 查看百度证书
# print(get_cert_info("www.baidu.com"))
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTPS 客户端配置

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 60-90）：

```python
import aiohttp
import ssl

class SecureSSRFProxy:
    """安全的 HTTPS 客户端。

    dify 的 HTTPS 请求配置：
    - 默认启用 SSL 证书验证
    - 支持现代 TLS 版本
    - 自定义 CA 证书（私有部署）
    """

    def __init__(self):
        # 创建 SSL context
        self._ssl_context = ssl.create_default_context()

        # 设置 TLS 版本（优先 TLS 1.3）
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        # aiohttp 自动协商 TLS 1.3（如果服务器支持）

        # 创建连接器
        self._connector = aiohttp.TCPConnector(
            ssl_context=self._ssl_context,
            ttl_dns_cache=300,
            keepalive_timeout=75,
            force_close=False,
        )

    async def fetch(self, url: str):
        """HTTPS 请求。"""
        async with aiohttp.ClientSession(connector=self._connector) as session:
            async with session.get(url) as resp:
                return await resp.text()


# dify 的 HTTPS 最佳实践：
# 1. 默认验证证书（不绕过）
# 2. 启用 TLS 1.3（如果服务器支持）
# 3. 启用证书透明度（CT）
# 4. 使用强加密套件
# 5. 配置 HSTS（生产环境）

# dify 服务器端配置（生产）：
# - Nginx 反向代理 + Let's Encrypt 证书
# - 配置 HSTS：Strict-Transport-Security: max-age=31536000
# - 配置 OCSP Stapling
# - 禁用 TLS 1.0/1.1（仅 TLS 1.2+）
```

**解读**：
- 第 19 行：最低 TLS 1.2
- 第 21 行：aiohttp 自动协商 TLS 1.3
- **设计意图**：启用现代 TLS 版本，保证安全性

## 4. 关键要点总结

- **TLS 1.2**：2 RTT 握手
- **TLS 1.3**：1 RTT 握手，**性能更好**
- **0-RTT**：恢复连接无 RTT
- **证书链**：CA → 中间证书 → 服务器证书
- **强制前向保密**：即使私钥泄露，过去会话仍安全
- dify 默认启用 TLS 1.2+，自动协商 TLS 1.3

## 5. 练习题

### 练习 1：基础（必做）

用 Python 访问 `https://www.baidu.com`，打印 TLS 版本、加密套件、证书信息。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何默认验证证书而不绕过。

### 练习 3：挑战（选做）

用 OpenSSL 命令行模拟 TLS 1.3 握手：`openssl s_client -tls1_3 -connect example.com:443`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 8446：TLS 1.3 规范
- 《HTTPS 权威指南》

---

**文档版本**：v1.0
**最后更新**：2026-07-13