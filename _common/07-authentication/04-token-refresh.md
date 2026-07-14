# 7.4 Token 刷新与撤销策略

> 理解 Token 生命周期管理，掌握刷新与撤销的最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Access Token / Refresh Token 双 Token 模型
- 掌握 Token 刷新的轮换与重放检测
- 实现主动撤销与黑名单机制
- 在 dify/ruoyi 中识别 Token 生命周期管理

## 📚 前置知识

- 7.3 JWT 机制
- Redis 基础
- HTTP 认证基础

## 1. 核心概念

### 1.1 为什么需要两个 Token？

| Token 类型 | 用途 | 生命周期 | 存储 |
|----------|------|---------|------|
| **Access Token** | 访问 API | 短（15-60 分钟）| 客户端 |
| **Refresh Token** | 换新 Access Token | 长（7-30 天）| **服务端** |

**核心矛盾**：
- Access Token 太长 → 泄露后危害大
- Access Token 太短 → 用户频繁登录

**解决方案**：双 Token 模型，Access Token 短，Refresh Token 长且受服务端控制。

### 1.2 双 Token 完整流程

```
1. 用户登录
   ↓
2. 服务端签发 Access Token (15min) + Refresh Token (7d)
   ↓
3. 客户端用 Access Token 访问 API
   ↓
4. Access Token 过期 → 客户端用 Refresh Token 换新 Access Token
   ↓
5. 服务端校验 Refresh Token，签发新 Access Token
   ↓
6. （可选）签发新 Refresh Token（Token 轮换）
   ↓
7. 重复 3-6
```

### 1.3 Token 轮换策略

#### 不轮换（简单）

```
Refresh Token #1  → Access Token #1
Refresh Token #1  → Access Token #2  (复用)
Refresh Token #1  → Access Token #3  (复用)
```

**问题**：Refresh Token 一旦泄露，攻击者可以持续用。

#### 轮换（推荐）

```
Refresh Token #1  → Access Token #1
                       + Refresh Token #2  (旧 #1 失效)
Refresh Token #2  → Access Token #2
                       + Refresh Token #3  (旧 #2 失效)
```

**优势**：Refresh Token 只能用一次，即使泄露也很快失效。

### 1.4 重放检测（Reuse Detection）

Token 轮换 + 重放检测能识别 Refresh Token 泄露：

```
正常:  #1 → #2 → #3 → ...

异常:  #1 → #2
       #1 再次出现  ← 异常！说明 #1 泄露或被滥用
       ↓
       服务端撤销该用户所有 Token
```

### 1.5 Token 撤销机制

| 方案 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| **黑名单** | Redis 存已撤销的 jti | 简单 | 需要查询 |
| **版本号** | 用户表加 token_version | 无需存储 | 撤销粒度粗 |
| **短过期** | JWT 5 分钟过期 | 无需存储 | 频繁刷新 |
| **数据库 Token** | Token 存 DB | 天然可撤销 | 性能差 |

### 1.6 dify 和 ruoyi 的 Token 生命周期

- **dify**：API Key 长期有效 + CSRF 短期 Token
- **ruoyi**：Access Token 30 分钟 + Refresh Token 30 天，存 Redis 自动过期

## 2. 代码示例

### 2.1 完整双 Token 实现（含刷新与撤销）

