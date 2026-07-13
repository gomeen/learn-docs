# 5.1.5 OAuth 2.0 协议

> 理解 OAuth 2.0 四种授权流程，能看懂 dify 的 OAuth 数据源集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 OAuth 2.0 的核心角色（Resource Owner、Client、Authorization Server、Resource Server）
- 理解四种授权流程：Authorization Code、Implicit、Client Credentials、Password
- 理解为何 dify 选用 Authorization Code + PKCE
- 能看懂 dify 中 `data_source_oauth.py` 的实现

## 📚 前置知识

- 03-jwt-auth.md
- 02-session-auth.md

## 1. 核心概念

### 1.1 OAuth 2.0 解决什么问题？

传统方式：你把你的 **GitHub 密码**给第三方应用，它才能访问你的仓库。问题：
- 第三方拿走密码，能干任何事
- 你不能单独撤销它的访问（只能改密码）
- 密码泄露影响所有授权

**OAuth 2.0** 引入"**授权而非登录**"：你授权第三方用"令牌"代替你的密码访问特定资源。

### 1.2 四个核心角色

```
┌──────────────────┐       ┌──────────────────┐
│ Resource Owner   │       │ Client           │
│ (用户: Alice)    │       │ (Dify 这种应用)   │
└──────────────────┘       └──────────────────┘
        │                         │
        │ 授权                    │ 请求授权
        ▼                         ▼
┌──────────────────────────────────────────┐
│ Authorization Server (GitHub/Google)      │
│ - 颁发 access_token                       │
└──────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│ Resource Server (API 提供方)              │
└──────────────────────────────────────────┘
```

### 1.3 四种授权流程对比

| 流程 | 适用场景 | 是否需要用户参与 |
|------|---------|----------------|
| **Authorization Code** | 有后端的 Web 应用 | 是 |
| **Authorization Code + PKCE** | 移动端 / SPA（dify 用此） | 是 |
| **Client Credentials** | 服务对服务（无用户） | 否 |
| **Password** | 用户高度信任 Client | 是（已弃用） |
| **Implicit** | 纯前端 SPA（已弃用） | 是 |

### 1.4 Authorization Code + PKCE 流程

```
1. Client → 用户: 跳转到 Authorization Server
   (URL 带 client_id, redirect_uri, code_challenge, state)

2. 用户: 在 Authorization Server 上登录并同意授权

3. Authorization Server → Client: 重定向回 redirect_uri
   (URL 带 ?code=xxx&state=yyy)

4. Client → Authorization Server:
   POST /token (code + code_verifier)

5. Authorization Server → Client:
   { access_token, refresh_token, expires_in }
```

**PKCE**（Proof Key for Code Exchange）= 用 `code_verifier` 哈希作为 `code_challenge`，防止授权码被中间人截获。

## 2. 代码示例

### 2.1 简化版 OAuth 2.0 Authorization Code 客户端

```python
import hashlib
import secrets
import base64
import urllib.parse

def generate_pkce_pair() -> tuple[str, str]:
    """生成 PKCE 的 code_verifier 和 code_challenge"""
    # 1. 生成 43~128 字符的随机串
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    # 2. 哈希后做 challenge
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(client_id: str, redirect_uri: str, scope: str) -> str:
    """构造跳转到 Authorization Server 的 URL"""
    verifier, challenge = generate_pkce_pair()
    # 把 verifier 存到 session，供第二步换 token 用
    state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"https://auth.example.com/authorize?{urllib.parse.urlencode(params)}", verifier, state


def exchange_code_for_token(client_id: str, redirect_uri: str,
                            code: str, verifier: str) -> dict:
    """用授权码换 access_token"""
    # POST https://auth.example.com/token
    # body: { grant_type: "authorization_code", code, redirect_uri,
    #         client_id, code_verifier: verifier }
    # 返回: { access_token, refresh_token, expires_in }
    return {"access_token": "xxx", "expires_in": 3600}
```

### 2.2 常见错误：把 access_token 存在前端

```python
# ❌ 错误：把 token 直接渲染到 HTML（会被 XSS 偷）
return f'<script>localStorage.setItem("token", "{token}")</script>'

# ✅ 正确：token 存服务端 Session 或 HttpOnly Cookie
session["access_token"] = token
resp.set_cookie("access_token", token, httponly=True)
```

