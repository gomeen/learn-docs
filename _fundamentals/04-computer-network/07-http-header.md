# 4.2.4 HTTP Header 详解：Cache-Control / CORS / Cookie

> HTTP Header 是请求和响应的元数据，是后端必掌握的内容。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握常用 HTTP Header 的作用
- 理解 Cache-Control 的缓存策略
- 知道 CORS 的实现原理
- 能在 dify 中识别 Header 的应用

## 📚 前置知识

- 04-http-versions.md
- 06-http-status.md

## 1. 核心概念

### 1.1 请求 Header

| Header | 用途 |
|--------|------|
| **Host** | 目标主机（虚拟主机） |
| **User-Agent** | 客户端标识 |
| **Accept** | 可接受的响应类型 |
| **Accept-Language** | 语言偏好 |
| **Accept-Encoding** | 编码（gzip, deflate, br） |
| **Authorization** | 认证信息 |
| **Cookie** | 客户端 Cookie |
| **Referer** | 来源页面 |
| **If-None-Match** | 协商缓存 |
| **If-Modified-Since** | 协商缓存 |
| **Origin** | 跨域请求源 |

### 1.2 响应 Header

| Header | 用途 |
|--------|------|
| **Content-Type** | 响应类型（MIME） |
| **Content-Length** | 响应大小 |
| **Content-Encoding** | 编码（gzip） |
| **Cache-Control** | 缓存策略 |
| **ETag** | 资源标识 |
| **Last-Modified** | 最后修改时间 |
| **Set-Cookie** | 设置 Cookie |
| **Location** | 重定向目标 |
| **Access-Control-Allow-Origin** | CORS |
| **Server** | 服务器信息 |
| **Date** | 响应时间 |

### 1.3 Cache-Control 详解

```
Cache-Control: max-age=3600, public, must-revalidate
                ↓        ↓       ↓
              缓存时间   公共缓存   必须重新验证
```

**指令**：

| 指令 | 说明 |
|------|------|
| `no-cache` | 必须重新验证（可能命中 304） |
| `no-store` | 不缓存（敏感数据） |
| `public` | 公共缓存（CDN 可缓存） |
| `private` | 私有缓存（仅浏览器） |
| `max-age=N` | 缓存 N 秒 |
| `s-maxage=N` | CDN 缓存 N 秒 |
| `must-revalidate` | 过期后必须重新验证 |

### 1.4 CORS（跨域）

**同源策略**：浏览器要求协议、域名、端口都相同才能访问。

**CORS 解除限制**：

```
请求：
Origin: https://example.com

响应：
Access-Control-Allow-Origin: https://example.com
Access-Control-Allow-Methods: GET, POST
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 3600
```

### 1.5 Cookie 机制

```
响应：
Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Strict; Max-Age=3600

后续请求：
Cookie: session=abc123
```

**属性**：
- **HttpOnly**：JS 不可访问（防 XSS）
- **Secure**：仅 HTTPS
- **SameSite**：跨站策略（防 CSRF）
- **Max-Age / Expires**：过期时间

### 1.6 协商缓存

**ETag + If-None-Match**：
```
首次响应：
ETag: "abc123"

后续请求：
If-None-Match: "abc123"

服务器命中（未修改）：
HTTP/1.1 304 Not Modified
```

**Last-Modified + If-Modified-Since**：
```
首次响应：
Last-Modified: Mon, 13 Jul 2026 12:00:00 GMT

后续请求：
If-Modified-Since: Mon, 13 Jul 2026 12:00:00 GMT

服务器命中：
HTTP/1.1 304 Not Modified
```

## 2. 代码示例

### 2.1 设置 Cache-Control

```python
# 文件：cache_control.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/api/data")
def get_data():
    resp = jsonify({"data": "value"})
    # 公共缓存 1 小时
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp

@app.route("/api/private")
def get_private():
    resp = jsonify({"data": "secret"})
    # 不缓存（敏感数据）
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.route("/api/cached-validate")
def get_cached_validate():
    resp = jsonify({"data": "value"})
    # 必须重新验证（强缓存 + 协商缓存）
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["ETag"] = "abc123"
    return resp
```

