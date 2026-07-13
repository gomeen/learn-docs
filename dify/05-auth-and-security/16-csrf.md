# 5.3.4 CSRF：跨站请求伪造

> 理解 CSRF 的攻击机制，掌握 dify 的双重提交 Cookie 防御方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 CSRF 的攻击原理（Cookie 自动携带）
- 掌握三种防御手段：CSRF Token、SameSite Cookie、Origin 校验
- 能看懂 dify 的 `csrf_token` 实现
- 区分 CSRF 与 XSS 的本质区别

## 📚 前置知识

- 02-session-auth.md
- 15-xss.md

## 1. 核心概念

### 1.1 什么是 CSRF？

CSRF（Cross-Site Request Forgery）= 攻击者诱导**已登录用户**在不知情下向目标网站发起请求。

```
用户已登录 bank.com（Cookie 自动携带）

攻击者诱导用户访问 evil.com：
  <img src="https://bank.com/transfer?to=attacker&amount=1000">

浏览器自动带上 bank.com 的 Cookie → 转账成功！
```

### 1.2 CSRF 的攻击前提

- 用户已登录目标网站（Cookie 有效）
- 目标网站只靠 Cookie 鉴权
- 用户被诱导发起请求（无需用户主动操作）

### 1.3 三种防御手段

**1. CSRF Token**：服务端下发随机 token，前端每次请求把 token 放进请求头。攻击者拿不到这个 token。

**2. SameSite Cookie**：`SameSite=Lax/Strict` 阻止跨站携带 Cookie。

**3. Origin / Referer 校验**：服务端检查请求的 Origin 头是否可信。

### 1.4 dify 的双重提交 Cookie 模式

dify 用 **Synchronizer Token + Double Submit Cookie** 组合：

```
1. 登录成功：set-cookie csrf_token=xxx（前端 JS 可读）
2. 前端发起请求：同时带 Cookie csrf_token 和 Header X-CSRF-Token
3. 服务端：检查 Cookie 和 Header 的值是否一致
```

攻击者在 evil.com 上：可以读到 bank.com 设置的 Cookie（理论上），但无法把值放进 Header 里（浏览器同源策略）。

## 2. 代码示例

### 2.1 简化版 CSRF Token 中间件

```python
import secrets

# 登录时生成 CSRF Token，存到 session
session["csrf_token"] = secrets.token_urlsafe(32)

# 前端发起请求时：
# fetch('/api/transfer', {
#     method: 'POST',
#     headers: { 'X-CSRF-Token': getCookie('csrf_token') },
#     credentials: 'include',  // 自动带 Cookie
# })

# 服务端校验
def verify_csrf(request):
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or cookie_token != header_token:
        raise PermissionError("CSRF token mismatch")
```

### 2.2 常见错误：依赖 SameSite 就够了

```python
# ❌ 错误：只设 SameSite，没用 CSRF Token
resp.set_cookie("session_id", value, httponly=True, samesite="Strict")
# 某些老浏览器不支持 SameSite，或用户关闭浏览器 SameSite 默认值
# → 仍有 CSRF 风险

# ✅ 正确：双保险
resp.set_cookie("session_id", value, httponly=True, samesite="Lax")
# 同时要求前端必须带 X-CSRF-Token
```

## 3. dify 仓库源码解读

### 3.1 CSRF Token 校验函数

**文件位置**：`/Users/xu/code/github/dify/api/libs/token.py`
**核心代码**（行 182-210）：

```python
def check_csrf_token(request: Request, user_id: str) -> None:
    """校验 CSRF Token：检查 Header 与 Cookie 一致。"""
    if request.method in EXEMPT_METHODS:
        return

    auth_token = extract_access_token(request)
    if not auth_token:
        return  # 未登录无需 CSRF

    csrf_token = extract_csrf_token(request)              # 从 Header
    csrf_token_from_cookie = extract_csrf_token_from_cookie(request)  # 从 Cookie

    if csrf_token != csrf_token_from_cookie:
        raise Unauthorized("CSRF token mismatch.")

    if not csrf_token:
        raise Unauthorized("CSRF token missing.")

    verified = PassportService().verify(csrf_token)
    if not verified:
        raise Unauthorized("CSRF token invalid.")
```

