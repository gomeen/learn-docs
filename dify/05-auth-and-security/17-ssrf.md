# 5.3.5 SSRF：服务端请求伪造

> 理解 SSRF 的攻击原理，掌握 Squid 代理 + 黑名单的纵深防御。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SSRF 的攻击场景（访问内网 / 元数据端点）
- 掌握 SSRF 防护的三大策略：白名单、代理、黑名单
- 了解 dify 的 Squid 代理 + ssrf_proxy 双层防御
- 能识别代码中所有"用户控制 URL"的危险点

## 📚 前置知识

- 13-owasp-top10.md
- HTTP 协议基础

## 1. 核心概念

### 1.1 什么是 SSRF？

SSRF（Server-Side Request Forgery）= 攻击者让**服务端**代替他发起请求，绕过网络边界访问内部资源。

```
正常流程：
  用户 → dify → 外网 API（合法）

SSRF 攻击：
  攻击者 → dify → 内网 169.254.169.254（云元数据）
                                ↑ dify 在云上能访问到
```

### 1.2 攻击者能做什么？

- **访问云元数据**：AWS 的 `169.254.169.254/latest/meta-data/iam/` 拿到 IAM 凭证
- **扫描内网端口**：探测内网开放的服务
- **读取本地文件**：`file:///etc/passwd`（如果驱动支持）
- **绕过 IP 黑名单**：`http://2130706433/`（十进制 IP 形式）
- **DNS rebinding**：DNS 解析时返回合法 IP，使用时返回内网 IP

### 1.3 三种防御策略

**1. 白名单**：只允许请求特定域名（最严格，但灵活性差）
**2. 黑名单**：禁止内网 IP、localhost、metadata IP
**3. 代理转发**：所有出站请求走 Squid 代理，由代理层做过滤

**dify 用方案 3**：所有 HTTP 出站请求走 Squid 代理，dify 自己实现黑名单兜底。

## 2. 代码示例

### 2.1 SSRF 漏洞示例

```python
import requests

@app.post("/fetch")
def fetch_url():
    url = request.json["url"]
    # ❌ 攻击者可传 http://169.254.169.254/... 拿云元数据
    return requests.get(url).text
```

### 2.2 简易 SSRF 防护

```python
import ipaddress
from urllib.parse import urlparse

def is_safe_url(url: str) -> bool:
    """阻止内网 IP。"""
    parsed = urlparse(url)
    hostname = parsed.hostname

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # 域名形式 → 需要 DNS 解析后再判断
        return True  # 简化示例

    # 阻止内网 / 回环 / 链路本地 / 多播
    return not (
        ip.is_private or ip.is_loopback or
        ip.is_link_local or ip.is_multicast or
        ip.is_reserved
    )


# 使用
if not is_safe_url(user_url):
    raise ValueError("URL not allowed")
```

### 2.3 常见错误：DNS rebinding

```python
# ❌ 错误：解析一次就用
import socket
ip = socket.gethostbyname(hostname)
if not is_safe_ip(ip):  # 此时 IP 合法
    raise Forbidden()
requests.get(url)  # 此时 DNS 可能返回内网 IP

# ✅ 正确：代理转发，由 Squid 在出站时再做一次检查
# （dify 的做法）
```

## 3. dify 仓库源码解读

### 3.1 SSRF 防护模块入口

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 1-50）：

```python
"""SSRF-protected HTTP client for generic outbound requests.

Use this module when the URL represents a normal external HTTP interaction that
must go through network/proxy policy exactly as requested, such as HTTP Request
nodes, provider/API integrations, auth discovery, or custom tool calls.

Do not use this directly for "remote file" retrieval. File downloads, probes,
and metadata checks should use `core.file.remote_fetcher` instead so Dify-signed
file URLs can be resolved through DB + storage before falling back to this SSRF
client.
"""

import logging
import time
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from configs import dify_config
from core.helper.http_client_pooling import get_pooled_http_client
from core.tools.errors import ToolSSRFError
from graphon.http.response import HttpResponse

logger = logging.getLogger(__name__)

SSRF_DEFAULT_MAX_RETRIES = dify_config.SSRF_DEFAULT_MAX_RETRIES

BACKOFF_FACTOR = 0.5
STATUS_FORCELIST = [429, 500, 502, 503, 504]

type Headers = dict[str, str]
_HEADERS_ADAPTER: TypeAdapter[Headers] = TypeAdapter(Headers)

_SSL_VERIFIED_POOL_KEY = "ssrf:verified"
_SSL_UNVERIFIED_POOL_KEY = "ssrf:unverified"
_SSRF_CLIENT_LIMITS = httpx.Limits(
    max_connections=dify_config.SSRF_POOL_MAX_CONNECTIONS,
    max_keepalive_connections=dify_config.SSRF_POOL_MAX_KEEPALIVE_CONNECTIONS,
    keepalive_expiry=dify_config.SSRF_POOL_KEEPALIVE_EXPIRY,
)
```

