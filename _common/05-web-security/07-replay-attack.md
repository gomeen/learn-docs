# 5.7 防重放攻击：nonce / 时间戳 / 序列号

> 理解重放攻击的原理，掌握 nonce、时间戳、序列号三种主流防御手段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解重放攻击的原理与危害
- 掌握 nonce（一次性随机数）、时间戳、序列号三种防御手段
- 能结合 HMAC 签名设计防重放的 API
- 识别 dify 和 ruoyi 中防重放的实现

## 📚 前置知识

- HTTP 协议基础
- HMAC 签名原理
- 5.1 OWASP Top 10 概览

## 1. 核心概念

### 1.1 什么是重放攻击？

重放攻击（Replay Attack）指攻击者**截获合法请求**，原封不动地重复发送给服务端。

**典型场景**：
- 用户 A 给用户 B 转账 1000 元，攻击者截获请求，重复发送 100 次
- 用户登录后获得有效 Token，攻击者盗用 Token 反复使用
- OAuth 授权码被截获，攻击者用它换取 Token

### 1.2 重放攻击的两种类型

#### 1.2.1 直接重放

```
1. 用户发起：POST /transfer {to: B, amount: 1000}
2. 攻击者截获整个请求（包括 Cookie、Token）
3. 攻击者重发：POST /transfer {to: B, amount: 1000}
4. 服务端认为是合法请求，再次转账
```

#### 1.2.2 反射型重放

```
1. 攻击者构造恶意链接：https://bank.com/transfer?to=attacker&amount=10000
2. 诱导已登录用户点击（CSRF 攻击）
3. 这本质上是 CSRF，可以看作重放攻击的一种
```

### 1.3 三大防御手段

#### 1.3.1 Nonce（一次性随机数）

```
请求：{to: B, amount: 1000, nonce: "abc123"}
                       ↑ 服务端记录所有用过的 nonce
```

**原理**：每个请求带一个唯一的随机字符串，服务端记录已用过的 nonce，重复 nonce 直接拒绝。

**缺点**：需要存储所有 nonce，存储压力大。

#### 1.3.2 时间戳

```
请求：{to: B, amount: 1000, timestamp: 1700000000, sign: HMAC(...)}
                                  ↑ 服务端检查 |now - timestamp| < 60s
```

**原理**：请求必须包含时间戳，且服务端只接受"最近 N 秒内"的请求。

**缺点**：仍可能有 N 秒的重放窗口。

#### 1.3.3 序列号

```
请求：{to: B, amount: 1000, seq: 10086, sign: HMAC(...)}
                       ↑ 服务端记录最大 seq，拒绝 <= max_seq 的请求
```

**原理**：每个用户维护递增序列号，服务端记录最大 seq，拒绝任何"小于等于历史最大值"的请求。

**缺点**：需要每个用户维护计数器，实现复杂。

### 1.4 实战最佳实践：组合使用

```
最终方案 = 时间戳 + Nonce + HMAC 签名
  ├─ 时间戳：限制 5 分钟内的请求
  ├─ Nonce：Redis 存储 5 分钟，去重
  └─ HMAC 签名：保证请求完整性 + 抗篡改
```

```
客户端请求:
POST /transfer
Headers:
  X-Timestamp: 1700000000
  X-Nonce: 7a3b5c9e
  X-Signature: HMAC_SHA256(secret, timestamp + nonce + body)

服务端校验:
1. |now - timestamp| > 300s → 拒绝
2. SET nonce 7a3b5c9e NX EX 300 → 失败说明已用 → 拒绝
3. 重新计算签名，不匹配 → 拒绝
4. 全部通过 → 处理请求
```

### 1.5 dify 和 ruoyi 的防重放策略

- **dify**：API 用 App ID + API Key 签名 + Token 短期有效（10 分钟），结合 Redis 黑名单
- **ruoyi**：Token 存 Redis 设置过期时间，自动失效；OAuth2 Access Token 默认 30 分钟

## 2. 代码示例

### 2.1 漏洞示例：纯 Token 认证的转账接口

```python
# 文件：replay_vulnerable.py
# ❌ 故意写错：仅用 Token 认证，无防重放
import hashlib
import hmac
from flask import Flask, request, abort

app = Flask(__name__)
SECRET = b"my-secret"

def sign(body: str) -> str:
    return hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()

@app.route("/transfer", methods=["POST"])
def transfer():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Signature", "")

    # 只验证签名，没验证时间戳和 nonce
    if not hmac.compare_digest(signature, sign(body)):
        abort(403)

    # 执行转账...
    return "ok"

# 攻击：截获请求后原封不动重发
# 1. 用户 A 转账：POST /transfer {"to":"B","amount":1000}  + 签名
# 2. 攻击者截获后重发，服务端签名仍然有效 → 转账多次
```

### 2.2 修正：时间戳 + Nonce + 签名

