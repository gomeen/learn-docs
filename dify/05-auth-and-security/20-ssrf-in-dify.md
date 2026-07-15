# 5.3.8 dify 的 SSRF 防护实现（ssrf_proxy）

> 端到端解析 dify 的 SSRF 防护：连接池、代理转发、重试、Squid 兜底。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整理解 dify SSRF 防护的架构（连接池 + 代理 + 兜底）
- 掌握 `ssrf_proxy` 模块的所有公开 API
- 能看懂 Squid 拦截响应如何被识别
- 能在 dify 中用 SSRF 安全的 HTTP 客户端

## 📚 前置知识

- SSRF 攻击与防护原理（详见 [SSRF](../../_common/05-web-security/06-ssrf.md)）
- 异步编程背景（详见 [async/asyncio](../01-fundamentals/12-async-asyncio.md)）——httpx 异步客户端场景

## 1. 核心概念

### 1.1 dify SSRF 防护的四层架构

```
┌────────────────────────────────────────────────┐
│ 第 1 层：调用方                                  │
│  - 业务代码调用 ssrf_proxy.get/post              │
└────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────┐
│ 第 2 层：连接池管理                              │
│  - 按 ssl_verify 标记分两个池                    │
│  - httpx 连接复用，避免每次新建 TCP 连接         │
└────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────┐
│ 第 3 层：代理转发                                │
│  - 所有请求走 SSRF_PROXY_*_URL                   │
│  - Squid 代理层做真正的 IP 黑名单                 │
└────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────┐
│ 第 4 层：兜底检测                                │
│  - 识别 Squid 拦截响应（401/403 + squid 标识）    │
│  - 抛 ToolSSRFError                             │
└────────────────────────────────────────────────┘
```

### 1.2 模块入口：`ssrf_proxy`

`ssrf_proxy.py` 导出的关键对象：

| 对象 | 类型 | 用途 |
|------|------|------|
| `ssrf_proxy` | `SSRFProxy` 实例 | 通用 HTTP 客户端（带重试） |
| `graphon_ssrf_proxy` | `GraphonSSRFProxy` 实例 | 兼容 Graphon 的传输封装 |
| `make_request(method, url, **kwargs)` | 函数 | 底层请求函数 |
| `get/post/put/delete/...` | 函数 | 快捷方法 |
| `MaxRetriesExceededError` | 异常 | 重试耗尽 |
| `ToolSSRFError` | 异常 | Squid 拦截 |

## 2. 代码示例

### 2.1 调用 ssrf_proxy 的典型用法

```python
from core.helper.ssrf_proxy import ssrf_proxy, MaxRetriesExceededError

def fetch_external_api(url: str) -> dict:
    """通过 SSRF 防护的客户端访问外网 API。"""
    try:
        resp = ssrf_proxy.get(
            url,
            params={"key": "value"},
            headers={"Authorization": "Bearer xxx"},
            timeout=10,
        )
        return resp.json()
    except MaxRetriesExceededError:
        raise ServiceUnavailable("External API unavailable")
```

### 2.2 POST 请求

```python
from core.helper.ssrf_proxy import ssrf_proxy

resp = ssrf_proxy.post(
    "https://api.example.com/webhook",
    json={"event": "test", "data": {"x": 1}},
    timeout=(5, 30),  # (connect_timeout, read_timeout)
    follow_redirects=False,  # 不跟随重定向（防 SSRF 重定向绕过）
)
```

### 2.3 常见错误：直接用 requests

```python
# ❌ 错误：用 requests 不走 SSRF 防护
import requests
resp = requests.get(user_provided_url)
# 攻击者可访问 http://169.254.169.254/

# ✅ 正确：用 ssrf_proxy
from core.helper.ssrf_proxy import ssrf_proxy
resp = ssrf_proxy.get(user_provided_url)
```

## 3. dify 仓库源码解读

### 3.1 客户端构建（连接池 + 代理）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 86-93）：

