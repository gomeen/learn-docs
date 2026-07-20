# 06 - 安全与多租户

> ruoyi-vue-pro 的核心能力：Spring Security + Token + 多租户 + 数据权限。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| HTTP 认证基础 | [01-http-auth](../../_common/07-authentication/01-http-auth.md) | Filter Chain 等项目文待补 |
| JWT 机制 | [03-jwt](../../_common/07-authentication/03-jwt.md) | 项目 JWT 文待补；见 Token + Redis 本地文 |
| OAuth 2.0 / SSO | [05-oauth2](../../_common/07-authentication/05-oauth2.md)、[06-oidc-sso](../../_common/07-authentication/06-oidc-sso.md) | 项目 OAuth/SSO 文待补 |
| RBAC | [01-rbac](../../_common/08-authorization/01-rbac.md) | 项目权限表文待补 |
| 多租户 | [05-multi-tenant](../../_common/08-authorization/05-multi-tenant.md) | 项目多租户章节待补 |
| CSRF / CORS | [04-csrf](../../_common/05-web-security/04-csrf.md)、[05-cors](../../_common/05-web-security/05-cors.md) | 项目 CSRF/CORS 文待补 |
| XSS / SQL 注入 | [02-xss](../../_common/05-web-security/02-xss.md)、[03-sql-injection](../../_common/05-web-security/03-sql-injection.md) | 项目文待补 |
| 防重放 | [07-replay-attack](../../_common/05-web-security/07-replay-attack.md) | 项目文待补 |
| 加密 | [_common/06-encryption/](../../_common/06-encryption/) | 项目国密文待补 |

## 模块 6.1 Spring Security

- [ ] Spring Security 核心概念：Filter Chain（公共见 [_common/07-authentication/](../../_common/07-authentication/)；项目文待补）
- [ ] Authentication 与 Authorization（公共见 [_common/07-authentication/](../../_common/07-authentication/)、[_common/08-authorization/](../../_common/08-authorization/)；项目文待补）
- [ ] SecurityFilterChain 配置（项目文待补）
- [ ] UserDetailsService（项目文待补）
- [ ] PasswordEncoder：BCrypt（公共见加密/认证相关 [_common/06-encryption/03-hash](../../_common/06-encryption/03-hash.md)；项目文待补）
- [ ] [1.6 @PreAuthorize 注解权限](./01-preauthorize.md)
- [ ] [1.7 自定义 Filter](./02-custom-filter.md)
- [ ] CSRF 与 CORS 配置（公共见 [_common/05-web-security/04-csrf](../../_common/05-web-security/04-csrf.md)、[05-cors](../../_common/05-web-security/05-cors.md)；项目文待补）

## 模块 6.2 Token 认证

- [ ] JWT 原理（公共见 [_common/07-authentication/03-jwt](../../_common/07-authentication/03-jwt.md)；项目文待补）
- [ ] [2.2 Token + Redis 实现](./03-token-redis.md)
- [ ] [2.3 自研 TokenUtils](./04-token-utils.md)
- [ ] [2.4 登录流程：账号密码](./05-login-flow.md)
- [ ] [2.5 社交登录：微信/钉钉/企业微信](./06-social-login.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-security-token: 注解权限 / 过滤器 / Token 登录流](./07-*-security-token.md)
  - 覆盖：01-preauthorize.md, 02-custom-filter.md, 03-token-redis.md, 04-token-utils.md, 05-login-flow.md, 06-social-login.md

- [ ] OAuth 2.0 接入（公共见 [_common/07-authentication/05-oauth2](../../_common/07-authentication/05-oauth2.md)；项目文待补）
- [ ] SSO 单点登录（公共见 [_common/07-authentication/06-oidc-sso](../../_common/07-authentication/06-oidc-sso.md)；项目文待补）

## 模块 6.3 RBAC 权限模型

- [ ] RBAC 概念：用户/角色/权限（公共见 [_common/08-authorization/01-rbac](../../_common/08-authorization/01-rbac.md)；项目文待补）
- [ ] ruoyi 的权限表设计（待补）
- [ ] 菜单权限：动态路由（待补）
- [ ] 按钮权限：自定义注解（待补）
- [ ] 接口权限：API 级别控制（待补）

## 模块 6.4 多租户

- [ ] 多租户架构：SAAS 模式（公共见 [_common/08-authorization/05-multi-tenant](../../_common/08-authorization/05-multi-tenant.md)；项目文待补）
- [ ] ruoyi 多租户实现原理（待补）
- [ ] TenantContext 租户上下文（待补）
- [ ] SQL 拦截器：自动加 tenant_id（待补）
- [ ] @TenantIgnore 忽略租户隔离（待补）
- [ ] 跨租户查询与超级管理员（待补）

## 模块 6.5 数据权限

- [ ] 数据权限概念：本人/本部门/本部门及下级/全部（公共可参考 [_common/08-authorization/](../../_common/08-authorization/)；项目文待补）
- [ ] @DataPermission 注解（待补）
- [ ] [5.3 ruoyi 的数据权限实现](./08-ruoyi-data-permission.md)
- [ ] 自定义数据权限规则（待补）

## 模块 6.6 Web 安全

- [ ] XSS 防护（公共见 [_common/05-web-security/02-xss](../../_common/05-web-security/02-xss.md)；项目文待补）
- [ ] SQL 注入防护（公共见 [_common/05-web-security/03-sql-injection](../../_common/05-web-security/03-sql-injection.md)；项目文待补）
- [ ] 防重放攻击（公共见 [_common/05-web-security/07-replay-attack](../../_common/05-web-security/07-replay-attack.md)；项目文待补）
- [ ] [6.4 限流与防刷](./09-rate-limit.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [10-*-data-permission-rate: 数据权限与限流](./10-*-data-permission-rate.md)
  - 覆盖：08-ruoyi-data-permission.md, 09-rate-limit.md

- [ ] 加密：国密 SM4 / AES（公共见 [_common/06-encryption/](../../_common/06-encryption/)；项目文待补）

## 🎯 ruoyi-vue-pro 仓库对应位置

- Security Starter：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- 多租户 Starter：`yudao-framework/yudao-spring-boot-starter-biz-tenant/`
- 数据权限 Starter：`yudao-framework/yudao-spring-boot-starter-biz-data-permission/`
- 登录相关：`yudao-module-system/.../controller/admin/auth/`
- 权限相关：`yudao-module-system/.../controller/admin/permission/`