## 3. dify 仓库源码解读

### 3.1 OAuth 集成路由

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/data_source_oauth.py`
**核心代码**（典型结构）：

```python
@console_ns.route("/oauth/data-source/<string:provider>/callback")
class OAuthDataSourceCallback(Resource):
    """OAuth 数据源回调：用户授权后跳回此接口。"""

    def get(self, provider: str):
        # 1. 校验 state（防 CSRF）
        state = request.args.get("state")
        if not _validate_state(state):
            raise InvalidStateError()

        # 2. 从 URL 拿授权码
        code = request.args.get("code")
        if not code:
            raise OAuthError("missing authorization code")

        # 3. 用 code 换 token
        token_info = OAuthService.exchange_code_for_token(
            provider=provider, code=code, session=db.session(),
        )

        # 4. 把 token 绑定到当前用户的 tenant
        ApiKeyAuthService.create_provider_auth(
            tenant_id=current_tenant_id,
            args={"provider": provider, "credentials": token_info},
            session=db.session(),
        )
        return {"result": "success"}
```

**解读**：
- 第 6-9 行：**先校验 `state`** 是 OAuth 2.0 防御 CSRF 的关键步骤
- 第 12-14 行：从 query string 取 `code`（Authorization Code 流程）
- 第 17-20 行：用 `code` 调 OAuth 服务换 token（这一步是**服务端到服务端**调用，不暴露在前端）
- 第 23-28 行：把得到的 token **绑定到当前 tenant**，写入 DB
- **设计意图**：用户授权一次后，dify 可以代表用户访问数据源 API（如 Notion、Google Drive）

### 3.2 OAuth Provider 配置

**文件位置**：`/Users/xu/code/github/dify/api/libs/oauth.py`
**核心代码**（典型结构）：

```python
class OAuthProvider:
    """封装 OAuth provider 的发现与 token 交换逻辑。"""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorize_url(self, state: str, code_challenge: str) -> str:
        """构造跳转到 OAuth provider 的 URL。"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.authorize_endpoint}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> dict:
        """用授权码 + PKCE verifier 换 token。"""
        response = httpx.post(
            self.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code_verifier": code_verifier,
            },
        )
        response.raise_for_status()
        return response.json()
```

**解读**：
- 第 1-9 行：`OAuthProvider` 把"配置 + 流程"封装成对象，每个 provider 一个实例
- 第 11-25 行：`get_authorize_url` 自动构造标准的 OAuth 2.0 URL（含 PKCE）
- 第 27-39 行：`exchange_code` 是 server-to-server 调用，**用 client_secret 鉴权**
- **设计意图**：把 OAuth 协议的所有样板代码封装起来，业务代码只需调用 `get_authorize_url()` 和 `exchange_code()`

## 4. 关键要点总结

- OAuth 2.0 是**授权**协议，不是**认证**协议（不验证用户身份，只授权访问资源）
- **Authorization Code + PKCE** 是现代 Web/SPA 的首选流程
- **state 参数**防 CSRF，**PKCE** 防授权码被截获
- dify 用 OAuth 让用户把"数据源"（Notion 等）的访问权授权给 Dify
- **client_secret 永远不能放到前端**，只能服务端持有

## 5. 练习题

### 练习 1：基础（必做）

用 Python 写一个函数 `simulate_oauth_flow()`，模拟完整的 Authorization Code + PKCE 流程：生成 verifier/challenge、构造 URL、模拟授权码、用 code + verifier 换 token。

### 练习 2：进阶

阅读 `api/libs/oauth.py`，解释 `code_verifier` 和 `code_challenge` 的关系，以及为什么 PKCE 能防御授权码被截获的攻击。

### 练习 3：挑战（选做）

扩展 `OAuthProvider`，添加 refresh_token 流程：access_token 过期后自动用 refresh_token 换新，并把新 token 持久化到 DB。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/data_source_oauth.py`
- `/Users/xu/code/github/dify/api/libs/oauth.py`
- RFC 6749（OAuth 2.0）：https://datatracker.ietf.org/doc/html/rfc6749
- RFC 7636（PKCE）：https://datatracker.ietf.org/doc/html/rfc7636
- OAuth 2.0 Simplified：https://www.oauth.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13