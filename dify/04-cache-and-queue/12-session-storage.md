# 4.2.5 Session 与 Token 存储

> Session 和 Token 是有状态认证的核心。Redis 因高性能 + TTL 自动过期，成为 Session 存储首选。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Session、Cookie、Token 的区别
- 掌握 Redis 存储 Session / Token 的设计模式
- 实现 JWT refresh token 的存取
- 理解 dify 的 refresh token 存储方案

## 📚 前置知识

- HTTP 协议基础
- 认证与授权
- 01-redis-data-structures.md、08-redis-cache.md

## 1. 核心概念

### 1.1 什么是 Session？

服务器为每个用户创建的**服务端状态**。客户端只持有 Session ID。

```
客户端 Cookie:  SESSIONID=abc123
                     ↓
服务器内存/Redis: {abc123 → {user_id: 1, role: "admin"}}
```

**优点**：可随时撤销（删 Session）。**缺点**：需要服务器存储，分布式要共享。

### 1.2 什么是 Token？

无状态的认证凭证。客户端持有 Token，服务器**只验证签名**。

```
客户端 Header:  Authorization: Bearer eyJhbGc...
                ↓
服务器: 验证 JWT 签名，解析 claims
```

**优点**：无状态、易扩展。**缺点**：撤销困难（除非额外存储）。

### 1.3 JWT 双 Token 模型

实际生产用 **Access Token + Refresh Token**：

| Token | 用途 | 生命周期 |
|-------|------|---------|
| Access Token | 访问 API | 短（15-30 分钟） |
| Refresh Token | 刷新 Access Token | 长（7-30 天） |

**为什么要两个**：Access Token 短（泄露风险小）+ Refresh Token 可撤销（存 Redis）。

### 1.4 Session 存储方案对比

| 方案 | 性能 | 持久化 | 适用场景 |
|------|------|--------|---------|
| 内存（dict）| 最快 | 无 | 单进程 |
| 文件 | 慢 | 有 | 传统 PHP |
| 数据库 | 慢 | 有 | 小规模 |
| **Redis** | **快** | **可配** | **分布式首选** |
| Memcached | 快 | 无 | 纯缓存 |

### 1.5 Redis 存储 Session 的设计

```bash
# 简单方案
SET session:{session_id} {user_data_json} EX 3600

# 高级方案
HSET session:{session_id} user_id 1 role "admin" last_seen "2024-..."
EXPIRE session:{session_id} 3600
```

## 2. 代码示例

### 2.1 简单 Session 存储

```python
import json
import redis
import secrets

r = redis.Redis(decode_responses=True)

class SessionStore:
    def __init__(self, ttl=3600):
        self.ttl = ttl

    def create(self, user_id: int, data: dict) -> str:
        session_id = secrets.token_urlsafe(32)
        session_data = {"user_id": user_id, **data}
        r.setex(f"session:{session_id}", self.ttl, json.dumps(session_data))
        return session_id

    def get(self, session_id: str) -> dict | None:
        data = r.get(f"session:{session_id}")
        return json.loads(data) if data else None

    def destroy(self, session_id: str):
        r.delete(f"session:{session_id}")

# 使用
store = SessionStore()
sid = store.create(user_id=1, data={"role": "admin"})
user = store.get(sid)
store.destroy(sid)  # 登出
```

### 2.2 JWT + Refresh Token 存储

```python
import jwt
import redis
import secrets
from datetime import datetime, timedelta

r = redis.Redis(decode_responses=True)
SECRET = "your-secret-key"

class TokenService:
    REFRESH_TTL = 7 * 24 * 3600  # 7 天

    def create_access_token(self, user_id: int) -> str:
        """创建短期 Access Token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "type": "access",
        }
        return jwt.encode(payload, SECRET, algorithm="HS256")

    def create_refresh_token(self, user_id: int) -> str:
        """创建长期 Refresh Token，存储到 Redis"""
        refresh_token = secrets.token_urlsafe(64)

        # 存到 Redis（双向索引）
        pipe = r.pipeline()
        pipe.setex(f"refresh_token:{refresh_token}", self.REFRESH_TTL, user_id)
        pipe.setex(f"user_refresh:{user_id}", self.REFRESH_TTL, refresh_token)
        pipe.execute()

        return refresh_token

    def refresh(self, refresh_token: str) -> tuple[str, str] | None:
        """用 Refresh Token 换新的 Access Token"""
        user_id = r.get(f"refresh_token:{refresh_token}")
        if not user_id:
            return None  # 已失效

        # 撤销旧 token（轮换）
        self.revoke_refresh(refresh_token, int(user_id))

        return self.create_access_token(int(user_id)), self.create_refresh_token(int(user_id))

    def revoke_refresh(self, refresh_token: str, user_id: int):
        r.delete(f"refresh_token:{refresh_token}")
        r.delete(f"user_refresh:{user_id}")

# 使用
svc = TokenService()
access = svc.create_access_token(1)
refresh = svc.create_refresh_token(1)

# 客户端用 refresh token 换新 token
new_access, new_refresh = svc.refresh(refresh)
```

