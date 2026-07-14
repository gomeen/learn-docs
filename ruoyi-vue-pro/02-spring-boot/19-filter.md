# 19 过滤器：Filter 与 OncePerRequestFilter

> 掌握 Servlet Filter 的工作原理，能在 ruoyi-vue-pro 中读懂 CORS、请求体缓存、API 加密等过滤器。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Filter 的工作原理和生命周期
- 掌握 `OncePerRequestFilter` 的作用
- 能在 ruoyi-vue-pro 中读懂 CORS Filter、CacheRequestBodyFilter
- 区分 Filter 与 Interceptor 的使用场景

## 📚 前置知识

- 18-interceptor.md（上篇）

## 1. 核心概念

### 1.1 Filter 是什么？

Filter 是 Servlet 规范定义的**请求拦截器**，在请求到达 Servlet 之前 / 之后执行：
- 多个 Filter 组成 Filter 链（按 `@Order` 排序）
- 常用于：跨域（CORS）、请求体缓存、XSS 过滤、API 加密、字符编码

### 1.2 Filter 生命周期

```
init()           ← 容器启动时调用一次
↓
doFilter()       ← 每个请求调用一次
  ├── chain.doFilter(request, response)  // 传递给下一个 Filter
  │     └── ... (更多 Filter / Servlet)
  └── 自定义逻辑
↓
destroy()        ← 容器关闭时调用一次
```

### 1.3 `OncePerRequestFilter`

Spring 提供的便捷基类，保证 Filter **每个请求只执行一次**（防止内部 forward / include 重复触发）。

```java
public abstract class OncePerRequestFilter implements Filter {
    public final void doFilter(...) {
        // 内部检查，避免重复执行
        if (request.getAttribute("filterName") == null) {
            request.setAttribute("filterName", true);
            doFilterInternal(request, response, chain);
        } else {
            chain.doFilter(request, response);
        }
    }
    protected abstract void doFilterInternal(...);
}
```

## 2. 代码示例

### 2.1 字符编码 Filter

```java
// 文件：EncodingFilter.java
public class EncodingFilter implements Filter {
    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        log.info("[init] 字符编码过滤器启动");
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) {
        request.setCharacterEncoding("UTF-8");
        response.setCharacterEncoding("UTF-8");
        chain.doFilter(request, response);
    }

    @Override
    public void destroy() {
        log.info("[destroy] 字符编码过滤器销毁");
    }
}
```

### 2.2 OncePerRequestFilter

```java
// 文件：AuthFilter.java
public class AuthFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) {
        String token = request.getHeader("Authorization");
        if (token == null) {
            response.setStatus(401);
            return;
        }
        chain.doFilter(request, response);
    }
}
```

### 2.3 注册 Filter

```java
// 方式 1：@Component（自动注册）
@Component
@Order(1)
public class MyFilter extends OncePerRequestFilter { ... }

// 方式 2：@Bean + FilterRegistrationBean（更灵活）
@Bean
public FilterRegistrationBean<MyFilter> myFilter() {
    FilterRegistrationBean<MyFilter> bean = new FilterRegistrationBean<>(new MyFilter());
    bean.setOrder(1);
    bean.addUrlPatterns("/*");
    return bean;
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 CORS Filter 解决跨域

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 102-119）：

```java
// ========== Filter 相关 ==========

/**
 * 创建 CorsFilter Bean，解决跨域问题
 */
