# 5.1.6 OpenID Connect（OIDC）

> 理解 OAuth 2.0 之上的身份认证层，掌握 OIDC 的核心扩展。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 OAuth 2.0 与 OIDC 的关键区别（授权 vs 认证）
- 掌握 OIDC 的三个核心扩展：ID Token、UserInfo Endpoint、Discovery
- 理解 OIDC 的 ID Token 是 JWT，且包含 `nonce` 防重放
- 能在 dify 中识别哪些流程用了 OIDC（如企业 SSO 登录）

## 📚 前置知识

- 05-oauth2.md（OAuth 2.0 四种流程）
- 03-jwt-auth.md（JWT 结构）

## 1. 核心概念

### 1.1 OAuth 2.0 与 OIDC 的核心区别

| 维度 | OAuth 2.0 | OIDC |
|------|-----------|------|
| 目的 | **授权**（让第三方访问资源） | **认证**（证明用户身份） |
| Token | access_token（访问资源用） | ID Token（包含用户身份）+ access_token |
| 协议层 | IETF 标准 | 在 OAuth 2.0 之上 |
| 是否定义"我是谁" | 否 | 是（通过 `sub` claim） |

**一句话总结**：OAuth 2.0 解决"让 A 代替 B 访问 C 的资源"，OIDC 解决"让 A 告诉 B 用户是谁"。

### 1.2 OIDC 的三个核心扩展

**1. ID Token**：JWT 格式的令牌，**专门**用来"证明用户身份"。

```json
{
  "iss": "https://accounts.google.com",  // 签发方
  "sub": "110169484474386276334",        // 用户在 IdP 内的唯一 ID
  "aud": "client-id-xxx",                // 受众：哪个应用
  "iat": 1735689600,
  "exp": 1735693200,
  "nonce": "abc123",                     // 防重放
  "email": "alice@example.com",
  "name": "Alice"
}
```

**2. UserInfo Endpoint**：用 access_token 调用 `GET /userinfo` 拿最新用户信息。

**3. Discovery**：通过 `/.well-known/openid-configuration` 自动发现 IdP 的所有端点。

### 1.3 为什么需要 `nonce`？

OIDC 在前端发起授权时生成随机 `nonce`，IdP 把这个 `nonce` 放进 ID Token，前端验证时检查 `nonce` 是否与当初一致。这能防御：
- **重放攻击**：攻击者截获 ID Token 试图重用
- **Token 替换**：攻击者把自己的 ID Token 替换给受害者

## 2. 代码示例

### 2.1 验证 ID Token

```python
import jwt

def verify_id_token(id_token: str, client_id: str, issuer: str,
                    expected_nonce: str, jwks_client) -> dict:
    """验证 OIDC ID Token。"""
    # 1. 从 JWT header 拿到 kid，从 JWKS 找到对应公钥
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    public_key = jwks_client.get_signing_key(kid).key

    # 2. 强制验签 + 校验 iss/aud/exp/nonce
    claims = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],      # OIDC 几乎都用非对称
        audience=client_id,        # aud 必须是自己的 client_id
        issuer=issuer,             # iss 必须是可信的 IdP
    )

    # 3. 校验 nonce（防重放）
    if claims.get("nonce") != expected_nonce:
        raise ValueError("nonce mismatch")

    return claims


# 使用示例
claims = verify_id_token(
    id_token="eyJhbGciOiJSUzI1NiIs...",
    client_id="dify-web",
    issuer="https://accounts.google.com",
    expected_nonce="xyz789",
    jwks_client=jwks_client,
)
print(claims["email"])  # alice@example.com
```

### 2.2 常见错误：信任未验证的 `email` 字段

```python
# ❌ 错误：直接相信 ID Token 里的 email，没验签
claims = jwt.decode(id_token, options={"verify_signature": False})
print(claims["email"])  # 攻击者可伪造任意 ID Token

# ✅ 正确：必须验证签名 + iss + aud + nonce
claims = jwt.decode(id_token, public_key, algorithms=["RS256"],
                    audience=client_id, issuer=issuer)
```

## 3. dify 仓库源码解读

### 3.1 OIDC Discovery 与 JWKS

**文件位置**：`/Users/xu/code/github/dify/api/libs/oauth.py`
**核心代码**（典型 OIDC 配置）：