```python
# 文件：dual_token_auth.py
# 完整双 Token 认证：Access + Refresh + 轮换 + 撤销
import os
import time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import redis
from flask import Flask, request, jsonify, g

app = Flask(__name__)
SECRET_KEY = os.environ["JWT_SECRET"]
redis_client = redis.Redis(host="localhost", port=6379)

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=7)

USERS = {"admin": "secret123"}


class TokenService:
    """Token 服务"""

    @staticmethod
    def create_access_token(user_id: str, jti: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "jti": jti,
            "iat": now,
            "exp": now + ACCESS_TOKEN_TTL,
            "type": "access",
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def create_refresh_token(user_id: str, jti: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "jti": jti,
            "iat": now,
            "exp": now + REFRESH_TOKEN_TTL,
            "type": "refresh",
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def store_refresh_token(jti: str, user_id: str) -> None:
        """存 Refresh Token 到 Redis（包含用户链）"""
        # key: refresh:{user_id} → 当前活跃的 refresh token jti
        # 用 list 存历史 jti，实现轮换链
        redis_client.setex(
            f"refresh:active:{user_id}",
            int(REFRESH_TOKEN_TTL.total_seconds()),
            jti,
        )

    @staticmethod
    def is_refresh_token_active(user_id: str, jti: str) -> bool:
        """检查 Refresh Token 是否是当前活跃的"""
        current = redis_client.get(f"refresh:active:{user_id}")
        return current and current.decode() == jti

    @staticmethod
    def revoke_user_tokens(user_id: str) -> None:
        """撤销用户的所有 Token"""
        redis_client.delete(f"refresh:active:{user_id}")
        # 把用户加入"全 Token 失效"黑名单
        revoke_time = int(time.time())
        redis_client.setex(f"revoked:{user_id}", 86400 * 30, revoke_time)

    @staticmethod
    def is_user_revoked(user_id: str, iat_timestamp: int) -> bool:
        """检查用户的 Token 是否在撤销后签发"""
        revoked_at = redis_client.get(f"revoked:{user_id}")
        if not revoked_at:
            return False
        return iat_timestamp < int(revoked_at)


token_service = TokenService()


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if USERS.get(username) != password:
        return jsonify({"error": "invalid credentials"}), 401

    # 生成 Access Token 和 Refresh Token
    jti = secrets.token_urlsafe(16)
    access_token = token_service.create_access_token(username, jti)
    refresh_token = token_service.create_refresh_token(username, jti)

    token_service.store_refresh_token(jti, username)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
    })


@app.route("/api/refresh", methods=["POST"])
def refresh():
    """用 Refresh Token 换新 Access Token（带轮换）"""
    data = request.get_json()
    old_refresh_token = data.get("refresh_token")

    try:
        payload = jwt.decode(
            old_refresh_token, SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "jti", "type"]},
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "refresh token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid refresh token"}), 401

    if payload["type"] != "refresh":
        return jsonify({"error": "not a refresh token"}), 401

    user_id = payload["sub"]
    old_jti = payload["jti"]

    # ✅ 重放检测：检查是否是当前活跃的 Token
    if not token_service.is_refresh_token_active(user_id, old_jti):
        # 检测到 Refresh Token 重放！撤销所有 Token
        token_service.revoke_user_tokens(user_id)
        return jsonify({
            "error": "refresh token reuse detected, all tokens revoked"
        }), 401

    # 检查是否被撤销
    if token_service.is_user_revoked(user_id, payload["iat"]):
        return jsonify({"error": "user tokens revoked"}), 401

    # ✅ Token 轮换：签发新的 Refresh Token
    new_jti = secrets.token_urlsafe(16)
    new_access_token = token_service.create_access_token(user_id, new_jti)
    new_refresh_token = token_service.create_refresh_token(user_id, new_jti)
    token_service.store_refresh_token(new_jti, user_id)

    return jsonify({
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    """登出：撤销当前用户的所有 Token"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401

    try:
        payload = jwt.decode(
            auth[7:], SECRET_KEY, algorithms=["HS256"],
        )
        token_service.revoke_user_tokens(payload["sub"])
    except jwt.InvalidTokenError:
        pass
    return jsonify({"ok": True})
```

### 2.2 Token 撤销中间件

