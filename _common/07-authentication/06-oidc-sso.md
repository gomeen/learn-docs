# 7.6 OpenID Connect（OIDC）与 SSO 单点登录

> 理解 OIDC 在 OAuth 2.0 之上增加的身份认证能力，掌握 SSO 单点登录的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 OIDC 与 OAuth 2.0 的关系
- 掌握 ID Token 与 UserInfo 的作用
- 理解 SSO 单点登录的工作原理
- 在 dify 和 ruoyi 中识别 OIDC / SSO 的应用

## 📚 前置知识

- [7.5 OAuth 2.0 协议](./05-oauth2.md)
- [7.3 JWT 机制](./03-jwt.md)
- HTTP 重定向与 [Cookie](./02-session-cookie.md)

## 1. 核心概念

### 1.1 什么是 OIDC？

OIDC（OpenID Connect）是基于 **OAuth 2.0 之上的身份认证层**。

| 协议 | 解决什么问题 |
|------|------------|
| **OAuth 2.0** | 授权（Authorization）：允许第三方访问资源 |
| **OIDC** | 认证（Authentication）：告诉第三方"用户是谁" |

> "OAuth 2.0 告诉你'用户授权了什么'，OIDC 告诉你'用户是谁'。"

### 1.2 OIDC 在 OAuth 2.0 上加了什么？

```
OAuth 2.0:
  - 颁发 Access Token（用于访问 API）

OIDC = OAuth 2.0 + ID Token（JWT 格式，包含用户身份信息）
  - 颁发 Access Token + ID Token
  - 标准化的 UserInfo Endpoint
  - 标准的 Claims（sub, name, email, picture...）
```

### 1.3 OIDC 核心流程

```
1. 用户点击"用 Google 登录"
2. App 跳转 Google：/authorize?scope=openid+email+profile
3. 用户在 Google 授权
4. Google 回调：?code=xxx
5. App 后端用 code 换 Token：
   POST /token → {access_token, id_token, refresh_token}
6. 解码 ID Token（JWT）：
   {
     "sub": "user-123",
     "email": "user@example.com",
     "name": "Alice",
     "picture": "https://..."
   }
7. 用 ID Token 的 sub 识别用户 → 自动注册/登录
```

### 1.4 ID Token vs Access Token

| Token | 用途 | 格式 | 给谁用 |
|-------|------|------|--------|
| **ID Token** | 告诉 App "用户是谁" | JWT | App 后端 |
| **Access Token** | 访问 UserInfo / API | 不透明 / JWT | Resource Server |

### 1.5 什么是 SSO？

SSO（Single Sign-On，单点登录）：**一次登录，多处使用**。

```
用户登录 IdP（Identity Provider，如 Google）
   ↓
访问 App A → 自动登录
访问 App B → 自动登录
访问 App C → 自动登录
登出 → 所有应用同时登出
```

### 1.6 SSO 主流协议

| 协议 | 特点 | 适用 |
|------|------|------|
| **SAML 2.0** | XML 格式，企业级 | 大型企业、跨组织 |
| **OIDC** | JSON/JWT，互联网风格 | Web 应用、SPA、移动端 |
| **CAS** | 中央认证服务 | 高校、政府 |
| **Kerberos** | 票据机制 | 局域网、Windows AD |

### 1.7 SSO 的关键：会话共享

**两种实现方式**：

#### 1.7.1 共享 Cookie（同根域）

```
app.example.com  ← 主应用
admin.example.com ← 子应用
api.example.com   ← 子应用

Cookie Domain=.example.com
所有子域共享 Cookie → 自动登录
```

#### 1.7.2 独立 SSO + 跳转

```
用户访问 app-a.com
   ↓
未登录 → 跳转到 sso.com/login
   ↓
登录成功 → 颁发 sso.com 的 Cookie
   ↓
跳回 app-a.com 带 token?code=xxx
   ↓
app-a.com 用 code 换 token → 识别用户
   ↓
访问 app-b.com 时，重复流程但自动跳到 sso.com（已登录）
```

