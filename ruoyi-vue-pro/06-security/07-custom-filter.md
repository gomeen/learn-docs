# 7 自定义 Filter：扩展 Spring Security

> 学习如何编写自定义 Filter 并插入到 Spring Security 过滤器链中，实现业务特有的安全需求。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `OncePerRequestFilter` 的使用
- 理解 `addFilterBefore` 和 `addFilterAfter` 的区别
- 能编写租户上下文 Filter（解析 Header 中的 tenant-id）
- 看懂 ruoyi 的 `TenantContextWebFilter` 实现

## 📚 前置知识

- Spring Security 过滤器链（详见 [Spring Security](../03-spring-boot-starters/20-spring-security.md)）
- Servlet Filter 规范（详见 [Filter](../02-spring-boot/19-filter.md)）
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
- 接口限流（详见 [限流与防刷](./34-rate-limit.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 TenantContextWebFilter（多租户上下文 Filter）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`
**核心代码**（行 19-37）：

```java
public class TenantContextWebFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        // 1. 设置：从 Header / Attribute 中拿到 tenantId，放入 ThreadLocal
        Long tenantId = WebFrameworkUtils.getTenantId(request);
        if (tenantId != null) {
            TenantContextHolder.setTenantId(tenantId);
        }
        try {
            // 2. 继续过滤链
            chain.doFilter(request, response);
        } finally {
            // 3. 清理：清空 ThreadLocal（防内存泄漏 + 防跨请求污染）
            TenantContextHolder.clear();
        }
    }
}
```

**解读**：
- 第 25 行：从 `WebFrameworkUtils.getTenantId(request)` 拿租户 ID（可能是 Header 传的，也可能是 Token 里解析的）
- 第 27 行：放入 `TenantContextHolder`（基于 `TransmittableThreadLocal`）
- 第 32-33 行：`finally` 中**清空** ThreadLocal（关键！否则下一次请求会读到上次的值）
- 这个 Filter 不需要 Spring Security 鉴权，所以**注册到 Web Filter 链**，而不是 Security 链

### 3.2 TokenAuthenticationFilter（最重要的自定义 Filter）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 40-69）：

```java
@Override
@SuppressWarnings("NullableProblems")
protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
        throws ServletException, IOException {
    String token = SecurityFrameworkUtils.obtainAuthorization(request,
            securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
    if (StrUtil.isNotEmpty(token)) {
        Integer userType = WebFrameworkUtils.getLoginUserType(request);
        try {
            // 1.1 基于 token 构建登录用户
            LoginUser loginUser = buildLoginUserByToken(token, userType);
            // 1.2 模拟 Login 功能，方便日常开发调试
            if (loginUser == null) {
                loginUser = mockLoginUser(request, token, userType);
            }

            // 2. 设置当前用户
            if (loginUser != null) {
                SecurityFrameworkUtils.setLoginUser(loginUser, request);
            }
        } catch (Throwable ex) {
            // 3. 异常处理：直接返回 JSON 响应 + return
            CommonResult<?> result = globalExceptionHandler.allExceptionHandler(request, ex);
            ServletUtils.writeJSON(response, result);
            return;  // 中断请求
        }
    }

    // 继续过滤链
    chain.doFilter(request, response);
}
```

**解读**：
- 第 44-45 行：从请求 Header 提取 Token（如果 Header 没有，尝试从 Parameter 拿）
- 第 50 行：调用 `buildLoginUserByToken` 从 Redis 还原 LoginUser
- 第 52-54 行：如果正常 Token 校验失败，尝试**模拟登录**（开发环境用，线上必须关闭）
- 第 58 行：把 LoginUser 放入 `SecurityContextHolder`
- 第 60-64 行：捕获所有异常 → 返回 JSON → **return 中断**（不调用 `chain.doFilter`）
- 第 68 行：正常情况放行

### 3.3 Filter 在 Security 链中的位置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 151）：

```java
// 关键：把 Token Filter 插入到 UsernamePasswordAuthenticationFilter 之前
httpSecurity.addFilterBefore(authenticationTokenFilter, UsernamePasswordAuthenticationFilter.class);
```

**为什么在 `UsernamePasswordAuthenticationFilter` 之前？**
- `UsernamePasswordAuthenticationFilter` 处理表单登录，ruoyi 不使用
- Token 认证是 ruoyi 的核心，必须在更早的位置执行，这样后续 Filter 才能拿到 LoginUser
- 排在 `AnonymousAuthenticationFilter` 之前，避免被当成"匿名用户"

## 4. 关键要点总结

- 自定义 Filter 继承 `OncePerRequestFilter`，保证每个请求只执行一次
- `addFilterBefore` / `addFilterAfter` 控制插入位置
- `TenantContextWebFilter` 注册为**普通 Web Filter**（不经过 Security）
- `TokenAuthenticationFilter` 插入到 Security 链中，在 `UsernamePasswordAuthenticationFilter` 之前
- **关键**：finally 块清理 ThreadLocal，防止内存泄漏

## 5. 练习题

### 练习 1：基础（必做）

写一个 `ApiAccessLogFilter`，在请求结束后打印"用户 ID + URL + 耗时"。

### 练习 2：进阶

修改 `TenantContextWebFilter`，让它也支持从 `?tenantId=xxx` 参数中获取租户 ID（用于 SSE / WebSocket 场景）。

### 练习 3：挑战（选做）

阅读 `TokenAuthenticationFilter.mockLoginUser` 方法，思考：为什么 ruoyi 提供了这个"模拟登录"功能？它如何提升开发效率？生产环境如何关闭？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`
- Spring Security 添加 Filter：https://docs.spring.io/spring-security/reference/servlet/architecture.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
