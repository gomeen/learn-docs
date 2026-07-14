# 18 拦截器：HandlerInterceptor

> 掌握 Spring MVC 的拦截器机制，能在 ruoyi-vue-pro 中实现权限校验、日志记录等横切逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `HandlerInterceptor` 的作用：拦截 Controller 方法前后
- 掌握拦截器的三个方法：`preHandle`、`postHandle`、`afterCompletion`
- 能在 ruoyi-vue-pro 中读懂 API 访问日志拦截器
- 区分拦截器（Interceptor）与过滤器（Filter）的差异

## 📚 前置知识

- 17-exception-handler.md
- 19-filter.md（下篇）

## 1. 核心概念

### 1.1 拦截器执行时机

```
HTTP 请求 → Filter 链 → DispatcherServlet → 拦截器链（preHandle）
→ Controller 方法 → 拦截器链（postHandle）→ 视图渲染
→ 拦截器链（afterCompletion）→ Filter 链（响应）
```

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 API 访问日志拦截器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/apilog/core/interceptor/ApiAccessLogInterceptor.java`（基于文件搜索存在）

ruoyi 中有 `ApiAccessLogInterceptor` 用于记录 API 访问日志。框架还提供了 Filter 版本：

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/apilog/core/filter/ApiAccessLogFilter.java`
**核心代码**（行 1-30）：

```java
package cn.iocoder.yudao.framework.apilog.core.filter;

import cn.iocoder.yudao.framework.apilog.core.annotation.ApiAccessLog;
import cn.iocoder.yudao.framework.common.biz.infra.logger.ApiAccessLogCommonApi;
import cn.iocoder.yudao.framework.common.biz.infra.logger.dto.ApiAccessLogCreateReqDTO;
import cn.iocoder.yudao.framework.web.core.util.WebFrameworkUtils;
import lombok.RequiredArgsConstructor;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * API 访问日志 Filter
 *
 * @author 芋道源码
 */
@RequiredArgsConstructor
public class ApiAccessLogFilter extends OncePerRequestFilter {
```

**解读**：
- 第 24 行：继承 `OncePerRequestFilter`（Filter 形式）
- ruoyi 选择 **Filter 而非 Interceptor** 实现 API 日志，因为：
  - Filter 在所有请求（不限于 Spring MVC）前生效
  - 性能更优（不需要 Spring MVC 的 HandlerExecutionChain）
  - 与 ruoyi 的"Filter 链"架构一致

### 3.2 Web 配置中注册拦截器（推测）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 101-127）：

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

/**
 * 创建 RequestBodyCacheFilter Bean，可重复读取请求内容
 */
@Bean
public FilterRegistrationBean<CacheRequestBodyFilter> requestBodyCacheFilter() {
    return createFilterBean(new CacheRequestBodyFilter(), WebFilterOrderEnum.REQUEST_BODY_CACHE_FILTER);
}
```

**解读**：
- 第 3 行：`@Order(value = WebFilterOrderEnum.CORS_FILTER)` 用枚举管理 Filter 顺序
- 第 4 行：注释说明这个顺序设置是为了修复 CORS 失效问题
- 第 6-15 行：CORS 配置（跨域资源共享）
- 第 18 行：注册 `CacheRequestBodyFilter`，支持多次读取请求体
- **设计模式**：`FilterRegistrationBean<T>` + `createFilterBean` 工厂方法统一创建 Filter

### 3.3 全局异常处理 + 拦截器的配合

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 130-160）：

```java
/**
 * 处理 ServiceException 业务异常
 */
@ExceptionHandler(value = ServiceException.class)
public CommonResult<?> serviceExceptionHandler(ServiceException ex) {
    log.warn("[serviceExceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, null);
    return CommonResult.error(ex.getCode(), ex.getMessage());
}
```

**解读**：
- 拦截器在 `preHandle` 中抛 `ServiceException` 也会被 `GlobalExceptionHandler` 捕获
- **配合使用**：拦截器用于权限校验，抛业务异常（如 `ACCESS_DENIED`），由 `GlobalExceptionHandler` 统一返回
- **优势**：避免在每个 Controller 重复权限校验代码

## 4. 关键要点总结

- **拦截器三个方法**：`preHandle`（前）、`postHandle`（后）、`afterCompletion`（完成）
- **注册方式**：`WebMvcConfigurer.addInterceptors(InterceptorRegistry)`
- **Interceptor vs Filter**：
  - Filter 范围更广（所有请求）
  - Interceptor 能拿到 `HandlerMethod`（更适合 Spring MVC 场景）
- **ruoyi 用 Filter 实现 API 日志**（性能更优）
- **ruoyi 用 Interceptor + GlobalExceptionHandler 实现权限校验**
- **Filter 顺序用 `WebFilterOrderEnum` 统一管理**

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `LogInterceptor`，在 `preHandle` 中记录请求 URL + method + IP，在 `afterCompletion` 中记录响应状态码 + 耗时。

### 练习 2：进阶

解释为什么 ruoyi 用 `ApiAccessLogFilter`（Filter）实现 API 日志，而不是用 `HandlerInterceptor`？这两种实现各有什么优劣？

### 练习 3：挑战（选做）

实现一个 `PermissionInterceptor`，从 `@PreAuthorize("hasAuthority('system:user:create')")` 注解读取权限标识，在 `preHandle` 中检查当前用户是否有权限，无权限抛 `ServiceException`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/apilog/core/filter/ApiAccessLogFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- Spring MVC 拦截器：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html
- 芋道拦截器：https://doc.iocoder.cn/spring-boot-interceptor/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
