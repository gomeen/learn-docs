# 17 全局异常处理：@ControllerAdvice

> 掌握 `@RestControllerAdvice` + `@ExceptionHandler` 的全局异常处理，能在 ruoyi-vue-pro 中统一处理各种异常。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@RestControllerAdvice` 与 `@ControllerAdvice` 的差异
- 掌握 `@ExceptionHandler` 的使用，捕获 Controller 抛出的异常
- 能在 ruoyi-vue-pro 中读懂 `GlobalExceptionHandler` 的设计
- 理解业务异常（ServiceException）与系统异常的处理策略

## 📚 前置知识

- 18-result-wrapper.md

## 1. 核心概念

### 1.1 `@RestControllerAdvice` 是什么？

是 `@ControllerAdvice` + `@ResponseBody` 的组合，用于：
- 全局处理 Controller 抛出的异常
- 把异常转换为统一的 `CommonResult` 返回（`CommonResult` 详见 [16-result-wrapper](./18-result-wrapper.md)；Java 异常体系见 [06-exception](../01-java-fundamentals/07-exception.md)）

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

## 3. 关键要点总结

- **`@RestControllerAdvice` = 全局异常处理 + 自动转 JSON**
- **三种处理方式**：`@ExceptionHandler`（方法级）→ `@RestControllerAdvice`（全局）→ `ErrorController`（兜底）
- **ruoyi 异常分类**：
  - 业务异常（ServiceException）→ WARN 日志 + 业务错误码
  - 系统异常（Exception）→ ERROR 日志 + 500 错误码
- **allExceptionHandler**：处理 Filter 抛出的异常（不通过 Spring MVC）
- **createExceptionLog**：异步记录异常日志（通过 RPC + MQ）
- **HTTP 状态码 200**，业务状态码在 `CommonResult.code` 中

---

**文档版本**：v1.0
**最后更新**：2026-07-13
