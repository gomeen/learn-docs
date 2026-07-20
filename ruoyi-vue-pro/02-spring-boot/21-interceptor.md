# 18 拦截器：HandlerInterceptor

> 掌握 Spring MVC 的拦截器机制，能在 ruoyi-vue-pro 中实现权限校验、日志记录等横切逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `HandlerInterceptor` 的作用：拦截 Controller 方法前后
- 掌握拦截器的三个方法：`preHandle`、`postHandle`、`afterCompletion`
- 能在 ruoyi-vue-pro 中读懂 API 访问日志拦截器
- 区分拦截器（Interceptor）与过滤器（Filter）的差异

## 📚 前置知识

- [20-exception-handler.md](./20-exception-handler.md)
- [22-filter.md](./22-filter.md)（下篇）

## 1. 核心概念

### 1.1 拦截器执行时机

```
HTTP 请求 → Filter 链 → DispatcherServlet → 拦截器链（preHandle）
→ Controller 方法 → 拦截器链（postHandle）→ 视图渲染
→ 拦截器链（afterCompletion）→ Filter 链（响应）
```

> 📌 **Sighting**：Filter 专题见 [19-filter](./22-filter.md)。此处只需知道「Filter 更靠前、Interceptor 在 Spring MVC 内」。

| 方法 | 触发时机 | 用途 |
|------|---------|------|
| `preHandle` | Controller 执行前 | 权限校验、参数预处理 |
| `postHandle` | Controller 执行后、视图渲染前 | 日志记录、修改 ModelAndView |
| `afterCompletion` | 整个请求完成后 | 资源清理、异常处理 |

### 1.2 拦截器 vs 过滤器

| 特性 | Filter | Interceptor |
|------|--------|-------------|
| 规范 | Servlet 规范 | Spring MVC |
| 范围 | 所有请求 | 仅 Spring MVC 处理的请求 |
| 触发 | DispatcherServlet 之前 | DispatcherServlet 之后 |
| 拿得到 HandlerMethod | ❌ | ✅ |
| 异常处理 | ❌ | ✅（`afterCompletion`） |

## 2. 代码示例

### 2.1 自定义拦截器

```java
// 文件：LoginInterceptor.java
@Component
public class LoginInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String token = request.getHeader("Authorization");
        if (token == null || !checkToken(token)) {
            response.setStatus(401);
            return false;  // 阻止 Controller 执行
        }
        // 把用户信息放入 request attribute
        request.setAttribute("user", getUserByToken(token));
        return true;
    }

    @Override
    public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler, ModelAndView modelAndView) {
        // Controller 执行后，视图渲染前
        log.info("[postHandle] {}", request.getRequestURI());
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        // 整个请求完成后（包括异常）
        log.info("[afterCompletion] status={}", response.getStatus());
    }
}
```

### 2.2 注册拦截器

```java
// 文件：WebMvcConfig.java
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new LoginInterceptor())
            .addPathPatterns("/admin-api/**")   // 拦截路径
            .excludePathPatterns("/admin-api/auth/login");  // 排除路径
    }
}
```

## 3. 关键要点总结

- **拦截器三个方法**：`preHandle`（前）、`postHandle`（后）、`afterCompletion`（完成）
- **注册方式**：`WebMvcConfigurer.addInterceptors(InterceptorRegistry)`
- **Interceptor vs Filter**：
  - Filter 范围更广（所有请求）
  - Interceptor 能拿到 `HandlerMethod`（更适合 Spring MVC 场景）
- **ruoyi 用 Filter 实现 API 日志**（性能更优）
- **ruoyi 用 Interceptor + GlobalExceptionHandler 实现权限校验**
- **Filter 顺序用 `WebFilterOrderEnum` 统一管理**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