**解读**：
- 第 3-4 行：OPTIONS / GET 等方法无需 CSRF（按 W3C CORS 规范）
- 第 6-8 行：未登录的用户无需 CSRF 检查（没敏感操作可做）
- 第 10-13 行：**核心**：Header 中的 `X-CSRF-Token` 必须等于 Cookie 中的值
- 第 14-16 行：值非空校验
- 第 18-20 行：`PassportService().verify(csrf_token)` 服务端再验一次签名，确保 Token 不是伪造的
- **三重防护**：Header == Cookie + 签名验证 + 异常方法豁免

### 3.2 dify 的 CSRF Token Cookie 设置

**文件位置**：`/Users/xu/code/github/dify/api/libs/token.py`
**核心代码**（行 122-145）：

```python
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
- 第 4-7 行：Cookie 名（如 `csrf_token`）+ 同 access_token 的过期时间
- 第 7 行：**故意 `httponly=False`**，让前端 JS 能读到 Cookie 值
- 第 8 行：`secure=is_secure(request)` 生产环境 HTTPS 才发
- 第 9 行：`SameSite=Lax` 阻止跨站 GET 携带
- **设计意图**：csrf_token 必须能从前端读出来塞进 Header，否则双提交模式不成立

### 3.3 login_required 中触发 CSRF 校验

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 143-162）：

```python
    @wraps(func)
    def decorated_view(*args: Any, **kwargs: Any) -> R | Response:
        if request.method in EXEMPT_METHODS or dify_config.LOGIN_DISABLED:
            return current_app.ensure_sync(func)(*args, **kwargs)

        user = _resolve_current_user()
        if user is None or not user.is_authenticated:
            unauthorized_response: Response = _get_login_manager().unauthorized()
            return unauthorized_response
        g._login_user = user
        # we put csrf validation here for less conflicts
        # TODO: maybe find a better place for it.
        check_csrf_token(request, user.id)
        return current_app.ensure_sync(func)(*args, **kwargs)

    return decorated_view
```

**解读**：
- 第 13 行：`check_csrf_token(request, user.id)` —— **登录态校验后立刻做 CSRF 校验**
- 第 14 行：注释说明这是为了避免与其他地方冲突，把 CSRF 集中到这里
- **关键设计**：所有受保护接口自动获得 CSRF 防护，开发者无需手动添加

## 4. 关键要点总结

- CSRF = 攻击者诱导已登录用户发起请求
- **根本防御**：CSRF Token（攻击者拿不到）
- dify 用**双重提交 Cookie** 模式：Cookie + Header 双通道，值必须相等
- csrf_token Cookie **故意不设 HttpOnly**，让前端 JS 能读取
- `login_required` 装饰器内置 CSRF 校验，业务代码零感知
- `SameSite=Lax` 是额外保险，配合 CSRF Token 双重防御

## 5. 练习题

### 练习 1：基础（必做）

用 Flask 写一个简化版 CSRF 校验装饰器：要求 POST/PUT/DELETE 请求的 `X-CSRF-Token` 头必须等于 Cookie 中的 `csrf_token`。

### 练习 2：进阶

阅读 `api/libs/token.py:182-210`，解释 dify 的 CSRF 校验为什么"未登录用户无需 CSRF 检查"？这种短路逻辑有什么好处？

### 练习 3：挑战（选做）

设计 **CSRF Token 一次性使用**：每次校验成功后立即作旧，下一次请求必须用新 token（与 Session 模式结合）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/token.py`
- `/Users/xu/code/github/dify/api/libs/login.py`
- OWASP CSRF 防护：https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- SameSite Cookie：https://web.dev/articles/samesite-cookies-explained

---

**文档版本**：v1.0
**最后更新**：2026-07-13