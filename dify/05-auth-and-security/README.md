# 05 - 认证与安全

> 后端系统必须考虑认证、授权、安全防护。Dify 实现了多租户认证 + RBAC。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| HTTP 认证基础 | [`_common/07-authentication/01-http-auth`](../../_common/07-authentication/01-http-auth.md) | 01（待补） |
| Session / Cookie | [`_common/07-authentication/02-session-cookie`](../../_common/07-authentication/02-session-cookie.md) | 02（待补） |
| JWT 机制 | [`_common/07-authentication/03-jwt`](../../_common/07-authentication/03-jwt.md) | 03（待补） |
| Token 刷新 | [`_common/07-authentication/04-token-refresh`](../../_common/07-authentication/04-token-refresh.md) | 04（待补） |
| OAuth 2.0 | [`_common/07-authentication/05-oauth2`](../../_common/07-authentication/05-oauth2.md) | 05（待补） |
| SSO / OIDC | [`_common/07-authentication/06-oidc-sso`](../../_common/07-authentication/06-oidc-sso.md) | 06–07（待补） |
| RBAC | [`_common/08-authorization/01-rbac`](../../_common/08-authorization/01-rbac.md) | 08（待补） |
| 多租户 / 资源所有权 | [`_common/08-authorization/05-multi-tenant`](../../_common/08-authorization/05-multi-tenant.md) · [`04-resource-ownership`](../../_common/08-authorization/04-resource-ownership.md) | [11](./01-resource-ownership.md)、[12](./02-auth-in-dify.md) |
| OWASP | [`_common/05-web-security/01-owasp-top10`](../../_common/05-web-security/01-owasp-top10.md) | 13（待补） |
| XSS / CSRF / SQL 注入 / SSRF / CORS | [`_common/05-web-security/`](../../_common/05-web-security/) | 14–18（待补）；[20-ssrf-in-dify](./03-ssrf-in-dify.md) |
| 对称/非对称加密 / 哈希 / 签名 / 密钥 | [`_common/06-encryption/`](../../_common/06-encryption/) | 21–25（待补） |
| 防重放 | [`_common/05-web-security/07-replay-attack`](../../_common/05-web-security/07-replay-attack.md) | 27（待补） |

## 前置依赖

- `01-fundamentals` 全部
- `04-cache-and-queue` 中 Redis Session 存储

## 模块 5.1 认证机制

- [ ] [1.1 HTTP 认证基础：Basic / Digest / Bearer](../../_common/07-authentication/01-http-auth.md)
- [ ] [1.2 Cookie 与 Session 认证](../../_common/07-authentication/02-session-cookie.md)
- [ ] [1.3 JWT 机制与无状态认证](../../_common/07-authentication/03-jwt.md)
- [ ] [1.4 Token 刷新与撤销策略](../../_common/07-authentication/04-token-refresh.md)
- [ ] [1.5 OAuth 2.0 协议](../../_common/07-authentication/05-oauth2.md)
- [ ] [1.6 OpenID Connect（OIDC）与企业 SSO](../../_common/07-authentication/06-oidc-sso.md)
- 1.x 本仓 dify 认证补充文 01–07（待补）

## 模块 5.2 授权模型

- [ ] [2.1 RBAC：基于角色的访问控制](../../_common/08-authorization/01-rbac.md)
- [ ] [2.2 ABAC：基于属性的访问控制](../../_common/08-authorization/02-abac.md)
- [ ] [2.3 ACL：访问控制列表](../../_common/08-authorization/03-acl.md)
- [ ] [2.4 资源所有权与租户隔离](./01-resource-ownership.md)
- [ ] [2.5 dify 的多租户认证流程分析](./02-auth-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [04-*-auth-multitenant: 资源所有权与 dify 认证流程](./04-*-auth-multitenant.md)
  - 覆盖：01-resource-ownership.md, 02-auth-in-dify.md

- 2.x 本仓 08–10（待补）；通用见上表

## 模块 5.3 Web 安全

- [ ] [3.1 OWASP Top 10 漏洞概览](../../_common/05-web-security/01-owasp-top10.md)
- [ ] [3.2 SQL 注入与参数化查询](../../_common/05-web-security/03-sql-injection.md)
- [ ] [3.3 XSS：跨站脚本攻击与防护](../../_common/05-web-security/02-xss.md)
- [ ] [3.4 CSRF：跨站请求伪造](../../_common/05-web-security/04-csrf.md)
- [ ] [3.5 SSRF：服务端请求伪造](../../_common/05-web-security/06-ssrf.md)
- [ ] [3.6 CORS：跨域资源共享](../../_common/05-web-security/05-cors.md)
- [ ] [3.7 输入校验与输出编码](./05-input-validation.md)
- [ ] [3.8 dify 的 SSRF 防护实现（`ssrf_proxy`）](./03-ssrf-in-dify.md)
- 3.x 本仓 13–18（待补）

## 模块 5.4 加密与密钥管理

- [ ] [4.1 对称加密：AES / DES](../../_common/06-encryption/01-symmetric.md)
- [ ] [4.2 非对称加密：RSA / ECC](../../_common/06-encryption/02-asymmetric.md)
- [ ] [4.3 哈希算法：MD5 / SHA / bcrypt](../../_common/06-encryption/03-hash.md)
- [ ] [4.4 数字签名与证书](../../_common/06-encryption/04-digital-signature.md)
- [ ] [4.5 密钥管理：Vault / KMS / 环境变量](../../_common/06-encryption/05-key-management.md)
- 4.x 本仓 21–25（待补）

## 模块 5.5 API 安全

- [ ] [5.1 API 限流：令牌桶 / 漏桶 / 滑动窗口](../../_common/03-cache-patterns/04-rate-limiting.md)
- [ ] [5.2 防重放攻击（Replay Attack）](../../_common/05-web-security/07-replay-attack.md)
- [ ] [5.3 API Key 与 Secret 管理](./06-api-key.md)
- [ ] [5.4 dify 的 API Key 体系分析](./07-api-key-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [08-*-validation-ssrf-apikey: 输入校验 · SSRF · API Key](./08-*-validation-ssrf-apikey.md)
  - 覆盖：05-input-validation.md, 03-ssrf-in-dify.md, 06-api-key.md, 07-api-key-in-dify.md

- 5.x 本仓 26–27（待补）

## 🎯 dify 仓库对应位置

- 登录控制器：`/Users/xu/code/github/dify/api/controllers/console/auth.py`
- 鉴权装饰器：`/Users/xu/code/github/dify/api/libs/login.py`
- 租户上下文：`/Users/xu/code/github/dify/api/libs/tenant_id.py`
- SSRF 防护：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- API Key：`/Users/xu/code/github/dify/api/services/api_key_service.py`
