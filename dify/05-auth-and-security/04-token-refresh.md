# 5.1.4 Token 刷新与撤销策略

> 理解短 TTL + Refresh Token 的轮换机制，看懂 dify 的双 Token 体系。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解为什么需要 Access Token + Refresh Token 双 Token
- 掌握 Refresh Token 的轮换与撤销策略
- 能看懂 dify 中 `/refresh-token` 接口的实现
- 区分"主动撤销"和"自然过期"两种失效路径

## 📚 前置知识

- 03-jwt-auth.md（JWT 结构）
- 04-cache-and-queue/02-redis-cache.md（Redis 缓存）

## 1. 核心概念

### 1.1 为什么需要 Refresh Token？

JWT 一旦签发就**无法主动撤销**。如果只用一个长 TTL 的 Token：
- 用户改密码后，旧 Token 仍然能用（直到过期）
- Token 泄露后，无法让攻击者手里的 Token 失效

**双 Token 方案**：

```
┌──────────────────────────────────────────────────┐
│  Access Token (短期: 1h)                          │
│  → 携带用户身份，每次请求都用                     │
│  → 泄露风险窗口小（最坏 1 小时）                  │
├──────────────────────────────────────────────────┤
│  Refresh Token (长期: 30d)                        │
│  → 仅用于"换新 Access Token"                     │
│  → 服务端存有映射关系，可以主动撤销                │
└──────────────────────────────────────────────────┘
```

### 1.2 Refresh Token 轮换（Rotation）

每次用 Refresh Token 换新 Access Token 时，**同时签发新的 Refresh Token**，旧的作废。这样即使 Refresh Token 泄露，也只能用一个很短的时间窗口。

```
客户端                       服务端
  │                            │
  │ ── POST /refresh-token ─→  │  (用旧 refresh)
  │                            │
  │ ←─ 200 + 新 access + 新 refresh ──  │
  │                            │  (旧 refresh 入黑名单)
```

### 1.3 dify 的 Token 三件套

| Token | TTL | 存储位置 | 撤销策略 |
|-------|-----|---------|---------|
| `access_token` Cookie | 默认几小时 | 无（JWT 自含） | 等过期 |
| `refresh_token` Cookie | 默认 30 天 | DB/Redis | 可撤销 |
| `csrf_token` Cookie | 同步 access_token | 无 | 等过期 |

## 2. 代码示例

### 2.1 简化版 Refresh Token 服务端

```python
import secrets
from datetime import datetime, timedelta

# 内存版，生产用 Redis
_active_refresh_tokens: dict[str, dict] = {}

def issue_token_pair(user_id: str) -> dict:
    """登录成功：返回 access + refresh"""
    access = create_jwt(user_id, ttl=3600)              # 1 小时
    refresh = secrets.token_urlsafe(32)
    _active_refresh_tokens[refresh] = {
        "user_id": user_id,
        "expires_at": datetime.now() + timedelta(days=30),
    }
    return {"access_token": access, "refresh_token": refresh}


def refresh_tokens(refresh_token: str) -> dict:
    """用 refresh 换新 access + refresh（轮换）"""
    record = _active_refresh_tokens.get(refresh_token)
    if record is None:
        raise ValueError("Invalid refresh token")
    if record["expires_at"] < datetime.now():
        raise ValueError("Refresh token expired")

    # 1. 删除旧 refresh（轮换）
    del _active_refresh_tokens[refresh_token]

    # 2. 签发新的 access + refresh
    return issue_token_pair(record["user_id"])


def revoke_all_tokens(user_id: str) -> int:
    """用户改密码时调用：撤销该用户的所有 refresh token"""
    count = 0
    for token, record in list(_active_refresh_tokens.items()):
        if record["user_id"] == user_id:
            del _active_refresh_tokens[token]
            count += 1
    return count
```

### 2.2 客户端自动刷新逻辑

```python
import time

class ApiClient:
    def __init__(self, base_url: str, access_token: str, refresh_token: str):
        self.base_url = base_url
        self.access_token = access_token
        self.refresh_token = refresh_token

    def request(self, path: str) -> dict:
        # 第一次尝试
        resp = self._do_request(path, self.access_token)
        if resp.status_code != 401:
            return resp.json()

        # 401 时：尝试 refresh
        new_pair = self._do_refresh()
        self.access_token = new_pair["access_token"]
        self.refresh_token = new_pair["refresh_token"]

        # 用新 token 重试
        resp = self._do_request(path, self.access_token)
        return resp.json()
```

