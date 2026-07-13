# 05 - 认证与安全

> 后端系统必须考虑认证、授权、安全防护。Dify 实现了多租户认证 + RBAC。

## 前置依赖

- `01-fundamentals` 全部
- `04-cache-and-queue` 中 Redis Session 存储

## 模块 5.1 认证机制

- [ ] [1.1 HTTP 认证基础：Basic / Digest / Bearer](./01-http-auth.md)
- [ ] [1.2 Cookie 与 Session 认证](./02-session-auth.md)
- [ ] [1.3 JWT 机制与无状态认证](./03-jwt-auth.md)
- [ ] [1.4 Token 刷新与撤销策略](./04-token-refresh.md)
- [ ] [1.5 OAuth 2.0 协议](./05-oauth2.md)
- [ ] [1.6 OpenID Connect（OIDC）](./06-oidc.md)
- [ ] [1.7 SAML 与企业 SSO](./07-saml-sso.md)

## 模块 5.2 授权模型

- [ ] [2.1 RBAC：基于角色的访问控制](./08-rbac.md)
- [ ] [2.2 ABAC：基于属性的访问控制](./09-abac.md)
- [ ] [2.3 ACL：访问控制列表](./10-acl.md)
- [ ] [2.4 资源所有权与租户隔离](./11-resource-ownership.md)
- [ ] [2.5 dify 的多租户认证流程分析](./12-auth-in-dify.md)

## 模块 5.3 Web 安全

- [ ] [3.1 OWASP Top 10 漏洞概览](./13-owasp-top10.md)
- [ ] [3.2 SQL 注入与参数化查询](./14-sql-injection.md)
- [ ] [3.3 XSS：跨站脚本攻击与防护](./15-xss.md)
- [ ] [3.4 CSRF：跨站请求伪造](./16-csrf.md)
- [ ] [3.5 SSRF：服务端请求伪造](./17-ssrf.md)
- [ ] [3.6 CORS：跨域资源共享](./18-cors.md)
- [ ] [3.7 输入校验与输出编码](./19-input-validation.md)
- [ ] [3.8 dify 的 SSRF 防护实现（`ssrf_proxy`）](./20-ssrf-in-dify.md)

## 模块 5.4 加密与密钥管理

- [ ] [4.1 对称加密：AES / DES](./21-symmetric-encryption.md)
- [ ] [4.2 非对称加密：RSA / ECC](./22-asymmetric-encryption.md)
- [ ] [4.3 哈希算法：MD5 / SHA / bcrypt](./23-hashing.md)
- [ ] [4.4 数字签名与证书](./24-digital-signature.md)
- [ ] [4.5 密钥管理：Vault / KMS / 环境变量](./25-key-management.md)

## 模块 5.5 API 安全

- [ ] [5.1 API 限流：令牌桶 / 漏桶 / 滑动窗口](./26-api-rate-limit.md)
- [ ] [5.2 防重放攻击（Replay Attack）](./27-replay-attack.md)
- [ ] [5.3 API Key 与 Secret 管理](./28-api-key.md)
- [ ] [5.4 dify 的 API Key 体系分析](./29-api-key-in-dify.md)

## 🎯 dify 仓库对应位置

- 登录控制器：`/Users/xu/code/github/dify/api/controllers/console/auth.py`
- 鉴权装饰器：`/Users/xu/code/github/dify/api/libs/login.py`
- 租户上下文：`/Users/xu/code/github/dify/api/libs/tenant_id.py`
- SSRF 防护：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- API Key：`/Users/xu/code/github/dify/api/services/api_key_service.py`
