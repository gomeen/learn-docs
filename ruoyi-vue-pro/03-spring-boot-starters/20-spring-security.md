# 4.2 Spring Security 核心概念

> 理解 Spring Security 的核心概念与过滤器链。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Security 的过滤器链机制
- 掌握 `Authentication`、`Authorization`、`Principal` 等核心接口
- 理解 `SecurityContextHolder` 与 `ThreadLocal` 的关系
- 能看懂 Spring Security 源码

## 📚 前置知识

- [19-security-starter.md](./19-security-starter.md)
- Servlet Filter 基础
- HTTP Basic / Digest 认证

## 1. 核心概念

### 1.1 Spring Security 的核心组件

| 组件 | 作用 |
|------|------|
| `SecurityFilterChain` | 过滤器链，替代旧版 `WebSecurityConfigurerAdapter` |
| `SecurityContextHolder` | 存放当前线程的安全上下文 |
| `Authentication` | 认证信息（用户、权限、是否已认证） |
| `AuthenticationManager` | 认证管理器（`authenticate()`） |
| `AuthenticationProvider` | 具体认证方式 |
| `UserDetailsService` | 加载用户信息 |
| `PasswordEncoder` | 密码加密 |
| `AccessDecisionManager` | 授权决策 |

### 1.2 过滤器链

Spring Security 的核心是一系列 Filter，按顺序执行：

```
1. SecurityContextPersistenceFilter    恢复 SecurityContext
2. UsernamePasswordAuthenticationFilter  表单登录
3. TokenAuthenticationFilter          Token 认证（yudao 替换这里）
4. AnonymousAuthenticationFilter      匿名用户
5. AuthorizationFilter                鉴权（@PreAuthorize）
6. ExceptionTranslationFilter         异常处理
```

yudao 在第 3 步替换为 `TokenAuthenticationFilter`。

## 2. 代码示例

### 2.1 SecurityContextHolder 用法

```java
// 获取当前认证信息
Authentication auth = SecurityContextHolder.getContext().getAuthentication();
String username = auth.getName();
Collection<? extends GrantedAuthority> authorities = auth.getAuthorities();

// 设置认证信息
UsernamePasswordAuthenticationToken token = new UsernamePasswordAuthenticationToken(
        userDetails, null, userDetails.getAuthorities());
SecurityContextHolder.getContext().setAuthentication(token);
```

### 2.2 自定义 UserDetailsService

```java
@Service
public class MyUserDetailsService implements UserDetailsService {
    @Override
    public UserDetails loadUserByUsername(String username) {
        // 查 DB
        UserDO user = userMapper.selectByUsername(username);
        if (user == null) {
            throw new UsernameNotFoundException(username);
        }
        // 构造 UserDetails
        return new User(username, user.getPassword(), getAuthorities(user));
    }
}
```

### 2.3 SecurityFilterChain 配置（Spring Security 6+）

