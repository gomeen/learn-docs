# 5.1.3 JWT 机制与无状态认证

> 理解 JWT 的结构与工作原理，看懂 dify 中 HS256 签名的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 JWT 三段式结构（header/payload/signature）
- 理解签名验证的密码学原理
- 能用 Python 自己签发和验证 JWT
- 能看懂 dify 中 `libs/jws.py` 的 KeySet 设计

## 📚 前置知识

- 01-fundamentals/01-flask-basics.md
- 加密学基础（哈希、对称加密）

## 1. 核心概念

### 1.1 什么是 JWT？

JWT（JSON Web Token）是一种**自包含**的令牌：Token 里就携带了用户信息，服务端**无需查 DB**就能识别身份。

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

JWT 由三段组成，用 `.` 分隔：

```
┌──────────────────┬──────────────────────────┬──────────────────┐
│   Header(算法)   │    Payload(载荷)         │ Signature(签名)  │
│   base64         │    base64                │ HMACSHA256       │
└──────────────────┴──────────────────────────┴──────────────────┘
```

### 1.2 三段详解

**Header**：声明算法和 Token 类型。

```json
{"alg": "HS256", "typ": "JWT"}
```

**Payload**：携带业务数据（声明）。标准字段：

| 字段 | 含义 |
|------|------|
| `iss` | 签发者（Issuer） |
| `sub` | 主题（Subject，通常是用户 ID） |
| `aud` | 受众（Audience） |
| `iat` | 签发时间（Issued At） |
| `exp` | 过期时间（Expiration） |

```json
{"sub": "user-123", "exp": 1735689600, "aud": "api.sso.state_envelope"}
```

**Signature**：用密钥对 `base64(header) + "." + base64(payload)` 做 HMAC-SHA256。

```
HMACSHA256(base64(header) + "." + base64(payload), secret)
```

### 1.3 JWT 的两大优势与三大陷阱

**优势**：
- **无状态**：服务端不需要存储会话表（无需 Redis/DB 查询）
- **跨服务**：只要共享密钥，多个服务都能验证

**陷阱**：
- **无法主动撤销**：签发后只能等过期（dify 用短 TTL + refresh 缓解）
- **密钥泄露即破产**：HS256 一旦密钥泄露，攻击者可签发任意 Token
- **Payload 不加密**：敏感信息别放进去

## 2. 代码示例

### 2.1 用 `pyjwt` 签发和验证 JWT

```python
import time
import jwt

SECRET = "my-super-secret-key-change-in-production"

def sign_token(user_id: str, ttl_seconds: int = 3600) -> str:
    """签发 JWT"""
    now = int(time.time())
    payload = {
        "sub": user_id,            # 主题：用户 ID
        "iat": now,                # 签发时间
        "exp": now + ttl_seconds,  # 过期时间
        "aud": "dify.console",     # 受众：标识用途
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    """验证 JWT，失败抛出异常"""
    try:
        # 验证签名 + 过期时间 + 受众
        claims = jwt.decode(
            token, SECRET,
            algorithms=["HS256"],
            audience="dify.console",
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise ValueError("Token 已过期")
    except jwt.InvalidAudienceError:
        raise ValueError("Token 受众不匹配")
    except jwt.InvalidSignatureError:
        raise ValueError("Token 签名无效")


# 使用示例
token = sign_token("user-123", ttl_seconds=60)
print(f"Token: {token}")

# 模拟客户端传回
claims = verify_token(token)
print(f"解码后: {claims}")  # {'sub': 'user-123', ...}
```

### 2.2 常见错误：信任未校验的 Header

```python
# ❌ 错误：手动拆解 JWT，没有验签
import base64, json

def bad_decode(token: str) -> dict:
    payload_b64 = token.split(".")[1]
    # 攻击者可以伪造任意 payload！
    return json.loads(base64.b64decode(payload_b64))

# ✅ 正确：用 jwt 库强制验签
def good_decode(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=["HS256"])
```

## 3. dify 仓库源码解读