### 2.3 Session 续期（滑动过期）

```python
def get_session_with_sliding(session_id: str, ttl=3600):
    """每次访问滑动续期"""
    key = f"session:{session_id}"
    data = r.get(key)
    if data:
        # 续期（剩余 ttl 重置）
        r.expire(key, ttl)
        return json.loads(data)
    return None
```

### 2.4 常见错误：Session ID 不够随机

```python
# ❌ 错误：用自增 ID 当 Session ID
session_id = str(user_id)  # 攻击者可以遍历所有 session

# ✅ 正确：用密码学安全的随机数
session_id = secrets.token_urlsafe(32)  # 256 位熵
```

## 3. dify 仓库源码解读

### 3.1 Refresh Token 双向索引

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 269-274）：

```python
@staticmethod
def _store_refresh_token(refresh_token: str, account_id: str):
    redis_client.setex(AccountService._get_refresh_token_key(refresh_token), REFRESH_TOKEN_EXPIRY, account_id)
    redis_client.setex(
        AccountService._get_account_refresh_token_key(account_id), REFRESH_TOKEN_EXPIRY, refresh_token
    )
```

**解读**：
- **双向索引**：
  - `refresh_token:{token}` → `account_id`（验证 refresh token 时用）
  - `account_refresh:{account_id}` → `token`（按账户撤销时用）
- **删除时也双向**：
  ```python
  redis_client.delete(f"refresh_token:{token}")
  redis_client.delete(f"account_refresh:{account_id}")
  ```
- **TTL 自动过期**：不需要清理任务

### 3.2 Refresh Token Key 设计

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 230-237）：

```python
@staticmethod
def _get_account_refresh_token_key(account_id: str) -> str:
    return f"{ACCOUNT_REFRESH_TOKEN_PREFIX}{account_id}"

@staticmethod
def _get_account_last_active_refresh_key(account_id: str) -> str:
    return f"{ACCOUNT_LAST_ACTIVE_REFRESH_PREFIX}{account_id}"
```

**解读**：
- dify 用**前缀**区分不同用途的 Redis key
- `ACCOUNT_REFRESH_TOKEN_PREFIX = "account_refresh_token:"`
- `ACCOUNT_LAST_ACTIVE_REFRESH_PREFIX = "account_last_active_refresh:"`
- 命名规范：`{业务}:{实体}:{ID}`
- 这样 `KEYS *` 排查问题时能快速定位

### 3.3 登录锁定状态存储

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1085-1100）：

```python
@staticmethod
@redis_fallback(default_return=None)
def add_forgot_password_error_rate_limit(email: str):
    key = f"forgot_password_error_rate_limit:{email}"
    count = redis_client.get(key)
    if count is None:
        count = 0
    count = int(count) + 1
    redis_client.setex(key, dify_config.FORGOT_PASSWORD_LOCKOUT_DURATION, count)

@staticmethod
@redis_fallback(default_return=None)
def add_email_register_error_rate_limit(email: str) -> None:
    key = f"email_register_error_limit:{email}"
    count = redis_client.get(key)
    if count is None:
        count = 0
    count = int(count) + 1
    redis_client.setex(key, dify_config.EMAIL_REGISTER_LOCKOUT_DURATION, count)
```

**解读**：
- dify 用 Redis 存多个场景的"失败状态"：
  - 登录失败
  - 忘记密码失败
  - 邮箱注册失败
  - 改邮箱失败
  - 转账失败
- 每个场景独立 key + 不同 TTL
- **统一模式**：`{场景}_rate_limit:{email}` → 计数，TTL 自动清零
- `redis_fallback` 保证 Redis 故障时不限流（**安全 vs 可用性**）

## 4. 关键要点总结

- Session / Token 都需要存储，Redis 是分布式首选
- **JWT 双 Token**：Access 短期 + Refresh 长期
- Refresh Token 存 Redis 可撤销，Access Token 短命不存
- **双向索引**支持通过 token 或 user 双向查找
- TTL 自动过期，免清理任务
- **key 命名规范**：`{业务}:{实体}:{ID}`
- `redis_fallback` 保证高可用

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Session 类，支持：
- 创建（生成随机 session_id）
- 读取（自动续期）
- 销毁

### 练习 2：进阶

实现 JWT 双 Token 模型，Access Token 15 分钟，Refresh Token 7 天，Refresh 存 Redis。

### 练习 3：挑战（选做）

为 dify 设计一个"异地登录检测"功能：同一账户在新 IP 登录时发送邮件通知。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`（第 230-237、269-274、1085-1100 行）
- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- JWT 规范：https://datatracker.ietf.org/doc/html/rfc7519
- Redis Session 最佳实践：https://redis.io/docs/manual/patterns/

---

**文档版本**：v1.0
**最后更新**：2026-07-13