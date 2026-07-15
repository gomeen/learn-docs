# 7.1 HTTP 认证基础：Basic / Digest / Bearer

> 理解 HTTP 协议的三大认证机制，能为 API 选择合适的认证方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Basic / Digest / Bearer 三种 HTTP 认证的原理
- 区分它们的优缺点和适用场景
- 能在 Flask/Spring 项目中实现 HTTP 认证
- 识别 dify 和 ruoyi 的认证方式选择

## 📚 前置知识

- HTTP 协议基础（Header、状态码）
- Base64 编码
- 后续：[Session/Cookie](./02-session-cookie.md)、[JWT](./03-jwt.md)、[OAuth2](./05-oauth2.md)

## 1. 核心概念

### 1.1 HTTP 认证通用流程

```
1. 客户端发起请求（无凭证）
2. 服务端返回 401 Unauthorized
   Header: WWW-Authenticate: <scheme> realm="..."
3. 客户端用凭证重试
   Header: Authorization: <scheme> <credentials>
4. 服务端验证凭证，返回 200 或 403
```

### 1.2 Basic 认证

```
GET /api/users HTTP/1.1
Authorization: Basic dXNlcjpwYXNz  ← base64("user:pass")
```

**原理**：把 `username:password` Base64 编码后放在 Header。

**优点**：简单，浏览器原生支持（弹窗输入用户名密码）
**缺点**：
- Base64 不是加密，**必须配合 HTTPS**
- 每次请求都带密码，泄露风险高
- 无法注销（除非改密码）

### 1.3 Digest 认证

**原理**：用 MD5/SHA 哈希密码 + 随机数（nonce）防止重放。

```
服务端 401:
WWW-Authenticate: Digest realm="api",
                  nonce="abc123",
                  qop="auth"

客户端请求:
Authorization: Digest username="user",
                       realm="api",
                       nonce="abc123",
                       uri="/api/users",
                       response="<hash>",
                       qop=auth,
                       nc=00000001,
                       cnonce="xyz"
```

**优点**：密码不在网络上明文传
**缺点**：仍用 MD5/SHA-1，已不推荐；现在基本被 HTTPS + Basic 取代

### 1.4 Bearer 认证（现代主流）

```
GET /api/users HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...  ← JWT Token
```

**原理**：服务端发一个 Token 给客户端，客户端每次请求带这个 Token。

**优点**：
- Token 可设置短期过期，降低泄露风险
- 支持撤销、刷新
- 适合无状态 API

**缺点**：
- Token 一旦签发，服务端无法主动失效（除非引入黑名单）
- Token 一旦泄露，攻击者可以冒用（直到过期）

### 1.5 三种方案对比

| 维度 | Basic | Digest | Bearer |
|------|-------|--------|--------|
| 安全性 | 低（依赖 HTTPS） | 中 | 高（短 Token） |
| 性能 | 快 | 中（哈希计算） | 快 |
| 实现复杂度 | 极低 | 中 | 中 |
| 浏览器支持 | ✅ 原生 | ✅ 原生 | ❌ 需 JS |
| 适用场景 | 内部工具、监控 | 几乎不用 | **现代 API 推荐** |

### 1.6 dify 和 ruoyi 的认证方式

| 项目 | 控制台 | 服务 API |
|------|--------|---------|
| **dify** | Flask-Login（Session + Cookie）| API Key + Bearer Token |
| **ruoyi** | Spring Security（Token）| OAuth2 + Bearer Token |

## 2. 代码示例

### 2.1 Basic 认证

```python
# 文件：basic_auth.py
# HTTP Basic 认证
import base64
from flask import Flask, request, abort

app = Flask(__name__)

# 模拟用户数据库
USERS = {"admin": "secret123", "user": "userpass"}

@app.route("/api/users")
def list_users():
    # 1. 解析 Authorization Header
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        # 第一次请求：返回 401 触发浏览器弹窗
        return "", 401, {"WWW-Authenticate": 'Basic realm="API"'}

    # 2. 解码 base64
    try:
        encoded = auth.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode()
        username, _, password = decoded.partition(":")
    except Exception:
        abort(400)

    # 3. 验证
    if USERS.get(username) != password:
        abort(401)

    return {"users": ["alice", "bob"]}

# 测试
# curl -u admin:secret123 http://localhost:5000/api/users
# 浏览器访问 http://localhost:5000/api/users  → 弹窗输入用户名密码
```

### 2.2 Bearer Token 认证（推荐）

```python
# 文件：bearer_auth.py
# HTTP Bearer Token 认证（JWT 风格）
import os
import hmac
import hashlib
import time
from flask import Flask, request, abort, jsonify

app = Flask(__name__)
SECRET = os.urandom(32)

# 模拟 Token 存储（生产用 Redis）
TOKENS: dict[str, dict] = {}

@app.route("/login", methods=["POST"])
def login():
    """登录获取 Token"""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # 验证用户（省略）...
    if username != "admin" or password != "secret":
        abort(401)

    # 签发 Token（生产用 JWT 库）
    token = os.urandom(32).hex()
    TOKENS[token] = {
        "username": username,
        "expires_at": time.time() + 3600,  # 1 小时过期
    }
    return jsonify({"token": token, "expires_in": 3600})

@app.route("/api/users")
def list_users():
    """需要 Bearer Token 的接口"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401

    token = auth.split(" ", 1)[1]

    # 验证 Token
    info = TOKENS.get(token)
    if not info:
        abort(401)
    if time.time() > info["expires_at"]:
        TOKENS.pop(token, None)
        abort(401)

    return jsonify({"users": ["alice", "bob"], "by": info["username"]})

# 测试
# 1. 登录获取 Token
# TOKEN=$(curl -X POST -d '{"username":"admin","password":"secret"}' \
#          -H "Content-Type: application/json" \
#          http://localhost:5000/login | jq -r .token)
#
# 2. 访问 API
# curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/users
```