```python
def _get_ssrf_client(ssl_verify_enabled: bool) -> httpx.Client:
    if not isinstance(ssl_verify_enabled, bool):
        raise ValueError("SSRF client verify flag must be a boolean")

    return get_pooled_http_client(
        _SSL_VERIFIED_POOL_KEY if ssl_verify_enabled else _SSL_UNVERIFIED_POOL_KEY,
        lambda: _build_ssrf_client(verify=ssl_verify_enabled),
    )
```

**解读**：
- 第 6-8 行：连接池按 `ssl_verify` 分为两个 key，避免混用
- 第 9 行：用 lambda 延迟构建，首次访问时才创建 httpx.Client
- **设计意图**：连接复用降低握手开销，分池管理避免 verify 状态污染

### 3.2 重试机制

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 179-220）：

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

    raise MaxRetriesExceededError(f"Reached maximum retries ({max_retries}) for URL {url}")
```

**解读**：
- 第 1 行：重试计数
- 第 5-9 行：保留用户提供的 Host 头（防被代理覆盖）
- 第 12 行：实际发起请求
- 第 15-26 行：**核心防御**：检测 Squid 拦截（401/403 + squid 标识），抛 `ToolSSRFError`
- 第 28-32 行：非重试状态码直接返回
- 第 36-40 行：连接错误日志 + 重试判断
- **设计模式**：重试 + 兜底 + 异常分类 = 完整防护

### 3.3 指数退避

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 217-220）：

```python
        retries += 1
        if retries <= max_retries:
            time.sleep(BACKOFF_FACTOR * (2 ** (retries - 1)))
    raise MaxRetriesExceededError(f"Reached maximum retries ({max_retries}) for URL {url}")
```

**解读**：
- 第 2 行：指数退避 —— 每次重试等待 `0.5 * 2^(n-1)` 秒
  - 第 1 次：0.5s
  - 第 2 次：1.0s
  - 第 3 次：2.0s
- 第 3 行：重试耗尽抛 `MaxRetriesExceededError`
- **设计意图**：避免对失败服务造成"重试风暴"

### 3.4 HTTP 方法快捷封装

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 223-244）：

```python
def get(url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    return make_request("GET", url, max_retries=max_retries, **kwargs)


def post(url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    return make_request("POST", url, max_retries=max_retries, **kwargs)


def put(url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    return make_request("PUT", url, max_retries=max_retries, **kwargs)


def patch(url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    return make_request("PATCH", url, max_retries=max_retries, **kwargs)


def delete(url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    return make_request("DELETE", url, max_retries=max_retries, **kwargs)


def head(url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    return make_request("HEAD", url, max_retries=max_retries, **kwargs)
```

**解读**：
- 6 个 HTTP 方法的快捷函数，**所有调用最终走 `make_request`**
- 默认重试次数来自配置 `SSRF_DEFAULT_MAX_RETRIES`
- **设计意图**：API 表面简单（get/post/...），底层统一防护

## 4. 关键要点总结

- dify SSRF 防护 = **连接池 + 代理转发 + Squid 兜底 + 指数退避**
- **入口**：`ssrf_proxy.get/post/put/delete/...` 或 `make_request`
- **兜底逻辑**：401/403 + squid 标识 → `ToolSSRFError`
- **重试机制**：指数退避避免对失败服务雪崩
- **Host 头保留**：使用代理时不会被覆盖
- **降级路径**：未配置代理时回退到直接请求（牺牲防御换取可用性）

## 5. 练习题

### 练习 1：基础（必做）

写一个简化版 `simple_ssrf_get(url)`：用 httpx + 简单黑名单（拒绝 `127.0.0.1`、`10.0.0.0/8`、`169.254.0.0/16`），抛异常如果 URL 不安全。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py:178-220`，画出完整的"请求 → 重试 → 兜底"状态机。

### 练习 3：挑战（选做）

基于 dify 的 `ssrf_proxy`，实现一个"SSRF 监控指标"：记录每次请求的 URL、是否被 Squid 拦截、最终状态码，输出 Prometheus 指标。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- `/Users/xu/code/github/dify/docker/squid.conf`（Squid 代理配置）
- Squid SSRF 防护：https://github.com/sameersbn/docker-squid#preventing-ssrf
- httpx 文档：https://www.python-httpx.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13