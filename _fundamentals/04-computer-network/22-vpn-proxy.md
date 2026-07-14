# 4.5.3 VPN 与代理

> VPN 和代理是常见的网络访问技术。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 VPN 和代理的区别
- 掌握常见的代理协议
- 知道实际应用场景
- 能在 dify 中识别代理的应用

## 📚 前置知识

- 19-nat.md
- 08-https.md

## 1. 核心概念

### 1.1 VPN（Virtual Private Network）

**VPN**：通过公网建立**加密的私有通道**，让远程访问像内网一样。

**工作原理**：
```
远程员工（公网）        VPN 服务器        企业内网
   │                       │                  │
   ├── 加密隧道 ────────→ │ 解密 → 转发 ───→ │
   │                       │                  │
   │←─ 加密响应 ──────────┤←─ 响应 ──────────┤
```

### 1.2 VPN 的类型

| 类型 | 协议 | 特点 |
|------|------|------|
| **SSL VPN** | HTTPS | 浏览器即可访问 |
| **IPSec VPN** | IP 层 | 全流量加密 |
| **PPTP** | TCP | 简单但不安全 |
| **L2TP** | UDP | 与 IPSec 结合 |
| **WireGuard** | UDP | 现代、快速 |
| **OpenVPN** | TCP/UDP | 开源、灵活 |

### 1.3 VPN vs 代理

| 维度 | VPN | 代理 |
|------|-----|------|
| 层级 | 网络层（IP） | 应用层 |
| 范围 | 全流量 | 单应用 |
| 加密 | 通常有 | HTTP 代理无 |
| 性能 | 较慢 | 较快 |
| 配置 | 系统级 | 应用级 |

### 1.4 代理的类型

#### HTTP 代理

```
客户端 → HTTP 代理 → 服务器
```

**用途**：
- 访问控制（公司内网）
- 缓存加速
- 内容过滤

#### SOCKS 代理

**更底层**，支持任何 TCP/UDP 流量。

```
SOCKS5：
- 支持 UDP
- 支持认证
- 支持 IPv6
```

#### 反向代理

**代表客户端**向内部服务器请求。

```
客户端 → 反向代理 → 内部服务器
（不知道内部服务器地址）
```

**应用**：Nginx、HAProxy。

#### 正向代理

**代表客户端**访问外部服务器。

```
客户端 → 正向代理 → 外部服务器
（外部服务器看到的是代理）
```

**应用**：科学上网。

### 1.5 透明代理

**客户端无感知**，流量被强制走代理。

**应用**：企业网关、ISP。

### 1.6 代理协议对比

| 协议 | 加密 | 速度 | 用途 |
|------|------|------|------|
| **HTTP CONNECT** | ✗ | 快 | HTTP 代理 |
| **SOCKS5** | 可选 | 快 | 通用代理 |
| **HTTPS Proxy** | ✓ | 中 | 安全代理 |
| **Shadowsocks** | ✓ | 中 | 科学上网 |
| **VMess/VLESS** | ✓ | 中 | 科学上网 |
| **Trojan** | ✓ | 中 | 伪装 HTTPS |

## 2. 代码示例

### 2.1 Python 设置 HTTP 代理

```python
# 文件：http_proxy.py
import requests

# 方法 1：环境变量
import os
os.environ["HTTP_PROXY"] = "http://proxy.example.com:8080"
os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"

# 方法 2：requests 参数
proxies = {
    "http": "http://proxy.example.com:8080",
    "https": "http://proxy.example.com:8080",
}
resp = requests.get("https://api.example.com", proxies=proxies)

# 方法 3：SOCKS 代理（需要 pip install requests[socks]）
socks_proxies = {
    "http": "socks5://user:pass@proxy.example.com:1080",
    "https": "socks5://user:pass@proxy.example.com:1080",
}
resp = requests.get("https://api.example.com", proxies=socks_proxies)
```

### 2.2 实现简单的 HTTP 代理

```python
# 文件：simple_http_proxy.py
import socket
import threading

def proxy_server(listen_port: int):
    """简单的 HTTP 代理服务器。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", listen_port))
    server.listen()
    print(f"HTTP 代理: 0.0.0.0:{listen_port}")

    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

def handle_client(client: socket.socket):
    """处理代理请求。"""
    # 读取 HTTP 请求
    request = b""
    client.settimeout(5)
    while b"\r\n\r\n" not in request:
        chunk = client.recv(4096)
        if not chunk:
            client.close()
            return
        request += chunk

    # 解析目标 URL
    first_line = request.split(b"\r\n")[0]
    method, url, _ = first_line.split(b" ", 2)

    if method == b"CONNECT":
        # HTTPS 代理
        host, port = url.split(b":")
        port = int(port)
        # 连接目标
        target = socket.create_connection((host.decode(), port))
        # 响应客户端
        client.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        # 双向转发
        forward_data(client, target)
        forward_data(target, client)
    else:
        # HTTP 代理
        from urllib.parse import urlparse
        parsed = urlparse(url.decode())
        host = parsed.hostname
        port = parsed.port or 80
        target = socket.create_connection((host, port))
        target.send(request)
        forward_data(target, client)
        forward_data(client, target)

def forward_data(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        src.close()
        dst.close()
```

