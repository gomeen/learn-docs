# 7.5 OAuth 2.0 协议详解

> 理解 OAuth 2.0 四种授权流程，能识别"授权"与"认证"的本质区别。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 OAuth 2.0 的核心角色与令牌概念
- 区分 Authorization Code、Client Credentials、Password、Implicit 四种模式
- 在 dify 和 ruoyi 中识别 OAuth 2.0 的应用
- 为第三方应用集成选择合适的授权模式

## 📚 前置知识

- 7.3 JWT 机制
- HTTP 重定向与回调
- 7 认证系列前置

## 1. 核心概念

### 1.1 OAuth 2.0 是什么？

OAuth 2.0 是一个**授权**（Authorization）协议，让第三方应用**有限访问**用户在某个服务上的资源。

**OAuth ≠ 认证**：OAuth 不告诉你"用户是谁"，只告诉你"用户授权第三方访问某些资源"。

> "OAuth 2.0 之于授权，就像 JWT 之于令牌——它是行业标准。"

### 1.2 核心角色

```
┌────────────┐
│ Resource   │ ← 资源所有者（用户）
│ Owner      │
└────────────┘
       │ 授权
       ↓
┌────────────┐
│  Client    │ ← 第三方应用
│ (App)      │
└────────────┘
       │ 用令牌访问
       ↓
┌────────────┐
│  Resource  │ ← 受保护资源 API
│  Server    │
└────────────┘
       ↑
       │ 颁发令牌
┌────────────┐
│ Auth       │ ← 授权服务器
│ Server     │
└────────────┘
```

### 1.3 令牌类型

| 令牌 | 用途 | 生命周期 |
|------|------|---------|
| **Authorization Code** | 短期，换 Access Token | 一次性，10 分钟 |
| **Access Token** | 访问资源 API | 短期，1 小时 |
| **Refresh Token** | 换新 Access Token | 长期，30 天 |

### 1.4 四种授权模式

#### 1.4.1 Authorization Code（最常用，Web 应用）

```
1. 用户点击"用 GitHub 登录"
2. 跳转到 GitHub: https://github.com/login/oauth/authorize
                 ?client_id=xxx
                 &redirect_uri=https://app.com/callback
                 &response_type=code
                 &scope=user:email
3. 用户在 GitHub 授权
4. GitHub 回调 https://app.com/callback?code=abc123
5. App 后端用 code 换 Access Token:
   POST https://github.com/login/oauth/access_token
        {code, client_id, client_secret, redirect_uri}
6. GitHub 返回 Access Token
7. App 用 Access Token 访问 GitHub API
```

**优点**：最安全，code 不暴露给前端
**缺点**：需要后端参与

#### 1.4.2 Client Credentials（机器对机器）

```
1. 后端服务用 client_id + client_secret 直接换 Access Token
2. 不需要用户参与
```

**用途**：微服务间调用、定时任务
**典型场景**：ruoyi 用此模式做内部服务调用

#### 1.4.3 Password（遗留，不推荐）

```
1. 用户把用户名密码给第三方
2. 第三方直接换 Access Token
```

**问题**：第三方能拿到密码，违反最小权限原则
**现状**：仅用于"高度信任的第一方应用"

#### 1.4.4 Implicit（遗留，已废弃）

```
1. 直接返回 Access Token（无 code 中转）
```

**问题**：Token 暴露在 URL，易被劫持
**现状**：OAuth 2.1 已移除，**不要再用**

### 1.5 PKCE（Proof Key for Code Exchange）

授权码模式的增强版，防止 code 被劫持：

```
1. 客户端生成 code_verifier（随机字符串）
2. 计算 code_challenge = SHA256(code_verifier)
3. 授权请求带 code_challenge
4. 换 Token 时带 code_verifier
5. 服务端验证 SHA256(code_verifier) == code_challenge
```

**用途**：移动端、SPA（防止恶意应用截获 code）

### 1.6 dify 和 ruoyi 的 OAuth 2.0 应用

| 项目 | 应用 |
|------|------|
| **dify** | 第三方 OAuth 登录（GitHub、Google）|
| **ruoyi** | 自建 OAuth2 服务（`yudao-module-system` 提供授权服务器）|

## 2. 代码示例

### 2.1 完整的 Authorization Code 流程（GitHub 登录）

