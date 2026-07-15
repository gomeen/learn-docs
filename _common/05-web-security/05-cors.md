# 5.5 CORS：跨域资源共享原理

> 理解浏览器的同源策略与 CORS 跨域机制，能正确配置跨域响应头。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解浏览器的"同源策略"与"跨域"的概念
- 掌握 CORS 的预检请求与简单请求的区别
- 能正确配置 `Access-Control-Allow-*` 系列响应头
- 在 Flask/Spring 项目中实现 CORS 中间件

## 📚 前置知识

- HTTP Header 基础
- 浏览器同源策略（Same-Origin Policy）
- [5.1 OWASP Top 10 概览](./01-owasp-top10.md)；Cookie 场景常与 [CSRF](./04-csrf.md) 一起考虑

## 1. 核心概念

### 1.1 什么是同源策略？

**同源** = 协议 + 域名 + 端口 完全相同。

```
https://example.com:443/page1
https://example.com:443/page2  ← 同源
http://example.com:443/page1   ← 不同源（协议不同）
https://api.example.com/page   ← 不同源（域名不同）
https://example.com:8080/page  ← 不同源（端口不同）
```

**同源策略限制**：
- AJAX 请求（XMLHttpRequest / Fetch）跨源会被浏览器拦截
- 但 `<img>`、`<script>`、`<link>`、`<form>` 不受限（历史遗留）

### 1.2 什么是 CORS？

CORS（Cross-Origin Resource Sharing，跨域资源共享）是**服务端**主动声明"我允许哪些跨域请求访问我"的机制。

```
浏览器: GET https://api.example.com/users
Origin: https://web.example.com

服务端: Access-Control-Allow-Origin: https://web.example.com
       Access-Control-Allow-Methods: GET, POST
```

### 1.3 简单请求 vs 预检请求

#### 简单请求（Simple Request）

满足**所有**条件才算简单：
- 方法：`GET` / `HEAD` / `POST`
- Header：`Accept`、`Accept-Language`、`Content-Language`、`Content-Type`（限于 `text/plain`、`multipart/form-data`、`application/x-www-form-urlencoded`）

**流程**：
```
浏览器 ─── GET /users ───→ 服务端
浏览器 ←── 200 OK ─────── 服务端
浏览器 ←── Access-Control-Allow-Origin: https://web.example.com  ← 服务端
```

#### 预检请求（Preflight Request）

不满足简单请求条件时，浏览器**先发一个 OPTIONS 请求**：

```
浏览器 ─── OPTIONS /users ─────────────────────────────→ 服务端
        Origin: https://web.example.com
        Access-Control-Request-Method: DELETE
        Access-Control-Request-Headers: X-Custom-Header

浏览器 ←── 204 No Content ───────────────────────────── 服务端
        Access-Control-Allow-Origin: https://web.example.com
        Access-Control-Allow-Methods: GET, POST, DELETE
        Access-Control-Allow-Headers: X-Custom-Header
        Access-Control-Max-Age: 86400

浏览器 ─── DELETE /users ─────────────────────────────→ 服务端（真正请求）
        Origin: https://web.example.com
```

### 1.4 关键响应头

| Header | 含义 |
|--------|------|
| `Access-Control-Allow-Origin` | 允许的来源（`*` 或具体域名） |
| `Access-Control-Allow-Methods` | 允许的方法 |
| `Access-Control-Allow-Headers` | 允许的自定义 Header |
| `Access-Control-Allow-Credentials` | 是否允许带 Cookie（`true` / `false`） |
| `Access-Control-Max-Age` | 预检结果缓存秒数 |
| `Access-Control-Expose-Headers` | 浏览器 JS 可读取的 Header 列表 |

### 1.5 CORS 的安全陷阱

⚠️ **不要配 `Access-Control-Allow-Origin: *` 且同时允许 Cookie**：

```
Access-Control-Allow-Origin: *           ← 通配符
Access-Control-Allow-Credentials: true   ← 允许 Cookie
```

这是**被禁止的组合**！浏览器会直接拒绝。CORS 规范明确要求：
- `Allow-Credentials: true` 时，`Allow-Origin` 必须是具体域名，不能是 `*`

**正确做法**：
- 开发环境可以用 `*`（不带 Cookie）
- 生产环境必须白名单具体域名

## 2. 代码示例

### 2.1 Flask 实现 CORS 中间件