### 3.1 KeySet：支持多密钥轮换

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（行 1-50）：

```python
"""HS256 compact JWS keyed on the shared Dify SECRET_KEY. Used by the SSO
state envelope, external subject assertion, and approval-grant cookie —
all three share one key-set so api ↔ enterprise can verify each other.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from configs import dify_config

AUD_STATE_ENVELOPE = "api.sso.state_envelope"
AUD_EXT_SUBJECT_ASSERTION = "api.device_flow.external_subject_assertion"
AUD_APPROVAL_GRANT = "api.device_flow.approval_grant"

ACTIVE_KID_V1 = "dify-shared-v1"


class KeySetError(Exception):
    pass


class KeySet:
    """``from_entries`` reserves multi-kid construction for rotation slots."""

    def __init__(self, entries: dict[str, bytes], active_kid: str) -> None:
        if active_kid not in entries:
            raise KeySetError(f"active kid {active_kid!r} missing from key-set")
        if not entries[active_kid]:
            raise KeySetError(f"active kid {active_kid!r} has empty secret")
        self._entries: dict[str, bytes] = {k: bytes(v) for k, v in entries.items()}
        self._active_kid = active_kid

    @classmethod
    def from_shared_secret(cls) -> KeySet:
        secret = dify_config.SECRET_KEY
        if not secret:
            raise KeySetError("dify_config.SECRET_KEY is empty; cannot build key-set")
        return cls({ACTIVE_KID_V1: secret.encode("utf-8")}, ACTIVE_KID_V1)
```

**解读**：
- 第 4-6 行：注释说明 dify 用 JWT 的三个用途：SSO 状态、跨服务主题断言、授权 cookie
- 第 14-16 行：定义三个不同的 `aud`（受众）值，**强制不同用途的 Token 不可混用**
- 第 18 行：`ACTIVE_KID_V1` 是 key ID，用于将来密钥轮换时支持多版本共存
- 第 36-41 行：`KeySet` 用字典管理多把密钥，`active_kid` 标识当前签名用哪把
- **设计意图**：把"密钥集合"抽象成对象，为将来无缝轮换密钥（如 90 天周期）做准备

### 3.2 JWT 签发函数

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
- 第 57-58 行：**防御性设计**，拒绝 payload 中已包含 `aud/iat/exp` 的调用，避免外部篡改关键字段
- 第 65-70 行：内部统一注入三个时间/受众字段，调用方只需关心业务 payload
- 第 73 行：JWT header 里写 `kid`（Key ID），便于将来轮换密钥时识别
- **关键设计**：签名密钥来自 `keyset.active_kid`，验证时按 `kid` 选密钥 → 完美支持灰度轮换

## 4. 关键要点总结

- JWT = Header（算法） + Payload（业务数据） + Signature（HMAC 签名）
- **Payload 不加密**，敏感数据不要放进去
- `aud`（Audience）字段可防止不同用途的 Token 混用
- `kid`（Key ID）让密钥轮换无需停服
- dify 用 HS256 共享密钥，所有 SSO 凭证签发都来自 `dify_config.SECRET_KEY`

## 5. 练习题

### 练习 1：基础（必做）

用 `pyjwt` 签发一个 JWT，payload 包含 `user_id="alice"`、`role="admin"`，TTL 1 小时。然后写一个验证函数：返回 `(is_valid, claims_or_error)`。

### 练习 2：进阶

阅读 `api/libs/jws.py`，为什么 dify 在 `sign()` 函数里**强制禁止**调用方传入 `aud/iat/exp`？这种"防御性编程"的好处是什么？

### 练习 3：挑战（选做）

扩展 `KeySet`，实现一个 `rotate(new_secret: bytes)` 方法：把新密钥作为 `active_kid`，但**保留旧密钥**用于验证尚未过期的 Token。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/jws.py`
- RFC 7519 (JWT)：https://datatracker.ietf.org/doc/html/rfc7519
- PyJWT 文档：https://pyjwt.readthedocs.io/en/stable/
- JWT 调试工具：https://jwt.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13