# 5.1.2 Cookie 与 Session 认证

> 理解 Web 应用最经典的有状态认证机制，看懂 dify 的 Cookie 策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Cookie 与 Session 的工作原理
- 掌握 dify 登录后下发的三组 Cookie：`access_token`、`refresh_token`、`csrf_token`
- 理解 `HttpOnly`/`Secure`/`SameSite` 三个安全属性的作用
- 能区分"有状态 Session"和"无状态 Token"的差异

## 📚 前置知识

- 01-fundamentals/01-flask-basics.md（Flask 上下文）
- 01-fundamentals/06-async-asyncio.md
- 04-cache-and-queue/02-redis-cache.md

## 1. 核心概念

### 1.1 什么是 Cookie？

Cookie 是**服务端写到浏览器的小文本**，浏览器在后续请求中自动带回。

```
Server → 200 OK + Set-Cookie: session_id=abc123
Browser → Cookie: session_id=abc123
```

Cookie 适合存**会话标识符**，不能存敏感数据（明文可见）。

### 1.2 Session：服务端的会话存储

Session = 服务端为每个用户维护的"状态机"。Cookie 里只存 `session_id`，真正的用户数据存在服务端。

```
┌────────┐                                  ┌──────────────┐
│Browser │ ── Cookie: session_id=abc123 ──→ │ Flask Server │
│        │                                  │              │
│        │ ←── 200 OK ──────────────────── │ Memory/Redis │
└────────┘                                  │ session_abc: │
                                           │ {user:alice} │
                                           └──────────────┘
```

### 1.3 dify 的三组 Cookie

dify 在登录成功后同时下发三个 Cookie，分别承担不同职责：

| Cookie 名 | 类型 | 用途 |
|-----------|------|------|
| `access_token` | HttpOnly + Secure | 短期访问凭证（默认几小时） |
| `refresh_token` | HttpOnly + Secure | 长期刷新凭证（默认 30 天） |
| `csrf_token` | 普通 Cookie | 跨站请求伪造防御（前端可读） |

**设计巧妙之处**：把 `csrf_token` 放在**非 HttpOnly** Cookie，是为了前端 JS 能读到并放进 `X-CSRF-Token` 请求头；而 `access_token` 用 HttpOnly 防止 XSS 偷走。

### 1.4 Cookie 安全三剑客

| 属性 | 作用 |
|------|------|
| `HttpOnly` | JS 无法读取（防 XSS 窃取） |
| `Secure` | 仅 HTTPS 传输（防抓包） |
| `SameSite=Lax/Strict` | 阻止跨站携带（防 CSRF） |

## 2. 代码示例

### 2.1 Flask 中手动设置安全 Cookie

```python
from flask import Flask, make_response, jsonify

app = Flask(__name__)

@app.post("/login")
def login():
    # 登录成功后，下发三组 Cookie
    resp = make_response(jsonify({"result": "success"}))

    # access_token：短期，HttpOnly，前端 JS 读不到
    resp.set_cookie(
        "access_token", value="eyJhbGciOi...",
        max_age=3600, httponly=True, secure=True, samesite="Lax",
    )

    # refresh_token：长期，HttpOnly
    resp.set_cookie(
        "refresh_token", value="rt_abc123...",
        max_age=30 * 86400, httponly=True, secure=True, samesite="Lax",
    )

    # csrf_token：短期，非 HttpOnly（前端 JS 需要读取）
    resp.set_cookie(
        "csrf_token", value="csrf_xyz789",
        max_age=3600, httponly=False, secure=True, samesite="Lax",
    )
    return resp


@app.post("/logout")
def logout():
    resp = make_response(jsonify({"result": "success"}))
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    resp.delete_cookie("csrf_token")
    return resp
```

### 2.2 常见错误：把 Token 放在普通 Cookie

```python
# ❌ 错误：access_token 没设 HttpOnly，XSS 可以直接偷走
resp.set_cookie("access_token", "secret_value")

# ✅ 正确：HttpOnly + Secure 双保险
resp.set_cookie("access_token", "secret_value", httponly=True, secure=True)
```

## 3. dify 仓库源码解读

### 3.1 登录成功下发 Cookie

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
**核心代码**（行 168-181）：

