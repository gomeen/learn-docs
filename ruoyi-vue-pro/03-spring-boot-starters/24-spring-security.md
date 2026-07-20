# 4.2 Spring Security 核心概念

> 理解 Spring Security 的核心概念与过滤器链。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Security 的过滤器链机制
- 掌握 `Authentication`、`Authorization`、`Principal` 等核心接口
- 理解 `SecurityContextHolder` 与 `ThreadLocal` 的关系
- 能看懂 Spring Security 源码

## 📚 前置知识

- [23-security-starter.md](./23-security-starter.md)
- Servlet Filter 基础（详见 [19-filter](../02-spring-boot/22-filter.md)）
- HTTP Basic / Digest 认证（详见 [HTTP Auth](../../_common/07-authentication/01-http-auth.md)）

## 1. 核心概念

### 1.1 Spring Security 的核心组件

| 组件 | 作用 |
|------|------|
| `SecurityFilterChain` | 过滤器链，替代旧版 `WebSecurityConfigurerAdapter` |
| `SecurityContextHolder` | 存放当前线程的安全上下文（ThreadLocal 详见 [30-threadlocal](../01-java-fundamentals/36-threadlocal.md)） |
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

## 3. 关键要点总结

- **Spring Security 的核心 = 过滤器链 + SecurityContextHolder**
- **Spring Security 6+ 用 `SecurityFilterChain` Bean** 替代旧 `WebSecurityConfigurerAdapter`
- **yudao 用 TTL 替代 ThreadLocal**（线程池友好）
- **`AuthorizeRequestsCustomizer` SPI** 让业务方灵活扩展
- **Token 流程**：Filter 解析 → 校验 → 设置 Authentication

---

**文档版本**：v1.0
**最后更新**：2026-07-13
