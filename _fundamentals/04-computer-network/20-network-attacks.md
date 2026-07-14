# 4.5.1 常见网络攻击：CSRF / XSS / SSRF / MITM

> 网络安全是后端开发的必修课。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握常见网络攻击的原理（CSRF、XSS、SSRF、MITM）
- 理解每种攻击的防护方法
- 能在 dify 中识别安全防护的实现

## 📚 前置知识

- 07-http-header.md
- 10-dns.md

## 1. 核心概念

### 1.1 CSRF（跨站请求伪造）

**攻击原理**：诱导用户在已登录的网站上执行非预期操作。

```
1. 用户登录 bank.com（带 Cookie）
2. 用户访问恶意网站 evil.com
3. evil.com 发送请求到 bank.com/transfer
4. 浏览器自动带上 bank.com 的 Cookie
5. bank.com 以为是用户的请求
```

**防护**：
- **CSRF Token**：每次请求带 token
- **SameSite Cookie**：限制跨站 Cookie
- **Referer 检查**：验证来源

### 1.2 XSS（跨站脚本）

**攻击原理**：在网页注入恶意 JavaScript。

```
1. 攻击者提交评论：<script>steal_cookie()</script>
2. 网站未过滤，存入数据库
3. 其他用户查看评论，脚本执行
4. 攻击者获取用户的 Cookie
```

**类型**：
- **反射型**：URL 参数注入
- **存储型**：存入数据库（更危险）
- **DOM 型**：前端 JS 处理

**防护**：
- **输入过滤**：HTML 转义
- **输出编码**：& → &amp; 等
- **Content-Security-Policy**：限制脚本来源
- **HttpOnly Cookie**：JS 不可访问

### 1.3 SSRF（服务端请求伪造）

**攻击原理**：服务器代替攻击者访问内部资源。

```
1. 攻击者调用 API：fetch("http://169.254.169.254/")
2. 服务器执行请求
3. 访问 AWS metadata，获取凭证
4. 攻击者获取云凭证
```

**防护**：
- **URL 白名单**：只允许指定域名
- **DNS 解析验证**：检查是否是内网 IP
- **禁用危险协议**：file://、gopher://
- **限制端口**：禁用 22、3306 等

### 1.4 MITM（中间人攻击）

**攻击原理**：攻击者在客户端和服务器之间截获/篡改通信。

```
客户端 ←→ 攻击者 ←→ 服务器
         (拦截 + 篡改)
```

**场景**：
- 公共 WiFi
- DNS 污染
- 证书伪造

**防护**：
- **HTTPS**：加密传输
- **证书校验**：验证服务器身份
- **HSTS**：强制 HTTPS
- **证书锁定**（pinning）

### 1.5 其他常见攻击

| 攻击 | 说明 |
|------|------|
| **SQL 注入** | SQL 语句拼接 |
| **DDoS** | 大量请求耗尽资源 |
| **暴力破解** | 尝试弱密码 |
| **零日漏洞** | 未公开的漏洞 |

## 2. 代码示例

### 2.1 CSRF 防护（Flask）

```python
# 文件：csrf_demo.py
from flask import Flask, request, abort
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"

# 启用 CSRF 防护
csrf = CSRFProtect(app)

@app.route("/transfer", methods=["POST"])
@csrf.exempt  # API 不需要 CSRF（用其他方式验证）
def transfer():
    # API 用 token 或其他认证方式
    token = request.headers.get("Authorization")
    if not token:
        abort(401)
    # ... 处理转账
    return "OK"

@app.route("/web/transfer", methods=["POST"])
def web_transfer():
    # Web 表单：CSRF 自动检查（来自 Flask-WTF）
    # 自动从 cookie 或 form 取 token 验证
    amount = request.form["amount"]
    # ... 处理转账
    return "OK"
```

### 2.2 XSS 防护（HTML 转义）

```python
# 文件：xss_demo.py
import html
from markupsafe import escape

def safe_html(text: str) -> str:
    """HTML 转义，防止 XSS。"""
    return html.escape(text)

# 演示
user_input = '<script>alert("XSS")</script>'
safe_output = safe_html(user_input)
print(f"原始: {user_input}")
print(f"转义后: {safe_output}")
# 转义后：&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;

# 在模板中（Jinja2 自动转义）
# {{ user_input }}  ← 自动转义
# {{ user_input | safe }}  ← 不转义（危险！）

# 设置 CSP
@app.after_request
def set_csp(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'"
    )
    return response
```

### 2.3 SSRF 防护（IP 验证）

