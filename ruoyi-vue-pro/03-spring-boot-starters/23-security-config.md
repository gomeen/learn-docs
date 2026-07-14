# 4.5 Spring Security 配置：SecurityFilterChain

> 深入理解 yudao 中 `SecurityFilterChain` 的配置细节。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `SecurityFilterChain` 的全部配置项
- 掌握 yudao 的 `AuthorizeRequestsCustomizer` 扩展机制
- 能根据业务需求定制安全配置
- 了解 Spring Security 6+ 的新配置风格

## 📚 前置知识

- [20-spring-security.md](./20-spring-security.md)
- [19-security-starter.md](./19-security-starter.md)
- Spring Security 6+ 配置风格

## 1. 核心概念

### 1.1 SecurityFilterChain（Spring Security 6+）

Spring Security 6 开始，`WebSecurityConfigurerAdapter` 被废弃，改用 `SecurityFilterChain` Bean 配置。

### 1.2 yudao 的 SecurityFilterChain

yudao 在 `YudaoWebSecurityConfigurerAdapter` 中定义了**核心 SecurityFilterChain**：

- 关闭 CSRF
- 关闭 FormLogin
- 关闭 HttpBasic
- 关闭 Session
- 关闭 Logout
- 添加 TokenAuthenticationFilter
- 自定义异常处理

### 1.3 业务方扩展

通过 `AuthorizeRequestsCustomizer` SPI：

```java
@Bean
public AuthorizeRequestsCustomizer myAuthorizeRequestsCustomizer() {
    return registry -> registry
        .requestMatchers("/public/**").permitAll()
        .requestMatchers("/admin/**").hasRole("ADMIN");
}
```

## 2. 代码示例

### 2.1 完整 SecurityFilterChain

```java
@Bean
public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                List<AuthorizeRequestsCustomizer> customizers,
                                                TokenAuthenticationFilter tokenFilter,
                                                AuthenticationEntryPoint entryPoint,
                                                AccessDeniedHandler deniedHandler) throws Exception {
    http
        .csrf(csrf -> csrf.disable())
        .formLogin(form -> form.disable())
        .httpBasic(basic -> basic.disable())
        .logout(logout -> logout.disable())
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .addFilterBefore(tokenFilter, UsernamePasswordAuthenticationFilter.class)
        .exceptionHandling(ex -> ex
            .authenticationEntryPoint(entryPoint)
            .accessDeniedHandler(deniedHandler))
        .authorizeHttpRequests(auth -> {
            customizers.forEach(c -> c.customize(auth));
            auth.anyRequest().authenticated();
        });
    return http.build();
}
```

### 2.2 多个 SecurityFilterChain（admin / app 分离）

```java
@Bean
@Order(1)
public SecurityFilterChain adminFilterChain(HttpSecurity http) throws Exception {
    http.securityMatcher("/admin-api/**")  // 仅匹配 admin-api
        .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
        .addFilterBefore(adminTokenFilter, UsernamePasswordAuthenticationFilter.class);
    return http.build();
}

@Bean
@Order(2)
public SecurityFilterChain appFilterChain(HttpSecurity http) throws Exception {
    http.securityMatcher("/app-api/**")
        .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
        .addFilterBefore(appTokenFilter, UsernamePasswordAuthenticationFilter.class);
    return http.build();
}
```

### 2.3 路径匹配规则

```java
.authorizeHttpRequests(auth -> auth
    .requestMatchers("/public/**").permitAll()
    .requestMatchers("/admin/**").hasRole("ADMIN")
    .requestMatchers("/api/user/*").hasAuthority("USER_READ")
    .requestMatchers(HttpMethod.POST, "/api/order").hasAuthority("ORDER_CREATE")
    .anyRequest().authenticated()
)
```

## 3. ruoyi 仓库源码解读

### 3.1 YudaoWebSecurityConfigurerAdapter

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`

**核心代码**（节选）：

```java
public class YudaoWebSecurityConfigurerAdapter {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                   List<AuthorizeRequestsCustomizer> customizers,
                                                   TokenAuthenticationFilter tokenFilter,
                                                   AuthenticationEntryPoint authEntryPoint,
                                                   AccessDeniedHandler accessDeniedHandler) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .formLogin(form -> form.disable())
            .httpBasic(basic -> basic.disable())
            .logout(logout -> logout.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .addFilterBefore(tokenFilter, UsernamePasswordAuthenticationFilter.class)
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint(authEntryPoint)
                .accessDeniedHandler(accessDeniedHandler))
            .authorizeHttpRequests(auth -> {
                customizers.forEach(c -> c.customize(auth));
                auth.anyRequest().authenticated();
            });
        return http.build();
    }
}
```

**解读**：
- **关闭一切默认行为**（前后端分离 + Token）
- **核心 Filter 在 UsernamePasswordAuthenticationFilter 之前**插入
- **业务扩展**：通过 `customizers` 注入所有 `AuthorizeRequestsCustomizer` Bean
- **统一异常处理**：`AuthenticationEntryPointImpl`（未登录）+ `AccessDeniedHandlerImpl`（权限不足）

### 3.2 AuthenticationEntryPointImpl

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/handler/AuthenticationEntryPointImpl.java`
**核心代码**（节选）：

```java
public class AuthenticationEntryPointImpl implements AuthenticationEntryPoint {

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
                         AuthenticationException ex) throws IOException {
        log.warn("[commence][访问 URL({}) 时，用户未登录]", request.getRequestURI(), ex);
        // 返回 401
        ServletUtils.writeJSON(response, CommonResult.error(UNAUTHORIZED));
    }
}
```

**解读**：
- 未登录返回 **401 Unauthorized** + 统一 JSON 格式
- 日志记录请求 URL 便于排查

### 3.3 AccessDeniedHandlerImpl

**核心代码**（节选）：

```java
public class AccessDeniedHandlerImpl implements AccessDeniedHandler {

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response,
                       AccessDeniedException ex) throws IOException {
        log.warn("[handle][访问 URL({}) 时，权限不足]", request.getRequestURI(), ex);
        // 返回 403
        ServletUtils.writeJSON(response, CommonResult.error(FORBIDDEN));
    }
}
```

**解读**：
- 权限不足返回 **403 Forbidden**

## 4. 关键要点总结

- **Spring Security 6+ 全面用 `SecurityFilterChain` Bean**
- **yudao 关闭所有默认行为**（CSRF、Form、Session、Logout）
- **`AuthorizeRequestsCustomizer` 是业务扩展入口**
- **统一异常处理**返回 JSON
- **支持多 SecurityFilterChain**（admin / app 分离）

## 5. 练习题

### 练习 1：基础（必做）

阅读 `YudaoWebSecurityConfigurerAdapter.java` 全文，列出所有配置项。

### 练习 2：进阶

实现 admin / app 两条 SecurityFilterChain，分别用不同的 TokenAuthenticationFilter。

### 练习 3：挑战（选做）

实现 IP 白名单：只允许 `127.0.0.1` 访问 `/admin-api/secret/**`，其他 IP 返回 403。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- Spring Security 文档：https://docs.spring.io/spring-security/reference/servlet/configuration/java.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
