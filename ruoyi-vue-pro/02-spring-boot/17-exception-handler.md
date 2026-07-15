# 17 全局异常处理：@ControllerAdvice

> 掌握 `@RestControllerAdvice` + `@ExceptionHandler` 的全局异常处理，能在 ruoyi-vue-pro 中统一处理各种异常。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@RestControllerAdvice` 与 `@ControllerAdvice` 的差异
- 掌握 `@ExceptionHandler` 的使用，捕获 Controller 抛出的异常
- 能在 ruoyi-vue-pro 中读懂 `GlobalExceptionHandler` 的设计
- 理解业务异常（ServiceException）与系统异常的处理策略

## 📚 前置知识

- 16-result-wrapper.md

## 1. 核心概念

### 1.1 `@RestControllerAdvice` 是什么？

是 `@ControllerAdvice` + `@ResponseBody` 的组合，用于：
- 全局处理 Controller 抛出的异常
- 把异常转换为统一的 `CommonResult` 返回（`CommonResult` 详见 [16-result-wrapper](./16-result-wrapper.md)；Java 异常体系见 [06-exception](../01-java-fundamentals/06-exception.md)）

### 1.2 三种异常处理方式

| 方式 | 作用域 | 优先级 |
|------|--------|--------|
| `@ExceptionHandler`（方法级） | 当前 Controller | 高 |
| `@RestControllerAdvice` + `@ExceptionHandler` | 全局 | 中 |
| `ErrorController` / `BasicErrorController` | 兜底 | 低 |

### 1.3 ruoyi 的异常分类

```java
// 1. 业务异常（可预期，由业务代码抛）
throw exception(USER_NOT_EXISTS);  // → ServiceException → 200 + code != 0

// 2. 参数异常（用户输入错误）
throw new IllegalArgumentException("xxx");  // → 200 + 400