```python
# 文件：oauth2_authorization_code.py
# OAuth 2.0 Authorization Code 模式实现（GitHub 登录）
import os
import secrets
import requests
from urllib.parse import urlencode
from flask import Flask, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET"]

# GitHub OAuth App 配置（在 GitHub Settings > Developer settings 注册）
GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]
GITHUB_REDIRECT_URI = "http://localhost:5000/auth/github/callback"

# State：CSRF 防护
STATE_STORE: dict[str, str] = {}


@app.route("/login/github")
def login_github():
    """步骤 1：跳转用户到 GitHub 授权"""
    # 生成随机 state 防 CSRF
    state = secrets.token_urlsafe(32)
    STATE_STORE[state] = "github"

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "user:email",        # 申请的权限范围
        "state": state,                # CSRF 防护
        "allow_signup": "true",
    }
    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return redirect(github_auth_url)


@app.route("/auth/github/callback")
def github_callback():
    """步骤 2：GitHub 回调，用 code 换 Access Token"""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return f"GitHub auth failed: {error}", 400

    # ✅ 校验 state（防 CSRF）
    if state not in STATE_STORE:
        return "invalid state", 400
    STATE_STORE.pop(state)

    # 用 code 换 Access Token
    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_REDIRECT_URI,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_data = resp.json()

    if "access_token" not in token_data:
        return f"failed to get token: {token_data}", 400

    access_token = token_data["access_token"]

    # 用 Access Token 获取用户信息
    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    user = user_resp.json()

    # ✅ 创建本地会话（或查找已有用户）
    session["user_id"] = user["login"]
    session["github_token"] = access_token

    return jsonify({
        "user": user["login"],
        "name": user["name"],
        "email": user.get("email"),
    })
```

### 2.2 Client Credentials 模式（机器对机器）

```python
# 文件：oauth2_client_credentials.py
# OAuth 2.0 Client Credentials 模式（服务间调用）
import os
import requests
from datetime import datetime, timedelta

# 服务 A 的凭证（向授权服务器注册获得）
CLIENT_ID = os.environ["SERVICE_A_CLIENT_ID"]
CLIENT_SECRET = os.environ["SERVICE_A_CLIENT_SECRET"]
TOKEN_URL = "https://auth.example.com/oauth2/token"

# Token 缓存
_token_cache: dict = {}


def get_service_token() -> str:
    """获取服务调用的 Access Token（带缓存）"""
    now = datetime.utcnow()

    # 缓存有效期内直接返回
    if _token_cache.get("access_token") and _token_cache["expires_at"] > now:
        return _token_cache["access_token"]

    # 重新获取
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "api.read api.write",
        },
        timeout=10,
    )
    data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + timedelta(seconds=data["expires_in"] - 60)

    return data["access_token"]


def call_service_b():
    """服务 A 调用服务 B"""
    token = get_service_token()
    return requests.get(
        "https://service-b.example.com/api/data",
        headers={"Authorization": f"Bearer {token}"},
    )
```

### 2.3 PKCE 增强（SPA / 移动端）

```python
# 文件：oauth2_pkce.py
# OAuth 2.0 + PKCE（适用于 SPA 和移动应用）
import os
import secrets
import hashlib
import base64
from urllib.parse import urlencode

def generate_pkce_pair() -> tuple[str, str]:
    """生成 PKCE 的 code_verifier 和 code_challenge"""
    # 1. 生成 code_verifier（43-128 字符的随机字符串）
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

    # 2. 计算 code_challenge = SHA256(code_verifier)
    challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode()

    return code_verifier, code_challenge


# 步骤 1：跳转授权（带上 code_challenge）
def redirect_to_auth():
    verifier, challenge = generate_pkce_pair()
    # 保存 verifier 到 session（用于回调时验证）
    session["pkce_verifier"] = verifier

    params = {
        "client_id": "your-spa-client",
        "redirect_uri": "https://app.com/callback",
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": secrets.token_urlsafe(16),
    }
    return redirect(f"https://auth.example.com/authorize?{urlencode(params)}")


# 步骤 2：回调换 Token（带上 code_verifier）
def callback(code: str):
    verifier = session.pop("pkce_verifier")

    resp = requests.post(
        "https://auth.example.com/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": "your-spa-client",
            "code_verifier": verifier,  # ✅ 用 verifier 而不是 client_secret
        },
    )
    # 服务端会验证 SHA256(verifier) == challenge
    return resp.json()
```

## 3. dify 仓库源码解读

### 3.1 dify 的第三方 OAuth 登录（GitHub/Google）

**文件位置**：`/Users/xu/code/github/dify/api/libs/oauth.py`
**核心代码**（典型 OAuth 流程）：

```python
"""
dify OAuth utilities for third-party login (GitHub, Google).
"""
import os
import requests
from typing import Optional


class OAuthClient:
    """OAuth 2.0 客户端封装"""

    def __init__(self, provider: str):
        self.provider = provider
        if provider == "github":
            self.client_id = os.environ.get("GITHUB_CLIENT_ID")
            self.client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
            self.authorize_url = "https://github.com/login/oauth/authorize"
            self.token_url = "https://github.com/login/oauth/access_token"
            self.user_info_url = "https://api.github.com/user"
        # ... 其他 provider 配置

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[str]:
        """用 Authorization Code 换 Access Token"""
        resp = requests.post(
            self.token_url,
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        data = resp.json()
        return data.get("access_token")

    def get_user_info(self, access_token: str) -> dict:
        """用 Access Token 获取用户信息"""
        resp = requests.get(
            self.user_info_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        return resp.json()
```