### 2.2 配置 CORS

```python
# 文件：cors_demo.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.after_request
def add_cors_headers(resp):
    """添加 CORS 头。"""
    resp.headers["Access-Control-Allow-Origin"] = "https://example.com"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Max-Age"] = "3600"
    return resp

@app.route("/api/data")
def get_data():
    return jsonify({"data": "value"})

@app.route("/api/data", methods=["OPTIONS"])
def options():
    # 预检请求
    return "", 204
```

### 2.3 使用 Cookie

```python
# 文件：cookie_demo.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/login", methods=["POST"])
def login():
    # 设置 session cookie
    resp = jsonify({"status": "ok"})
    resp.set_cookie(
        "session_id",
        "abc123",
        httponly=True,  # JS 不可访问
        secure=True,    # 仅 HTTPS
        samesite="Strict",  # 防 CSRF
        max_age=3600,
    )
    return resp

@app.route("/user")
def get_user():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return jsonify({"error": "Not logged in"}), 401
    # 验证 session
    return jsonify({"user_id": 123})
```

### 2.4 实现 ETag 协商缓存

```python
# 文件：etag_demo.py
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    # 计算响应内容的 hash 作为 ETag
    data = {"id": user_id, "name": f"User {user_id}"}
    body = jsonify(data)
    etag = '"' + hashlib.md5(body.data).hexdigest() + '"'

    # 客户端发送 If-None-Match
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match == etag:
        # 未修改，返回 304
        return "", 304

    body.headers["ETag"] = etag
    body.headers["Cache-Control"] = "private, must-revalidate"
    return body
```

## 3. dify 仓库源码解读

### 3.1 dify 的 CORS 配置

**文件位置**：`/Users/xu/code/github/dify/api/app_factory.py`
**核心代码**（行 50-80）：

```python
from flask import Flask
from flask_cors import CORS

def create_app():
    """dify 应用工厂。

    dify 配置 CORS：
    - 允许 Web 前端跨域访问 API
    - 限制 Origin（不能是 * + credentials）
    """
    app = Flask(__name__)

    # 配置 CORS
    CORS(
        app,
        origins=[
            "http://localhost:3000",     # 开发前端
            "https://cloud.dify.ai",     # 生产前端
            # ... 其他允许的域名
        ],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        supports_credentials=True,
        max_age=3600,
    )

    return app


# dify 的 Cookie 配置：
def configure_session(app):
    """配置 session cookie。"""
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # 防 XSS
    app.config["SESSION_COOKIE_SECURE"] = True     # 仅 HTTPS
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax" # 防 CSRF
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600 * 24 * 7  # 7 天


# dify 的缓存策略：
# - API 响应：通常 no-cache（实时数据）
# - 静态资源：浏览器缓存 + CDN 缓存
# - Embedding 结果：Redis 缓存
# - 工作流状态：Redis 缓存
```

**解读**：
- 第 16 行：限制 Origin 列表（不能用 `*`）
- 第 22 行：支持 credentials（Cookie）
- **设计意图**：CORS 让 Web 前端能调用 API，但限制 Origin 防 CSRF

## 4. 关键要点总结

- **Cache-Control**：缓存策略（max-age、public/private、no-store）
- **CORS**：跨域共享，允许特定 Origin
- **Cookie**：HttpOnly、Secure、SameSite 属性
- **ETag / If-None-Match**：协商缓存（304）
- dify 用 CORS 让前端跨域调用 API

## 5. 练习题

### 练习 1：基础（必做）

用 Flask 写一个 API，配置 Cache-Control 实现 5 分钟缓存。

### 练习 2：进阶

阅读 `api/app_factory.py`，说明 dify 为何限制 Origin 而不是用 `*`。

### 练习 3：挑战（选做）

实现完整的 ETag 协商缓存机制，包括 200 和 304 响应。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/app_factory.py`
- RFC 7234：HTTP 缓存
- MDN HTTP Headers：https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Headers

---

**文档版本**：v1.0
**最后更新**：2026-07-13