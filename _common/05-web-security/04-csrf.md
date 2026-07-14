# 5.4 CSRF 攻击与防护：同步令牌 / 双重提交 Cookie / SameSite

> 理解 CSRF（跨站请求伪造）的攻击原理，掌握三种主流防御手段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 CSRF 攻击的"借刀杀人"原理
- 掌握同步令牌、双重提交 Cookie、SameSite 三种防御手段
- 识别 dify 中 CSRF Token 的校验位置
- 在 Flask/Django/Spring 项目中正确实施 CSRF 防护

## 📚 前置知识

- HTTP Cookie / Session 基础
- 跨域与同源策略
- 5.1 OWASP Top 10 概览

## 1. 核心概念

### 1.1 什么是 CSRF？

CSRF（Cross-Site Request Forgery，跨站请求伪造）指攻击者**诱导已登录的用户**，在不知情的情况下向目标站点发起请求。

**核心思想**："借刀杀人"——攻击者利用用户已认证的浏览器自动携带 Cookie 的特性。

```
1. 用户登录 bank.com，浏览器获得 sessionid Cookie
2. 用户访问 evil.com（攻击者控制的网站）
3. evil.com 包含：<img src="http://bank.com/transfer?to=attacker&amount=10000">
4. 浏览器自动带上 bank.com 的 Cookie 发起请求
5. bank.com 认为是合法请求 → 转账成功
```

### 1.2 CSRF 攻击条件

1. 用户已登录目标站点
2. 目标站点用 Cookie 做会话（且 Cookie 会被浏览器自动携带）
3. 攻击者能诱骗用户访问第三方站点
4. 目标站点没有 CSRF 防护

### 1.3 CSRF vs XSS

| 维度 | CSRF | XSS |
|------|------|-----|
| 目标 | 利用用户身份发起请求 | 在用户浏览器执行任意 JS |
| 攻击者能做什么 | 借用户身份发请求（不能读取响应）| 偷 Cookie、劫持会话、篡改 DOM |
| 是否需要用户登录 | 是 | 否 |
| 防御重点 | 验证请求来源 | 输出编码 |

### 1.4 三大防御手段

#### 1.4.1 同步令牌（Synchronizer Token Pattern）

```
1. 用户访问表单页面，服务端生成随机 token 存入 Session
2. 把 token 嵌入表单隐藏字段：<input type="hidden" name="csrf_token" value="abc123">
3. 提交表单时，token 一起 POST
4. 服务端对比 Session 中的 token 和表单中的 token，一致才放行
```

**优点**：最安全，是业界标准
**缺点**：需要 Session，无法用于纯无状态 API

#### 1.4.2 双重提交 Cookie（Double Submit Cookie）

```
1. 服务端下发 Set-Cookie: csrf_token=xyz (Cookie + 后续 JS 读取)
2. 前端 JS 把 csrf_token 放到请求 Header: X-CSRF-Token: xyz
3. 服务端对比 Cookie 和 Header 中的 token，必须一致才放行
```

**优点**：无状态，无需 Session
**缺点**：依赖前端 JS 读取 Cookie（XSS 攻击可绕过）

#### 1.4.3 SameSite Cookie

```
Set-Cookie: sessionid=xxx; SameSite=Strict
Set-Cookie: sessionid=xxx; SameSite=Lax  (默认)
```

| 值 | 行为 |
|----|------|
| `Strict` | 任何跨站请求都不带 Cookie |
| `Lax` | 跨站 GET（导航链接）可带，但 POST 不带 |
| `None` | 始终带 Cookie（必须配合 Secure）|

**优点**：浏览器层面防护，无需改业务代码
**缺点**：依赖浏览器支持，老浏览器不生效

### 1.5 实际项目中的组合策略

dify 和 ruoyi 都采用：**SameSite Cookie + 同步令牌**，双重保险。

## 2. 代码示例

### 2.1 漏洞示例：没有 CSRF 防护的转账

```python
# 文件：csrf_vulnerable.py
# ❌ 故意写错的 CSRF 漏洞示例
from flask import Flask, request, session

app = Flask(__name__)
app.secret_key = "demo"

@app.route("/transfer", methods=["POST"])
def transfer():
    # ❌ 只验证了 Cookie 中的 session，没有验证 CSRF Token
    if "user_id" not in session:
        return "未登录", 401

    to = request.form["to"]
    amount = request.form["amount"]

    # 执行转账...
    return f"已转账 {amount} 元给 {to}"

# 攻击：恶意网站包含
# <form action="http://bank.com/transfer" method="POST">
#   <input name="to" value="attacker">
#   <input name="amount" value="10000">
# </form>
# <script>document.forms[0].submit()</script>
# 用户在 bank.com 已登录，浏览器自动带 Cookie → 转账成功
```

### 2.2 修正：同步令牌模式

```python
# 文件：csrf_secure.py
# ✅ 正确做法：同步令牌 + SameSite Cookie
import os
from flask import Flask, request, session, abort
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(32)

def generate_csrf_token() -> str:
    if "_csrf_token" not in session:
        session["_csrf_token"] = os.urandom(32).hex()
    return session["_csrf_token"]

def csrf_protect(f):
    """CSRF 防护装饰器：验证请求中的 Token 与 Session 中一致"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return f(*args, **kwargs)

        # 从 Header 或表单字段获取 Token
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        session_token = session.get("_csrf_token")

        # ✅ 关键校验：Token 必须存在且一致
        if not token or token != session_token:
            abort(403, "CSRF token invalid")

        return f(*args, **kwargs)
    return wrapper

@app.route("/transfer", methods=["POST"])
@csrf_protect
def transfer():
    if "user_id" not in session:
        return "未登录", 401
    to = request.form["to"]
    amount = request.form["amount"]
    return f"已转账 {amount} 元给 {to}"

@app.after_request
def set_secure_cookie(response):
    """设置 SameSite Cookie"""
    for cookie_name in session:
        # Flask 通过 SESSION_COOKIE_SAMESITE 配置实现
        pass
    return response

# ✅ 配置：Session Cookie 必须设 SameSite=Lax 或 Strict
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True  # 生产必须 HTTPS
```