### 2.3 自定义认证装饰器

```python
# 文件：auth_decorator.py
# 通用 Bearer 认证装饰器
import time
from functools import wraps
from flask import request, abort, g

def require_bearer(token_store: dict, secret: bytes):
    """Bearer Token 认证装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                abort(401, "missing bearer token")

            token = auth[7:]
            info = token_store.get(token)
            if not info or time.time() > info["expires_at"]:
                abort(401, "invalid or expired token")

            # 把用户信息存到 g，方便业务使用
            g.current_user = info["username"]
            g.token = token
            return f(*args, **kwargs)
        return wrapper
    return decorator

# 使用
@app.route("/api/profile")
@require_bearer(TOKENS, SECRET)
def get_profile():
    return jsonify({"user": g.current_user})
```

## 3. dify 仓库源码解读

### 3.1 dify 的 API Key Bearer Token 模式

**文件位置**：`/Users/xu/code/github/dify/api/controllers/service_api/wraps.py`（典型实现）
**核心代码**（推断结构）：

```python
"""
dify 的服务 API 用 API Key + Bearer Token 鉴权
"""
from functools import wraps
from flask import request, abort, g


def validate_api_key(view):
    """验证 API Key（Bearer Token 模式）"""
    @wraps(view)
    def decorated(*args, **kwargs):
        # 1. 提取 Authorization Header
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401)

        api_key = auth[7:]  # 去掉 "Bearer "

        # 2. 查询数据库校验
        from models.dataset import ApiToken
        token_record = db.session.query(ApiToken).filter_by(token=api_key, enabled=True).first()
        if not token_record:
            abort(401)

        # 3. 把租户信息存到 g
        g.current_tenant_id = token_record.tenant_id
        g.current_user = token_record.user

        return view(*args, **kwargs)

    return decorated
```

**解读**：
- 第 13 行：从 `Authorization: Bearer <token>` 提取 API Key
- 第 22 行：DB 查询校验 Token（生产场景会用 Redis 缓存）
- 第 26-27 行：把租户、用户上下文存到 Flask `g`，业务代码直接用
- **设计意图**：dify 的"服务 API"专门给程序调用（不是浏览器），所以走 Bearer Token 模式，天然防 CSRF

### 3.2 ruoyi 的 Authorization Header 认证

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 44-46）：

```java
String token = SecurityFrameworkUtils.obtainAuthorization(request,
        securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
```

**SecurityProperties 默认配置**：
```java
@Data
public class SecurityProperties {
    /**
     * HTTP Header 名称，默认 Authorization
     */
    private String tokenHeader = "Authorization";

    /**
     * URL Query 参数名称（用于 WebSocket 等无法设置 Header 的场景）
     */
    private String tokenParameter = "token";
}
```

**解读**：
- 第 44 行：从 Header（默认 `Authorization`）读取 Token
- 第 44 行：也支持从 URL Query `?token=xxx` 读取（用于 WebSocket）
- 第 46 行：WebSocket 必须用 Query 参数（JS WebSocket API 不支持自定义 Header）
- **设计意图**：ruoyi 统一用 Bearer Token，Header 优先，Query 兜底

## 4. 关键要点总结

- **Basic**：用户名密码 base64 编码，依赖 HTTPS，浏览器原生支持
- **Digest**：MD5/SHA + nonce 防重放，已过时
- **Bearer**：现代 API 标准，配合 JWT/OAuth2 使用
- **HTTPS 是 HTTP 认证的前提**——Basic/Digest 没有 HTTPS 都不安全
- **Token 必须有过期时间**——泄露后影响有限
- dify 用 Flask-Login + API Key 双重认证（控制台 vs API）
- ruoyi 用 Spring Security + Token Authentication Filter

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Flask `/api/private` 接口：
1. 只接受 `Authorization: Bearer <token>` 头
2. Token 是 32 字节随机 hex
3. 登录接口 `/login` 校验用户名密码后签发 Token
4. Token 存内存字典，过期时间 1 小时

**参考答案**：见 `solutions/01-bearer-token.md`

### 练习 2：进阶

对比 Basic 和 Bearer 的安全性：
1. Basic 在没有 HTTPS 的情况下如何被攻击？
2. Bearer Token 泄露后，攻击者能做什么？有什么缓解措施？

### 练习 3：挑战（选做）

实现一个"自定义 Token 协议"：
- Token 格式：`{user_id}.{expires_at}.{signature}`
- Signature = HMAC(secret, `{user_id}.{expires_at}`)
- 服务端无需存储 Token，只需验证签名
- 比较这与 JWT 的异同

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/controllers/service_api/wraps.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`
- RFC 7617（Basic）：https://datatracker.ietf.org/doc/html/rfc7617
- RFC 6750（Bearer）：https://datatracker.ietf.org/doc/html/rfc6750

---

**文档版本**：v1.0
**最后更新**：2026-07-13