```python
# 文件：ssrf_demo.py
import ipaddress
import socket

def safe_request(url: str) -> bool:
    """SSRF 防护：验证 URL 不指向内网。"""
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # 1. 协议检查
    if parsed.scheme not in ("http", "https"):
        return False

    # 2. 解析域名
    try:
        ips = socket.gethostbyname_ex(parsed.hostname)[2]
    except socket.gaierror:
        return False

    # 3. 检查每个 IP
    for ip in ips:
        if is_private_ip(ip):
            return False

    return True

def is_private_ip(ip: str) -> bool:
    """检查是否是内网 IP。"""
    try:
        addr = ipaddress.ip_address(ip)
        return (addr.is_private or addr.is_loopback
                or addr.is_link_local or addr.is_multicast)
    except ValueError:
        return False

# 测试
print(safe_request("https://www.baidu.com"))  # True
# print(safe_request("http://127.0.0.1/"))     # False
# print(safe_request("http://169.254.169.254/"))  # False
```

### 2.4 HTTPS 证书验证

```python
# 文件：tls_verify.py
import ssl
import socket

def secure_https_request(host: str, path: str = "/"):
    """HTTPS 请求，强制证书验证。"""
    # 创建 SSL context（默认验证证书）
    context = ssl.create_default_context()
    # 启用证书验证（默认开启）
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    sock = socket.create_connection((host, 443))
    sock = context.wrap_socket(sock, server_hostname=host)

    # TLS 1.3 优先
    print(f"TLS 版本: {sock.version()}")
    print(f"加密套件: {sock.cipher()}")

    # 发送请求
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    sock.send(request.encode())

    response = sock.recv(4096)
    sock.close()
    return response
```

## 3. dify 仓库源码解读

### 3.1 dify 的 SSRF 防护

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 30-90）：

```python
import ipaddress
import socket

class SSRFProxy:
    """dify 的 SSRF 防护。

    防护层次：
    1. 协议白名单（只允许 http/https）
    2. 域名黑名单（禁用 localhost、内网域名）
    3. DNS 解析验证（解析后检查 IP）
    4. IP 黑名单（内网 IP 段）
    5. 端口限制（禁用敏感端口）
    """

    # 黑名单：内网 IP 段
    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
    ]

    # 黑名单：敏感端口
    BLOCKED_PORTS = [
        22,    # SSH
        3306,  # MySQL
        5432,  # PostgreSQL
        6379,  # Redis
        27017, # MongoDB
    ]

    async def fetch_safe(self, url: str):
        """SSRF 安全的 HTTP 请求。"""
        from urllib.parse import urlparse

        parsed = urlparse(url)

        # 1. 协议检查
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"不允许的协议: {parsed.scheme}")

        # 2. 端口检查
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port in self.BLOCKED_PORTS:
            raise ValueError(f"不允许的端口: {port}")

        # 3. DNS 解析
        try:
            ips = socket.gethostbyname_ex(parsed.hostname)[2]
        except socket.gaierror:
            raise ValueError(f"DNS 解析失败: {parsed.hostname}")

        # 4. IP 验证
        for ip in ips:
            addr = ipaddress.ip_address(ip)
            if any(addr in net for net in self.PRIVATE_RANGES):
                raise ValueError(f"拒绝内网 IP: {ip}")

        # 5. 发起请求
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.text()


# dify 的其他安全防护：
# - SQLAlchemy ORM（防 SQL 注入）
# - JWT token（认证）
# - RBAC 权限控制（授权）
# - HTTPS（防 MITM）
# - CORS（防 CSRF）
```

**解读**：
- 第 13-19 行：IP 黑名单
- 第 21-27 行：端口黑名单
- 第 36 行：协议白名单
- **设计意图**：多层防护防止 SSRF 攻击

## 4. 关键要点总结

- **CSRF**：用 token / SameSite Cookie 防护
- **XSS**：用 HTML 转义 / CSP 防护
- **SSRF**：用 IP 黑名单 / 域名白名单防护
- **MITM**：用 HTTPS / 证书验证防护
- dify 多层防护 SSRF

## 5. 练习题

### 练习 1：基础（必做）

用 Python 写 SSRF 防护函数：检查 URL 是否指向内网 IP。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何需要多层 SSRF 防护。

### 练习 3：挑战（选做）

实现一个完整的 Web 应用，集成 CSRF、XSS、SSRF 防护。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- OWASP Top 10：https://owasp.org/Top10/
- 《Web 安全深度剖析》

---

**文档版本**：v1.0
**最后更新**：2026-07-13