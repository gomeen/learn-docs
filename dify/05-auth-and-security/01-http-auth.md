# 5.1.1 HTTP 认证基础：Basic / Digest / Bearer

> 理解 HTTP 协议层面的认证机制及其差异，能看懂 dify 接口的 Authorization 头。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 HTTP 协议的三大认证模式：Basic、Digest、Bearer
- 理解它们各自的安全性和适用场景
- 能根据不同接口选择正确的认证方式
- 能看懂 dify 中所有 HTTP 接口的认证流程

## 📚 前置知识

- HTTP 协议基础（请求头、状态码）
- 01-fundamentals/04-typing-annotations.md（TypeHint 基础）

## 1. 核心概念

### 1.1 什么是 HTTP 认证？

HTTP 认证是 **服务端识别客户端身份** 的机制。每次请求，客户端通过 `Authorization` 请求头携带凭证，服务端校验后决定是否放行。

```
┌─────────┐                          ┌─────────┐
│ Client  │  Authorization: Bearer xx │  Server │
│         │ ────────────────────────→ │         │
│         │ ←──────────────────────── │         │
└─────────┘    200 OK / 401            └─────────┘
```

### 1.2 Basic 认证

最简单的方式：把 `username:password` 用 Base64 编码后放在请求头。

```
Authorization: Basic dXNlcjpwYXNz
```

**优点**：简单、易实现。
**缺点**：Base64 不是加密！必须搭配 HTTPS 使用；每次请求都发密码，泄露面大。

```python
import base64

def make_basic_auth(username: str, password: str) -> str:
    """生成 Basic 认证头"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"

# 使用示例
header = make_basic_auth("alice", "secret123")
print(header)  # Basic YWxpY2U6c2VjcmV0MTIz
```

### 1.3 Digest 认证

服务端先发 `401 Unauthorized` + `WWW-Authenticate` 头（携带 `nonce`），客户端再用 `nonce + password` 计算哈希后回传。

```
Server → 401 + WWW-Authenticate: Digest realm="api", nonce="abc123"
Client → GET + Authorization: Digest username="alice", nonce="abc123", response="哈希值"
```

**优点**：密码不在网络上明文传输。
**缺点**：实现复杂、对中间人攻击防御有限，现代项目已较少使用。

### 1.4 Bearer 认证（最主流）

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

客户端拿到一个 **Token**（通常是 JWT），之后每次请求把 Token 放在 `Authorization: Bearer <token>`。

**优点**：服务端无需存储会话（无状态），易于水平扩展。
**缺点**：Token 一旦签发就难以撤销（需要黑名单或短 TTL）。

dify 的 `/v1/chat-messages` 等对外 API 就用 Bearer。

## 2. 代码示例

### 2.1 Python 中三种认证的客户端实现

```python
import base64
import hashlib
import secrets

def basic_auth_header(username: str, password: str) -> dict[str, str]:
    """构造 Basic 认证请求头"""
    raw = f"{username}:{password}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return {"Authorization": f"Basic {encoded}"}


def digest_auth_header(username: str, password: str, method: str,
                       uri: str, nonce: str) -> dict[str, str]:
    """构造 Digest 认证请求头（简化版，演示用）"""
    # HA1 = MD5(username:realm:password)
    ha1 = hashlib.md5(f"{username}:api:{password}".encode()).hexdigest()
    # HA2 = MD5(method:uri)
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    # response = MD5(HA1:nonce:HA2)
    response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    return {
        "Authorization": (
            f'Digest username="{username}", nonce="{nonce}", '
            f'uri="{uri}", response="{response}"'
        )
    }


def bearer_auth_header(token: str) -> dict[str, str]:
    """构造 Bearer 认证请求头"""
    return {"Authorization": f"Bearer {token}"}


# 测试
print(basic_auth_header("alice", "secret"))
print(bearer_auth_header("eyJhbGciOiJIUzI1NiJ9.payload.sig"))
```

### 2.2 服务端校验 Bearer Token（伪代码）

```python
from flask import request, abort, jsonify

# 假设 dify 风格的接口
def protected_endpoint():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Missing or malformed Authorization header")

    token = auth_header[7:]  # 去掉 "Bearer "
    # 实际中会查 DB 或验签 JWT
    if not is_valid_token(token):
        abort(401, description="Invalid or expired token")

    user = get_user_from_token(token)
    return jsonify({"hello": user.name})
```

