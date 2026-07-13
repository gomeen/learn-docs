# 5.5.2 防重放攻击（Replay Attack）

> 理解重放攻击的威胁，掌握 nonce、时间戳、序列号三种防御策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解重放攻击的威胁场景
- 掌握三种防重放机制：nonce、时间戳、序列号
- 理解 dify 在不同接口的防重放策略
- 能用 Python 实现一个 nonce 防重放方案

## 📚 前置知识

- 03-jwt-auth.md（JWT 时间戳）
- 26-api-rate-limit.md

## 1. 核心概念

### 1.1 什么是重放攻击？

攻击者截获合法请求，**原封不动**重新发送，欺骗服务端。

```
正常：Alice → 转账 100 给 Bob → Server ✅
攻击：Mallory 截获这条请求，重发 → Server 又转 100 给 Bob
```

### 1.2 三种防重放机制

**1. Nonce（一次性随机数）**
- 请求中带随机串，服务端记录已用 nonce
- 同一个 nonce 只能用一次

**2. 时间戳窗口**
- 请求中带时间戳，服务端只接受时间差 < N 秒的请求
- 减小攻击窗口（但不能完全防重放）

**3. 序列号 / 计数器**
- 请求带递增序列号，服务端拒绝乱序或重复

### 1.3 dify 的防重放策略

| 场景 | 防御手段 |
|------|---------|
| Access Token | JWT `exp` 字段自动过期 |
| Refresh Token | 每次刷新**轮换**旧 Token |
| 邮件验证码 | 一次性 + 5 分钟过期 |
| API Key | 长 TTL，靠 HTTPS 防截获 |
| Webhook | 签名 + 时间戳 |

## 2. 代码示例

### 2.1 Nonce 防重放（Redis）

```python
import redis
import secrets

class NonceCache:
    """用 Redis SETNX 实现 nonce 防重放。"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def is_used(self, nonce: str, ttl_seconds: int = 300) -> bool:
        """检查 nonce 是否已被使用，并标记。"""
        key = f"nonce:{nonce}"
        # SETNX：只在 key 不存在时设置
        was_set = self.redis.set(key, "1", nx=True, ex=ttl_seconds)
        return not was_set  # True = 已使用（重放）


# 使用
cache = NonceCache(redis_client)
nonce = secrets.token_urlsafe(16)

# 客户端发请求时附带 nonce
# 服务端：
if cache.is_used(nonce):
    raise ValueError("Duplicate request (replay attack)")
# 第一次通过，第二次（重放）会失败
```

### 2.2 时间戳防重放

```python
import time

class TimestampGuard:
    """时间戳窗口：拒绝时间差 > 300 秒的请求。"""

    def __init__(self, window_seconds: int = 300):
        self.window = window_seconds

    def verify(self, request_timestamp: float) -> None:
        now = time.time()
        diff = abs(now - request_timestamp)
        if diff > self.window:
            raise ValueError(f"Request too old or too far in future (diff={diff}s)")


# 使用（请求中带 timestamp）
# 服务器：guard.verify(request.json["timestamp"])
```

### 2.3 序列号防重放

```python
class SequenceGuard:
    """序列号：拒绝 <= 上次序列号的请求。"""

    def __init__(self):
        self.last_seq = 0

    def verify(self, sequence: int) -> None:
        if sequence <= self.last_seq:
            raise ValueError(f"Invalid sequence: {sequence} <= {self.last_seq}")
        self.last_seq = sequence
```

### 2.4 常见错误：忽略时间戳窗口

```python
# ❌ 错误：只检查签名，不检查时间
def verify_webhook(signature: str, body: bytes) -> bool:
    expected = hmac.new(secret, body, sha256).hexdigest()
    return signature == expected
# 攻击者截获后任意时间重发都通过

# ✅ 正确：签名 + 时间戳窗口
def verify_webhook_safe(signature: str, body: bytes, timestamp: int) -> bool:
    if abs(time.time() - timestamp) > 300:
        return False
    expected = hmac.new(secret, f"{timestamp}.".encode() + body, sha256).hexdigest()
    return signature == expected
```

## 3. dify 仓库源码解读

### 3.1 Refresh Token 轮换防重放

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
**核心代码**（行 347-377）：