### 2.3 双重提交 Cookie 模式（无状态 API）

```python
# 文件：double_submit.py
# ✅ 无状态 API：双重提交 Cookie 模式
import os
import hmac
from flask import Flask, request, abort, make_response

app = Flask(__name__)
app.secret_key = os.urandom(32)

# 用于签名 CSRF Token（防止攻击者伪造 Cookie）
def sign_csrf_cookie() -> str:
    random = os.urandom(16).hex()
    sig = hmac.new(app.secret_key, random.encode(), "sha256").hexdigest()[:16]
    return f"{random}.{sig}"

def verify_csrf_cookie(token: str) -> bool:
    try:
        random, sig = token.split(".")
        expected = hmac.new(app.secret_key, random.encode(), "sha256").hexdigest()[:16]
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False

@app.route("/login")
def login():
    """登录后下发 CSRF Cookie"""
    # 假设登录成功，设置会话 Cookie
    resp = make_response("logged in")
    # ✅ Set-Cookie: csrf_token=xxx; Path=/; Secure; SameSite=Lax
    resp.set_cookie("csrf_token", sign_csrf_cookie(), samesite="Lax", httponly=False)
    # httponly=False 是关键：前端 JS 必须能读
    return resp

@app.route("/api/transfer", methods=["POST"])
def transfer():
    """API 接口：要求 Header 中的 Token 与 Cookie 一致"""
    cookie_token = request.cookies.get("csrf_token", "")
    header_token = request.headers.get("X-CSRF-Token", "")

    # ✅ 关键：Cookie 必须签名防伪造 + Header 与 Cookie 必须一致
    if not verify_csrf_cookie(cookie_token) or cookie_token != header_token:
        abort(403, "CSRF check failed")

    return "transfer ok"
```

## 3. dify 仓库源码解读

### 3.1 dify 的 login_required 装饰器内置 CSRF 校验

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
- 第 147 行：`EXEMPT_METHODS` 是 `{"OPTIONS"}`，CORS 预检不校验登录/CSRF
- 第 156 行：`g._login_user = user` 把登录用户存到 Flask 的 `g` 对象（请求作用域）
- 第 159 行：**核心 CSRF 校验**——调用 `check_csrf_token(request, user.id)` 验证 Token
- **设计意图**：所有需要登录的接口都加 `@login_required`，自动获得 CSRF 防护，开发者无需手动写

### 3.2 ruoyi 的 Token 过滤器（无 CSRF，但有 SameSite 兜底）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 44-46）：

```java
String token = SecurityFrameworkUtils.obtainAuthorization(request,
        securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
```

**TokenProperties 中默认的 Header 配置**（`SecurityProperties.java`）：
```java
@Data
public class SecurityProperties {
    private String tokenHeader = "Authorization";  // 默认从 Authorization Header 读取
    private String tokenParameter = "token";        // 也允许从 ?token=xxx 读取（用于 WebSocket）
    private String mockSecret = "mock";             // Mock 登录密钥
    // ... 其他配置
}
```

**解读**：
- ruoyi 默认用 **Authorization Header** 传递 Token（不是 Cookie），天然防 CSRF
- 因为 CSRF 攻击依赖 Cookie 自动携带，而 Header 中的 Token 必须由 JS 显式设置，浏览器跨站时无法自动加
- **设计意图**：ruoyi 走的是"用 Header 不用 Cookie"的路子，从根本上规避 CSRF 问题

## 4. 关键要点总结

- CSRF 利用浏览器自动携带 Cookie 的特性，让用户在不知情下发起请求
- **三种防御**：同步令牌（最安全）、双重提交 Cookie（无状态）、SameSite Cookie（兜底）
- dify 用 Flask Session + 同步令牌，所有 `@login_required` 装饰器自动校验 CSRF
- ruoyi 用 Authorization Header 传递 Token，**天然防 CSRF**
- **绝不能只依赖 Referer / Origin 校验**——可以被绕过或缺失
- 即使有 CSRF Token，也不能放松 XSS 防护（XSS 可读取 Token）

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Flask 装饰器 `@csrf_protect`，要求：
- 从 `X-CSRF-Token` Header 中读取 Token
- 从 Flask `session["csrf_token"]` 读取对比
- 使用 `hmac.compare_digest` 常数时间比较
- 不匹配返回 403

**参考答案**：见 `solutions/04-csrf-decorator.md`

### 练习 2：进阶

阅读 ruoyi 的 `LoginUser.java` 与 `TokenAuthenticationFilter.java`，分析 ruoyi 为什么选择"Authorization Header"模式而非 Cookie 模式，并写一份对比报告（从 CSRF、XSS、移动端兼容性三个维度）。

### 练习 3：挑战（选做）

为 dify 写一个**CSRF 漏洞扫描器**：扫描 `api/controllers/` 下的所有路由，找出没有 `@login_required` 装饰器但修改了数据的接口（POST/PUT/DELETE），输出报告。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/libs/token.py`（`check_csrf_token` 实现）
- `/Users/xu/code/github/dify/api/extensions/ext_login.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`
- OWASP CSRF 防护手册：https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13