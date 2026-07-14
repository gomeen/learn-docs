# 3 SecurityFilterChain 配置

> 详解 ruoyi 的 `SecurityFilterChain` Bean：URL 白名单、CSRF、CORS、自定义规则、Filter 顺序。

## 🎯 学习目标

完成本文档后，你将能够：
- 用新版 `SecurityFilterChain`（基于 `HttpSecurity`）配置 Spring Security
- 理解 ruoyi 的三层 URL 匹配规则：静态资源 / `@PermitAll` / 配置项
- 看懂 `AuthorizeRequestsCustomizer` 抽象类如何让每个 Module 自定义规则
- 掌握 `addFilterBefore` 的用法

## 📚 前置知识

- 01-filter-chain.md
- Spring `@Configuration` 和 `@Bean`
- Java 8 函数式接口 `Customizer`

## 1. 核心概念

### 1.1 新版 vs 旧版 Spring Security 配置

Spring Security 5.7+ 弃用了 `WebSecurityConfigurerAdapter`（继承方式），推荐使用 **`SecurityFilterChain` Bean**（组合方式）：

```java
// ❌ 旧版（已废弃）
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) { ... }
}

// ✅ 新版（推荐）
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http.authorizeHttpRequests(c -> c.anyRequest().authenticated());
    return http.build();
}
```

### 1.2 ruoyi 的三层 URL 规则

```
Layer 1: 全局共享规则（白名单）
    ├─ 静态资源 (*.html, *.css, *.js)
    ├─ @PermitAll 注解标记的 URL
    └─ yudao.security.permit-all-urls 配置项
↓
Layer 2: 项目自定义规则（AuthorizeRequestsCustomizer）
↓
Layer 3: 兜底规则
    └─ anyRequest().authenticated()（必须登录）
```

## 2. 代码示例

### 2.1 最小化 SecurityFilterChain

```java
// 文件：SecurityConfig.java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())       // 禁用 CSRF
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()  // 白名单
                .anyRequest().authenticated()               // 其他需登录
            );
        return http.build();
    }
}
```

### 2.2 多个自定义规则（顺序敏感）

```java
// 文件：MultiCustomRuleConfig.java
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http.authorizeHttpRequests(auth -> auth
        // 注意：规则按顺序匹配，先匹配先生效
        .requestMatchers("/admin/**").hasRole("ADMIN")      // 1. 管理员路径
        .requestMatchers("/user/**").hasAnyRole("USER", "ADMIN") // 2. 用户路径
        .requestMatchers("/login", "/register").permitAll()  // 3. 公开路径
        .anyRequest().denyAll()                             // 4. 兜底
    );
    return http.build();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 YudaoWebSecurityConfigurerAdapter

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 109-153）：

```java
@AutoConfiguration
@AutoConfigureOrder(-1) // 先于 Spring Security 自动配置
@EnableMethodSecurity(securedEnabled = true)
public class YudaoWebSecurityConfigurerAdapter {

    @Resource
    private WebProperties webProperties;
    @Resource
    private SecurityProperties securityProperties;
    @Resource
    private AuthenticationEntryPoint authenticationEntryPoint;
    @Resource
    private AccessDeniedHandler accessDeniedHandler;
    @Resource
    private TokenAuthenticationFilter authenticationTokenFilter;
    @Resource
    private List<AuthorizeRequestsCustomizer> authorizeRequestsCustomizers;