**解读**：
- 第 13-19 行：不同 Provider 的端点配置（GitHub、Google 等）
- 第 22-32 行：**标准的 Authorization Code 流程**——用 code + client_secret 换 Access Token
- 第 35-42 行：用 Access Token 调用 Provider 的 user_info API
- **设计意图**：dify 把不同 Provider 的 OAuth 流程封装成统一接口，业务代码只关心 `get_user_info(access_token)`

### 3.2 ruoyi 的自建 OAuth2 授权服务器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/oauth2/OAuth2TokenController.java`
**核心代码**（典型 Spring 实现）：

```java
@RestController
@RequestMapping("/system/oauth2/token")
public class OAuth2TokenController {

    @Resource
    private OAuth2TokenService oauth2TokenService;

    /**
     * 授权码模式：用户授权后回调
     */
    @PostMapping("/access-token")
    public CommonResult<OAuth2AccessTokenRespDTO> getAccessToken(
            @RequestParam("grant_type") String grantType,
            @RequestParam(value = "code", required = false) String code,
            @RequestParam(value = "client_id") String clientId,
            @RequestParam(value = "client_secret") String clientSecret) {

        // 1. 校验客户端凭证
        OAuth2ClientDO client = oauth2ClientService.validClient(clientId, clientSecret);
        if (client == null) {
            return CommonResult.error(401, "invalid client");
        }

        // 2. 根据 grant_type 处理
        if ("authorization_code".equals(grantType)) {
            // 用 code 换 token
            return oauth2TokenService.createByAuthorizationCode(code, client);
        } else if ("client_credentials".equals(grantType)) {
            // 客户端凭证模式（机器对机器）
            return oauth2TokenService.createByClientCredentials(client);
        } else if ("refresh_token".equals(grantType)) {
            // 刷新 Token
            return oauth2TokenService.refresh(request.getParam("refresh_token"), client);
        }
        return CommonResult.error(400, "unsupported grant_type");
    }
}
```

**解读**：
- 第 17 行：标准的 `/oauth2/token` 端点
- 第 23 行：先校验 client_id + client_secret
- 第 28-37 行：支持三种 grant_type：authorization_code、client_credentials、refresh_token
- **设计意图**：ruoyi 实现了完整的 OAuth 2.0 授权服务器，既能对外提供"第三方登录"能力，也能让内部微服务用 client_credentials 调用

## 4. 关键要点总结

- OAuth 2.0 是**授权**协议，不是认证协议
- **Authorization Code** 是最安全的模式（Web 应用首选）
- **Client Credentials** 用于机器对机器（无用户参与）
- **PKCE** 是 Authorization Code 的增强版（SPA / 移动端）
- **Implicit / Password** 模式已过时，避免使用
- **scope** 限制第三方权限（最小权限原则）
- **state** 参数防 CSRF
- dify 用 OAuth 做第三方登录，ruoyi 自己实现 OAuth2 服务器

## 5. 练习题

### 练习 1：基础（必做）

实现"用 GitHub 登录"流程：
1. `/login/github` 跳转到 GitHub 授权
2. `/auth/github/callback` 处理回调
3. 用 code 换 Access Token
4. 用 Token 获取用户信息
5. 创建本地会话

**参考答案**：见 `solutions/05-github-oauth.md`

### 练习 2：进阶

对比四种 OAuth 2.0 模式的适用场景：
1. Authorization Code 适合什么？为什么？
2. Client Credentials 为什么不需要用户参与？
3. Implicit 模式为什么被废弃？
4. Password 模式还有什么合法用途？

### 练习 3：挑战（选做）

为 dify 添加 OAuth 2.0 Client Credentials 模式：
- dify 作为 Resource Server，暴露 `/api/v1/apps` 等接口
- 实现 `/oauth2/token` 端点签发 Access Token
- 实现 `/oauth2/introspect` 端点校验 Token
- 用 Redis 存储 Access Token，过期自动清理

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/oauth.py`
- `/Users/xu/code/github/dify/api/libs/oauth_bearer.py`（Bearer Token 验证）
- `/Users/xu/code/github/dify/api/libs/oauth_data_source.py`（OAuth 数据源）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/oauth2/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/oauth2/`
- RFC 6749（OAuth 2.0）：https://datatracker.ietf.org/doc/html/rfc6749
- RFC 7636（PKCE）：https://datatracker.ietf.org/doc/html/rfc7636

---

**文档版本**：v1.0
**最后更新**：2026-07-13