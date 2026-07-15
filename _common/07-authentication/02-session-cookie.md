# 7.2 Session 与 Cookie 认证

> 理解 Web 应用最经典的认证机制：服务器 Session + 浏览器 Cookie。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Session/Cookie 的工作原理与生命周期
- 区分服务端 Session 和客户端 JWT
- 正确配置 Cookie 的安全属性（HttpOnly、Secure、SameSite）
- 识别 dify 和 ruoyi 的会话管理实现

## 📚 前置知识

- HTTP 协议基础（Header、Cookie）
- 7.1 HTTP 认证基础
- Flask-Login 或类似框架基础

## 1. 核心概念

### 1.1 什么是 Cookie？

Cookie 是服务端发给浏览器的**小型文本**（≤ 4KB），浏览器后续请求会自动带上。

```
服务端 → Set-Cookie: sessionid=abc123 → 浏览器
浏览器 → Cookie: sessionid=abc123 → 服务端（自动）
```

### 1.2 什么是 Session？

Session 是服务端**保存用户状态**的数据结构。

```
1. 用户登录成功
2. 服务端创建 Session: {"user_id": 123, "expires_at": ...}
3. 生成唯一 SessionID: abc123
4. Set-Cookie: sessionid=abc123 发给浏览器
5. 浏览器后续请求带 Cookie: sessionid=abc123
6. 服务端用 abc123 查找 Session → 识别用户
```

### 1.3 Session 存储方式

| 存储方式 | 优点 | 缺点 |
|---------|------|------|
| **内存** | 快 | 重启丢失、不支持多机 |
| **文件** | 简单 | 多机不同步 |
| **数据库** | 持久化 | 慢 |
| **Redis** | **快 + 多机共享** | 需要额外部署 |
| **加密 Cookie** | 无需服务端存储 | Cookie 大小受限、撤销困难 |

### 1.4 Cookie 安全属性

```http
Set-Cookie: sessionid=abc123; 
            HttpOnly;        ← JS 读不到，防 XSS 偷 Cookie
            Secure;          ← 只在 HTTPS 下发送
            SameSite=Strict; ← 跨站请求不带，防 CSRF
            Path=/;          ← Cookie 作用路径
            Domain=example.com;
            Max-Age=3600;    ← 过期时间
```

| 属性 | 作用 |
|------|------|
| `HttpOnly` | JS 无法读取，防 [XSS](../05-web-security/02-xss.md) |
| `Secure` | 仅 HTTPS，防明文传输 |
| `SameSite=Strict` | 跨站请求不带，防 [CSRF](../05-web-security/04-csrf.md) |
| `Path` / `Domain` | Cookie 作用范围 |
| `Max-Age` / `Expires` | 过期时间 |

### 1.5 会话攻击与防御

| 攻击 | 原理 | 防御 |
|------|------|------|
| **会话固定** | 攻击者给受害者一个已知 SessionID | 登录后**强制更换 SessionID** |
| **会话劫持** | XSS 偷 Cookie / 网络嗅探 | HttpOnly + Secure + HTTPS |
| **会话超时** | 长期有效的会话被滥用 | 合理设置过期时间 |
| **CSRF** | 跨站请求伪造（详见 [04-csrf](../05-web-security/04-csrf.md)） | SameSite + CSRF Token |

### 1.6 dify 和 ruoyi 的会话方案

| 项目 | 会话方案 | 存储 |
|------|---------|------|
| **dify** | Flask-Login + Session | 加密 Cookie 或 [Redis](../01-redis/01-data-structures.md) |
| **ruoyi** | Token (无 Cookie，见 [JWT](./03-jwt.md)) | Redis |

**dify 用 Session**：浏览器场景天然适配，配合 CSRF Token 防护
**ruoyi 用 Token**：前后端分离，移动端友好，天然防 CSRF

## 2. 代码示例

### 2.1 完整 Flask Session 认证

