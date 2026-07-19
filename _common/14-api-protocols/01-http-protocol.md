# 14.1 HTTP/HTTPS 协议：方法、状态码、Header、Cookie

> 掌握 HTTP 协议的核心概念，能阅读 dify 中所有 HTTP 请求与响应，理解 Web 通信基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 HTTP 方法（GET/POST/PUT/DELETE/PATCH）的语义
- 理解常见状态码的含义（2xx/3xx/4xx/5xx）
- 阅读 HTTP 头部（Header）和 Cookie 机制
- 理解 HTTPS 的 TLS 加密原理

## 📚 前置知识

- 网络基础：IP、端口、TCP
- 命令行基础

## 1. 核心概念

### 1.1 HTTP 请求/响应结构

HTTP 是**请求-响应**协议，客户端发送 Request，服务器返回 Response。

**请求（Request）**：

```
POST /v1/chat-messages HTTP/1.1           ← 请求行（方法 + 路径 + 版本）
Host: api.dify.ai                          ← Header
Authorization: Bearer app-xxx
Content-Type: application/json
Content-Length: 156
                                            ← 空行
{"query": "hi", "user": "user-001"}        ← Body（可选）
```

**响应（Response）**：

```
HTTP/1.1 200 OK                             ← 状态行
Content-Type: application/json
Content-Length: 234
                                            ← 空行
{"answer": "hello"}                         ← Body
```

### 1.2 HTTP 方法

| 方法 | 语义 | 幂等性 | 安全性 | 常见用途 |
|---|---|---|---|---|
| **GET** | 获取资源 | 是 | 是 | 查数据 |
| **POST** | 创建资源 | 否 | 否 | 提交表单、调用操作 |
| **PUT** | 替换资源 | 是 | 否 | 全量更新 |
| **PATCH** | 部分更新 | 否 | 否 | 局部更新 |
| **DELETE** | 删除资源 | 是 | 否 | 删除数据 |
| **HEAD** | 仅响应头 | 是 | 是 | 检查资源存在 |
| **OPTIONS** | 预检请求 | - | - | CORS |

**幂等性**：多次执行结果一致（PUT/DELETE 多次调用结果相同）。

### 1.3 状态码分类

| 范围 | 含义 | 常见状态码 |
|---|---|---|
| **1xx** | 信息 | 100 Continue |
| **2xx** | 成功 | 200 OK、201 Created、204 No Content |
| **3xx** | 重定向 | 301 Moved、302 Found、304 Not Modified |
| **4xx** | 客户端错误 | 400 Bad Request、401 Unauthorized、403 Forbidden、404 Not Found、429 Too Many Requests |
| **5xx** | 服务器错误 | 500 Internal Server Error、502 Bad Gateway、503 Service Unavailable、504 Gateway Timeout |

**dify 常用状态码**：
- 200：成功
- 201：资源创建（POST /v1/apps）
- 401：未登录或 token 无效
- 403：权限不足
- 404：应用/工作流不存在
- 429：触发频率限制
- 500：服务器内部错误

### 1.4 重要 Header

**通用 Header**：

| Header | 作用 |
|---|---|
| `Content-Type` | Body 类型（application/json、text/html） |
| `Content-Length` | Body 字节数 |
| `Cache-Control` | 缓存策略（max-age=3600, no-cache） |
| `Date` | 响应时间 |

**请求 Header**：

| Header | 作用 |
|---|---|
| `Host` | 域名（HTTP/1.1 必需） |
| `Authorization` | 认证凭据（Bearer token、Basic auth） |
| `User-Agent` | 客户端标识 |
| `Accept` | 客户端接受的响应类型 |
| `Cookie` | 客户端 Cookie |
| `Referer` | 来源页面 |

**响应 Header**：

| Header | 作用 |
|---|---|
| `Set-Cookie` | 设置 Cookie |
| `Location` | 重定向目标（3xx） |
| `Access-Control-Allow-Origin` | CORS 允许的来源 |

### 1.5 Cookie 机制

**HTTP 是无状态协议**，Cookie 是服务器"记住"客户端的方式：

```
1. 客户端首次请求
   GET /login HTTP/1.1

2. 服务器响应，设置 Cookie
   HTTP/1.1 200 OK
   Set-Cookie: session_id=abc123; Path=/; HttpOnly; Secure

3. 客户端后续请求自动带 Cookie
   GET /profile HTTP/1.1
   Cookie: session_id=abc123
```

**关键属性**：
- `HttpOnly`：JS 无法读取，防 XSS 窃取
- `Secure`：仅 HTTPS 传输
- `SameSite`：防 CSRF 攻击（`Strict`/`Lax`/`None`）
- `Max-Age`/`Expires`：过期时间

### 1.6 HTTPS = HTTP + TLS

HTTPS 在 HTTP 和 TCP 之间加入 TLS 加密层：
- **加密**：防窃听
- **认证**：防冒充（数字证书）
- **完整性**：防篡改

