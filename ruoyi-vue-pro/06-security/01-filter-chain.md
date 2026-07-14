# 1 Spring Security Filter Chain（过滤器链）

> 理解 Spring Security 核心：Filter Chain 是如何对每个 HTTP 请求进行安全过滤的。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Filter（过滤器）模式和责任链模式
- 理解 Spring Security 的 15+ 个内置 Filter 及其顺序
- 能看懂 `YudaoWebSecurityConfigurerAdapter` 中 `filterChain` 方法的配置
- 知道 ruoyi-vue-pro 的 `TokenAuthenticationFilter` 处于过滤链的哪个位置

## 📚 前置知识

- Servlet 规范（Servlet Filter）
- Spring Boot 自动配置原理
- 设计模式：责任链模式（Chain of Responsibility）

## 1. 核心概念

### 1.1 Filter 模式

**过滤器（Filter）** 是 Servlet 规范中的一种组件，作用在请求到达 Servlet 之前、响应返回客户端之前进行拦截处理。

```
HTTP Request
    ↓
[Filter 1] → 鉴权
    ↓
[Filter 2] → 日志
    ↓
[Filter 3] → XSS 清理
    ↓
Controller（业务逻辑）
    ↓
[Filter 3] ← 后置处理
    ↓
[Filter 2] ← 后置处理
    ↓
[Filter 1] ← 后置处理
    ↓
HTTP Response
```

每个 Filter 可以：
1. 拦截请求，进行预处理（如鉴权）
2. 决定是否继续传递（`chain.doFilter()`）
3. 对响应进行后置处理

### 1.2 Spring Security Filter Chain

Spring Security 的本质就是**一个巨大的 Filter Chain**。每个请求都会经过一连串的 Filter，每个 Filter 负责一个安全职责：

| Filter 名称 | 作用 |
|------------|------|
| `SecurityContextPersistenceFilter` | 加载/保存 SecurityContext |
| `LogoutFilter` | 处理登出 |
| `UsernamePasswordAuthenticationFilter` | 处理表单登录 |
| `TokenAuthenticationFilter` | **ruoyi 自定义：处理 Token 鉴权** |
| `AnonymousAuthenticationFilter` | 匿名用户兜底 |
| `ExceptionTranslationFilter` | 处理认证/授权异常 |
| `FilterSecurityInterceptor` | 最终授权决策 |
| ... | ... |

### 1.3 OncePerRequestFilter

ruoyi 自定义的 `TokenAuthenticationFilter` 继承自 `OncePerRequestFilter`，它保证**每个请求只执行一次**（即使内部 `chain.doFilter` 被多次调用）。

## 2. 代码示例

### 2.1 自定义 Filter 示例

```java
// 文件：MyFilter.java
@Component
public class MyFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        // 1. 前置处理：例如检查 Token
        String token = request.getHeader("X-Token");
        if (token == null || token.isEmpty()) {
            response.setStatus(401);
            response.getWriter().write("Unauthorized");
            return; // 阻断，不调用 chain.doFilter
        }

        // 2. 继续过滤链
        try {
            chain.doFilter(request, response);
        } finally {
            // 3. 后置处理：例如清理 ThreadLocal
            // cleanup();
        }
    }
}
```

**说明**：
- 继承 `OncePerRequestFilter` 而不是实现 `Filter`，避免在异步分发时重复执行
- 不调用 `chain.doFilter()` 表示中断请求
- `finally` 块保证清理逻辑一定会执行（防内存泄漏）

### 2.2 常见错误：忘记调用 chain.doFilter

```java
// ❌ 错误：忘记调用 chain.doFilter()，请求永远到不了 Controller
@Override
protected void doFilterInternal(...) {
    log.info("请求来了");
    // 忘记 chain.doFilter()，请求被吞掉
}

// ✅ 正确
@Override
protected void doFilterInternal(...) {
    log.info("请求来了");
    chain.doFilter(request, response);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 TokenAuthenticationFilter（自定义 Filter）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 32-69）：

```java
@RequiredArgsConstructor
public class TokenAuthenticationFilter extends OncePerRequestFilter {