```python
# 文件：flask_session_auth.py
# Flask Session + Cookie 完整认证
import os
import secrets
from datetime import timedelta
from flask import Flask, request, session, redirect, url_for, abort, render_template_string

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]  # 用于签名 Cookie

# Session 安全配置
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,    # JS 读不到
    SESSION_COOKIE_SECURE=True,       # 仅 HTTPS
    SESSION_COOKIE_SAMESITE="Lax",    # 跨站 GET 可带，POST 不带
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),  # 2 小时过期
)

# 模拟用户
USERS = {"admin": "secret123"}

# 模拟 Session 存储（生产用 Redis）
SESSIONS: dict[str, dict] = {}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if USERS.get(username) != password:
            return "invalid credentials", 401

        # ✅ 关键：登录成功生成新 SessionID（防会话固定）
        session.clear()
        session["user_id"] = username
        session["csrf_token"] = secrets.token_urlsafe(32)
        session.permanent = True

        return redirect(url_for("dashboard"))

    return render_template_string("""
        <form method="post">
          <input name="username"><input name="password" type="password">
          <button>登录</button>
        </form>
    """)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return f"Hello, {session['user_id']}!"

@app.route("/logout")
def logout():
    # ✅ 退出时清除服务端 Session
    session.clear()
    return redirect(url_for("login"))
```

### 2.2 加密 Cookie Session（无服务端存储）

```python
# 文件：encrypted_session.py
# 使用 itsdangerous 实现加密 Cookie（无服务端存储）
import os
from datetime import timedelta
from flask import Flask, request, session, abort
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
SECRET_KEY = os.environ["SECRET_KEY"]

# ✅ 加密签名 Session 数据
signer = URLSafeTimedSerializer(SECRET_KEY, salt="session")

def encrypt_session(data: dict) -> str:
    return signer.dumps(data)

def decrypt_session(token: str, max_age: int = 7200) -> dict:
    """解密 + 校验过期（2 小时）"""
    try:
        return signer.loads(token, max_age=max_age)
    except Exception:
        return {}

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    if password != "secret":
        abort(401)

    # ✅ 把 session 数据加密后写入 Cookie
    session_data = {"user_id": username}
    token = encrypt_session(session_data)

    resp = make_response("logged in")
    resp.set_cookie(
        "session", token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=7200,
    )
    return resp

@app.route("/profile")
def profile():
    token = request.cookies.get("session")
    if not token:
        abort(401)
    # ✅ 直接从 Cookie 解密，无需服务端存储
    data = decrypt_session(token)
    if not data:
        abort(401)
    return {"user": data["user_id"]}
```

### 2.3 Flask-Login 装饰器模式

```python
# 文件：flask_login_pattern.py
# 使用 Flask-Login 简化认证
from flask import Flask
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.secret_key = "secret"

login_manager = LoginManager(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route("/login")
def login():
    user = User("admin")
    login_user(user, remember=True)  # 设置 remember=True 可延长会话
    return "logged in"

@app.route("/dashboard")
@login_required  # ✅ 自动检查登录状态
def dashboard():
    return f"Hello, {current_user.id}"

@app.route("/logout")
@login_required
def logout():
    logout_user()  # ✅ 清除 Session
    return "logged out"
```

## 3. dify 仓库源码解读

### 3.1 dify 的 login_required 装饰器（含 CSRF 校验）

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 142-162）：

```python
@wraps(func)
def decorated_view(*args: Any, **kwargs: Any) -> R | Response:
    # The overloads keep Resource methods method-aware for pyrefly while
    # preserving support for plain Flask view functions.
    if request.method in EXEMPT_METHODS or dify_config.LOGIN_DISABLED:
        return current_app.ensure_sync(func)(*args, **kwargs)

    user = _resolve_current_user()
    if user is None or not user.is_authenticated:
        # `DifyLoginManager` guarantees that the registered unauthorized handler
        # is surfaced here as a concrete Flask `Response`.
        unauthorized_response: Response = _get_login_manager().unauthorized()
        return unauthorized_response
    g._login_user = user
    # we put csrf validation here for less conflicts
    # TODO: maybe find a better place for it.
    check_csrf_token(request, user.id)
    return current_app.ensure_sync(func)(*args, **kwargs)
```

