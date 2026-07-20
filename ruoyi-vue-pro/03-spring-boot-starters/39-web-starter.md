# 6.1 Web 增强：CORS、参数、异常

> 掌握 yudao Web Starter 的各项增强能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao Web Starter 的整体能力
- 掌握统一异常处理、统一响应
- 理解 CORS、加密、API 日志、防 XSS
- 能在 yudao 中使用 Web 增强

## 📚 前置知识

- Spring MVC（详见 [13-controller](../02-spring-boot/15-controller.md)）
- 过滤器 / 拦截器（详见 [18-interceptor](../02-spring-boot/21-interceptor.md) / [19-filter](../02-spring-boot/22-filter.md)）
- HTTP 协议基础

## 1. 核心概念

### 1.1 yudao Web Starter 的能力

| 能力 | 组件 |
|------|------|
| 统一响应 | `CommonResult` + `GlobalResponseHandler`（详见 [16-result-wrapper](../02-spring-boot/18-result-wrapper.md)） |
| 统一异常 | `GlobalExceptionHandler`（详见 [17-exception-handler](../02-spring-boot/20-exception-handler.md)） |
| 统一日志 | `ApiAccessLogFilter` + `ApiErrorLogFilter` |
| 防 XSS | `XssFilter`（详见 [XSS](../../_common/05-web-security/02-xss.md)） |
| 防重复提交 | `RepeatSubmitFilter`（防重放见 [重放攻击](../../_common/05-web-security/07-replay-attack.md)） |
| CORS | `CorsFilter`（详见 [CORS](../../_common/05-web-security/05-cors.md)） |
| API 加密 | `ApiEncryptFilter` + `ApiEncryptProperties`（加密见 [对称加密](../../_common/06-encryption/01-symmetric.md)） |
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

## 3. 关键要点总结

- **yudao Web Starter** 提供 10+ 个 Web 增强能力
- **统一响应 `CommonResult<T>`** + **统一异常 `GlobalExceptionHandler`**
- **API 日志** 自动记录所有请求
- **XSS 过滤** 通过 HttpServletRequestWrapper 实现
- **API 加密**支持 AES + RSA 混合

---

**文档版本**：v1.0
**最后更新**：2026-07-13