```python
# 文件：cors_middleware.py
# ✅ 完整 CORS 实现
from flask import Flask, request, make_response

app = Flask(__name__)

# 允许跨域的来源白名单
ALLOWED_ORIGINS = [
    "https://web.example.com",
    "https://admin.example.com",
    "http://localhost:3000",  # 开发环境
]

@app.before_request
def handle_preflight():
    """处理 OPTIONS 预检请求"""
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            resp = make_response("", 204)
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token, Authorization"
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Max-Age"] = "86400"  # 缓存 24 小时
            return resp
        return make_response("", 403)

@app.after_request
def add_cors_headers(response):
    """给所有响应添加 CORS 头"""
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count, X-Request-Id"
        # Vary 必须设置，CDN 缓存时按 Origin 区分
        response.headers["Vary"] = "Origin"
    return response
```

### 2.2 常见错误配置

```python
# 文件：cors_bad.py
# ❌ 反面教材

# ❌ 错误 1：通配符 + 凭据
@app.after_request
def bad_cors_1(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
# 浏览器会拒绝！违反 CORS 规范

# ❌ 错误 2：动态拼接 Origin（不经验证）
@app.after_request
def bad_cors_2(resp):
    origin = request.headers.get("Origin", "*")
    resp.headers["Access-Control-Allow-Origin"] = origin  # 直接信任任何来源
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
# 攻击者可以伪造 Origin: https://evil.com，绕过 CORS

# ❌ 错误 3：缺少 Vary: Origin
@app.after_request
def bad_cors_3(resp):
    resp.headers["Access-Control-Allow-Origin"] = "https://web.example.com"
    return resp
# CDN 缓存会把 web.example.com 的响应发给其他用户，导致其他用户拿到错的头
```

## 3. dify 仓库源码解读

### 3.1 dify 的 CSRF 豁免逻辑（OPTIONS 不校验登录）

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 142-160）：

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
- 第 147 行：`request.method in EXEMPT_METHODS`——`EXEMPT_METHODS` 默认包含 `OPTIONS`，**预检请求不校验登录/CSRF**
- 第 148 行：`dify_config.LOGIN_DISABLED`——测试时关闭所有认证
- **设计意图**：CORS 预检请求（OPTIONS）不带 Cookie 也不带 CSRF Token，必须豁免，否则跨域调用永远失败
- **CORS Header 在哪里？** dify 用 Flask-CORS 库统一配置（通常在 `app.py` / `dify_app.py` 注册）

### 3.2 ruoyi 的 CORS + 全局异常处理（典型 Spring 模式）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 60-63）：

```java
} catch (Throwable ex) {
    CommonResult<?> result = globalExceptionHandler.allExceptionHandler(request, ex);
    ServletUtils.writeJSON(response, result);
    return;
}
```

**解读**：
- 第 61 行：异常被全局处理器捕获
- 第 62 行：用 `ServletUtils.writeJSON` 直接写入响应（绕开 Spring MVC）
- **设计意图**：当 Token 校验失败时，要立即返回 JSON 错误响应，**不能进入 Spring MVC 的视图解析**（否则会被当作页面请求处理，丢失 JSON 内容类型）
- 这与 CORS 的关系：直接返回的 JSON 响应必须带上 CORS Header，否则浏览器跨域时会看不到错误详情

## 4. 关键要点总结

- 同源策略是浏览器的安全基石，CORS 是服务端主动声明的"放行名单"
- **简单请求**直接发，**非简单请求**先发 OPTIONS 预检
- **不要配 `*` + `Allow-Credentials: true`**，会被浏览器拒绝
- 必须**白名单** Origin，不能直接信任请求头
- 响应头要带 `Vary: Origin`，避免 CDN 缓存混淆
- dify 用 Flask-CORS + OPTIONS 豁免，ruoyi 用 Spring WebMvcConfigurer

## 5. 练习题

### 练习 1：基础（必做）

写一个 Flask `@app.route("/api/data")` 接口，要求：
- 只接受 `https://app.example.com` 的跨域请求
- 允许带 Cookie
- 支持自定义 Header `X-Request-Id`
- 用 `curl` 测试预检请求：`curl -X OPTIONS -H "Origin: https://app.example.com" -H "Access-Control-Request-Method: GET"`

**参考答案**：见 `solutions/05-cors-flask.md`

### 练习 2：进阶

解释为什么 `Access-Control-Allow-Origin: *` 与 `Access-Control-Allow-Credentials: true` 不能同时配置。从浏览器规范、CORS 协议设计意图两个角度分析。

### 练习 3：挑战（选做）

实现一个"CORS 安全扫描器"：模拟 OPTIONS 预检请求，分析目标站点的 CORS 响应头，判断是否存在以下风险：
1. 通配符 + 凭据
2. 反射 Origin 头（无白名单）
3. 允许 null origin
4. 缺少 Vary 头

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/dify_app.py`（Flask-CORS 配置位置）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- MDN CORS 文档：https://developer.mozilla.org/zh-CN/docs/Web/HTTP/CORS

---

**文档版本**：v1.0
**最后更新**：2026-07-13