    private final SecurityProperties securityProperties;
    private final GlobalExceptionHandler globalExceptionHandler;
    private final OAuth2TokenCommonApi oauth2TokenApi;

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
                CommonResult<?> result = globalExceptionHandler.allExceptionHandler(request, ex);
                ServletUtils.writeJSON(response, result);
                return;
            }
        }

        // 继续过滤链
        chain.doFilter(request, response);
    }
}
```

**解读**：
- 第 32 行：继承 `OncePerRequestFilter`，保证一个请求只过滤一次
- 第 44 行：从请求 Header（或参数）中提取 Token
- 第 50 行：调用 RPC 服务校验 Token，返回 `LoginUser`
- 第 58 行：调用 `setLoginUser` 将 `LoginUser` 设置到 `SecurityContextHolder`，供后续 Filter 和 Controller 使用
- 第 60-64 行：捕获异常后**直接返回 JSON 响应 + return**，不调用 `chain.doFilter`，中断请求
- 第 68 行：正常情况下放行到下一个 Filter

### 3.2 SecurityFilterChain 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 109-153）：

```java
@Bean
protected SecurityFilterChain filterChain(HttpSecurity httpSecurity) throws Exception {
    httpSecurity
            .cors(Customizer.withDefaults())
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(c -> c.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .headers(c -> c.frameOptions(HeadersConfigurer.FrameOptionsConfig::disable))
            .exceptionHandling(c -> c.authenticationEntryPoint(authenticationEntryPoint)
                    .accessDeniedHandler(accessDeniedHandler));

    // 1. 静态资源 + @PermitAll 注解 + yudao.security.permit-all-urls 全部免登录
    httpSecurity.authorizeHttpRequests(c -> c
            .requestMatchers(HttpMethod.GET, "/*.html", "/*.css", "/*.js").permitAll()
            .requestMatchers(HttpMethod.GET, permitAllUrls.get(HttpMethod.GET).toArray(new String[0])).permitAll()
            .requestMatchers(securityProperties.getPermitAllUrls().toArray(new String[0])).permitAll()
    );
    // 2. 项目的自定义规则
    httpSecurity.authorizeHttpRequests(c -> authorizeRequestsCustomizers.forEach(customizer -> customizer.customize(c)));
    // 3. 兜底：必须认证
    httpSecurity.authorizeHttpRequests(c -> c
            .dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()
            .anyRequest().authenticated());

    // 关键：将 TokenAuthenticationFilter 添加到 UsernamePasswordAuthenticationFilter 之前
    httpSecurity.addFilterBefore(authenticationTokenFilter, UsernamePasswordAuthenticationFilter.class);
    return httpSecurity.build();
}
```

**解读**：
- 第 116 行：禁用 CSRF（因为基于 Token，不依赖 Cookie）
- 第 118 行：设置 Session 为无状态（STATELESS），不创建 HttpSession
- 第 130-141 行：配置**白名单 URL**（静态资源、`@PermitAll` 注解标记的接口）
- 第 148 行：兜底规则 `anyRequest().authenticated()`，所有未匹配白名单的请求必须登录
- 第 151 行：**关键** — `addFilterBefore` 将自定义的 Token 过滤器插入到 Spring Security 过滤器链中，位置在 `UsernamePasswordAuthenticationFilter` 之前

## 4. 关键要点总结

- Spring Security 的核心是 `FilterChain`，每个请求都按顺序经过 N 个 Filter
- ruoyi 自定义 `TokenAuthenticationFilter` 继承 `OncePerRequestFilter`，负责解析 Token 并设置 LoginUser
- 通过 `HttpSecurity.addFilterBefore()` 把自定义 Filter 插入到内置 Filter 之前
- `chain.doFilter()` 放行；`return` 中断；`finally` 中清理 ThreadLocal
- ruoyi 禁用 CSRF、设置 Session 为 STATELESS，符合纯 Token 鉴权场景

## 5. 练习题

### 练习 1：基础（必做）

手写一个 `RequestLogFilter`，继承 `OncePerRequestFilter`，在请求前打印 `请求方法 + URL`，请求后打印 `耗时（毫秒）`。

### 练习 2：进阶

阅读 `YudaoWebSecurityConfigurerAdapter.java`，画出 ruoyi 的 Security Filter Chain 顺序图，标注每个 Filter 的作用。

### 练习 3：挑战（选做）

如果要在 ruoyi 中新增一个"IP 白名单" Filter，限制只有内网 IP 才能访问 `/admin-api/**`，请说明应该插入到 Filter Chain 的哪个位置，为什么？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- Spring Security 官方文档：https://docs.spring.io/spring-security/reference/servlet/architecture.html
- 责任链模式：https://refactoringguru.cn/design-patterns/chain-of-responsibility

---

**文档版本**：v1.0
**最后更新**：2026-07-13