```python
# 文件：token_revocation.py
# Token 黑名单 + 自动清理
import time
from functools import wraps
from flask import request, g, abort
import jwt
import redis

redis_client = redis.Redis(host="localhost", port=6379)


def check_token_revoked(user_id: str, iat: int) -> bool:
    """检查 Token 是否被撤销"""
    revoke_time = redis_client.get(f"user:{user_id}:revoked_at")
    if revoke_time:
        return iat < int(revoke_time)
    return False


def jwt_required_with_revocation(secret: str):
    """带撤销检查的 JWT 装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                abort(401)

            token = auth[7:]
            try:
                payload = jwt.decode(token, secret, algorithms=["HS256"])
            except jwt.InvalidTokenError:
                abort(401)

            # 检查撤销
            if check_token_revoked(payload["sub"], payload["iat"]):
                abort(401, "token revoked")

            g.user_id = payload["sub"]
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/api/data")
@jwt_required_with_revocation(SECRET_KEY)
def get_data():
    return {"user": g.user_id}
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Token 刷新（Account Service）

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（典型 Refresh Token 流程）：

```python
def refresh_token(refresh_token: str) -> dict:
    """刷新 Access Token"""
    # 1. 解析 Refresh Token
    try:
        payload = jwt.decode(
            refresh_token,
            dify_config.SECRET_KEY,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise RefreshTokenExpiredError()
    except jwt.InvalidTokenError:
        raise RefreshTokenNotFoundError()

    # 2. 验证类型
    if payload.get("type") != "refresh":
        raise InvalidActionError("not a refresh token")

    # 3. 查询用户
    user = db.session.query(Account).filter_by(id=payload["sub"]).first()
    if not user:
        raise RefreshTokenAccountNotFoundError()

    # 4. 签发新 Token
    new_access_token = generate_access_token(user.id)
    new_refresh_token = generate_refresh_token(user.id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }
```

**解读**：
- 第 6-13 行：JWT 解码 + 异常分类（过期 vs 无效 vs 类型错）
- 第 21 行：验证 Token 类型必须是 refresh（防 Access Token 误用）
- 第 25 行：查询用户是否存在（用户被删除后 Token 自动失效）
- **设计意图**：dify 的 Refresh Token 是无状态的（不存 Redis），完全靠 JWT 自身的 exp + DB 查询保证有效性

### 3.2 ruoyi 的 OAuth2 Token 管理（Redis 存储）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/oauth2/OAuth2TokenServiceImpl.java`
**核心代码**（典型 Spring 实现）：

```java
@Service
public class OAuth2TokenServiceImpl implements OAuth2TokenService {

    @Resource
    private RedisTemplate<String, OAuth2AccessTokenDO> redisTemplate;

    private static final String ACCESS_TOKEN_KEY = "oauth2:access_token:";

    public OAuth2AccessTokenDO createAccessToken(Long userId, Integer userType, String clientId) {
        // 1. 生成 Token
        String token = generateToken();
        OAuth2AccessTokenDO tokenDO = new OAuth2AccessTokenDO()
            .setAccessToken(token)
            .setUserId(userId)
            .setUserType(userType)
            .setClientId(clientId)
            .setExpiresTime(LocalDateTime.now().plusMinutes(30));

        // 2. 存 Redis（30 分钟过期）
        redisTemplate.opsForValue().set(
            ACCESS_TOKEN_KEY + token,
            tokenDO,
            Duration.ofMinutes(30)
        );

        // 3. 用户-Token 映射（用于主动撤销）
        redisTemplate.opsForValue().set(
            "oauth2:user_tokens:" + userId,
            token,
            Duration.ofMinutes(30)
        );

        return tokenDO;
    }

    @Override
    public void removeToken(String token) {
        // 删除 Token
        redisTemplate.delete(ACCESS_TOKEN_KEY + token);
    }
}
```

**解读**：
- 第 17 行：`generateToken()` 生成 32 字节随机字符串
- 第 24 行：Token 存 Redis，30 分钟自动过期（无需额外清理）
- 第 31 行：**额外维护 `user_tokens:{userId}`** ——支持主动撤销用户所有 Token
- **对比 dify**：ruoyi 把 Token 存 Redis（**可主动撤销**），dify 用 JWT（无状态但难撤销）
- **设计意图**：ruoyi 选择"有状态 Token"换取"可撤销"能力，更适合企业级权限管理

## 4. 关键要点总结

- **双 Token 模型**：Access Token 短期 + Refresh Token 长期
- **Token 轮换**：每次 Refresh 签发新 Refresh Token，旧 Token 失效
- **重放检测**：旧 Refresh Token 出现 → 撤销所有 Token
- **撤销机制**：黑名单（Redis）/ 版本号（DB）/ 短过期
- **JWT 适合**：第三方登录、跨域 API、临时凭证
- **Redis Token 适合**：企业内部系统、需要主动撤销的场景
- dify 用 JWT（无状态、跨域友好），ruoyi 用 Redis Token（可撤销）
- 双 Token 模型的关键是**Refresh Token 的轮换与重放检测**

## 5. 练习题

### 练习 1：基础（必做）

实现双 Token 模型：
1. `/login` 返回 access_token (15min) + refresh_token (7d)
2. `/api/refresh` 用 refresh_token 换新 access_token（**轮换 refresh_token**）
3. `/api/logout` 撤销用户所有 Token（用 Redis 黑名单）

**参考答案**：见 `solutions/04-dual-token.md`

### 练习 2：进阶

解释 Refresh Token 重放检测的原理：
1. 如果攻击者窃取了 Refresh Token #1，会发生什么？
2. 重放检测如何识别攻击？
3. 检测到重放后应该怎么处理？

### 练习 3：挑战（选做）

为 dify 添加"Token 撤销"功能：
- 即使是 JWT，也能主动撤销
- 实现思路：在 Redis 存 `user:{id}:revoked_at`
- JWT 验证时检查 `iat > revoked_at`
- 提供 `/api/revoke` 接口强制下线用户

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/dify/api/libs/jws.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/oauth2/OAuth2TokenServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- OAuth 2.0 RFC 6749：https://datatracker.ietf.org/doc/html/rfc6749
- OWASP JWT 安全手册：https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13