**解读**：
- 第 4-11 行：注释说明使用场景——HTTP Request 节点、provider 集成、OAuth 发现
- 第 21 行：从 dify_config 读取配置（连接池大小、超时等）
- 第 30 行：`STATUS_FORCELIST = [429, 500, 502, 503, 504]` 重试的状态码
- 第 37-41 行：连接池限制（防连接耗尽型 DoS）
- **设计意图**：SSRF 防护不只是"禁内网 IP"，还包括限流、重试、连接池管理

### 3.2 代理转发：核心防御

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 54-83）：

```python
def _create_proxy_mounts(verify: bool) -> dict[str, httpx.HTTPTransport]:
    """Build per-scheme proxy transports with the same TLS policy as the SSRF client."""
    return {
        "http://": httpx.HTTPTransport(
            proxy=dify_config.SSRF_PROXY_HTTP_URL,
            verify=verify,
        ),
        "https://": httpx.HTTPTransport(
            proxy=dify_config.SSRF_PROXY_HTTPS_URL,
            verify=verify,
        ),
    }


def _build_ssrf_client(verify: bool) -> httpx.Client:
    if dify_config.SSRF_PROXY_ALL_URL:
        return httpx.Client(
            proxy=dify_config.SSRF_PROXY_ALL_URL,
            verify=verify,
            limits=_SSRF_CLIENT_LIMITS,
        )

    if dify_config.SSRF_PROXY_HTTP_URL and dify_config.SSRF_PROXY_HTTPS_URL:
        return httpx.Client(
            mounts=_create_proxy_mounts(verify=verify),
            verify=verify,
            limits=_SSRF_CLIENT_LIMITS,
        )

    return httpx.Client(verify=verify, limits=_SSRF_CLIENT_LIMITS)
```

**解读**：
- 第 2-12 行：为 HTTP 和 HTTPS 分别配置代理传输
- 第 16-19 行：所有 URL 都通过统一代理转发
- 第 21-25 行：HTTP 和 HTTPS 分别走不同代理（部署灵活）
- 第 27-28 行：**降级路径**：未配置代理时回退到直接请求（牺牲防御换取可用性）
- **设计意图**：**真正的 SSRF 过滤在 Squid 代理层做**，dify 只负责把请求送过去

### 3.3 Squid 拦截检测

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 178-220）：

```python
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

                if response.status_code not in STATUS_FORCELIST:
                    return response
                else:
                    logger.warning(
                        "Received status code %s for URL %s which is in the force list",
                        response.status_code,
                        url,
                    )

            except httpx.RequestError as e:
                logger.warning("Request to URL %s failed on attempt %s: %s", url, retries + 1, e)
                if max_retries == 0:
                    raise
```

**解读**：
- 第 12 行：发起请求
- 第 15-26 行：**二次检测**：如果返回 401/403 且 Server/Via 头含 "squid"，说明 Squid 拦截了 SSRF 访问
- 第 25 行：抛 `ToolSSRFError` 让上层知道这是被 SSRF 防护拦截的
- 第 32-39 行：连接错误重试机制（指数退避）
- **关键设计**：dify 不自己判断 URL 是否安全，**全权委托给 Squid**；但兜底检测 Squid 是否拒绝了请求
- **整体架构**：用户 URL → httpx → Squid 代理 → 目标服务器；Squid 在中间拒绝内网访问

## 4. 关键要点总结

- SSRF = 攻击者让服务端访问内网 / 云元数据
- **三种防御**：白名单（严格）、黑名单（折衷）、代理转发（dify 用）
- dify 的 SSRF 防护**核心在 Squid 代理层**，应用层只做兜底检测
- 兜底逻辑：401/403 + Server/Via 头含 "squid" → 识别为 SSRF 拦截
- 连接池限制防止资源耗尽，重试机制带指数退避
- `ssrf_proxy.get/post/...` 是出站 HTTP 的**唯一合规入口**

## 5. 练习题

### 练习 1：基础（必做）

写一个 `is_safe_url(url)` 函数，能识别并阻止：`127.0.0.1`、`localhost`、`169.254.169.254`、`10.0.0.0/8`、`http://[::1]/`、`file:///etc/passwd`。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py:178-220`，解释为什么 dify **不自己判断 URL 是否安全**，而是依赖 Squid 代理？

### 练习 3：挑战（选做）

设计一个 **DNS rebinding 防护**：在请求前解析 DNS 并锁定 IP，请求时用这个 IP 直连（不重新解析）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- OWASP SSRF 防护：https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- AWS IMDS 防护：https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- Squid 代理文档：http://www.squid-cache.org/Doc/config/

---

**文档版本**：v1.0
**最后更新**：2026-07-13