**解读**：
- 第 147 行：`EXEMPT_METHODS = {"OPTIONS"}` —— CORS 预检不校验登录
- 第 151 行：未认证返回 401（`_get_login_manager().unauthorized()`）
- 第 156 行：把用户存到 Flask `g._login_user`，全局可访问
- 第 159 行：**CSRF 校验内嵌在 login_required**——所有需要登录的接口自动获得 CSRF 防护
- **设计意图**：dify 把"登录"和"CSRF"绑在一起，业务开发者只需 `@login_required` 一行，就同时获得两层保护

### 3.2 ruoyi 的 Token 替代 Session（前后端分离架构）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 56-69）：

```java
// 2. 设置当前用户
if (loginUser != null) {
    SecurityFrameworkUtils.setLoginUser(loginUser, request);
}

// 继续过滤链
chain.doFilter(request, response);
```

**SecurityFrameworkUtils.setLoginUser 实现**：
```java
public static void setLoginUser(LoginUser loginUser, HttpServletRequest request) {
    // 把 LoginUser 存到 SecurityContext（线程级别）
    SecurityContextHolder.getContext().setAuthentication(loginUser);
    // 同时设置 LoginUser ID 到请求属性（Controller 可读取）
    request.setAttribute(WebFrameworkUtils.ATTR_LOGIN_USER_ID, loginUser.getId());
}
```

**解读**：
- 第 58 行：把用户上下文存到 Spring SecurityContext（线程安全）
- **关键差异**：ruoyi 完全不用 Cookie！每个请求带 `Authorization: Bearer xxx`，服务端只校验 Token 有效性
- **Token 存 Redis**：ruoyi 的 OAuth2 服务把 Token 和用户信息存到 Redis，分布式共享
- **设计意图**：前后端分离架构天然不适合 Cookie（前端跨域），用 Token 模式更灵活

## 4. 关键要点总结

- **Session** 服务端存储 + **Cookie** 客户端标识 = 经典 Web 认证
- Cookie 必须设置 `HttpOnly` + `Secure` + `SameSite`
- **登录成功必须更换 SessionID**（防会话固定）
- 加密 Cookie Session（itsdangerous、JWT）是"无状态"折中方案
- 现代 API 用 Token + Bearer Header 更适合前后端分离
- dify 用 Flask-Login + Session（浏览器场景）
- ruoyi 用 Token + Redis（API 场景）

## 5. 练习题

### 练习 1：基础（必做）

实现 Flask 登录接口：
1. 设置 Session（HttpOnly、Secure、SameSite=Lax）
2. 登录成功更换 SessionID
3. `/dashboard` 验证登录
4. `/logout` 清除 Session

**参考答案**：见 `solutions/02-flask-session.md`

### 练习 2：进阶

分析以下三种会话方案的优劣：
1. 服务端 Session（Redis 存储）
2. 加密 Cookie（无服务端存储）
3. JWT Token

从"撤销能力"、"多机支持"、"性能"、"安全性"四个维度对比。

### 练习 3：挑战（选做）

为 dify 的 `login_required` 装饰器添加"会话超时"功能：
- Session 超过 2 小时无活动自动过期
- 有活动时自动延长（滑动过期）
- 实现"绝对最长会话时间"（即使活跃，超过 8 小时也强制重新登录）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/extensions/ext_login.py`（Flask-Login 配置）
- `/Users/xu/code/github/dify/api/libs/token.py`（CSRF Token 实现）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
- Flask Session 文档：https://flask.palletsprojects.com/en/latest/quickstart/#sessions

---

**文档版本**：v1.0
**最后更新**：2026-07-13