// 3. 系统异常（不可预期，如 NPE、DB 异常）
// → GlobalExceptionHandler 兜底 → 500
```

## 2. 代码示例

### 2.1 全局异常处理器

```java
// 文件：GlobalExceptionHandler.java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(ServiceException.class)
    public CommonResult<?> handleServiceException(ServiceException ex) {
        log.warn("[业务异常] {}", ex.getMessage());
        return CommonResult.error(ex.getCode(), ex.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public CommonResult<?> handleValidationException(MethodArgumentNotValidException ex) {
        String msg = ex.getBindingResult().getFieldErrors().stream()
            .map(FieldError::getDefaultMessage)
            .collect(Collectors.joining(", "));
        return CommonResult.error(400, msg);
    }

    @ExceptionHandler(Exception.class)
    public CommonResult<?> handleException(Exception ex) {
        log.error("[系统异常]", ex);
        return CommonResult.error(500, "系统繁忙，请稍后重试");
    }
}
```

### 2.2 业务异常类

```java
// 文件：ServiceException.java
public class ServiceException extends RuntimeException {
    private final Integer code;
    public ServiceException(Integer code, String message) {
        super(message);
        this.code = code;
    }
    public Integer getCode() { return code; }
}

// 工具方法
public static ServiceException exception(ErrorCode errorCode) {
    return new ServiceException(errorCode.getCode(), errorCode.getMsg());
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 GlobalExceptionHandler 概览

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 1-67）：

```java
package cn.iocoder.yudao.framework.web.core.handler;

import cn.hutool.core.exceptions.ExceptionUtil;
import cn.iocoder.yudao.framework.common.biz.infra.logger.ApiErrorLogCommonApi;
import cn.iocoder.yudao.framework.common.exception.ServiceException;
import cn.iocoder.yudao.framework.common.exception.util.ServiceExceptionUtil;
import cn.iocoder.yudao.framework.common.pojo.CommonResult;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.NoHandlerFoundException;

import javax.servlet.http.HttpServletRequest;
import javax.validation.ConstraintViolation;
import javax.validation.ConstraintViolationException;
import javax.validation.ValidationException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static cn.iocoder.yudao.framework.common.exception.enums.GlobalErrorCodeConstants.*;

/**
 * 全局异常处理器，将 Exception 翻译成 CommonResult + 对应的异常编号
 *
 * @author 芋道源码
 */
@RestControllerAdvice
@AllArgsConstructor
@Slf4j
public class GlobalExceptionHandler {

    /**
     * 忽略的 ServiceException 错误提示，避免打印过多 logger
     */
    public static final Set<String> IGNORE_ERROR_MESSAGES = SetUtils.asSet("无效的刷新令牌");

    @SuppressWarnings("SpringJavaInjectionPointsAutowiringInspection")
    private final String applicationName;

    private final ApiErrorLogCommonApi apiErrorLogApi;
```

**解读**：
- 第 39 行：`@RestControllerAdvice` 全局异常处理
- 第 40-41 行：`@AllArgsConstructor` 注入 `applicationName` 和 `apiErrorLogApi`
- 第 53 行：`@SuppressWarnings` 抑制 Spring 注入检查告警
- 第 56 行：`applicationName` 用于异常日志记录
- 第 58 行：`ApiErrorLogCommonApi` 是 RPC 接口，异步保存错误日志
- **第 50 行**：常量 `IGNORE_ERROR_MESSAGES` 包含"无效的刷新令牌"等高频但无害的错误，避免日志刷屏

### 3.2 allExceptionHandler 兜底方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 69-130）：

```java
/**
 * 处理所有异常，主要是提供给 Filter 使用（Filter 详见 [19-filter](./19-filter.md)）
 * 因为 Filter 不走 SpringMVC 的流程，但是我们又需要兜底处理异常，所以这里提供一个全量的异常处理过程，保持逻辑统一。
 *
 * @param request 请求
 * @param ex 异常
 * @return 通用返回
 */
public CommonResult<?> allExceptionHandler(HttpServletRequest request, Throwable ex) {
    if (ex instanceof MissingServletRequestParameterException) {
        return missingServletRequestParameterExceptionHandler((MissingServletRequestParameterException) ex);
    }
    if (ex instanceof MethodArgumentTypeMismatchException) {
        return methodArgumentTypeMismatchExceptionHandler((MethodArgumentTypeMismatchException) ex);
    }
    if (ex instanceof MethodArgumentNotValidException) {
        return methodArgumentNotValidExceptionExceptionHandler((MethodArgumentNotValidException) ex);
    }
    if (ex instanceof BindException) {
        return bindExceptionHandler((BindException) ex);
    }
    if (ex instanceof ConstraintViolationException) {
        return constraintViolationExceptionHandler((ConstraintViolationException) ex);
    }
    if (ex instanceof ValidationException) {
        return validationException((ValidationException) ex);
    }
    if (ex instanceof MaxUploadSizeExceededException) {
        return maxUploadSizeExceededExceptionHandler((MaxUploadSizeExceededException) ex);
    }
    if (ex instanceof NoHandlerFoundException) {
        return noHandlerFoundExceptionHandler((NoHandlerFoundException) ex);
    }
```

**解读**：
- 第 5-7 行：方法注释说明这个方法供 Filter 使用（因为 Filter 抛的异常不走 Spring MVC）
- 第 8-30 行：使用 `instanceof` 分发到具体的 `@ExceptionHandler` 方法
- **设计模式**：`if-else` 分发 + 调用专用处理方法 + 统一返回 `CommonResult`
- **覆盖 20+ 异常类型**：参数缺失、类型转换、JSON 解析、文件上传、404 等

### 3.3 业务异常处理

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

/**
 * 处理系统异常
 */
@ExceptionHandler(value = Exception.class)
public CommonResult<?> exceptionHandler(HttpServletRequest request, Throwable ex) {
    log.error("[exceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, WebFrameworkUtils.getLoginUserId());
    // 返回 ERROR CommonResult
    return CommonResult.error(INTERNAL_SERVER_ERROR.getCode(), INTERNAL_SERVER_ERROR.getMsg());
}
```

**解读**：
- 第 5 行：`@ExceptionHandler(value = ServiceException.class)` 拦截业务异常
- 第 7 行：`createExceptionLog(ex, null)` 异步记录异常日志（无登录用户）
- 第 8 行：返回带业务错误码的 `CommonResult`（HTTP 状态码仍是 200）
- 第 15 行：`@ExceptionHandler(value = Exception.class)` 兜底所有系统异常
- 第 17 行：`createExceptionLog(ex, loginUserId)` 记录登录用户（方便排查）
- 第 19 行：返回 500 错误的 `CommonResult`
- **关键设计**：
  - 业务异常 → WARN 级别日志 + 业务错误码
  - 系统异常 → ERROR 级别日志 + 500 错误码
  - 所有异常都异步记录日志（不阻塞响应）

## 4. 关键要点总结

- **`@RestControllerAdvice` = 全局异常处理 + 自动转 JSON**
- **三种处理方式**：`@ExceptionHandler`（方法级）→ `@RestControllerAdvice`（全局）→ `ErrorController`（兜底）
- **ruoyi 异常分类**：
  - 业务异常（ServiceException）→ WARN 日志 + 业务错误码
  - 系统异常（Exception）→ ERROR 日志 + 500 错误码
- **allExceptionHandler**：处理 Filter 抛出的异常（不通过 Spring MVC）
- **createExceptionLog**：异步记录异常日志（通过 RPC + MQ）
- **HTTP 状态码 200**，业务状态码在 `CommonResult.code` 中

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `GlobalExceptionHandler`，处理 `IllegalArgumentException`、`NullPointerException`、`RuntimeException` 三种异常，返回不同的错误码和提示。

### 练习 2：进阶

阅读 `GlobalExceptionHandler` 的 `allExceptionHandler` 方法，列出所有被它处理的异常类型，并说明每种异常对应的 HTTP 状态码。

### 练习 3：挑战（选做）

扩展 `GlobalExceptionHandler`，处理 `MaxUploadSizeExceededException`（文件上传过大）异常，返回友好的错误提示（"文件大小不能超过 10MB"），并附上当前文件大小。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- Spring 异常处理：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html
- 芋道异常处理：https://doc.iocoder.cn/spring-boot-exception-handler/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