## 3. dify 仓库源码解读

### 3.1 Basic 认证：密码字段加密传输

**文件位置**：`/Users/xu/code/github/dify/api/libs/encryption.py`
**核心代码**（行 17-40）：

```python
class FieldEncryption:
    """Handle decoding of sensitive fields during transmission"""

    @classmethod
    def decrypt_field(cls, encoded_text: str) -> str | None:
        """
        Decode Base64 encoded field from frontend.

        Args:
            encoded_text: Base64 encoded text from frontend

        Returns:
            Decoded plaintext, or None if decoding fails
        """
        try:
            # Decode base64
            decoded_bytes = base64.b64decode(encoded_text)
            decoded_text = decoded_bytes.decode("utf-8")
            logger.debug("Field decoding successful")
            return decoded_text

        except Exception:
            # Decoding failed - return None to trigger error in caller
            return None
```

**解读**：
- 第 33 行：`base64.b64decode` 解码前端传来的密码——这只是 **Base64 编码而非真正的加密**
- 第 38 行：注释明确说明"Real security relies on HTTPS"，Base64 只是前端做了简单混淆
- **设计意图**：避免密码在网络层明文可见（HTTP 抓包看到的就是乱码），但真实保护靠 HTTPS

### 3.2 Bearer 认证：API Key 校验

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 175-201）：

```python
@console_ns.route("/apps/<uuid:resource_id>/api-keys")
class AppApiKeyListResource(BaseApiKeyListResource):
    @console_ns.doc("get_app_api_keys")
    @console_ns.doc(description="Get all API keys for an app")
    @console_ns.doc(params={"resource_id": "App ID"})
    @console_ns.response(200, "API keys retrieved successfully", console_ns.models[ApiKeyList.__name__])
    @with_current_tenant_id
    def get(self, current_tenant_id: str, resource_id: UUID) -> dict[str, object]:
        """Get all API keys for an app"""
        return dump_response(ApiKeyList, self._get_api_key_list(str(resource_id), current_tenant_id))
```

**解读**：
- **关键设计**：dify 的"应用 API Key"采用 `app-` 前缀 + 24 位随机串（见 `models/model.py:2254` 的 `generate_api_key`）
- 调用方在 `Authorization: Bearer app-xxxxxxxx` 中携带这种 Key
- 这是典型的 Bearer 模式：Key 由服务端签发、客户端持有、每次请求携带

## 4. 关键要点总结

- **Basic**：Base64 编码的 `user:pass`，简单但必须配 HTTPS
- **Digest**：基于 nonce + 哈希，比 Basic 安全但实现复杂
- **Bearer**：现代主流，配合 JWT 实现无状态认证
- dify 的密码字段在 HTTP 层做了 Base64 混淆，**真实加密靠 HTTPS**
- dify 的应用 API Key 本质就是 Bearer Token：`app-` 前缀 + 24 位随机串

## 5. 练习题

### 练习 1：基础（必做）

实现一个函数 `parse_auth_header(header: str) -> tuple[str, str] | None`，能解析 `Basic xxx`、`Bearer xxx`、`Digest xxx` 三种头并返回 `(scheme, credentials)`，无法识别返回 `None`。

### 练习 2：进阶

阅读 `api/libs/encryption.py`，为什么 dify 选择 Base64 而不是真正的加密？这种"假加密"在什么场景下是合理的？

### 练习 3：挑战（选做）

设计一个支持 Basic + Bearer 双模式的 Flask 装饰器 `@require_auth`，根据 `Authorization` 头自动分发到 Basic 校验或 Bearer 校验。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/encryption.py`
- `/Users/xu/code/github/dify/api/controllers/console/apikey.py`
- `/Users/xu/code/github/dify/api/models/model.py`（`ApiToken` 模型）
- MDN HTTP Authentication：https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication
- RFC 7617（Basic）：https://datatracker.ietf.org/doc/html/rfc7617
- RFC 6750（Bearer）：https://datatracker.ietf.org/doc/html/rfc6750

---

**文档版本**：v1.0
**最后更新**：2026-07-13