```python
# 文件：replay_secure.py
# ✅ 防重放：时间戳 + Nonce + HMAC 签名
import hashlib
import hmac
import os
import time
import redis
from flask import Flask, request, abort

app = Flask(__name__)
SECRET = b"my-secret"
redis_client = redis.Redis(host="localhost", port=6379)
NONCE_TTL = 300  # nonce 保留 5 分钟
TIMESTAMP_TOLERANCE = 300  # 时间戳容忍 5 分钟

def sign(secret: bytes, timestamp: str, nonce: str, body: str) -> str:
    """按规则生成签名：timestamp + nonce + body"""
    message = f"{timestamp}.{nonce}.{body}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

@app.route("/transfer", methods=["POST"])
def transfer():
    body = request.get_data(as_text=True)
    timestamp = request.headers.get("X-Timestamp", "")
    nonce = request.headers.get("X-Nonce", "")
    signature = request.headers.get("X-Signature", "")

    # 1. ✅ 校验时间戳：防止过期请求重放
    try:
        ts = int(timestamp)
    except ValueError:
        abort(400, "invalid timestamp")
    if abs(time.time() - ts) > TIMESTAMP_TOLERANCE:
        abort(401, "timestamp expired")

    # 2. ✅ 校验 Nonce 唯一性：防止窗口期内重放
    if not nonce or len(nonce) < 16:
        abort(400, "invalid nonce")
    # SETNX：原子操作，只在不存在时设置
    if not redis_client.set(f"nonce:{nonce}", "1", nx=True, ex=NONCE_TTL):
        abort(401, "nonce reused (replay attack detected)")

    # 3. ✅ 校验签名：防篡改
    expected = sign(SECRET, timestamp, nonce, body)
    if not hmac.compare_digest(signature, expected):
        abort(403, "invalid signature")

    # 执行转账...
    return "ok"

# 客户端调用示例
def make_request(client_secret: bytes, body: str):
    timestamp = str(int(time.time()))
    nonce = os.urandom(16).hex()
    signature = sign(client_secret, timestamp, nonce, body)
    return {
        "headers": {
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
        },
        "body": body,
    }
```

### 2.3 序列号模式（高安全场景）

```python
# 文件：seq_replay_protection.py
# ✅ 金融级场景：序列号防重放
import time
from collections import defaultdict

# 实际生产用 Redis：INCR + GET + SET
class SequenceManager:
    """每个用户维护递增序列号"""

    def __init__(self):
        # 生产用 Redis 替换
        self.max_seq: dict[str, int] = defaultdict(int)

    def validate_and_update(self, user_id: str, seq: int) -> bool:
        """校验并更新序列号。返回 True 表示合法。"""
        # ✅ 关键：seq 必须严格大于历史最大值
        if seq <= self.max_seq[user_id]:
            return False
        self.max_seq[user_id] = seq
        return True

def make_transfer(user_id: str, to: str, amount: int, seq: int, sign: str):
    sm = SequenceManager()
    if not sm.validate_and_update(user_id, seq):
        return "replay detected", 401
    # ...
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Account 认证流程（看时间戳 + nonce 的影子）

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 39-49）：

```python
def current_account_with_tenant() -> tuple[Account, str]:
    """
    Resolve the underlying account for the current user proxy and ensure tenant context exists.
    Allows tests to supply plain Account mocks without the LocalProxy helper.
    """
    user = _resolve_current_user()

    if not isinstance(user, Account):
        raise ValueError("current_user must be an Account instance")
    assert user.current_tenant_id is not None, "The tenant information should be loaded."
    return user, user.current_tenant_id
```

**解读**：
- 第 47 行：用户必须是已登录的 `Account` 实例
- 第 48 行：**关键**：必须有租户上下文——dify 的会话自带过期时间（Flask Session 默认 31 天，但可配置为短期）
- **防重放机制**：dify 的会话本身在 Cookie 中签名 + 过期时间，配合 `check_csrf_token` 的 nonce 校验，组合实现防重放
- **设计意图**：通过短期会话 + CSRF Token 一次性校验，把"重放窗口"压到分钟级

### 3.2 ruoyi 的 Token 认证（短期 Token + Redis 黑名单）

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
- 第 73 行：通过 RPC 调用 OAuth2 服务校验 Token（不是本地校验，避免分布式不一致）
- 第 88 行：`setExpiresTime` 把过期时间记录到 LoginUser——**Token 过期自动失效，限制重放窗口**
- 第 89 行：抛 ServiceException 时返回 null（**不暴露具体错误原因**，防止攻击者探测）
- **设计意图**：ruoyi 把"防重放"的责任交给 OAuth2 服务，所有 Token 在 Redis 中带 TTL，过期即失效。结合 refresh_token 机制实现无感知续期。

## 4. 关键要点总结

- 重放攻击让攻击者"截获合法请求，原封不动重发"
- **三大防御**：Nonce（去重）、时间戳（限窗口）、序列号（严格递增）
- **最佳实践**：时间戳 + Nonce + HMAC 签名 三件套组合使用
- HMAC 签名保证请求完整性（防篡改），时间戳/Nonce 保证新鲜度（防重放）
- dify 用短期会话 + CSRF nonce 实现防重放
- ruoyi 用 OAuth2 Token + Redis TTL 自动失效实现防重放
- 即使有 Token 机制，敏感操作（转账、改密）也要强制二次验证

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `sign_request(secret, body)` 函数，返回包含 `X-Timestamp`、`X-Nonce`、`X-Signature` 的 headers 字典，并实现 `verify_request(headers, body)` 服务端校验函数。

**参考答案**：见 `solutions/07-replay-signature.md`

### 练习 2：进阶

解释为什么"单独使用时间戳"无法完全防重放？需要和哪些机制组合？

### 练习 3：挑战（选做）

为 dify 的 API 接口设计一个"防重放中间件"，要求：
- 自动提取所有 POST 请求的 `X-Timestamp`、`X-Nonce`、`X-Signature`
- 使用 dify 现有的 App Secret 作为 HMAC Key
- 用 Redis 存储 Nonce，过期时间 5 分钟
- 不匹配任何条件时返回 401 并记录日志

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`（认证流程）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/oauth2/OAuth2TokenServiceImpl.java`
- OWASP 重放攻击防护手册：https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13