    @Bean
    public AuthenticationManager authenticationManagerBean(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    protected SecurityFilterChain filterChain(HttpSecurity httpSecurity) throws Exception {
        // 基础配置
        httpSecurity
                .cors(Customizer.withDefaults())
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(c -> c.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .headers(c -> c.frameOptions(HeadersConfigurer.FrameOptionsConfig::disable))
                .exceptionHandling(c -> c.authenticationEntryPoint(authenticationEntryPoint)
                        .accessDeniedHandler(accessDeniedHandler));

        // ①：全局共享规则
        Multimap<HttpMethod, String> permitAllUrls = getPermitAllUrlsFromAnnotations();
        httpSecurity.authorizeHttpRequests(c -> c
                .requestMatchers(HttpMethod.GET, "/*.html", "/*.css", "/*.js").permitAll()
                .requestMatchers(HttpMethod.GET, permitAllUrls.get(HttpMethod.GET).toArray(new String[0])).permitAll()
                .requestMatchers(HttpMethod.POST, permitAllUrls.get(HttpMethod.POST).toArray(new String[0])).permitAll()
                .requestMatchers(securityProperties.getPermitAllUrls().toArray(new String[0])).permitAll()
        );
        // ②：项目自定义规则
        httpSecurity.authorizeHttpRequests(c -> authorizeRequestsCustomizers.forEach(customizer -> customizer.customize(c)));
        // ③：兜底
        httpSecurity.authorizeHttpRequests(c -> c
                .dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()
                .anyRequest().authenticated());

        // 关键：把 Token Filter 插入到 UsernamePasswordAuthenticationFilter 之前
        httpSecurity.addFilterBefore(authenticationTokenFilter, UsernamePasswordAuthenticationFilter.class);
        return httpSecurity.build();
    }
    // ... 省略 getPermitAllUrlsFromAnnotations
}
```

**解读**：
- 第 48 行 `@AutoConfiguration` + 第 47 行 `@AutoConfigureOrder(-1)`：让该配置类在 Spring Security 默认配置之前加载
- 第 48 行 `@EnableMethodSecurity(securedEnabled = true)`：开启方法级权限（支持 `@PreAuthorize`）
- 第 130-141 行：三层白名单的合并，按 HTTP Method 分别配置
- 第 144 行：调用所有 `AuthorizeRequestsCustomizer` 的 `customize` 方法（**每个 Module 可以自定义**）
- 第 151 行：插入自定义 Token 过滤器到 `UsernamePasswordAuthenticationFilter` 之前

### 3.2 AuthorizeRequestsCustomizer（抽象类）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/AuthorizeRequestsCustomizer.java`
**核心代码**（行 17-36）：

```java
public abstract class AuthorizeRequestsCustomizer
        implements Customizer<AuthorizeHttpRequestsConfigurer<HttpSecurity>.AuthorizationManagerRequestMatcherRegistry>, Ordered {

    @Resource
    private WebProperties webProperties;

    protected String buildAdminApi(String url) {
        return webProperties.getAdminApi().getPrefix() + url;
    }

    protected String buildAppApi(String url) {
        return webProperties.getAppApi().getPrefix() + url;
    }

    @Override
    public int getOrder() {
        return 0;
    }
}
```

**解读**：
- 第 17 行：抽象类 + `Customizer` 接口，每个 Module 继承它即可自定义规则
- 第 23-29 行：提供 `buildAdminApi`、`buildAppApi` 工具方法，自动拼接 URL 前缀（如 `/admin-api/system/permission/list`）
- 第 32 行 `getOrder()`：支持排序，多个 Customizer 之间可以通过 `@Order` 注解控制顺序

**使用示例**（假设在 system Module 中）：
```java
@Component
public class SystemAuthorizeRequestsCustomizer extends AuthorizeRequestsCustomizer {
    @Override
    public void customize(AuthorizationManagerRequestMatcherRegistry registry) {
        registry.requestMatchers(buildAdminApi("/system/user/get")).permitAll();
        registry.requestMatchers(buildAdminApi("/system/permission/**").hasRole("ADMIN"));
    }
}
```

### 3.3 @PermitAll 注解扫描

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 159-219）：

```java
private Multimap<HttpMethod, String> getPermitAllUrlsFromAnnotations() {
    Multimap<HttpMethod, String> result = HashMultimap.create();
    RequestMappingHandlerMapping requestMappingHandlerMapping = (RequestMappingHandlerMapping)
            applicationContext.getBean("requestMappingHandlerMapping");
    Map<RequestMappingInfo, HandlerMethod> handlerMethodMap = requestMappingHandlerMapping.getHandlerMethods();

    for (Map.Entry<RequestMappingInfo, HandlerMethod> entry : handlerMethodMap.entrySet()) {
        HandlerMethod handlerMethod = entry.getValue();
        // 关键：检查方法或类上是否有 @PermitAll 注解
        if (!handlerMethod.hasMethodAnnotation(PermitAll.class)
            && !handlerMethod.getBeanType().isAnnotationPresent(PermitAll.class)) {
            continue;
        }
        Set<String> urls = new HashSet<>();
        if (entry.getKey().getPatternsCondition() != null) {
            urls.addAll(entry.getKey().getPatternsCondition().getPatterns());
        }
        if (entry.getKey().getPathPatternsCondition() != null) {
            urls.addAll(convertList(entry.getKey().getPathPatternsCondition().getPatterns(), PathPattern::getPatternString));
        }
        if (urls.isEmpty()) continue;

        // 按 HTTP Method 分类
        Set<RequestMethod> methods = entry.getKey().getMethodsCondition().getMethods();
        if (CollUtil.isEmpty(methods)) {
            // 没写 method，认为所有 method 都要免登录
            result.putAll(HttpMethod.GET, urls);
            result.putAll(HttpMethod.POST, urls);
            // ... 其他方法
            continue;
        }
        methods.forEach(requestMethod -> {
            switch (requestMethod) {
                case GET: result.putAll(HttpMethod.GET, urls); break;
                case POST: result.putAll(HttpMethod.POST, urls); break;
                // ...
            }
        });
    }
    return result;
}
```

**解读**：
- 第 162-163 行：拿到 Spring MVC 的 `RequestMappingHandlerMapping`，里面是**所有 Controller 方法的映射**
- 第 167-170 行：判断方法或类上是否有 `@PermitAll` 注解
- 第 173-178 行：拿到 URL pattern（如 `/system/auth/login`）
- 第 184-192 行：如果 Controller 没有指定 HTTP Method（只写 `@RequestMapping`），默认所有 Method 都免登录
- 第 195-216 行：按 HTTP Method 归类 URL，存入 `Multimap`

## 4. 关键要点总结

- ruoyi 使用新版 `SecurityFilterChain` Bean 而非继承 `WebSecurityConfigurerAdapter`
- 三层 URL 规则：① 全局白名单 → ② Module 自定义 → ③ 兜底（必须登录）
- `AuthorizeRequestsCustomizer` 抽象类让每个 Module 自由扩展 URL 规则
- `getPermitAllUrlsFromAnnotations` 自动扫描 `@PermitAll` 注解并注册为白名单
- `addFilterBefore` 把自定义 Token Filter 插入到内置 Filter 之前

## 5. 练习题

### 练习 1：基础（必做）

写一个 `SecurityFilterChain` Bean：要求 `/login` 和 `/register` 免登录，**其他**路径必须登录。

### 练习 2：进阶

继承 `AuthorizeRequestsCustomizer`，写一个 `DemoAuthorizeRequestsCustomizer`，给 `/admin-api/demo/test` 配置成 `hasRole("TEST")` 才能访问。

### 练习 3：挑战（选做）

`getPermitAllUrlsFromAnnotations` 使用了 Spring MVC 的 `RequestMappingHandlerMapping`。如果启动时 Controller 还没注册完，会出现什么问题？ruoyi 是如何保证时机的？（提示：搜索 `@AutoConfiguration` 和 `ApplicationRunner`）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/AuthorizeRequestsCustomizer.java`
- Spring Security 6 配置：https://docs.spring.io/spring-security/reference/servlet/configuration/java.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
