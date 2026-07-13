# 5.1.7 SAML 与企业 SSO

> 理解 SAML 2.0 与企业 SSO 的工作原理，看懂 dify 在企业版中的 SSO 接入。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SAML 2.0 的 SP / IdP 模型
- 掌握 SAML 登录流程（SP-Initiated）
- 理解 SAML Assertion（XML 签名）的结构
- 对比 SAML 与 OIDC 的适用场景（SAML 适合传统企业，OIDC 适合现代 Web）

## 📚 前置知识

- 05-oauth2.md
- 06-oidc.md
- 加密学基础（XML 数字签名）

## 1. 核心概念

### 1.1 什么是 SAML？

SAML（Security Assertion Markup Language）= 基于 **XML** 的身份断言标准，用于**企业级 SSO**。

**OIDC 用 JSON，SAML 用 XML**——这是最直观的差异。SAML 在 2000 年代是企业 SSO 的事实标准。

### 1.2 三个核心角色

```
┌─────────────────┐                  ┌──────────────────┐
│  User (员工)    │                  │  SP (Dify)       │
│  浏览器         │                  │  服务提供方       │
└─────────────────┘                  └──────────────────┘
        │                                       │
        │ ① 访问 SP                            │
        │ ──────────────────────────────────→  │
        │                                       │
        │ ② SP 生成 SAML Request (XML, base64)  │
        │ ←──────────────────────────────────   │
        │                                       │
        │ ③ 跳转到 IdP（公司 Okta/Azure AD）     │
        │ ──────────────────────────────────→  │
        │                                       │
        │ ④ 用户在 IdP 登录（输入公司账号）      │
        │                                       │
        │ ⑤ IdP 返回 SAML Response (含 Assertion)
        │ ←──────────────────────────────────   │
        │                                       │
        │ ⑥ 浏览器把 SAML Response POST 给 SP  │
        │ ──────────────────────────────────→  │
        │                                       │
        │ ⑦ SP 验证 Assertion，签发 Session     │
        │ ←──────────────────────────────────   │
```

### 1.3 SAML Assertion 结构

```xml
<saml:Assertion>
  <saml:Issuer>https://idp.company.com</saml:Issuer>
  <saml:Subject>
    <saml:NameID>alice@company.com</saml:NameID>
  </saml:Subject>
  <saml:Conditions NotBefore="..." NotOnOrAfter="..." />
  <saml:AttributeStatement>
    <saml:Attribute Name="email">alice@company.com</saml:Attribute>
    <saml:Attribute Name="role">admin</saml:Attribute>
  </saml:AttributeStatement>
  <ds:Signature>...</ds:Signature>  <!-- IdP 签名 -->
</saml:Assertion>
```

**关键点**：整个 Assertion 用 **IdP 的私钥**签名，SP 用 IdP 的**公钥证书**验签。

### 1.4 SAML vs OIDC：何时选哪个？

| 维度 | SAML 2.0 | OIDC |
|------|----------|------|
| 数据格式 | XML | JSON |
| 典型场景 | 企业（员工登录） | 互联网（用户登录） |
| 集成对象 | 浏览器 + IdP 直连 | 通过重定向 + Token |
| 移动端支持 | 麻烦（XML） | 友好（JSON） |
| 现代 Web 友好度 | 一般 | 高 |

**经验法则**：对接企业（员工用公司账号登录）通常走 SAML；对接终端用户（公开注册）通常走 OIDC。

## 2. 代码示例

### 2.1 SP-Initiated SAML 登录：发起 AuthnRequest

```python
import base64
import urllib.parse

def build_saml_request(entity_id: str, idp_sso_url: str,
                      acs_url: str) -> str:
    """SP 发起 SAML 登录：生成 AuthnRequest。"""
    # 1. 构造 AuthnRequest XML
    authn_request = f"""<samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        ID="_request_id_123"
        Version="2.0"
        IssueInstant="2026-07-13T00:00:00Z"
        AssertionConsumerServiceURL="{acs_url}"
        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
      <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
        {entity_id}
      </saml:Issuer>
    </samlp:AuthnRequest>"""

    # 2. base64 编码 + URL 编码
    encoded = base64.b64encode(authn_request.encode()).decode()
    # 3. 跳转到 IdP
    return f"{idp_sso_url}?SAMLRequest={urllib.parse.quote(encoded)}"
```

### 2.2 解析 SAML Assertion（简化）

```python
import base64
import xml.etree.ElementTree as ET

def parse_saml_response(saml_response_b64: str, idp_cert: bytes) -> dict:
    """解析 IdP 返回的 SAML Response。"""
    # 1. base64 解码
    xml_bytes = base64.b64decode(saml_response_b64)
    root = ET.fromstring(xml_bytes)

    # 2. 提取关键字段（实际项目用 python3-saml 库）
    ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}

    email = root.find(".//saml:AttributeStatement/saml:Attribute[@Name='email']/saml:AttributeValue",
                       ns).text
    name_id = root.find(".//saml:Subject/saml:NameID", ns).text

    # 3. 验证签名（实际项目用 xmlsec 库 + IdP 证书）
    # verified = verify_xml_signature(xml_bytes, idp_cert)
    # assert verified, "SAML signature invalid"

    return {"email": email, "name_id": name_id}
```