```python
@console_ns.route("/refresh-token")
class RefreshTokenApi(Resource):
    @console_ns.response(200, "Success", console_ns.models[SimpleResultResponse.__name__])
    @console_ns.response(401, "Unauthorized", console_ns.models[SimpleResultMessageResponse.__name__])
    def post(self):
        # Get refresh token from cookie instead of request body
        refresh_token = extract_refresh_token(request)

        if not refresh_token:
            return SimpleResultMessageResponse(result="fail", message="No refresh token provided").model_dump(
                mode="json"
            ), 401

        try:
            new_token_pair = AccountService.refresh_token(refresh_token, session=db.session())
        except Unauthorized as exc:
            return SimpleResultMessageResponse(result="fail", message=exc.description or "Unauthorized.").model_dump(
                mode="json"
            ), 401
        except (RefreshTokenNotFoundError, RefreshTokenAccountNotFoundError) as exc:
            return SimpleResultMessageResponse(result="fail", message=str(exc)).model_dump(mode="json"), 401
```

**解读**：
- 第 14-19 行：用同一个 refresh_token 换新 Token，**旧 refresh_token 立即作废**
- 第 20-22 行：refresh_token 无效（已轮换或过期）→ 401
- **防重放效果**：攻击者截获的旧 refresh_token 一旦被用户用了一次，**立即失效**
- 即使攻击者"抢先"用 refresh_token，**新 token 也会给攻击者**——但攻击者没有用户 Cookie 上下文，也无法继续操作
- **设计意图**：配合 HttpOnly Cookie，攻击者拿到 refresh_token 也无法实际使用

### 3.2 JWT 时间戳字段

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（行 55-80）：

```python
def sign(keyset: KeySet, payload: dict, aud: str, ttl_seconds: int) -> str:
    """``iat`` + ``exp`` are injected here; callers must not set them."""
    if "aud" in payload or "iat" in payload or "exp" in payload:
        raise ValueError("reserved claim present in payload (aud/iat/exp)")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")

    now = datetime.now(UTC)
    claims = {
        **payload,
        "aud": aud,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(
        claims,
        keyset.lookup(keyset.active_kid),
        algorithm="HS256",
        headers={"kid": keyset.active_kid},
    )
```

**解读**：
- 第 17 行：注入 `iat`（签发时间）
- 第 18 行：注入 `exp`（过期时间）
- **JWT 库自带 `exp` 检查**：验证时自动拒绝过期 Token，**无需应用代码处理**
- **防重放效果**：攻击者截获 Token 后，最多只能用到 `exp` 时间
- **dify 默认**：access_token TTL 60 分钟，refresh_token TTL 30 天

### 3.3 邮件验证码防重放

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`（典型结构）

```python
def send_email_code_login_email(email: str, language: str = "en-US") -> str:
    """发送邮件验证码，返回 token。"""
    code = secrets.token_hex(4)  # 8 位十六进制
    token = secrets.token_urlsafe(32)
    # 存到 Redis，5 分钟过期
    redis_client.hset(f"email_code:{token}", mapping={
        "email": email,
        "code": code,
    })
    redis_client.expire(f"email_code:{token}", 300)
    # 发送邮件...
    return token
```

**解读**：
- 验证码存 Redis + 5 分钟 TTL
- 验证成功后 `revoke_email_code_login_token` 删除（见 `login.py:294`）
- **防重放**：验证码只能用一次 + 5 分钟过期
- **关联**：`EmailCodeLoginApi.post()` 中调用 `revoke_email_code_login_token(args.token)` 确保一次性使用

## 4. 关键要点总结

- 重放攻击 = 截获合法请求，原封不动重发
- **三种防御**：Nonce（一次性）、时间戳窗口、序列号
- dify 的 JWT 用 `exp` 字段，库自带过期校验
- dify 的 Refresh Token **轮换机制**：旧 Token 一次性
- 邮件验证码：5 分钟过期 + 一次性使用
- Webhook 应签名 + 时间戳双保险

## 5. 练习题

### 练习 1：基础（必做）

用 Redis 实现 `NonceCache.is_used(nonce, ttl=300)`，要求：第一次返回 False（未用过），后续返回 True（已用），5 分钟后自动失效。

### 练习 2：进阶

阅读 `api/controllers/console/auth/login.py:294` 的 `revoke_email_code_login_token`，解释为什么邮件验证码要在**校验成功后立即撤销**？

### 练习 3：挑战（选做）

设计一个 **Webhook 接收端**：要求签名 + 时间戳 + nonce 三重防重放，且能容忍 ±5 分钟时钟偏差。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
- `/Users/xu/code/github/dify/api/libs/jws.py`
- OWASP 重放攻击：https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html#replay-attacks
- GitHub Webhook 签名：https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

---

**文档版本**：v1.0
**最后更新**：2026-07-13