```
HTTP → TLS → TCP → IP → 网络
```

## 2. 代码示例

### 2.1 构造 HTTP 请求（Python）

```python
import httpx

# GET 请求
response = httpx.get("https://api.dify.ai/v1/health")
print(response.status_code)        # 200
print(response.headers["content-type"])  # application/json
print(response.json())              # {"status": "ok"}

# POST JSON
response = httpx.post(
    "https://api.dify.ai/v1/chat-messages",
    headers={
        "Authorization": "Bearer app-xxx",
        "Content-Type": "application/json",
    },
    json={
        "inputs": {},
        "query": "你好",
        "user": "user-001",
        "response_mode": "streaming",
    },
)
print(response.status_code)
```

### 2.2 解析 HTTP 响应

```python
response = httpx.get("https://api.example.com/data")

# 状态码判断
if response.status_code == 200:
    print(response.json())
elif response.status_code == 404:
    print("Not found")
elif response.status_code >= 500:
    print("Server error")

# 读取 Cookie
for cookie in response.cookies:
    print(f"{cookie.name}={cookie.value}")

# 读取 Header
print(response.headers.get("content-type"))
```

### 2.3 常见错误：忘记 `Content-Type`

```bash
# ❌ 错误：发送 JSON 但没声明 Content-Type
curl -X POST http://localhost:5001/v1/chat-messages \
    -H "Authorization: Bearer app-xxx" \
    -d '{"query": "hi"}'
# 服务器可能按 form-data 解析，失败

# ✅ 正确：显式声明
curl -X POST http://localhost:5001/v1/chat-messages \
    -H "Authorization: Bearer app-xxx" \
    -H "Content-Type: application/json" \
    -d '{"query": "hi"}'
```

## 3. dify 仓库源码解读

### 3.1 dify 的鉴权 Header

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 1-30）：

```python
from functools import wraps

from flask import request
from flask_login import current_user


def login_required(func):
    """Flask 路由装饰器：检查 Authorization Header。

    期望格式：Authorization: Bearer <api_key>
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"error": "Missing or invalid Authorization header"}, 401

        api_key = auth_header[7:]  # 去掉 "Bearer " 前缀
        user = authenticate_api_key(api_key)
        if not user:
            return {"error": "Invalid API key"}, 401

        return func(*args, **kwargs)
    return wrapper
```

**解读**：
- 用装饰器统一检查 Header（装饰器原理见 [10-decorator](../../dify/01-fundamentals/10-decorator.md)）；本文关注 **Authorization Header 语义**
- 第 12 行：所有受保护端点必须带 `Authorization: Bearer <key>`
- 第 13-14 行：缺失或格式错误返回 401 Unauthorized
- 第 16-18 行：API key 无效返回 401
- **关键设计**：Bearer Token 是 REST API 的主流鉴权方式

### 3.2 dify 的 CORS 配置

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_blueprint.py`
**核心代码**（行 1-30）：

```python
from flask_cors import CORS

# 允许所有来源的跨域请求
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
```

**解读**：
- 第 6 行：`origins: "*"` 允许任何来源（开发友好，生产环境应限制）
- 第 7 行：`supports_credentials=True` 允许 Cookie
- 第 8-9 行：白名单 Header 和方法
- **关键设计**：浏览器同源策略要求跨域请求显式声明允许，CORS 是 W3C 标准

## 4. 关键要点总结

- HTTP 是无状态请求-响应协议，每次请求独立
- 方法语义：GET 查、POST 创、PUT 替、PATCH 改、DELETE 删
- 状态码：2xx 成功、3xx 重定向、4xx 客户端错、5xx 服务器错
- 鉴权主流方式：`Authorization: Bearer <token>`
- Cookie 三个安全属性：`HttpOnly`、`Secure`、`SameSite`
- HTTPS = HTTP + TLS，提供加密、认证、完整性

## 5. 练习题

### 练习 1：基础（必做）

用 `curl -v` 请求 `https://api.dify.ai/v1/health`，列出：
1. 请求方法、路径、协议版本
2. 响应状态码
3. Content-Type

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/libs/login.py`，理解 dify 的鉴权流程：
1. 如何从 Header 提取 API key
2. 如何查询对应的用户
3. 哪些情况返回 401

### 练习 3：挑战（选做）

用 Python 写一个 `http_probe(url, expected_status=200)` 函数：发起 GET 请求，检查响应状态码、Content-Type、响应时间，返回结构化结果。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/extensions/ext_blueprint.py`
- MDN HTTP 文档：https://developer.mozilla.org/zh-CN/docs/Web/HTTP
- RFC 7231（HTTP/1.1 语义）：https://datatracker.ietf.org/doc/html/rfc7231

---

**文档版本**：v1.0
**最后更新**：2026-07-13