## 3. dify 仓库源码解读

### 3.1 Refresh Token 接口实现

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

        # Create response with new cookies
        # response-contract:ignore cookie-bearing Flask response
        response = make_response(SimpleResultResponse(result="success").model_dump(mode="json"))

        # Update cookies with new tokens
        set_csrf_token_to_cookie(request, response, new_token_pair.csrf_token)
        set_access_token_to_cookie(request, response, new_token_pair.access_token)
        set_refresh_token_to_cookie(request, response, new_token_pair.refresh_token)
        return response
```

**解读**：
- 第 4-6 行：从 Cookie 读 refresh token（不是 body），与登录接口保持一致
- 第 9-11 行：缺少 refresh token → 401
- 第 16-20 行：调用 `AccountService.refresh_token` 触发**轮换**，三种异常分别处理
- 第 29-31 行：把新的三组 Token 全部通过 Cookie 下发，**完整覆盖**而不是只更新 access_token
- **设计意图**：每次刷新都换全套，让旧的 refresh_token 立即失效，最大化攻击窗口压缩

### 3.2 Refresh Token 提取与清除

**文件位置**：`/Users/xu/code/github/dify/api/libs/token.py`
**核心代码**（行 60-100）：

```python
def extract_refresh_token(request: Request) -> str | None:
    """从 Cookie 读取 refresh token。"""
    return request.cookies.get(COOKIE_NAME_REFRESH_TOKEN)


def extract_csrf_token(request: Request) -> str | None:
    """从请求头读取 csrf token（X-CSRF-Token）。"""
    return request.headers.get(HEADER_NAME_CSRF_TOKEN)


def extract_csrf_token_from_cookie(request: Request) -> str | None:
    """从 Cookie 读取 csrf token，用于和请求头对比。"""
    return request.cookies.get(COOKIE_NAME_CSRF_TOKEN)


def extract_access_token(request: Request) -> str | None:
    """从 Authorization 头或 Cookie 读取 access token。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get(COOKIE_NAME_ACCESS_TOKEN)
```

**解读**：
- 第 1-2 行：refresh_token **只从 Cookie 读**（不接受 body/header 传递），避免被前端日志泄露
- 第 5-6 行：csrf_token 从请求头读，前端必须把 Cookie 里的值复制到 `X-CSRF-Token` 头
- 第 10-11 行：csrf_token 从 Cookie 读一份用于和服务端签发的值比对（双重提交 Cookie 模式）
- 第 14-19 行：access_token 优先看 `Authorization: Bearer` 头（API 调用），其次看 Cookie（Web）
- **设计意图**：区分多种调用方式，但 refresh_token 永远只在 Cookie，避免泄露到 URL/body/日志

## 4. 关键要点总结

- 双 Token 方案用短 TTL access + 长 TTL refresh，平衡安全与体验
- **Token 轮换**（Rotation）：每次 refresh 都换新 refresh，旧 refresh 立即作废
- dify 的 refresh token **只从 Cookie 读**，不接受 body/header
- CSRF Token 用**双重提交 Cookie 模式**（Cookie + Header 都带）
- 主动撤销（用户改密码）只能针对 refresh token，access token 只能等过期

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `TokenStore` 类，支持 `issue(user_id)`、`refresh(refresh_token)`、`revoke_all(user_id)` 三个方法，要求 refresh 时**轮换**（旧 refresh 失效）。

### 练习 2：进阶

阅读 `api/controllers/console/auth/login.py:347-377`，为什么 dify 在 `/refresh-token` 接口里把**三个 Cookie 都重新下发**，而不只是更新 access_token？

### 练习 3：挑战（选做）

设计"refresh token 复用检测"：如果同一个 refresh token 被用两次（第二次说明攻击者拿到了它），立即撤销该用户的**所有** refresh token 并要求重新登录。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
- `/Users/xu/code/github/dify/api/libs/token.py`
- OAuth 2.0 Refresh Token：https://datatracker.ietf.org/doc/html/rfc6749#section-6
- OWASP JWT Cheat Sheet：https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13