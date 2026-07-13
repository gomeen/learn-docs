# 5.3.6 CORS：跨域资源共享

> 理解 CORS 机制，掌握前后端分离架构下的跨域配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解浏览器的同源策略（Same-Origin Policy）
- 掌握 CORS 预检请求（preflight）的工作机制
- 理解 CORS 响应头的关键字段
- 能在 dify 中识别 CORS 配置点

## 📚 前置知识

- 15-xss.md
- HTTP 协议基础

## 1. 核心概念

### 1.1 同源策略

浏览器默认禁止一个域名的 JS 读取另一个域名的响应。同源 = **协议 + 域名 + 端口** 全部相同。

```
✅ 同源：
  https://app.dify.ai/page1
  https://app.dify.ai/page2

❌ 跨域：
  https://app.dify.ai  →  http://api.dify.ai  （协议不同）
  https://app.dify.ai  →  https://api.dify.ai  （子域不同）
```

### 1.2 CORS 如何放行跨域？

服务端在响应头中声明 `Access-Control-Allow-Origin: https://app.dify.ai`，浏览器看到才会放行。

```
浏览器 → OPTIONS https://api.dify.ai/users  （preflight 预检）
       ← Access-Control-Allow-Origin: https://app.dify.ai
       ← Access-Control-Allow-Methods: GET, POST, PUT, DELETE
       ← Access-Control-Allow-Headers: Authorization, Content-Type

浏览器 → GET https://api.dify.ai/users  （真实请求）
       ← 200 OK + 数据
```

### 1.3 关键 CORS 响应头

| Header | 含义 |
|--------|------|
| `Access-Control-Allow-Origin` | 允许的源（`https://app.dify.ai` 或 `*`） |
| `Access-Control-Allow-Methods` | 允许的方法 |
| `Access-Control-Allow-Headers` | 允许的自定义头 |
| `Access-Control-Allow-Credentials` | 是否允许 Cookie |
| `Access-Control-Max-Age` | 预检缓存时间 |

### 1.4 危险配置：通配符 + 凭证

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```

**这是非法组合**！浏览器会拒绝放行。带凭证的 CORS 必须指定明确域名。

## 2. 代码示例

### 2.1 Flask 中配置 CORS

```python
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# 全局配置
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://app.dify.ai"],  # 明确域名，不用 *
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-CSRF-Token"],
        "supports_credentials": True,         # 允许带 Cookie
        "max_age": 3600,
    }
})


@app.route("/api/users")
def users():
    return {"users": [...]}
```

### 2.2 自定义 CORS 中间件（不依赖 flask_cors）

```python
from flask import make_response, request

ALLOWED_ORIGINS = {"https://app.dify.ai", "https://staging.dify.ai"}

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-CSRF-Token"
    return response


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return make_response("", 204)
```

### 2.3 常见错误：`Access-Control-Allow-Origin: *` + Cookie

```python
# ❌ 错误：通配符 + 凭证，浏览器拒绝
resp.headers["Access-Control-Allow-Origin"] = "*"
resp.headers["Access-Control-Allow-Credentials"] = "true"

# ✅ 正确：明确域名 + 凭证
resp.headers["Access-Control-Allow-Origin"] = "https://app.dify.ai"
resp.headers["Access-Control-Allow-Credentials"] = "true"
```

## 3. dify 仓库源码解读

### 3.1 CORS 在 dify 中的实现位置

dify 用 Flask + flask_cors（或自实现）。**注意：CORS 配置通常在应用初始化阶段**（`dify_app.py`），而非业务代码中。

**文件位置**：`/Users/xu/code/github/dify/api/dify_app.py`（应用工厂）
**核心代码**（典型结构）：

```python
from flask_cors import CORS
from configs import dify_config

def create_app() -> Flask:
    app = Flask(__name__)
    # CORS 配置：基于环境变量
    if dify_config.CORS_ALLOWED_ORIGINS:
        origins = dify_config.CORS_ALLOWED_ORIGINS.split(",")
    else:
        origins = "*"

    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        supports_credentials=True,
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    return app
```

**解读**：
- 第 6-9 行：从环境变量读允许的 Origin 列表
- 第 11-16 行：所有路径都启用 CORS
- 第 14 行：`supports_credentials=True` 允许带 Cookie
- 第 15 行：明确列出允许的请求头（含 `X-CSRF-Token`）
- **设计意图**：CORS 集中在应用工厂层，业务代码无需关心

### 3.2 前端携带 Cookie 跨域

**说明**：dify 前端通过 `credentials: 'include'` 携带 Cookie：

```typescript
// web/src/.../client.ts
fetch("https://api.dify.ai/v1/apps", {
    credentials: "include",  // 跨域时携带 Cookie
    headers: { "X-CSRF-Token": getCookie("csrf_token") },
});
```

**解读**：
- `credentials: 'include'` 让浏览器把 `app.dify.ai` 的 Cookie 一起发给 `api.dify.ai`
- 但只有当服务端 CORS 配置了对应 Origin 才允许
- **配合 CSRF Token**：CORS 防跨域读取响应，CSRF Token 防跨域发起写操作

## 4. 关键要点总结

- 同源策略阻止跨域读取；CORS 是放行机制
- **预检请求**（OPTIONS）：非简单请求必须先发预检
- `Access-Control-Allow-Origin: *` **不能**和凭证（Cookie）共存
- 明确 Origin 列表 = 安全；通配符 = 风险
- dify 的 CORS 集中在应用工厂层，业务代码零感知
- CORS + CSRF Token 共同构成完整的跨域防护

## 5. 练习题

### 练习 1：基础（必做）

用 Flask `after_request` 钩子实现一个 CORS 中间件：仅允许 `https://app.dify.ai` 跨域访问 API，支持凭证和 `X-CSRF-Token` 头。

### 练习 2：进阶

解释 CORS 和 CSRF 的关系：它们防御的是不同的威胁吗？还是同一威胁的不同维度？

### 练习 3：挑战（选做）

设计一个 **动态 CORS 白名单**：根据请求的 Origin 动态查询 DB 是否在允许列表中（支持热更新），同时实现 Origin 缓存减少 DB 查询。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/dify_app.py`
- MDN CORS：https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
- flask-cors：https://flask-cors.readthedocs.io/
- CORS 与 CSRF：https://web.dev/articles/security-cors

---

**文档版本**：v1.0
**最后更新**：2026-07-13