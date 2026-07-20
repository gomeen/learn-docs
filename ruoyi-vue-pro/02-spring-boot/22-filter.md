# 19 过滤器：Filter 与 OncePerRequestFilter

> 掌握 Servlet Filter 的工作原理，能在 ruoyi-vue-pro 中读懂 CORS、请求体缓存、API 加密等过滤器。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Filter 的工作原理和生命周期
- 掌握 `OncePerRequestFilter` 的作用
- 能在 ruoyi-vue-pro 中读懂 CORS Filter、CacheRequestBodyFilter
- 区分 Filter 与 Interceptor 的使用场景

## 📚 前置知识

- [21-interceptor.md](./21-interceptor.md)（上篇）

## 1. 核心概念

### 1.1 Filter 是什么？

Filter 是 Servlet 规范定义的**请求拦截器**，在请求到达 Servlet 之前 / 之后执行：
- 多个 Filter 组成 Filter 链（按 `@Order` 排序）
- 常用于：跨域（CORS，详见 [CORS](../../_common/05-web-security/05-cors.md)）、请求体缓存、XSS 过滤（详见 [XSS](../../_common/05-web-security/02-xss.md)）、API 加密、字符编码

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

## 3. 关键要点总结

- **Filter 是 Servlet 规范**，Interceptor 是 Spring MVC
- **Filter 范围更广**（所有请求），Interceptor 仅 Spring MVC 请求
- **`OncePerRequestFilter`** 保证每个请求只执行一次
- **ruoyi Filter 链**：CORS → RequestBodyCache → Demo → ApiAccessLog → ApiEncrypt
- **`@Order` 控制 Filter 顺序**（数字越小越先）
- **`@ConditionalOnProperty` 让 Filter 按需启用**
- **ruoyi 用 `FilterRegistrationBean` + 工厂方法统一注册**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
