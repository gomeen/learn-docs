# 7.3 JWT 机制与无状态认证

> 理解 JWT（JSON Web Token）的结构与无状态认证原理，能正确使用 JWT 设计 API 鉴权。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 JWT 的三段式结构（Header / Payload / Signature）
- 掌握 JWT 的签名与验证流程
- 了解 JWT 的优势与陷阱
- 在 Python/Java 中正确使用 JWT 库

## 📚 前置知识

- [非对称加密](../06-encryption/02-asymmetric.md) / [哈希与 HMAC](../06-encryption/03-hash.md)
- Base64 编码
- [7.2 Session 与 Cookie](./02-session-cookie.md)

## 1. 核心概念

### 1.1 什么是 JWT？

JWT（JSON Web Token）是一种**自包含**的令牌格式，载荷信息编码在 Token 中，无需服务端存储。

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

↑ Header         ↑ Payload (Claims)                                    ↑ Signature
```

### 1.2 JWT 三段式结构

#### Header（头部）

```json
{
  "alg": "HS256",      // 签名算法：HMAC-SHA256
  "typ": "JWT"          // Token 类型
}
```
Base64Url 编码后：`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9`

#### Payload（载荷 / Claims）

```json
{
  "sub": "1234567890",   // subject: 用户 ID
  "name": "John Doe",
  "iat": 1516239022,      // issued at: 签发时间
  "exp": 1516242622,      // expiration: 过期时间
  "iss": "example.com",   // issuer: 签发方
  "aud": "client-id"      // audience: 受众
}
```

**Claims（声明）分类**：

| 类型 | 字段 | 含义 |
|------|------|------|
| **Registered** | `iss`, `sub`, `aud`, `exp`, `iat`, `nbf`, `jti` | 标准字段 |
| **Public** | 自定义但需要在 IANA 注册 | 公开声明 |
| **Private** | 自定义（如 `user_role`）| 内部使用 |

#### Signature（签名）

```
HMACSHA256(
  base64url(header) + "." + base64url(payload),
  secret
)
```

**签名目的**：保证 Token 不被篡改。服务端验证签名，发现篡改直接拒绝。

### 1.3 JWT 工作流程

```
1. 用户登录 → 服务端校验用户名密码
2. 服务端生成 JWT（包含 user_id、exp 等）
3. 返回 JWT 给客户端
4. 客户端存储 JWT（localStorage / cookie）
5. 后续请求带 Authorization: Bearer <JWT>
6. 服务端验证签名 + 解析 claims → 识别用户
```

### 1.4 JWT 签名算法

| 算法 | 类型 | 使用场景 |
|------|------|---------|
| **HS256** | HMAC + 共享密钥 | 单服务、对称场景 |
| **RS256** | RSA 非对称 | 多服务、需离线验证 |
| **ES256** | ECDSA 非对称 | 高性能、移动端 |
| **none** | **无签名** | **❌ 永远不要用！** |

### 1.5 JWT 的优势 vs 陷阱

#### 优势

- **无状态**：服务端无需存储会话，水平扩展简单
- **跨域友好**：Bearer Token，无 Cookie 跨域问题
- **自包含**：Token 本身携带用户信息，无需查询 DB

#### 陷阱

- **不能撤销**：Token 签发后，在过期前一直有效
- **体积大**：每次请求都带，可能比 SessionID 大几倍
- **敏感数据泄露**：Payload 仅 Base64 编码，**任何人都能解码看内容**
- **密钥泄露即全完**：HS256 密钥泄露 = 攻击者能签发任意 Token

### 1.6 JWT 的安全实践

| 实践 | 说明 |
|------|------|
| **HTTPS 强制** | Token 在网络上明文传输，必须 HTTPS |
| **短过期 + 刷新** | Access Token 15 分钟 + Refresh Token 7 天 |
| **不存敏感数据** | Payload 仅存 user_id、role 等非敏感字段 |
| **HttpOnly Cookie** | 存 Cookie 防 XSS 偷 Token |
| **黑名单** | 主动撤销时把 Token jti 加入 Redis 黑名单 |
| **alg 校验** | 严格指定算法（防 `alg: none` 攻击）|

### 1.7 dify 和 ruoyi 的 JWT 使用

| 项目 | JWT 使用 |
|------|---------|
| **dify** | API Key 用 JWT 风格签名（`libs/jws.py`）|
| **ruoyi** | 服务端不用 JWT，用 Redis 存 Token |

## 2. 代码示例

### 2.1 完整 JWT 签发与验证（PyJWT）

```python
# 文件：jwt_demo.py
# 完整的 JWT 签发、验证、刷新流程
import os
import time
from datetime import datetime, timedelta, timezone

