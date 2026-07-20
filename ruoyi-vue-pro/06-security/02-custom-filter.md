# 7 自定义 Filter：扩展 Spring Security

> 学习如何编写自定义 Filter 并插入到 Spring Security 过滤器链中，实现业务特有的安全需求。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `OncePerRequestFilter` 的使用
- 理解 `addFilterBefore` 和 `addFilterAfter` 的区别
- 能编写租户上下文 Filter（解析 Header 中的 tenant-id）
- 看懂 ruoyi 的 `TenantContextWebFilter` 实现

## 📚 前置知识

- Spring Security 过滤器链（详见 [Spring Security](../03-spring-boot-starters/24-spring-security.md)）
- Servlet Filter 规范（详见 [Filter](../02-spring-boot/22-filter.md)）
- Spring Bean 管理（详见 [IoC](../02-spring-boot/01-ioc.md)）

## 1. 核心概念

### 1.1 自定义 Filter 的步骤

```
1. 继承 OncePerRequestFilter（推荐）
2. 重写 doFilterInternal 方法
3. 在 SecurityFilterChain 中 addFilterBefore / addFilterAfter
4. 注册为 Spring Bean
```

### 1.2 Filter 插入位置

```java
http.addFilterBefore(myFilter, UsernamePasswordAuthenticationFilter.class);
http.addFilterAfter(myFilter, AuthorizationFilter.class);
```

| 位置 | 作用 |
|------|------|
| `addFilterBefore(filter, X.class)` | 在 Filter X **之前**执行 |
| `addFilterAfter(filter, X.class)` | 在 Filter X **之后**执行 |
| `addFilterAt(filter, X.class)` | 在 Filter X **同一位置**（不常用） |

### 1.3 常见自定义 Filter 场景

- 租户上下文（解析 `tenant-id` Header，多租户模型详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)）
- 请求日志（记录访问日志）
- 防重放（校验 nonce，详见 [防重放攻击](../../_common/05-web-security/07-replay-attack.md)）
- IP 黑名单
- 接口限流（详见 [限流与防刷](./09-rate-limit.md)）

## 2. 代码示例

### 2.1 基础自定义 Filter

```java
// 文件：RequestTimingFilter.java
@Slf4j
@Component
public class RequestTimingFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        long start = System.currentTimeMillis();
        try {
            chain.doFilter(request, response);
        } finally {
            long cost = System.currentTimeMillis() - start;
            log.info("{} {} 耗时 {}ms", request.getMethod(), request.getRequestURI(), cost);
        }
    }
}
```

### 2.2 注入到 SecurityFilterChain

```java
// 文件：SecurityConfig.java
@Bean
public SecurityFilterChain filterChain(HttpSecurity http, RequestTimingFilter timingFilter) throws Exception {
    http.authorizeHttpRequests(c -> c.anyRequest().authenticated());
    // 关键：插入到 AuthorizationFilter 之后（已认证的请求才计时）
    http.addFilterAfter(timingFilter, AuthorizationFilter.class);
    return http.build();
}
```

## 3. 关键要点总结

- 自定义 Filter 继承 `OncePerRequestFilter`，保证每个请求只执行一次
- `addFilterBefore` / `addFilterAfter` 控制插入位置
- `TenantContextWebFilter` 注册为**普通 Web Filter**（不经过 Security）
- `TokenAuthenticationFilter` 插入到 Security 链中，在 `UsernamePasswordAuthenticationFilter` 之前
- **关键**：finally 块清理 ThreadLocal，防止内存泄漏

---

**文档版本**：v1.0
**最后更新**：2026-07-13