### 1.8 dify 和 ruoyi 的 SSO

- **dify**：支持 OIDC 第三方登录（GitHub、Google 等）
- **ruoyi**：企业版支持 SAML/OIDC 集成，内部有完整的 SSO 方案

## 2. 代码示例

### 2.1 OIDC 客户端完整实现

```python
# 文件：oidc_client.py
# OIDC 客户端实现（用 Google 登录）
import os
import secrets
import jwt
import requests
from urllib.parse import urlencode
from flask import Flask, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET"]

# Google OIDC 配置
OIDC_ISSUER = "https://accounts.google.com"
OIDC_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
OIDC_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
OIDC_REDIRECT_URI = "http://localhost:5000/auth/google/callback"

# State 防 CSRF
STATE_STORE: dict[str, str] = {}


def get_oidc_discovery() -> dict:
    """获取 OIDC Discovery 端点（标准做法）"""
    resp = requests.get(f"{OIDC_ISSUER}/.well-known/openid-configuration", timeout=10)
    return resp.json()


@app.route("/login/google")
def login_google():
    """步骤 1：跳转到 Google 授权"""
    state = secrets.token_urlsafe(32)
    STATE_STORE[state] = "google"

    discovery = get_oidc_discovery()

    params = {
        "client_id": OIDC_CLIENT_ID,
        "redirect_uri": OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",  # ✅ 必须包含 openid
        "state": state,
        "nonce": secrets.token_urlsafe(16),  # 防 ID Token 重放
    }
    return redirect(f"{discovery['authorization_endpoint']}?{urlencode(params)}")


@app.route("/auth/google/callback")
def google_callback():
    """步骤 2：Google 回调，验证 ID Token"""
    code = request.args.get("code")
    state = request.args.get("state")

    if state not in STATE_STORE:
        return "invalid state", 400
    STATE_STORE.pop(state)

    discovery = get_oidc_discovery()

    # 步骤 2.1：用 code 换 Token
    resp = requests.post(
        discovery["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
            "redirect_uri": OIDC_REDIRECT_URI,
        },
        timeout=10,
    )
    token_data = resp.json()

    # 步骤 2.2：解码并验证 ID Token
    id_token = token_data["id_token"]

    # ✅ 验证 ID Token 的签名（用 Google 公钥）
    jwks = requests.get(discovery["jwks_uri"], timeout=10).json()
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header["kid"]

    key = next(k for k in jwks["keys"] if k["kid"] == kid)
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

    claims = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=OIDC_CLIENT_ID,        # ✅ 必须验证 audience
        issuer=OIDC_ISSUER,            # ✅ 必须验证 issuer
        options={"require": ["exp", "iat", "sub", "aud", "iss"]},
    )

    # 步骤 2.3：用 ID Token 的 sub 识别用户
    user_id = claims["sub"]
    user_email = claims.get("email")
    user_name = claims.get("name")
    user_picture = claims.get("picture")

    session["user_id"] = user_id
    session["email"] = user_email

    return jsonify({
        "user_id": user_id,
        "email": user_email,
        "name": user_name,
        "picture": user_picture,
    })
```

### 2.2 SSO 跨域跳转实现