```java
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/login", "/register").permitAll()
            .requestMatchers("/admin/**").hasRole("ADMIN")
            .anyRequest().authenticated()
        )
        .formLogin(form -> form.disable())
        .httpBasic(basic -> basic.disable())
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
    return http.build();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 YudaoWebSecurityConfigurerAdapter

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（节选）：

```java
public class YudaoWebSecurityConfigurerAdapter {
    /**
     * 核心配置：所有请求都走 SecurityFilterChain
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                    // 注入所有业务方自定义的 Customizer
                                                    List<AuthorizeRequestsCustomizer> customizers,
                                                    TokenAuthenticationFilter tokenFilter) throws Exception {
        http
            .csrf(csrf -> csrf.disable())  // 关闭 CSRF（前后端分离不需要）
            .formLogin(form -> form.disable())  // 不用表单登录
            .httpBasic(basic -> basic.disable())  // 不用 Basic
            .logout(logout -> logout.disable())  // 不用 Spring Security 的登出
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))  // 无状态
            .addFilterBefore(tokenFilter, UsernamePasswordAuthenticationFilter.class)  // Token 过滤
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint(authenticationEntryPoint)
                .accessDeniedHandler(accessDeniedHandler))
            .authorizeHttpRequests(auth -> {
                // 业务方扩展点
                customizers.forEach(c -> c.customize(auth));
                auth.anyRequest().authenticated();
            });
        return http.build();
    }
}
```

**解读**：
- 关闭 CSRF、表单、Basic、Session（前后端分离 + Token）
- 在 `UsernamePasswordAuthenticationFilter` **之前**插入 `TokenAuthenticationFilter`
- 通过 `AuthorizeRequestsCustomizer` SPI 让业务方扩展授权规则

### 3.2 AuthorizeRequestsCustomizer

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/AuthorizeRequestsCustomizer.java`
**核心代码**：

```java
@FunctionalInterface
public interface AuthorizeRequestsCustomizer {
    void customize(AuthorizeHttpRequestsConfigurer<HttpSecurity>.AuthorizationManagerRequestMatcherRegistry registry);
}
```

**用法**：

```java
@Component
public class MyAuthorizeRequestsCustomizer implements AuthorizeRequestsCustomizer {
    @Override
    public void customize(AuthorizeHttpRequestsConfigurer<HttpSecurity>.AuthorizationManagerRequestMatcherRegistry registry) {
        registry.requestMatchers("/public/**").permitAll();
    }
}
```

**解读**：
- **SPI 扩展点**：业务方可以添加多个 `AuthorizeRequestsCustomizer` Bean
- 比直接覆盖 `SecurityFilterChain` 更优雅

### 3.3 TransmittableThreadLocalSecurityContextHolderStrategy

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/context/TransmittableThreadLocalSecurityContextHolderStrategy.java`
**核心代码**（节选）：

```java
public class TransmittableThreadLocalSecurityContextHolderStrategy implements SecurityContextHolderStrategy {

    private static final ThreadLocal<SecurityContext> CONTEXT_HOLDER =
            new TransmittableThreadLocal<>();

    @Override
    public void clearContext() {
        CONTEXT_HOLDER.remove();
    }

    @Override
    public SecurityContext getContext() {
        SecurityContext ctx = CONTEXT_HOLDER.get();
        if (ctx == null) {
            ctx = createEmptyContext();
            CONTEXT_HOLDER.set(ctx);
        }
        return ctx;
    }
}
```

**解读**：
- 用 `TransmittableThreadLocal`（TTL）替代 `ThreadLocal`
- 解决**线程池**场景下上下文丢失问题
- 当一个 `@Async` 任务被提交，TTL 会把父线程的上下文**传递**给子线程

## 4. 关键要点总结

- **Spring Security 的核心 = 过滤器链 + SecurityContextHolder**
- **Spring Security 6+ 用 `SecurityFilterChain` Bean** 替代旧 `WebSecurityConfigurerAdapter`
- **yudao 用 TTL 替代 ThreadLocal**（线程池友好）
- **`AuthorizeRequestsCustomizer` SPI** 让业务方灵活扩展
- **Token 流程**：Filter 解析 → 校验 → 设置 Authentication

## 5. 练习题

### 练习 1：基础（必做）

阅读 `YudaoWebSecurityConfigurerAdapter` 全文，画出 yudao 的过滤器链。

### 练习 2：进阶

用 `AuthorizeRequestsCustomizer` 实现：`/public/**` 匿名访问，`/admin/**` 需要 `ROLE_ADMIN`。

### 练习 3：挑战（选做）

阅读 Spring Security 6 源码，理解 `AuthorizationFilter` 如何实现 `@PreAuthorize`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- Spring Security 官方文档：https://docs.spring.io/spring-security/reference/index.html
- Spring Security 6 迁移指南：https://docs.spring.io/spring-security/reference/5.8/migration/index.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
