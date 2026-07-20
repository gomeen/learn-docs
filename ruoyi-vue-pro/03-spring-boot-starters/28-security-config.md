# 4.5 Spring Security 配置：SecurityFilterChain

> 深入理解 yudao 中 `SecurityFilterChain` 的配置细节。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `SecurityFilterChain` 的全部配置项
- 掌握 yudao 的 `AuthorizeRequestsCustomizer` 扩展机制
- 能根据业务需求定制安全配置
- 了解 Spring Security 6+ 的新配置风格

## 📚 前置知识

- [24-spring-security.md](./24-spring-security.md)
- [23-security-starter.md](./23-security-starter.md)
- Spring Security 6+ 配置风格

## 1. 核心概念

### 1.1 SecurityFilterChain（Spring Security 6+）

Spring Security 6 开始，`WebSecurityConfigurerAdapter` 被废弃，改用 `SecurityFilterChain` Bean 配置。

### 1.2 yudao 的 SecurityFilterChain

yudao 在 `YudaoWebSecurityConfigurerAdapter` 中定义了**核心 SecurityFilterChain**：

- 关闭 CSRF（CSRF 原理见 [CSRF](../../_common/05-web-security/04-csrf.md)）
- 关闭 FormLogin
- 关闭 HttpBasic
- 关闭 Session（Session 见 [Session/Cookie](../../_common/07-authentication/02-session-cookie.md)）
- 关闭 Logout
- 添加 TokenAuthenticationFilter（详见 [21-token-auth](./25-token-auth.md)）
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

## 3. 关键要点总结

- **Spring Security 6+ 全面用 `SecurityFilterChain` Bean**
- **yudao 关闭所有默认行为**（CSRF、Form、Session、Logout）
- **`AuthorizeRequestsCustomizer` 是业务扩展入口**
- **统一异常处理**返回 JSON
- **支持多 SecurityFilterChain**（admin / app 分离）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
