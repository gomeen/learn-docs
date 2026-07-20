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
- 异步编程背景（详见 [async/asyncio](../01-fundamentals/14-async-asyncio.md)）——httpx 异步客户端场景

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

## 3. 关键要点总结

- dify SSRF 防护 = **连接池 + 代理转发 + Squid 兜底 + 指数退避**
- **入口**：`ssrf_proxy.get/post/put/delete/...` 或 `make_request`
- **兜底逻辑**：401/403 + squid 标识 → `ToolSSRFError`
- **重试机制**：指数退避避免对失败服务雪崩
- **Host 头保留**：使用代理时不会被覆盖
- **降级路径**：未配置代理时回退到直接请求（牺牲防御换取可用性）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
