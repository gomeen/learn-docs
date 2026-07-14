# 5.6 SSRF：服务端请求伪造与防护

> 理解 SSRF 的攻击原理，能识别并防护服务端发起的内部请求滥用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SSRF 的攻击路径与危害
- 掌握 IP 黑名单、协议限制、代理转发等防御手段
- 在 dify 中识别 SSRF 防护模块（`ssrf_proxy.py`）
- 在业务代码中拒绝未验证的 URL 输入

## 📚 前置知识

- HTTP 协议 / DNS 解析
- 内网 IP 地址段（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16）
- 5.1 OWASP Top 10 概览

## 1. 核心概念

### 1.1 什么是 SSRF？

SSRF（Server-Side Request Forgery，服务端请求伪造）指攻击者**诱导服务端**向非预期目标发起 HTTP 请求。

**与 CSRF 的区别**：
- CSRF：攻击者让**用户浏览器**发请求
- SSRF：攻击者让**服务端**发请求

### 1.2 典型攻击场景

```
攻击者输入 URL: http://169.254.169.254/latest/meta-data/
                                   ↑ AWS 元数据服务

服务端以为是合法请求，发起 HTTP 调用
       ↓
读取到 AWS 实例的 IAM 角色凭证
       ↓
用凭证访问 S3、内部服务等 → 数据泄露
```

**常见目标**：
- AWS / Azure / GCP 元数据服务：`169.254.169.254`、`metadata.google.internal`
- 内网服务：`127.0.0.1`、`localhost`、`192.168.x.x`
- 内网未授权服务：Redis、Elasticsearch、内部 API
- file:// 协议读本地文件：`file:///etc/passwd`

### 1.3 真实案例：Capital One 1 亿用户数据泄露

- 时间：2019 年
- 攻击路径：通过 SSRF 访问 AWS 元数据服务获取 IAM Token
- 结果：1.06 亿信用卡申请人的个人信息泄露，被罚 1.9 亿美元

### 1.4 SSRF 防护的核心思路

| 手段 | 原理 | 局限 |
|------|------|------|
| IP 黑名单 | 拒绝内网 IP | DNS Rebinding 可绕过 |
| URL 协议白名单 | 只允许 http/https | 无法防止域名解析到内网 |
| 代理转发 | 所有请求走代理，代理过滤 | 性能开销 |
| DNS 解析后校验 | 解析域名看 IP 是否内网 | 仍有 TOCTOU 风险 |
| 内容安全策略 | 限制响应内容 | 不通用 |

**最佳实践**：
1. **首选代理转发**（Squid、HAProxy）
2. 同时强制域名解析后 IP 校验
3. 禁用 file://、gopher://、dict:// 等危险协议

### 1.5 dify 的 SSRF 防护方案

dify 的 `ssrf_proxy.py` 是经典案例——通过 **Squid 代理 + 状态码识别 + 重试机制** 三层防护：

```
用户输入 URL → dify ssrf_proxy.py → Squid 代理 → 目标服务器
                                    ↑
                              内网 IP 拦截
                              协议限制
                              SSL 验证
```

## 2. 代码示例

### 2.1 漏洞示例：未限制的 URL 抓取

```python
# 文件：ssrf_vulnerable.py
# ❌ 故意写错的 SSRF 漏洞
import requests
from flask import Flask, request

app = Flask(__name__)

@app.route("/fetch")
def fetch_url():
    """用户提供 URL，服务端抓取内容"""
    url = request.args.get("url", "")
    # ❌ 直接用 requests 抓取，无任何限制
    resp = requests.get(url, timeout=5)
    return resp.text

# 攻击 1：访问 AWS 元数据
# /fetch?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/
#
# 攻击 2：读本地文件
# /fetch?url=file:///etc/passwd
#
# 攻击 3：扫描内网端口
# /fetch?url=http://127.0.0.1:6379/  (Redis 未授权访问)
```

### 2.2 修正：URL 校验 + IP 黑名单

