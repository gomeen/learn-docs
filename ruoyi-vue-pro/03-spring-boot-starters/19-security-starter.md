# 4.1 yudao-spring-boot-starter-security 架构

> 理解 yudao Security Starter 的整体架构，掌握其与 Spring Security 的关系。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao Security Starter 的整体设计
- 理解 Token 认证的核心流程
- 掌握 yudao 对 Spring Security 的定制点
- 能看懂 yudao 中所有安全相关代码

## 📚 前置知识

- Spring Security 基础（Filter、Authentication；详见 [20-spring-security](./20-spring-security.md)）
- RBAC 权限模型（详见 [RBAC](../../_common/08-authorization/01-rbac.md) / [22-rbac-model](./22-rbac-model.md)）
- HTTP 认证概览见 [HTTP Auth](../../_common/07-authentication/01-http-auth.md)

## 1. 核心概念

### 1.1 yudao Security Starter 的组件

| 组件 | 职责 |
|------|------|
| `YudaoSecurityAutoConfiguration` | 自动装配 |
| `YudaoWebSecurityConfigurerAdapter` | Spring Security 配置（`SecurityFilterChain`） |
| `TokenAuthenticationFilter` | Token 校验过滤器（详见 [21-token-auth](./21-token-auth.md)） |
| `LoginUser` | 当前登录用户 |
| `SecurityFrameworkService` | 权限校验 API |
| `SecurityProperties` | 配置（Token Header、Mock 开关） |
| `AuthenticationEntryPointImpl` | 认证失败处理器 |
| `AccessDeniedHandlerImpl` | 权限不足处理器 |
| `TransmittableThreadLocalSecurityContextHolderStrategy` | TTL 上下文（详见 [30-threadlocal](../01-java-fundamentals/30-threadlocal.md)） |

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

## 3. ruoyi 仓库源码解读

### 3.1 YudaoSecurityAutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoSecurityAutoConfiguration.java`
**核心代码**（行 32-93）：

```java
@AutoConfiguration
@AutoConfigureOrder(-1) // 先于 Spring Security 自动配置
@EnableConfigurationProperties(SecurityProperties.class)
public class YudaoSecurityAutoConfiguration {

    @Bean
    public AuthenticationEntryPoint authenticationEntryPoint() {
        return new AuthenticationEntryPointImpl();
    }

    @Bean
    public AccessDeniedHandler accessDeniedHandler() {
        return new AccessDeniedHandlerImpl();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(securityProperties.getPasswordEncoderLength());
    }

    @Bean
    public TokenAuthenticationFilter authenticationTokenFilter(GlobalExceptionHandler globalExceptionHandler,
                                                               OAuth2TokenCommonApi oauth2TokenApi) {
        return new TokenAuthenticationFilter(securityProperties, globalExceptionHandler, oauth2TokenApi);
    }

    @Bean("ss") // 命名为 "ss"，方便使用 @Resource(name = "ss")
    public SecurityFrameworkService securityFrameworkService(PermissionCommonApi permissionApi) {
        return new SecurityFrameworkServiceImpl(permissionApi);
    }

    @Bean
    public MethodInvokingFactoryBean securityContextHolderMethodInvokingFactoryBean() {
        // 设置 SecurityContextHolder 的策略
        MethodInvokingFactoryBean methodInvokingFactoryBean = new MethodInvokingFactoryBean();
        methodInvokingFactoryBean.setTargetClass(SecurityContextHolder.class);
        methodInvokingFactoryBean.setTargetMethod("setStrategyName");
        methodInvokingFactoryBean.setArguments(TransmittableThreadLocalSecurityContextHolderStrategy.class.getName());
        return methodInvokingFactoryBean;
    }
}
```

**解读**：
- `@AutoConfigureOrder(-1)` 让自己先于 Spring Security 自动配置
- `@Bean("ss")` 用短名 `ss` 命名 `SecurityFrameworkService`
- `MethodInvokingFactoryBean` 用于在启动时**设置 SecurityContextHolder 的策略**为 `TransmittableThreadLocal` 版本（线程池友好）

### 3.2 SecurityProperties

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`
**核心代码**（节选）：

```java
@Data
@ConfigurationProperties(prefix = "yudao.security")
public class SecurityProperties {
    /**
     * 请求头
     */
    private String tokenHeader = "Authorization";
    /**
     * 请求参数
     */
    private String tokenParameter = "token";
    /**
     * mock 开关
     */
    private Boolean mockEnable = false;
    /**
     * mock 密钥
     */
    private String mockSecret = "test";
    /**
     * BCrypt 强度
     */
    private Integer passwordEncoderLength = 10;
}
```

**解读**：
- `tokenHeader` = `Authorization` 是默认值
- `mockEnable` = 开发环境可以用 `Authorization: test1` 来 mock 用户 ID=1 的登录

### 3.3 TokenAuthenticationFilter 流程

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 42-69）：

```java
@Override
protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
        throws ServletException, IOException {
    String token = SecurityFrameworkUtils.obtainAuthorization(request,
            securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
    if (StrUtil.isNotEmpty(token)) {
        Integer userType = WebFrameworkUtils.getLoginUserType(request);
        try {
            // 1. 基于 token 构建登录用户
            LoginUser loginUser = buildLoginByToken(token, userType);
            // 2. 模拟登录（开发用）
            if (loginUser == null) {
                loginUser = mockLoginUser(request, token, userType);
            }
            // 3. 设置到上下文
            if (loginUser != null) {
                SecurityFrameworkUtils.setLoginUser(loginUser, request);
            }
        } catch (Throwable ex) {
            CommonResult<?> result = globalExceptionHandler.allExceptionHandler(request, ex);
            ServletUtils.writeJSON(response, result);
            return;
        }
    }
    chain.doFilter(request, response);
}
```

**解读**：
- 继承 `OncePerRequestFilter`，保证只执行一次
- **3 步**校验：Token → Mock → 设置上下文
- 异常时**直接返回 JSON**，不走后续 Filter

### 3.4 模拟登录（Mock 模式）

**核心代码**（行 105-117）：

```java
private LoginUser mockLoginUser(HttpServletRequest request, String token, Integer userType) {
    if (!securityProperties.getMockEnable()) return null;
    // 必须以 mockSecret 开头
    if (!token.startsWith(securityProperties.getMockSecret())) return null;
    // 构建模拟用户：mockSecret + 用户编号
    Long userId = Long.valueOf(token.substring(securityProperties.getMockSecret().length()));
    return new LoginUser().setId(userId).setUserType(userType)
            .setTenantId(WebFrameworkUtils.getTenantId(request));
}
```

**解读**：
- 开发期：发请求 `Authorization: test1` 即可模拟用户 1
- **生产环境必须关闭**（`mock-enable: false`）

## 4. 关键要点总结

- **yudao Security = Spring Security + Token + RPC 校验**
- **Token 流程**：请求 → Filter → 解析 → RPC 校验 → 设置上下文
- **TTL 替代 ThreadLocal**（线程池友好）
- **`@Bean("ss")` 短命名** 方便注入
- **Mock 登录** 仅开发期开启

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 3 个使用了 `SecurityFrameworkUtils.getLoginUser()` 的方法，理解 LoginUser 的来源。

### 练习 2：进阶

在 yudao 中新加一个 Controller，用 `@PreAuthorize("hasRole('admin')")` 保护它，验证无权限时返回 403。

### 练习 3：挑战（选做）

阅读 `YudaoWebSecurityConfigurerAdapter` 源码，理解 yudao 的 SecurityFilterChain 配置。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoSecurityAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- Spring Security 文档：https://docs.spring.io/spring-security/reference/index.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
