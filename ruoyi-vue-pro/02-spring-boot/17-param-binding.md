# 15 参数绑定：@RequestParam / @PathVariable / @RequestBody

> 掌握 Spring MVC 的参数绑定注解，能在 ruoyi-vue-pro 中正确接收各种类型的 HTTP 请求参数。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `@RequestParam`、`@PathVariable`、`@RequestBody` 的使用场景
- 掌握 `@RequestHeader`、`@CookieValue`、`@ModelAttribute` 的用法
- 能在 ruoyi-vue-pro 中读懂 VO（View Object）参数的接收
- 掌握 `@Valid` 参数校验的基本用法（完整校验专题见 [21-validation](./25-validation.md)）

## 📚 前置知识

- [15-controller.md](./15-controller.md)
- [16-request-mapping.md](./16-request-mapping.md)

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

## 3. 关键要点总结

- **`@RequestParam`**：单个 query / form 参数
- **`@PathVariable`**：URL 路径变量（必填）
- **`@RequestBody`**：JSON / XML 请求体（POST/PUT）
- **`@RequestHeader`** / **`@CookieValue`**：请求头 / Cookie
- **ruoyi 风格**：入参用 `*ReqVO`，出参用 `*VO`，结合 `@Valid` 校验
- **参数异常统一处理**：`GlobalExceptionHandler.allExceptionHandler`
- **统一返回**：`CommonResult<T>`（code + msg + data）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