```python
# 文件：ssrf_secure.py
# ✅ 基础 SSRF 防护：URL 解析 + IP 黑名单
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from flask import Flask, request, abort

app = Flask(__name__)

# 禁止访问的网段
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),     # loopback
    ipaddress.ip_network("10.0.0.0/8"),      # 私网
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),   # AWS 元数据
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
]

ALLOWED_SCHEMES = {"http", "https"}

def is_safe_url(url: str) -> tuple[bool, str]:
    """URL 安全校验"""
    try:
        parsed = urlparse(url)

        # 1. 协议白名单
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, f"scheme {parsed.scheme} not allowed"

        # 2. 域名解析后校验 IP
        hostname = parsed.hostname
        if not hostname:
            return False, "no hostname"

        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        except (socket.gaierror, ValueError):
            return False, "DNS resolution failed"

        # 3. IP 黑名单
        for net in BLOCKED_NETWORKS:
            if ip in net:
                return False, f"IP {ip} is blocked"

        # 4. 端口限制（只允许 80/443）
        if parsed.port and parsed.port not in (80, 443):
            return False, f"port {parsed.port} not allowed"

        return True, "ok"
    except Exception as e:
        return False, str(e)

@app.route("/fetch")
def fetch_url():
    url = request.args.get("url", "")
    safe, reason = is_safe_url(url)
    if not safe:
        abort(403, reason)

    # ✅ 只允许 https，且超时限制
    resp = requests.get(url, timeout=5, allow_redirects=False)
    return resp.text

# ✅ 关键：allow_redirects=False 防止 302 跳转到内网
```

### 2.3 更高级：代理转发模式

```python
# 文件：ssrf_via_proxy.py
# ✅ 更安全的方案：所有外部请求通过 Squid 代理
import httpx

class SafeHttpClient:
    """通过 Squid 代理转发请求，由代理层做 IP 黑名单"""

    def __init__(self, proxy_url: str = "http://squid:3128"):
        self.client = httpx.Client(
            proxy=proxy_url,
            timeout=httpx.Timeout(10.0),
            follow_redirects=False,  # 禁止跟随重定向
        )

    def get(self, url: str) -> httpx.Response:
        return self.client.get(url)

    def post(self, url: str, data: dict) -> httpx.Response:
        return self.client.post(url, json=data)

# 优势：
# 1. Squid 代理在网络层强制拒绝内网 IP，应用层代码完全无感
# 2. 多个微服务共用代理，统一安全策略
# 3. 可以做访问日志审计
```

## 3. dify 仓库源码解读

### 3.1 dify 的 SSRFProxy 核心（HTTP 请求入口）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 145-220）：

```python
def make_request(method: str, url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    # Convert requests-style allow_redirects to httpx-style follow_redirects
    if "allow_redirects" in kwargs:
        allow_redirects = kwargs.pop("allow_redirects")
        if "follow_redirects" not in kwargs:
            kwargs["follow_redirects"] = allow_redirects

    if "timeout" not in kwargs:
        kwargs["timeout"] = httpx.Timeout(
            timeout=dify_config.SSRF_DEFAULT_TIME_OUT,
            connect=dify_config.SSRF_DEFAULT_CONNECT_TIME_OUT,
            read=dify_config.SSRF_DEFAULT_READ_TIME_OUT,
            write=dify_config.SSRF_DEFAULT_WRITE_TIME_OUT,
        )

    # prioritize per-call option, which can be switched on and off inside the HTTP node on the web UI
    verify_option = kwargs.pop("ssl_verify", dify_config.HTTP_REQUEST_NODE_SSL_VERIFY)
    if not isinstance(verify_option, bool):
        raise ValueError("ssl_verify must be a boolean")
    client = _get_ssrf_client(verify_option)

    # Inject traceparent header for distributed tracing (when OTEL is not enabled)
    try:
        headers: Headers = _HEADERS_ADAPTER.validate_python(kwargs.get("headers") or {})
    except ValidationError as e:
        raise ValueError("headers must be a mapping of string keys to string values") from e
    headers = _inject_trace_headers(headers)
    kwargs["headers"] = headers

    # Preserve user-provided Host header
    # When using a forward proxy, httpx may override the Host header based on the URL.
    # We extract and preserve any explicitly set Host header to support virtual hosting.
    user_provided_host = _get_user_provided_host_header(headers)

    retries = 0
    while retries <= max_retries:
        try:
            # Preserve the user-provided Host header
            # httpx may override the Host header when using a proxy
            headers = {k: v for k, v in headers.items() if k.lower() != "host"}
            if user_provided_host is not None:
                headers["host"] = user_provided_host
            kwargs["headers"] = headers
            response = client.request(method=method, url=url, **kwargs)

            # Check for SSRF protection by Squid proxy
            if response.status_code in (401, 403):
                # Check if this is a Squid SSRF rejection
                server_header = response.headers.get("server", "").lower()
                via_header = response.headers.get("via", "").lower()

                # Squid typically identifies itself in Server or Via headers
                if "squid" in server_header or "squid" in via_header:
                    raise ToolSSRFError(
                        f"Access to '{url}' was blocked by SSRF protection. "
                        f"The URL may point to a private or local network address. "
                    )
```