### 2.3 SOCKS5 代理（简化版）

```python
# 文件：socks5_proxy.py
import socket
import struct
import threading

def socks5_server(listen_port: int):
    """简化的 SOCKS5 代理。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", listen_port))
    server.listen()

    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_socks5, args=(client,), daemon=True).start()

def handle_socks5(client: socket.socket):
    """处理 SOCKS5 握手。"""
    # 1. 认证协商
    # 客户端：VER NMETHODS METHODS
    data = client.recv(1024)
    ver, nmethods = data[0], data[1]
    # 响应：无认证
    client.send(b"\x05\x00")

    # 2. 请求
    # 客户端：VER CMD RSV ATYP DST.ADDR DST.PORT
    data = client.recv(1024)
    ver, cmd, _, atyp = data[0], data[1], data[2], data[3]

    if cmd != 1:  # CONNECT
        client.close()
        return

    # 解析目标地址
    if atyp == 1:  # IPv4
        addr = socket.inet_ntoa(data[4:8])
        port = struct.unpack("!H", data[8:10])[0]
    elif atyp == 3:  # 域名
        domain_len = data[4]
        addr = data[5:5 + domain_len].decode()
        port = struct.unpack("!H", data[5 + domain_len:7 + domain_len])[0]
    else:
        client.close()
        return

    # 3. 连接目标
    try:
        target = socket.create_connection((addr, port))
    except Exception:
        client.send(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
        client.close()
        return

    # 4. 响应：成功
    client.send(b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + struct.pack("!H", 0))

    # 5. 双向转发
    forward(client, target)
    forward(target, client)

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    finally:
        src.close()
        dst.close()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Nginx 反向代理配置

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf`
**核心代码**（简化）：

```nginx
# dify 的反向代理配置

# 上游（内部服务）
upstream dify-api {
    server api:5001;
}

upstream dify-web {
    server web:3000;
}

# 反向代理
server {
    listen 80;
    server_name dify.example.com;

    # API 代理
    location /v1/ {
        proxy_pass http://dify-api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Web 代理
    location / {
        proxy_pass http://dify-web;
    }

    # 文件上传大小
    client_max_body_size 100M;
}

# HTTPS 重定向
server {
    listen 443 ssl;
    server_name dify.example.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # 与 server block 相同的 location 配置
    # ...
}
```

**解读**：
- 第 4-10 行：上游（upstream）定义
- 第 15-25 行：反向代理 + 头部转发
- 第 36-39 行：HTTPS 配置
- **设计意图**：用 Nginx 做反向代理，统一入口 + HTTPS 终止

### 3.2 dify 的代理使用场景

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 100-120）：

```python
class ProxyConfig:
    """dify 的代理配置。

    场景：
    1. 企业部署：dify 服务器在内网，通过代理访问外网
    2. LLM API 代理：使用反向代理提高稳定性
    3. 测试环境：使用 mock 代理

    dify 支持通过环境变量配置代理：
    - HTTP_PROXY / HTTPS_PROXY
    - NO_PROXY（不走代理的地址）
    """

    def __init__(self):
        # 从环境变量读代理
        import os
        self.http_proxy = os.environ.get("HTTP_PROXY")
        self.https_proxy = os.environ.get("HTTPS_PROXY")
        self.no_proxy = os.environ.get("NO_PROXY", "")

    def get_proxies(self, url: str) -> dict:
        """根据 URL 返回代理配置。"""
        # 检查是否在 NO_PROXY 中
        from urllib.parse import urlparse
        parsed = urlparse(url)

        if self._is_no_proxy(parsed.hostname):
            return {}

        # 返回代理
        return {
            "http": self.http_proxy,
            "https": self.https_proxy,
        }

    def _is_no_proxy(self, host: str) -> bool:
        """检查是否不走代理。"""
        if not self.no_proxy:
            return False
        for pattern in self.no_proxy.split(","):
            pattern = pattern.strip()
            if pattern and (pattern == host or host.endswith("." + pattern)):
                return True
        return False


# 使用示例：
# export HTTP_PROXY=http://proxy.company.com:8080
# export NO_PROXY=localhost,127.0.0.1,.internal
# python app.py
```

**解读**：
- 第 14-16 行：从环境变量读代理配置
- 第 25-29 行：实现 NO_PROXY 规则
- **设计意图**：支持企业部署场景（需要通过代理访问外网）

## 4. 关键要点总结

- **VPN**：加密隧道，全流量
- **代理**：应用层，单应用
- **类型**：HTTP 代理、SOCKS 代理、反向代理、正向代理
- **dify 用 Nginx 反向代理**：统一入口 + HTTPS 终止
- **企业部署**：用 HTTP_PROXY 环境变量配置代理

## 5. 练习题

### 练习 1：基础（必做）

用 Python `requests` 库通过 HTTP 代理访问一个网站。

### 练习 2：进阶

阅读 `docker/nginx/conf.d/default.conf`，说明 dify 为何用 Nginx 反向代理而非直接暴露服务。

### 练习 3：挑战（选做）

实现一个简单的 HTTP 代理服务器（支持 HTTP CONNECT 方法）。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf`
- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- 《HTTPS 权威指南》第 10 章
- WireGuard：https://www.wireguard.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13