import jwt
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET_KEY = os.environ["JWT_SECRET"]

# Token 过期时间配置
ACCESS_TOKEN_TTL = timedelta(minutes=15)      # 短
REFRESH_TOKEN_TTL = timedelta(days=7)          # 长

# 模拟用户
USERS = {"admin": "secret123"}


def create_access_token(user_id: str) -> str:
    """签发 Access Token（短期）"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,                # 用户 ID
        "iat": now,                    # 签发时间
        "exp": now + ACCESS_TOKEN_TTL, # 过期时间
        "type": "access",              # 区分 token 类型
        "iss": "example.com",          # 签发方
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """签发 Refresh Token（长期）"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL,
        "type": "refresh",
        "jti": os.urandom(16).hex(),   # 唯一 ID（用于撤销）
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token: str, expected_type: str) -> dict:
    """验证 Token"""
    try:
        # ✅ 关键：algorithms=["HS256"] 必须显式指定，防 alg: none 攻击
        payload = jwt.decode(
            token, SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "type"]},
        )
        if payload["type"] != expected_type:
            raise jwt.InvalidTokenError(f"expected {expected_type}, got {payload['type']}")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("token expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"invalid token: {e}")


# 模拟 Token 黑名单（生产用 Redis）
REVOKED: set[str] = {}


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if USERS.get(username) != password:
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({
        "access_token": create_access_token(username),
        "refresh_token": create_refresh_token(username),
        "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
    })


@app.route("/api/profile")
def profile():
    """受保护的接口"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401

    token = auth[7:]
    try:
        payload = verify_token(token, "access")
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    # 检查黑名单
    if payload.get("jti") in REVOKED:
        return jsonify({"error": "token revoked"}), 401

    return jsonify({"user": payload["sub"]})


@app.route("/api/refresh", methods=["POST"])
def refresh():
    """用 Refresh Token 换新 Access Token"""
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    try:
        payload = verify_token(refresh_token, "refresh")
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    if payload.get("jti") in REVOKED:
        return jsonify({"error": "refresh token revoked"}), 401

    # ✅ 签发新 Access Token（Refresh Token 可以保持不变）
    return jsonify({
        "access_token": create_access_token(payload["sub"]),
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    """登出：把 Token 加入黑名单"""
    auth = request.headers.get("Authorization", "")
    token = auth[7:]
    try:
        payload = verify_token(token, "access")
        if payload.get("jti"):
            REVOKED.add(payload["jti"])
    except ValueError:
        pass
    return jsonify({"ok": True})
```

### 2.2 常见攻击：alg: none 与密钥混淆

```python
# 文件：jwt_attacks.py
# JWT 常见攻击演示
import jwt

# ❌ 攻击 1：alg: none 攻击
# 攻击者构造 Token：{"alg": "none", "typ": "JWT"}
# 服务端如果接受 "none" 算法 = 完全无验证
token_attack = jwt.encode(
    {"sub": "admin", "exp": 9999999999},
    key="",  # 不需要密钥
    algorithm="none",
)
print(f"伪造的 Token: {token_attack}")
# 防御：严格指定 algorithms=["HS256"]，不接受其他算法

# ❌ 攻击 2：RS256 → HS256 密钥混淆
# 攻击者把 alg 改成 HS256，用公钥当 HMAC 密钥
# 服务端如果用公钥验证 HS256 = 灾难！
# 防御：服务端根据 alg 选择正确的密钥和验证方法
```

### 2.3 JWT 中间件

```python
# 文件：jwt_middleware.py
# 通用 JWT 认证装饰器
from functools import wraps
from flask import request, g, abort
import jwt

def jwt_required(secret: str, algorithm: str = "HS256"):
    """JWT 认证装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                abort(401, "missing bearer token")

            token = auth[7:]
            try:
                payload = jwt.decode(
                    token, secret,
                    algorithms=[algorithm],  # ✅ 严格指定算法
                    options={"require": ["exp", "sub"]},
                )
            except jwt.ExpiredSignatureError:
                abort(401, "token expired")
            except jwt.InvalidTokenError:
                abort(401, "invalid token")

            # 把用户信息存到 g
            g.user_id = payload["sub"]
            g.token_claims = payload

            return f(*args, **kwargs)
        return wrapper
    return decorator

# 使用
@app.route("/api/data")
@jwt_required(SECRET_KEY)
def get_data():
    return {"user": g.user_id, "data": [...]}
```

## 3. dify 仓库源码解读

### 3.1 dify 的 JWS 实现（API Key 签名）

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（典型 JWS 实现）：

```python
"""
JWS utilities for signing/verifying API key requests.
"""
import hmac
import hashlib
import base64
import json

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def sign_jws(payload: dict, secret: bytes) -> str:
    """JWS 签名：返回 header.payload.signature"""
    header = {"alg": "HS256", "typ": "JWS"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jws(token: str, secret: bytes) -> dict:
    """验证 JWS 签名"""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()

        expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        actual_sig = base64url_decode(signature_b64)

        # ✅ 常数时间比较，防止时序攻击
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("invalid signature")

        return json.loads(base64url_decode(payload_b64))
    except Exception as e:
        raise ValueError(f"invalid jws: {e}")
```

**解读**：
- 第 14-17 行：标准的 `base64url` 编码（URL 安全，无 `=` 填充）
- 第 22-28 行：标准 JWS 三段式签名
- 第 39 行：`hmac.compare_digest` 常数时间比较
- **设计意图**：dify 用 JWS 签名 API Key 请求，让第三方应用可以用 HMAC 密钥自行验证 dify 的回调

### 3.2 ruoyi 的 Token 替代 JWT（Redis 存储）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 71-93）：

```java
private LoginUser buildLoginUserByToken(String token, Integer userType) {
    try {
        OAuth2AccessTokenCheckRespDTO accessToken = oauth2TokenApi.checkAccessToken(token);
        if (accessToken == null) {
            return null;
        }
        // 用户类型不匹配，无权限
        // 注意：只有 /admin-api/* 和 /app-api/* 有 userType，才需要比对用户类型
        // 类似 WebSocket 的 /ws/* 连接地址，是不需要比对用户类型的
        if (userType != null
                && ObjectUtil.notEqual(accessToken.getUserType(), userType)) {
            throw new AccessDeniedException("错误的用户类型");
        }
        // 构建登录用户
        return new LoginUser().setId(accessToken.getUserId()).setUserType(accessToken.getUserType())
                .setInfo(accessToken.getUserInfo()) // 额外的用户信息
                .setTenantId(accessToken.getTenantId()).setScopes(accessToken.getScopes())
                .setExpiresTime(accessToken.getExpiresTime());
    } catch (ServiceException serviceException) {
        // 校验 Token 不通过时，考虑到一些接口是无需登录的，所以直接返回 null 即可
        return null;
    }
}
```

**解读**：
- 第 73 行：调用 `oauth2TokenApi.checkAccessToken(token)` 校验 Token
- 这不是 JWT，而是**基于 Redis 的 Token**——服务端可随时撤销
- 第 88 行：`setExpiresTime` 让 Spring Security 自动检查过期
- **设计意图**：ruoyi 选择了"有状态 Token"路线——牺牲部分无状态特性，换取"可撤销"能力

## 4. 关键要点总结

- JWT = Header.Payload.Signature 三段式，自包含
- **签名算法必须显式指定**（防 `alg: none` 攻击）
- HS256（共享密钥）+ RS256（非对称，公钥可公开）
- **短 Access Token + 长 Refresh Token** 是主流方案
- JWT 优势是无状态，**陷阱是难撤销**——需要黑名单机制
- **不要把敏感数据放 Payload**（任何人都能 Base64 解码看）
- dify 用 JWS（HMAC），ruoyi 用 Redis Token（可撤销）
- JWT 不是银弹——根据业务选择"无状态 JWT"还是"有状态 Token"

## 5. 练习题

### 练习 1：基础（必做）

实现 `create_jwt(payload, secret)` 和 `verify_jwt(token, secret)`：
1. 使用 HMAC-SHA256
2. payload 包含 `sub`、`iat`、`exp`
3. 验证签名 + 检查过期时间
4. 严格指定算法

**参考答案**：见 `solutions/03-jwt-basic.md`

### 练习 2：进阶

JWT 的 `exp` 字段验证存在哪些陷阱？
1. 时钟不同步会导致什么问题？
2. 服务端如何在 Token 过期前主动撤销它？
3. Refresh Token 的"轮换"策略是什么？

### 练习 3：挑战（选做）

为 dify 实现一个"API Key + JWT"组合方案：
1. 用户生成 API Key 时同时生成 JWT Secret
2. 客户端用 Secret 签 JWT，请求带 `Authorization: Bearer <JWT>`
3. 服务端用 Secret 验证签名 + 检查 exp
4. 提供 `/rotate-key` 接口让用户轮换 Secret

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/jws.py`
- `/Users/xu/code/github/dify/api/controllers/service_api/`（服务 API 的 JWT 验证）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/oauth2/`
- RFC 7519（JWT）：https://datatracker.ietf.org/doc/html/rfc7519
- PyJWT 文档：https://pyjwt.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13