```python
class OIDCClient:
    """OIDC 客户端：通过 discovery 自动发现 IdP 端点。"""

    def __init__(self, issuer: str, client_id: str, client_secret: str):
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        # 自动发现：拉 /.well-known/openid-configuration
        self.metadata = httpx.get(
            f"{issuer}/.well-known/openid-configuration"
        ).json()
        self.authorize_endpoint = self.metadata["authorization_endpoint"]
        self.token_endpoint = self.metadata["token_endpoint"]
        self.jwks_uri = self.metadata["jwks_uri"]

    def get_jwks(self) -> dict:
        """获取 IdP 的公钥集合，用于验证 ID Token 签名。"""
        return httpx.get(self.jwks_uri).json()

    def build_authorize_url(self, state: str, nonce: str) -> str:
        """构造 OIDC 授权 URL（比 OAuth 2.0 多一个 nonce）。"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",  # 必须包含 openid
            "state": state,
            "nonce": nonce,                   # OIDC 特有
        }
        return f"{self.authorize_endpoint}?{urllib.parse.urlencode(params)}"
```

**解读**：
- 第 9-13 行：**Discovery** 是 OIDC 的核心便利——不用手动配置 IdP 端点，调用一个 URL 即可
- 第 18-20 行：JWKS 端点返回 IdP 的公钥集合，用于**非对称验签**（OIDC 默认 RS256）
- 第 23-34 行：`scope` 必须包含 `openid` 才能进入 OIDC 流程；`nonce` 是 OIDC 特有字段
- **设计意图**：让 dify 接入任意支持 OIDC 的 IdP（Google、Auth0、企业 Keycloak 等）无需改代码

### 3.2 dify 中的 OIDC 使用

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/oauth_server.py`
**核心代码**（典型结构）：

```python
class OIDCLoginCallback(Resource):
    """OIDC 登录回调：用户被 IdP 重定向回 dify。"""

    def get(self):
        # 1. 拿 code 和 state
        code = request.args.get("code")
        state = request.args.get("state")
        if not _validate_state(state):
            raise InvalidStateError()

        # 2. 用 code 换 ID Token + access_token
        token_response = oidc_client.exchange_code(code, code_verifier)
        id_token = token_response["id_token"]

        # 3. 验证 ID Token（验签 + nonce）
        claims = verify_id_token(
            id_token,
            client_id=dify_config.OIDC_CLIENT_ID,
            issuer=dify_config.OIDC_ISSUER,
            expected_nonce=session.pop("oidc_nonce"),
            jwks_client=jwks_client,
        )

        # 4. 在 dify 内查找或创建账号
        email = claims["email"]
        account = AccountService.get_or_create_by_email(
            email, name=claims.get("name"), session=db.session()
        )

        # 5. 签发 dify 自己的 access_token / refresh_token
        token_pair = AccountService.login(account, db.session(), ip_address)
        # ... 写入 Cookie 并返回
```

**解读**：
- 第 8-10 行：OIDC 流程第一阶段，Authorization Server 回调带回 code
- 第 14-16 行：`id_token` 是 OIDC 特有的"身份令牌"，**必须验证**才能信任 `claims`
- 第 19-23 行：验签 + 检查 nonce，确保这个 ID Token 确实是给当前会话的
- 第 26-28 行：从 `claims` 拿 email，**自动注册**用户（首次登录）
- 第 31-32 行：登录成功后**不再用 IdP 的 token**，而是签发 dify 自己的 Token
- **设计意图**：用 OIDC 做"首次身份确认"，用 dify 自己的 Session 做"后续请求授权"

## 4. 关键要点总结

- OIDC = OAuth 2.0 + 身份认证层
- 三个核心扩展：**ID Token**（JWT，含用户身份）、**UserInfo**（拉用户信息）、**Discovery**（自动发现端点）
- ID Token 必须验签 + 检查 `iss`、`aud`、`exp`、`nonce`
- OIDC 默认用 **RS256**（非对称），需要从 JWKS 拉公钥
- `nonce` 防重放、`state` 防 CSRF——两者不可混淆

## 5. 练习题

### 练习 1：基础（必做）

用 `pyjwt` 写一个函数 `decode_oidc_id_token(token, jwks)`，自动从 token header 取 `kid`，从 jwks 找公钥验签，返回 claims。手动 mock 一个 IdP 的 JWKS。

### 练习 2：进阶

解释为什么 OIDC 必须用 **RS256（非对称）** 而不是 HS256（对称）。从 IdP 与多个 SP（Service Provider）的场景出发。

### 练习 3：挑战（选做）

设计一个 `OIDCDiscovery` 类，给定 issuer URL，自动完成：发现 metadata、拉 JWKS、解析授权 URL，并支持**多 IdP**（Google + GitHub + 自建 Keycloak）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/oauth_server.py`
- `/Users/xu/code/github/dify/api/libs/oauth.py`
- OpenID Connect Core：https://openid.net/specs/openid-connect-core-1_0.html
- OpenID Connect Discovery：https://openid.net/specs/openid-connect-discovery-1_0.html
- Auth0 入门：https://auth0.com/docs/get-started/openid-connect-discovery

---

**文档版本**：v1.0
**最后更新**：2026-07-13