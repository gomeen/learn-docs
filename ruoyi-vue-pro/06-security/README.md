# 06 - 安全与多租户

> ruoyi-vue-pro 的核心能力：Spring Security + Token + 多租户 + 数据权限。

## 模块 6.1 Spring Security

- [ ] [1.1 Spring Security 核心概念：Filter Chain](./01-filter-chain.md)
- [ ] [1.2 Authentication 与 Authorization](./02-auth-principal.md)
- [ ] [1.3 SecurityFilterChain 配置](./03-security-config.md)
- [ ] [1.4 UserDetailsService](./04-user-details.md)
- [ ] [1.5 PasswordEncoder：BCrypt](./05-password-encoder.md)
- [ ] [1.6 @PreAuthorize 注解权限](./06-preauthorize.md)
- [ ] [1.7 自定义 Filter](./07-custom-filter.md)
- [ ] [1.8 CSRF 与 CORS 配置](./08-csrf-cors.md)

## 模块 6.2 Token 认证

- [ ] [2.1 JWT 原理](./09-jwt.md)
- [ ] [2.2 Token + Redis 实现](./10-token-redis.md)
- [ ] [2.3 自研 TokenUtils](./11-token-utils.md)
- [ ] [2.4 登录流程：账号密码](./12-login-flow.md)
- [ ] [2.5 社交登录：微信/钉钉/企业微信](./13-social-login.md)
- [ ] [2.6 OAuth 2.0 接入](./14-oauth2.md)
- [ ] [2.7 SSO 单点登录](./15-sso.md)

## 模块 6.3 RBAC 权限模型

- [ ] [3.1 RBAC 概念：用户/角色/权限](./16-rbac.md)
- [ ] [3.2 ruoyi 的权限表设计](./17-ruoyi-permission-tables.md)
- [ ] [3.3 菜单权限：动态路由](./18-dynamic-menu.md)
- [ ] [3.4 按钮权限：自定义注解](./19-button-permission.md)
- [ ] [3.5 接口权限：API 级别控制](./20-api-permission.md)

## 模块 6.4 多租户

- [ ] [4.1 多租户架构：SAAS 模式](./21-multi-tenant.md)
- [ ] [4.2 ruoyi 多租户实现原理](./22-ruoyi-tenant.md)
- [ ] [4.3 TenantContext 租户上下文](./23-tenant-context.md)
- [ ] [4.4 SQL 拦截器：自动加 tenant_id](./24-tenant-interceptor.md)
- [ ] [4.5 @TenantIgnore 忽略租户隔离](./25-tenant-ignore.md)
- [ ] [4.6 跨租户查询与超级管理员](./26-cross-tenant.md)

## 模块 6.5 数据权限

- [ ] [5.1 数据权限概念：本人/本部门/本部门及下级/全部](./27-data-permission.md)
- [ ] [5.2 @DataPermission 注解](./28-data-permission-annotation.md)
- [ ] [5.3 ruoyi 的数据权限实现](./29-ruoyi-data-permission.md)
- [ ] [5.4 自定义数据权限规则](./30-custom-data-permission.md)

## 模块 6.6 Web 安全

- [ ] [6.1 XSS 防护：参数过滤](./31-xss.md)
- [ ] [6.2 SQL 注入防护：MyBatis 参数化](./32-sql-injection.md)
- [ ] [6.3 防重放攻击：幂等性](./33-replay-attack.md)
- [ ] [6.4 限流与防刷](./34-rate-limit.md)
- [ ] [6.5 加密：国密 SM4 / AES](./35-encryption.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- Security Starter：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- 多租户 Starter：`yudao-framework/yudao-spring-boot-starter-biz-tenant/`
- 数据权限 Starter：`yudao-framework/yudao-spring-boot-starter-biz-data-permission/`
- 登录相关：`yudao-module-system/.../controller/admin/auth/`
- 权限相关：`yudao-module-system/.../controller/admin/permission/`
