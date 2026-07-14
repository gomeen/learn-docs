# 6.1 Web 增强：CORS、参数、异常

> 掌握 yudao Web Starter 的各项增强能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao Web Starter 的整体能力
- 掌握统一异常处理、统一响应
- 理解 CORS、加密、API 日志、防 XSS
- 能在 yudao 中使用 Web 增强

## 📚 前置知识

- Spring MVC
- 过滤器 / 拦截器
- HTTP 协议基础

## 1. 核心概念

### 1.1 yudao Web Starter 的能力

| 能力 | 组件 |
|------|------|
| 统一响应 | `CommonResult` + `GlobalResponseHandler` |
| 统一异常 | `GlobalExceptionHandler` |
| 统一日志 | `ApiAccessLogFilter` + `ApiErrorLogFilter` |
| 防 XSS | `XssFilter` |
| 防重复提交 | `RepeatSubmitFilter` |
| CORS | `CorsFilter` |
| API 加密 | `ApiEncryptFilter` + `ApiEncryptProperties` |
| Swagger/Knife4j | `OpenApiConfiguration` |
| 字典翻译 | `DictDataVOConvertSerializer` |
| 数据脱敏 | `DesensitizeSerializer` |

## 2. 代码示例

### 2.1 统一响应

```java
@GetMapping("/get")
public CommonResult<UserRespVO> getUser(@RequestParam("id") Long id) {
    UserRespVO user = userService.getUser(id);
    return CommonResult.success(user);
}

@GetMapping("/list")
public CommonResult<List<UserRespVO>> listUsers() {
    return CommonResult.success(userService.listUsers());
}
```

### 2.2 统一异常处理

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ServiceException.class)
    public CommonResult<?> handleServiceException(ServiceException ex) {
        return CommonResult.error(ex.getCode(), ex.getMessage());
    }
}
```

### 2.3 CORS 配置

```yaml
yudao:
  cors:
    enable: true
    allowed-origins:
      - http://localhost:3000
      - https://admin.example.com
```

## 3. ruoyi 仓库源码解读

### 3.1 WebAutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/`
**核心代码**（节选）：

```java
@AutoConfiguration
public class YudaoWebAutoConfiguration {

    @Bean
    public GlobalExceptionHandler globalExceptionHandler() {
        return new GlobalExceptionHandler();
    }

    @Bean
    public CorsFilter corsFilter(WebProperties webProperties) {
        // ...
    }

    @Bean
    public XssFilter xssFilter() {
        return new XssFilter();
    }
}
```

### 3.2 GlobalExceptionHandler

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（节选）：

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ServiceException.class)
    public CommonResult<?> serviceException(ServiceException ex) {
        return CommonResult.error(ex);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public CommonResult<?> methodArgumentNotValid(MethodArgumentNotValidException ex) {
        // @Valid 校验失败
        FieldError fieldError = ex.getBindingResult().getFieldError();
        return CommonResult.error(BAD_REQUEST, fieldError.getDefaultMessage());
    }

    @ExceptionHandler(Exception.class)
    public CommonResult<?> allException(Exception ex) {
        return CommonResult.error(INTERNAL_ERROR);
    }
}
```

**解读**：
- 统一处理 `ServiceException`、`MethodArgumentNotValidException`、`Exception`
- **业务方只需抛 `ServiceException`**，全局自动返回友好提示

### 3.3 ApiAccessLogFilter（API 访问日志）

```java
public class ApiAccessLogFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) {
        // 1. 记录开始时间
        long begin = System.currentTimeMillis();
        try {
            chain.doFilter(request, response);
        } finally {
            // 2. 记录访问日志
            long cost = System.currentTimeMillis() - begin;
            log.info("URL: {} Method: {} Status: {} Cost: {}ms",
                request.getRequestURI(), request.getMethod(), response.getStatus(), cost);
        }
    }
}
```

### 3.4 XssFilter

```java
public class XssFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) {
        // 用 XssHttpServletRequestWrapper 包装 request，过滤所有参数
        chain.doFilter(new XssHttpServletRequestWrapper(request), response);
    }
}
```

## 4. 关键要点总结

- **yudao Web Starter** 提供 10+ 个 Web 增强能力
- **统一响应 `CommonResult<T>`** + **统一异常 `GlobalExceptionHandler`**
- **API 日志** 自动记录所有请求
- **XSS 过滤** 通过 HttpServletRequestWrapper 实现
- **API 加密**支持 AES + RSA 混合

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中触发一个 `ServiceException`，观察统一响应格式。

### 练习 2：进阶

自定义一个 `GlobalExceptionHandler`，捕获所有 `IllegalArgumentException` 并返回 `BAD_REQUEST`。

### 练习 3：挑战（选做）

实现"接口签名校验"：请求必须带 `sign` 参数，由时间戳 + secret + body 计算。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- Spring MVC 文档：https://docs.spring.io/spring-framework/reference/web/webmvc.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
