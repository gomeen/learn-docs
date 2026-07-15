# 15 参数绑定：@RequestParam / @PathVariable / @RequestBody

> 掌握 Spring MVC 的参数绑定注解，能在 ruoyi-vue-pro 中正确接收各种类型的 HTTP 请求参数。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `@RequestParam`、`@PathVariable`、`@RequestBody` 的使用场景
- 掌握 `@RequestHeader`、`@CookieValue`、`@ModelAttribute` 的用法
- 能在 ruoyi-vue-pro 中读懂 VO（View Object）参数的接收
- 掌握 `@Valid` 参数校验的基本用法（完整校验专题见 [21-validation](./21-validation.md)）

## 📚 前置知识

- [13-controller.md](./13-controller.md)
- [14-request-mapping.md](./14-request-mapping.md)

## 1. 核心概念

### 1.1 五大参数绑定注解

| 注解 | 来源 | 用途 | 例子 |
|------|------|------|------|
| `@RequestParam` | Query / Form | 单个参数 | `?id=1&name=foo` |
| `@PathVariable` | URL 路径 | 路径变量 | `/user/{id}` |
| `@RequestBody` | 请求体 | JSON / XML | `{"id": 1, "name": "foo"}` |
| `@RequestHeader` | 请求头 | 自定义头 | `X-Token: xxx` |
| `@CookieValue` | Cookie | Cookie 值 | `JSESSIONID=xxx` |
| `@ModelAttribute` | Query / Form | 表单对象 | 注册表单 |

### 1.2 ruoyi 的 VO 模式

```java
// Request VO（入参）
public class UserCreateReqVO {
    @NotBlank(message = "用户名不能为空")
    private String username;
    @Email(message = "邮箱格式错误")
    private String email;
    @Min(value = 0, message = "年龄必须大于等于 0")
    private Integer age;
}

// Controller
@PostMapping("/create")
public CommonResult<Long> create(@Valid @RequestBody UserCreateReqVO req) {
    return CommonResult.success(userService.createUser(req));
}
```

- **VO（View Object）**：Controller 与前端交互的数据模型
- **`@Valid`** 触发 JSR-303 校验
- **统一返回**：`CommonResult<Long>`

## 2. 代码示例

### 2.1 @RequestParam

```java
// 单个参数
@GetMapping("/get")
public CommonResult<UserVO> get(@RequestParam("id") Long id) { ... }

// 可选参数
@GetMapping("/search")
public CommonResult<List<UserVO>> search(
    @RequestParam(required = false) String name,
    @RequestParam(defaultValue = "1") Integer page) { ... }
```

### 2.2 @PathVariable

```java
@GetMapping("/user/{id}")
public CommonResult<UserVO> get(@PathVariable Long id) { ... }

@GetMapping("/user/{userId}/order/{orderId}")
public CommonResult<OrderVO> get(
    @PathVariable Long userId,
    @PathVariable Long orderId) { ... }
```

### 2.3 @RequestBody

```java
@PostMapping("/create")
public CommonResult<Long> create(@RequestBody UserCreateReqVO req) { ... }

// 多个 body（不常见，Spring 6.1+ 支持）
@PostMapping("/batch")
public CommonResult<Boolean> batch(
    @RequestBody List<UserCreateReqVO> reqs) { ... }
```

### 2.4 @RequestHeader / @CookieValue

```java
@GetMapping("/profile")
public CommonResult<UserVO> profile(
    @RequestHeader("Authorization") String token,
    @CookieValue("JSESSIONID") String sessionId) { ... }
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 DefaultController.test 多种参数接收

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
**核心代码**（行 99-112）：

```java
/**
 * 测试接口：打印 query、header、body
 */
@RequestMapping(value = { "/test" })
@PermitAll
public CommonResult<Boolean> test(HttpServletRequest request) {
    // 打印查询参数
    log.info("Query: {}", ServletUtils.getParamMap(request));
    // 打印请求头
    log.info("Header: {}", ServletUtils.getHeaderMap(request));
    // 打印请求体
    log.info("Body: {}", ServletUtils.getBody(request));
    return CommonResult.success(true);
}
```

**解读**：
- 第 7 行：通过 `HttpServletRequest` 接收整个请求（不显式绑定某个参数）
- 第 9 行：`ServletUtils.getParamMap(request)` 提取所有 query 参数（`?id=1&name=foo`）
- 第 11 行：`ServletUtils.getHeaderMap(request)` 提取所有请求头
- 第 13 行：`ServletUtils.getBody(request)` 提取请求体（需要 `CacheRequestBodyFilter` 支持）
- **设计意图**：调试用接口，演示如何读取各类参数

### 3.2 GlobalExceptionHandler 处理参数异常

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 130-160）：

```java
/**
 * 处理所有异常，主要是提供给 Filter 使用
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
```

**解读**：
- 第 12 行：`MissingServletRequestParameterException` 处理 `@RequestParam` 缺失
- 第 15 行：`MethodArgumentTypeMismatchException` 处理类型转换失败（如 `id=abc`）
- 第 18 行：`MethodArgumentNotValidException` 处理 `@RequestBody` + `@Valid` 校验失败
- 第 21 行：`BindException` 处理 `@ModelAttribute` 绑定失败
- 第 24 行：`ConstraintViolationException` 处理 `@Validated` 校验失败
- **设计意图**：把 Spring MVC 的各种参数异常统一转换为 `CommonResult` 返回

### 3.3 错误码常量

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 47）：

```java
import static cn.iocoder.yudao.framework.common.exception.enums.GlobalErrorCodeConstants.*;
```

**解读**：
- `GlobalErrorCodeConstants` 定义全局错误码（如 `BAD_REQUEST`、`MISSING_REQUEST_PARAM`）
- 在 `allExceptionHandler` 中用 `BAD_REQUEST` 等错误码返回给前端
- **ruoyi 统一错误码**：所有 Controller 参数错误最终都返回相同格式的 `CommonResult`

## 4. 关键要点总结

- **`@RequestParam`**：单个 query / form 参数
- **`@PathVariable`**：URL 路径变量（必填）
- **`@RequestBody`**：JSON / XML 请求体（POST/PUT）
- **`@RequestHeader`** / **`@CookieValue`**：请求头 / Cookie
- **ruoyi 风格**：入参用 `*ReqVO`，出参用 `*VO`，结合 `@Valid` 校验
- **参数异常统一处理**：`GlobalExceptionHandler.allExceptionHandler`
- **统一返回**：`CommonResult<T>`（code + msg + data）

## 5. 练习题

### 练习 1：基础（必做）

编写一个 `UserQueryController`，提供：
- `GET /admin-api/user/{id}` 返回用户详情（`@PathVariable`）
- `GET /admin-api/user?name=foo&page=1` 返回用户列表（`@RequestParam`）
- `POST /admin-api/user` 接收 JSON 创建用户（`@RequestBody` + `@Valid`）

### 练习 2：进阶

阅读 `GlobalExceptionHandler.allExceptionHandler`，列出所有它能处理的异常类型，并说明每种异常的触发场景。

### 练习 3：挑战（选做）

实现一个 `BatchCreateController`，接收 `Content-Type: application/json` 数组，校验后批量创建。要求：参数缺失、类型错误、JSON 解析失败都返回统一的 `CommonResult` 错误格式。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- Spring MVC 参数绑定：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-methods.html
- 芋道 Spring MVC：https://doc.iocoder.cn/spring-boot-springmvc/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