@Bean
@Order(value = WebFilterOrderEnum.CORS_FILTER) // 特殊：修复因执行顺序影响到跨域配置不生效问题
public FilterRegistrationBean<CorsFilter> corsFilterBean() {
    // 创建 CorsConfiguration 对象
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowCredentials(true);
    config.addAllowedOriginPattern("*"); // 设置访问源地址
    config.addAllowedHeader("*"); // 设置访问源请求头
    config.addAllowedMethod("*"); // 设置访问源请求方法
    // 创建 UrlBasedCorsConfigurationSource 对象
    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/**", config); // 对接口配置跨域设置
    return createFilterBean(new CorsFilter(source), WebFilterOrderEnum.CORS_FILTER);
}
```

**解读**：
- 第 6 行：`@Order(WebFilterOrderEnum.CORS_FILTER)` CORS Filter 优先级最高（最先执行）
- 第 7 行注释：说明这个顺序设置是为了**修复 CORS 配置不生效问题**（如果 CORS Filter 不是最先执行，预检请求 OPTIONS 可能被其他 Filter 拦截）
- 第 8-15 行：跨域配置（允许所有来源、所有请求头、所有方法）
- **设计要点**：`setAllowCredentials(true)` + `addAllowedOriginPattern("*")` 允许跨域携带 Cookie

### 3.2 RequestBody Cache Filter 重复读取请求体

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 121-127）：

```java
/**
 * 创建 RequestBodyCacheFilter Bean，可重复读取请求内容
 */
@Bean
public FilterRegistrationBean<CacheRequestBodyFilter> requestBodyCacheFilter() {
    return createFilterBean(new CacheRequestBodyFilter(), WebFilterOrderEnum.REQUEST_BODY_CACHE_FILTER);
}
```

**解读**：
- 第 3 行：注册 `CacheRequestBodyFilter`
- **为什么需要缓存请求体？** HTTP 请求体（`InputStream`）默认只能读一次
  - Controller 用 `@RequestBody` 读取
  - 访问日志 / API 加密 Filter 也想读取
  - 没有缓存时，第二个读取会得到空内容
- **解决方案**：用 `ContentCachingRequestWrapper` 包装请求，缓存请求体到内存

### 3.3 Demo Filter 演示模式

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 129-136）：

```java
/**
 * 创建 DemoFilter Bean，演示模式
 */
@Bean
@ConditionalOnProperty(value = "yudao.demo", havingValue = "true")
public FilterRegistrationBean<DemoFilter> demoFilter() {
    return createFilterBean(new DemoFilter(), WebFilterOrderEnum.DEMO_FILTER);
}
```

**解读**：
- 第 3 行：`@ConditionalOnProperty(value = "yudao.demo", havingValue = "true")` 只在演示模式启用
- **典型应用**：
  - 演示环境开启：所有 POST/PUT/DELETE 请求返回假成功
  - 生产环境关闭：所有写操作真实执行
- **设计意图**：演示环境防止数据被误删，运维不慎操作

### 3.4 Filter 工厂方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 138-142）：

```java
public static <T extends Filter> createFilterBean(T filter, Integer order) {
    FilterRegistrationBean<T> bean = new FilterRegistrationBean<>(filter);
    bean.setOrder(order);
    return bean;
}
```

**解读**：
- 第 2 行：`<T extends Filter>` 泛型方法，接收任何 Filter 子类
- 第 3-5 行：创建 `FilterRegistrationBean` 并设置 order
- **设计模式**：工厂方法 + 泛型，消除重复代码
- **ruoyi Filter 链顺序**（从早到晚）：
  1. CORS_FILTER（跨域）
  2. REQUEST_BODY_CACHE_FILTER（请求体缓存）
  3. DEMO_FILTER（演示模式）
  4. ApiAccessLogFilter（API 日志）
  5. ApiEncryptFilter（API 加密）

## 4. 关键要点总结

- **Filter 是 Servlet 规范**，Interceptor 是 Spring MVC
- **Filter 范围更广**（所有请求），Interceptor 仅 Spring MVC 请求
- **`OncePerRequestFilter`** 保证每个请求只执行一次
- **ruoyi Filter 链**：CORS → RequestBodyCache → Demo → ApiAccessLog → ApiEncrypt
- **`@Order` 控制 Filter 顺序**（数字越小越先）
- **`@ConditionalOnProperty` 让 Filter 按需启用**
- **ruoyi 用 `FilterRegistrationBean` + 工厂方法统一注册**

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `TimeCostFilter` 继承 `OncePerRequestFilter`，打印每个请求的耗时（毫秒）+ URL + 状态码。

### 练习 2：进阶

阅读 `YudaoWebAutoConfiguration`，列出所有 Filter 的注册顺序，并解释为什么 CORS Filter 必须排在最前面。

### 练习 3：挑战（选做）

实现一个 `RateLimitFilter`，限制每个 IP 每分钟最多 60 次请求（用 Redis 计数器），超过返回 429 状态码。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- Spring Filter 文档：https://docs.spring.io/spring-framework/reference/web/webmvc/filters.html
- 芋道 Filter 教程：https://doc.iocoder.cn/spring-boot-filter/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