### 2.3 常见错误：跳过签名验证

```python
# ❌ 错误：拿到 SAML Response 直接信任，没验签
claims = parse_saml_response(saml_response)  # 攻击者可伪造整个 XML
# ✅ 正确：用 xmlsec 库 + IdP 证书验签后，再用 claims
```

## 3. dify 仓库源码解读

### 3.1 SSO 相关路由

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/`
**核心代码**（典型 SSO 入口）：

```python
@console_ns.route("/sso/<string:provider>/login")
class SSOLogin(Resource):
    """SSO 登录入口：跳转到企业 IdP。"""

    def get(self, provider: str):
        sso_config = SSOConfigService.get_by_provider(provider, db.session())
        if sso_config is None:
            raise NotFound("SSO provider not configured")

        # 1. 生成 SAML AuthnRequest（或 OIDC 跳转）
        redirect_url = sso_client.build_authn_request(
            entity_id=sso_config.entity_id,
            acs_url=sso_config.acs_url,
        )
        return redirect(redirect_url)


@console_ns.route("/sso/<string:provider>/acs")
class SSOLoginCallback(Resource):
    """SSO 回调（Assertion Consumer Service）。"""

    def post(self, provider: str):
        # 1. 拿到 IdP POST 回来的 SAML Response
        saml_response = request.form.get("SAMLResponse")

        # 2. 用 IdP 证书验签 + 解析 Assertion
        claims = SAMLClient(provider).process_response(
            saml_response,
            tenant_id=current_tenant_id,
        )

        # 3. 在 dify 中查找或创建账号
        email = claims["email"]
        account = AccountService.get_or_create_by_email(
            email=email, name=claims.get("name"),
            session=db.session(),
        )

        # 4. 签发 dify 自己的 Token 并写入 Cookie
        token_pair = AccountService.login(account, db.session(), ip_address)
        # ... set_cookie(access_token/refresh_token/csrf_token)
```

**解读**：
- 第 1-12 行：`/sso/<provider>/login` 是**入口接口**，SP 发起 SAML 跳转
- 第 16-23 行：`/sso/<provider>/acs` 是**回调接口**（Assertion Consumer Service），IdP 把 SAML Response POST 回来
- 第 25-29 行：`process_response` 内部完成 **base64 解码 → XML 解析 → 签名验证 → 时间窗口校验**
- 第 32-35 行：拿到 email 后**自动 provision**（首次登录自动创建账号）
- 第 38-40 行：dify 不保留 IdP 的 SAML 凭证，只信任 SAML 提供的身份信息
- **设计意图**：把 SSO 视为"外部身份证明"，dify 内仍用自己的 Token 体系

### 3.2 SSO 配置存储

dify 在 DB 中存储每个 tenant 的 SSO 配置（`IdP entity_id`、`acs_url`、`IdP 证书`），运行期通过 SSO Service 加载。

```python
# 简化示意（实际 dify 用 enterprise SSO service）
class SSOConfig:
    tenant_id: str
    provider: str           # "saml" / "oidc"
    entity_id: str          # SP 的 entity ID
    acs_url: str            # SP 回调地址
    idp_entity_id: str      # IdP 的 entity ID
    idp_sso_url: str        # IdP 登录入口
    idp_certificate: str    # IdP 的 X.509 证书（验签用）
```

## 4. 关键要点总结

- SAML 2.0 = XML 时代的 SSO 标准，OIDC = JSON 时代的新标准
- **SP-Initiated** 是最常见的流程：用户访问 SP → SP 跳转 IdP → IdP 登录 → IdP POST SAML Response 回 SP
- **签名验证是核心**：SAML Response 必须用 IdP 的 X.509 证书验签
- dify 把 SSO 仅作为"身份证明"，登录成功后立即签发自己的 Token
- XML 处理复杂，建议用 `python3-saml` 而非手写解析

## 5. 练习题

### 练习 1：基础（必做）

用 Python 写一个简化版 SP：模拟 `/login` 跳转到 mock IdP，IdP 回 SAML Response，SP 解析并签发 dify Token（可用 in-memory dict）。

### 练习 2：进阶

阅读 `api/controllers/console/auth/` 目录下的文件，列出所有与 SSO 相关的接口路径，并画出一个完整的 SAML SP-Initiated 流程时序图。

### 练习 3：挑战（选做）

基于 SAML metadata XML 实现 IdP 自动发现：给定 IdP metadata URL，自动提取 `entityID`、`SSO URL`、`X.509 证书`，省去手动配置。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/oauth_server.py`
- `/Users/xu/code/github/dify/api/controllers/console/auth/` 目录
- SAML 2.0 规范：https://docs.oasis-open.org/security/saml/v2.0/
- python3-saml 库：https://github.com/SAML-Toolkits/python3-saml
- OneLogin SAML 工具：https://www.samltool.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13