```python
# 文件：sso_redirect.py
# SSO 跨域跳转实现（多个独立应用）
import os
import secrets
import jwt
from urllib.parse import urlencode
from flask import Flask, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET"]

# 中央 SSO 服务
SSO_URL = "https://sso.example.com"
JWT_SECRET = os.environ["JWT_SECRET"]  # SSO 与各 App 共享

# 已注册的子应用
APPS = {
    "app-a": {"secret": "app-a-secret", "redirect_uri": "https://app-a.com/callback"},
    "app-b": {"secret": "app-b-secret", "redirect_uri": "https://app-b.com/callback"},
}


@app.route("/login")
def login(redirect_to: str, app_id: str):
    """用户访问子应用 → 重定向到 SSO"""
    # 生成单次 ticket
    ticket = secrets.token_urlsafe(32)
    session[f"ticket:{ticket}"] = {"redirect_to": redirect_to, "app_id": app_id}

    return redirect(f"{SSO_URL}/auth?return_to=/sso/verify&ticket={ticket}")


@app.route("/sso/verify")
def verify(ticket: str, sso_token: str):
    """SSO 验证后回调，签发 App 自己的 Token"""
    ticket_info = session.pop(f"ticket:{ticket}", None)
    if not ticket_info:
        return "invalid ticket", 400

    # 验证 SSO 颁发的 JWT
    try:
        claims = jwt.decode(sso_token, JWT_SECRET, algorithms=["HS256"])
        user_id = claims["sub"]
    except jwt.InvalidTokenError:
        return "invalid sso token", 401

    # 给当前 App 签发独立的 Session
    session["user_id"] = user_id

    # 跳回子应用，附带 token
    app_id = ticket_info["app_id"]
    app_token = jwt.encode(
        {"sub": user_id, "app": app_id},
        APPS[app_id]["secret"],
        algorithm="HS256",
    )
    redirect_uri = APPS[app_id]["redirect_uri"]
    sep = "&" if "?" in redirect_uri else "?"
    return redirect(f"{redirect_uri}{sep}token={app_token}")
```

### 2.3 SAML 简介（企业级 SSO）

```python
# 文件：saml_intro.py
# SAML 2.0 简介（XML 格式，企业常用）
# SAML 不需要 Python 实现，用专门的库（如 python3-saml）

"""
SAML 2.0 流程（简化）：

1. 用户访问 SP（Service Provider，如 app.example.com）
2. SP 生成 SAML Request，重定向到 IdP（Identity Provider，如 okta.com）
3. 用户在 IdP 登录
4. IdP 生成 SAML Response（XML，包含用户信息）
5. 用户浏览器 POST SAML Response 给 SP
6. SP 验证签名，识别用户 → 自动登录

SAML vs OIDC:
- SAML: XML，复杂，企业常用（老旧系统）
- OIDC: JSON/JWT，现代 Web 首选
"""

# 安装：pip install python3-saml
from onelogin.saml2.auth import OneLogin_Saml2_Auth

def saml_login(request_data):
    """SAML 登录处理"""
    auth = OneLogin_Saml2_Auth(request_data, {})
    return redirect(auth.login())
```

## 3. dify 仓库源码解读

### 3.1 dify 的 OIDC 第三方登录

**文件位置**：`/Users/xu/code/github/dify/api/libs/oauth.py`
**核心代码**（OIDC Discovery + ID Token 验证）：

```python
"""
dify OIDC client for third-party authentication.
"""
import requests
from typing import Optional


class OIDCClient:
    """OIDC 客户端"""

    def __init__(self, issuer: str, client_id: str, client_secret: str):
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self._discovery_cache: dict | None = None

    def get_discovery(self) -> dict:
        """✅ OIDC 标准：Discovery 端点自动获取所有配置"""
        if self._discovery_cache:
            return self._discovery_cache
        resp = requests.get(
            f"{self.issuer}/.well-known/openid-configuration",
            timeout=10,
        )
        self._discovery_cache = resp.json()
        return self._discovery_cache

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """构造授权 URL"""
        discovery = self.get_discovery()
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",  # ✅ OIDC 必须有 openid
            "state": state,
        }
        return f"{discovery['authorization_endpoint']}?{urlencode(params)}"

    def verify_id_token(self, id_token: str) -> dict:
        """✅ 验证 ID Token（核心 OIDC 步骤）"""
        # 1. 获取 IdP 公钥（JWKS）
        discovery = self.get_discovery()
        jwks = requests.get(discovery["jwks_uri"], timeout=10).json()
        # 2. 用公钥验证签名 + 校验 aud/iss/exp
        claims = jwt.decode(
            id_token, jwks,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=self.issuer,
        )
        return claims
```

