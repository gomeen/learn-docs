# 4.1 yudao-spring-boot-starter-security 架构

> 理解 yudao Security Starter 的整体架构，掌握其与 Spring Security 的关系。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao Security Starter 的整体设计
- 理解 Token 认证的核心流程
- 掌握 yudao 对 Spring Security 的定制点
- 能看懂 yudao 中所有安全相关代码

## 📚 前置知识

- Spring Security 基础（Filter、Authentication；详见 [20-spring-security](./24-spring-security.md)）
- RBAC 权限模型（详见 [RBAC](../../_common/08-authorization/01-rbac.md) / [22-rbac-model](./26-rbac-model.md)）
- HTTP 认证概览见 [HTTP Auth](../../_common/07-authentication/01-http-auth.md)

## 1. 核心概念

### 1.1 yudao Security Starter 的组件

| 组件 | 职责 |
|------|------|
| `YudaoSecurityAutoConfiguration` | 自动装配 |
| `YudaoWebSecurityConfigurerAdapter` | Spring Security 配置（`SecurityFilterChain`） |
| `TokenAuthenticationFilter` | Token 校验过滤器（详见 [21-token-auth](./25-token-auth.md)） |
| `LoginUser` | 当前登录用户 |
| `SecurityFrameworkService` | 权限校验 API |
| `SecurityProperties` | 配置（Token Header、Mock 开关） |
| `AuthenticationEntryPointImpl` | 认证失败处理器 |
| `AccessDeniedHandlerImpl` | 权限不足处理器 |
| `TransmittableThreadLocalSecurityContextHolderStrategy` | TTL 上下文（详见 [30-threadlocal](../01-java-fundamentals/36-threadlocal.md)） |

### 1.2 与 Spring Security 的关系

yudao 不是替换 Spring Security，而是**在其基础上定制**：
- 用 Token（OAuth2 风格，详见 [OAuth2](../../_common/07-authentication/05-oauth2.md)）替代默认的 Session（Session 见 [Session/Cookie](../../_common/07-authentication/02-session-cookie.md)）
- 用 TTL 替代 ThreadLocal（线程池友好）
- 用 RPC 校验 Token（微服务架构）

## 2. 代码示例

### 2.1 获取当前登录用户

```java
import static cn.iocoder.yudao.framework.security.core.util.SecurityFrameworkUtils.*;

public void someMethod() {
    Long userId = getLoginUserId();
    Integer userType = getLoginUser().getUserType();
    String nickname = getLoginUser().getInfo(LoginUser.INFO_KEY_NICKNAME);
}
```

### 2.2 权限校验

```java
// 注入 SecurityFrameworkService（bean 名称是 "ss"）
@Resource
private SecurityFrameworkService securityFrameworkService;

public void checkPermission() {
    // 校验是否有 role_admin 角色
    securityFrameworkService.hasRole("admin");
    // 校验是否有 system:user:create 权限
    securityFrameworkService.hasPermission("system:user:create");
}
```

### 2.3 配置 Token

```yaml
yudao:
  security:
    token-header: Authorization
    mock-enable: true           # 开启 mock 登录（开发用）
    mock-secret: test           # mock 时的 token 前缀
```

## 3. 关键要点总结

- **yudao Security = Spring Security + Token + RPC 校验**
- **Token 流程**：请求 → Filter → 解析 → RPC 校验 → 设置上下文
- **TTL 替代 ThreadLocal**（线程池友好）
- **`@Bean("ss")` 短命名** 方便注入
- **Mock 登录** 仅开发期开启

---

**文档版本**：v1.0
**最后更新**：2026-07-13