**解读**：
- 第 162 行：参数类型严格校验（`ssl_verify` 必须是 bool），防止异常输入
- 第 164 行：`_get_ssrf_client` 通过 Squid 代理获取客户端（**网络层 SSRF 防护**）
- 第 191-201 行：**关键**：Squid 拒绝请求时返回 401/403，dify 检查 `Server` 或 `Via` Header 识别 Squid，主动抛 `ToolSSRFError`
- 第 219 行：指数退避重试（应对瞬时网络问题）
- **设计意图**：dify 的"HTTP Request 节点"允许用户输入 URL，通过 Squid 代理 + 状态码识别，把"内网拦截"的责任从应用层下沉到基础设施层

### 3.2 ruoyi 的 SSRF 防护（应用层黑白名单）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/xss/core/filter/XssFilter.java`（虽然这是 XSS，但其架构思想类似）
**核心代码**（行 41-50）：

```java
@Override
protected boolean shouldNotFilter(HttpServletRequest request) {
    // 如果关闭，则不过滤
    if (!properties.isEnable()) {
        return true;
    }

    // 如果匹配到无需过滤，则不过滤
    String uri = request.getRequestURI();
    return properties.getExcludeUrls().stream().anyMatch(excludeUrl -> pathMatcher.match(excludeUrl, uri));
}
```

**解读**：
- 第 43 行：通过 `properties.isEnable()` 全局开关控制（生产环境开启）
- 第 49 行：**白名单机制**——`excludeUrls` 是不需要过滤的 URL 列表
- **SSRF 防护思路**：ruoyi 倾向于在**应用层维护白名单**，而不是依赖外部代理
- **对比 dify**：dify 用 Squid 代理（网络层），ruoyi 用应用层 Filter 拦截（应用层）。两种思路各有优劣

## 4. 关键要点总结

- SSRF 让服务端被迫访问内网或元数据服务，危害极大
- **首选代理转发**（Squid 模式），网络层强制拒绝
- 兜底方案：URL 协议白名单 + IP 黑名单 + DNS 解析后校验
- 禁用 `file://`、`gopher://` 等危险协议
- **不要跟随重定向**（`allow_redirects=False`），否则 302 可绕过校验
- dify 用 Squid 代理 + 状态码识别，ruoyi 用应用层白名单
- 即使有 SSRF 防护，也要配合**最小权限 IAM 角色**，即使泄露凭证也无法做大

## 5. 练习题

### 练习 1：基础（必做）

实现 `is_safe_url(url)` 函数，要求：
1. 只允许 `http`/`https` 协议
2. 拒绝所有 IPv4 loopback / 私网 / link-local 地址
3. 处理 DNS Rebinding 风险：解析域名后再次校验 IP

**参考答案**：见 `solutions/06-ssrf-validator.md`

### 练习 2：进阶

阅读 dify 的 `ssrf_proxy.py`，画出完整的 SSRF 防护流程图：
1. 用户在 Workflow 中配置 HTTP Request 节点
2. URL 提交到后端
3. `make_request` 调用 Squid 代理
4. Squid 拒绝内网请求
5. 401/403 响应回传 dify
6. dify 抛 `ToolSSRFError`

### 练习 3：挑战（选做）

写一个 Squid 配置文件（`squid.conf`），要求：
1. 拒绝所有 RFC1918 私网地址
2. 拒绝 AWS 元数据 IP `169.254.169.254`
3. 限制响应大小为 10MB（防止 DoS）
4. 记录所有请求到 access.log

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- `/Users/xu/code/github/dify/docker/squid.conf` 或 `docker/squid/` 目录
- `/Users/xu/code/github/dify/api/core/tools/errors.py`（`ToolSSRFError` 定义）
- OWASP SSRF 防护手册：https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13