```python
        token_pair = AccountService.login(account=account, session=db.session(), ip_address=extract_remote_ip(request))
        AccountService.reset_login_error_rate_limit(normalized_email)

        # Create response with cookies instead of returning tokens in body
        # response-contract:ignore cookie-bearing Flask response
        response = make_response(
            SimpleResultOptionalDataResponse(result="success").model_dump(mode="json", exclude_none=True)
        )

        set_access_token_to_cookie(request, response, token_pair.access_token)
        set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
        set_csrf_token_to_cookie(request, response, token_pair.csrf_token)

        return response
```

**解读**：
- 第 168 行：`AccountService.login()` 返回一个 `token_pair` 对象（含 access/refresh/csrf 三个 Token）
- 第 177-179 行：分别调用三个工具函数把 Token 写入 Cookie，**不在响应体里返回 Token**——这是关键安全决策：避免 Token 被日志、浏览器历史、前端代码泄露
- **设计意图**：Cookie 是唯一载体，前端不需要处理 Token，浏览器自动管理

### 3.2 Cookie 工具函数

**文件位置**：`/Users/xu/code/github/dify/api/libs/token.py`
**核心代码**（行 96-130）：

```python
def set_access_token_to_cookie(request: Request, response: Response, token: str, samesite: str = "Lax"):
    """Set access token cookie with HttpOnly + Secure (in production)."""
    response.set_cookie(
        COOKIE_NAME_ACCESS_TOKEN,
        value=token,
        max_age=dify_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=is_secure(request),
        samesite=samesite,
    )


def set_refresh_token_to_cookie(request: Request, response: Response, token: str):
    """Set refresh token cookie with HttpOnly + Secure."""
    response.set_cookie(
        COOKIE_NAME_REFRESH_TOKEN,
        value=token,
        max_age=dify_config.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=is_secure(request),
        samesite="Lax",
    )


def set_csrf_token_to_cookie(request: Request, response: Response, token: str):
    """Set CSRF token cookie (NOT HttpOnly so frontend JS can read it)."""
    response.set_cookie(
        COOKIE_NAME_CSRF_TOKEN,
        value=token,
        max_age=dify_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=False,  # 前端需要读取
        secure=is_secure(request),
        samesite="Lax",
    )
```

**解读**：
- 第 6-8 行：`access_token` 三件套：`HttpOnly` + `Secure` + `SameSite=Lax`
- 第 22 行：`csrf_token` 故意 `httponly=False`，让前端 JS 能读到并塞进 `X-CSRF-Token` 头
- 第 24-25 行：TTL 与 Token 本身的过期时间一致，避免 Token 过期但 Cookie 还在
- **安全组合**：HttpOnly 防止 XSS 偷 access_token，CSRF Token 弥补 SameSite 不够强时的 CSRF 防御

## 4. 关键要点总结

- **Session = 服务端状态** + Cookie = 客户端载体；Cookie 只存 ID，不存数据
- dify 用 **三组 Cookie** 分别承担 access/refresh/csrf 三种职责
- `HttpOnly` 防 XSS，`Secure` 防抓包，`SameSite` 防 CSRF
- dify **从不在响应体里返回 Token**，所有凭证仅通过 Cookie 下发
- `csrf_token` 故意不设 HttpOnly，以便前端 JS 读取并放入请求头

## 5. 练习题

### 练习 1：基础（必做）

用 Flask 写一个 `/login` 接口，登录成功后下发 `access_token`（HttpOnly、5 分钟过期）和 `csrf_token`（非 HttpOnly、5 分钟过期），并写一个 `/logout` 接口清空这两个 Cookie。

### 练习 2：进阶

阅读 `api/libs/token.py`，对比 access_token 与 csrf_token 的 Cookie 属性差异，解释为什么 csrf_token 不设 HttpOnly 反而是安全的。

### 练习 3：挑战（选做）

设计一个中间件：当用户连续 5 次访问受保护接口但 Token 过期时，自动用 `refresh_token` 调用 `/refresh-token` 重新下发新 Cookie，无需用户重新登录。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
- `/Users/xu/code/github/dify/api/libs/token.py`
- Flask Cookie 文档：https://flask.palletsprojects.com/en/latest/quickstart/#cookies
- OWASP Cookie 安全：https://owasp.org/www-chapter-vancouver/assets/presentations/2020-01_Attacking_and_Securing_Cookies.pdf
- SameSite 解释：https://web.dev/articles/samesite-cookies-explained

---

**文档版本**：v1.0
**最后更新**：2026-07-13