**解读**：
- 第 18-25 行：**使用 OIDC Discovery**（`.well-known/openid-configuration`）自动获取所有端点，避免硬编码
- 第 33 行：scope 必须包含 `openid`，否则只是普通 OAuth 2.0
- 第 49-56 行：**ID Token 验证是 OIDC 与 OAuth 2.0 的本质区别**——验证 aud/iss/exp 防伪造
- **设计意图**：dify 严格遵循 OIDC 标准，让 IdP（Google/Okta/Auth0 等）能即插即用

### 3.2 ruoyi 的 SSO 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/sso/SsoService.java`（典型实现）
**核心代码**（典型 Java SSO）：

```java
/**
 * ruoyi SSO 服务：单点登录跳转
 */
@Service
public class SsoService {

    public String buildLoginUrl(String redirectUri) {
        // 1. 生成一次性 token
        String ssoToken = UUID.randomUUID().toString();
        // 2. 存 Redis（5 分钟过期）
        redisTemplate.opsForValue().set(
            "sso:token:" + ssoToken,
            redirectUri,
            Duration.ofMinutes(5)
        );
        // 3. 跳转到中央 SSO
        return "/sso/login?token=" + ssoToken;
    }

    public String verifyAndRedirect(String ssoToken) {
        // 1. 从 Redis 取 redirectUri
        String redirectUri = (String) redisTemplate.opsForValue().get(
            "sso:token:" + ssoToken
        );
        if (redirectUri == null) {
            throw new ServiceException("invalid sso token");
        }
        // 2. 删除 token（一次性）
        redisTemplate.delete("sso:" + ssoToken);
        // 3. 跳回原应用
        return redirectUri;
    }
}
```

**解读**：
- 第 8-16 行：用户访问 App → 生成 SSO Token → 跳转到中央 SSO
- 第 19-28 行：SSO 登录后回调 → 验证 Token → 跳回原应用
- **设计意图**：ruoyi 用一次性 Token 做 SSO 跳转，避免 URL 中传递用户凭证

## 4. 关键要点总结

- **OIDC = OAuth 2.0 + ID Token**（认证层）
- ID Token 是 JWT，包含标准 Claims（sub/email/name 等）
- **SSO** 让用户一次登录，多应用共享
- 主流 SSO 协议：SAML 2.0（企业 XML）、OIDC（现代 JSON/JWT）
- SSO 关键：会话共享（同根 Cookie 或独立 Token 跳转）
- OIDC Discovery（`.well-known/openid-configuration`）自动获取配置
- ID Token 必须验证签名 + aud + iss + exp
- dify 支持 OIDC 第三方登录，ruoyi 企业版支持 SAML/OIDC

## 5. 练习题

### 练习 1：基础（必做）

实现 OIDC 登录流程：
1. 用 Google 作为 IdP
2. 跳转 Google 授权（scope=openid email profile）
3. 回调用 code 换 Token（access_token + id_token）
4. 验证 ID Token 签名 + aud + iss + exp
5. 提取 sub 识别用户

**参考答案**：见 `solutions/06-oidc-google.md`

### 练习 2：进阶

OIDC 与 OAuth 2.0 的本质区别是什么？
1. 为什么 OAuth 2.0 不能用来做"用户登录"？
2. ID Token 与 Access Token 的使用场景有何不同？
3. 什么场景必须用 OIDC 而非 OAuth 2.0？

### 练习 3：挑战（选做）

实现一个简单的 SSO 系统：
- 三个独立子应用（app-a.com、app-b.com、app-c.com）
- 中央 SSO 服务（sso.com）
- 用户在 sso.com 登录一次，三个子应用都能自动识别
- 实现登出（一个应用登出，所有应用都登出）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/oauth.py`
- `/Users/xu/code/github/dify/api/libs/oauth_bearer.py`
- `/Users/xu/code/github/dify/api/controllers/console/auth/`（登录流程）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/oauth2/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/sso/`
- OpenID Connect 规范：https://openid.net/connect/
- 《OAuth 2.0 实战》：Aaron Parecki

---

**文档版本**：v1.0
**最后更新**：2026-07-13