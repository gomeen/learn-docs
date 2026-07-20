# 21 参数校验：@Valid / @Validated

> 掌握 JSR-303 / Bean Validation 的使用，能在 ruoyi-vue-pro 中正确校验 Controller 入参。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 JSR-303（Bean Validation）规范
- 掌握 `@Valid` 与 `@Validated` 的差异
- 能在 ruoyi-vue-pro 中读懂 `@Valid` + `@RequestBody` 的参数校验
- 掌握常用校验注解：@NotBlank、@NotNull、@Min、@Email 等

## 📚 前置知识

- [17-param-binding.md](./17-param-binding.md)
- [20-exception-handler.md](./20-exception-handler.md)（校验失败异常由此捕获）

## 1. 核心概念

### 1.1 JSR-303 / Bean Validation

Java 标准的**对象校验**规范（基于注解），Spring Boot 通过 `spring-boot-starter-validation` 自动集成。

### 1.2 `@Valid` vs `@Validated`

| 特性 | `@Valid` | `@Validated` |
|------|---------|-------------|
| 来源 | JSR-303（Java 标准） | Spring |
| 位置 | 方法参数、字段 | 类、方法参数 |
| 分组校验 | ❌ | ✅（`@Validated({Group.class})`） |
| 嵌套校验 | ✅（配合 `@Valid`） | ✅ |

### 1.3 常用校验注解

| 注解 | 校验内容 | 适用类型 |
|------|---------|---------|
| `@NotNull` | 不为 null | 任何类型 |
| `@NotEmpty` | 不为 null 且长度 > 0 | String、Collection、Map、数组 |
| `@NotBlank` | 不为 null 且至少一个非空白字符 | String |
| `@Min(value)` | 大于等于 value | 数字 |
| `@Max(value)` | 小于等于 value | 数字 |
| `@Size(min, max)` | 长度在 [min, max] | String、Collection |
| `@Email` | 邮箱格式 | String |
| `@Pattern(regexp)` | 匹配正则 | String |
| `@Past` / `@Future` | 过去 / 未来 | Date |
| `@DecimalMin` / `@DecimalMax` | 数值范围 | BigDecimal |

## 2. 代码示例

### 2.1 基础校验

```java
// 文件：UserCreateReqVO.java
@Data
public class UserCreateReqVO {

    @NotBlank(message = "用户名不能为空")
    @Length(min = 3, max = 20, message = "用户名长度 3-20")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Length(min = 6, message = "密码至少 6 位")
    private String password;

    @Email(message = "邮箱格式错误")
    private String email;

    @NotNull(message = "年龄不能为空")
    @Min(value = 0, message = "年龄必须 >= 0")
    @Max(value = 150, message = "年龄必须 <= 150")
    private Integer age;
}

// Controller
@PostMapping("/create")
public CommonResult<Long> create(@Valid @RequestBody UserCreateReqVO req) {
    return CommonResult.success(userService.createUser(req));
}
```

### 2.2 嵌套校验

```java
public class OrderCreateReqVO {
    @NotNull
    @Valid  // 触发嵌套校验
    private UserVO user;

    @NotEmpty
    @Valid
    private List<OrderItemVO> items;
}
```

### 2.3 分组校验

```java
public class UserReqVO {
    @NotNull(groups = Update.class)  // 只在更新时校验
    private Long id;

    @NotBlank(groups = {Create.class, Update.class})  // 创建和更新都校验
    private String username;

    public interface Create {}
    public interface Update {}
}

// Controller
@PostMapping("/create")
public CommonResult<Long> create(@Validated(UserReqVO.Create.class) @RequestBody UserReqVO req) { ... }

@PutMapping("/update")
public CommonResult<Boolean> update(@Validated(UserReqVO.Update.class) @RequestBody UserReqVO req) { ... }
```

## 3. 关键要点总结

- **JSR-303 = Bean Validation** = Java 标准的注解式校验
- **`@Valid`（JSR-303）** vs **`@Validated`（Spring）**：后者支持分组校验
- **校验注解**：`@NotBlank`、`@NotNull`、`@Min`、`@Max`、`@Email`、`@Pattern`
- **校验失败抛**：`MethodArgumentNotValidException` / `ConstraintViolationException` / `BindException`
- **ruoyi 中校验失败** → `GlobalExceptionHandler` 统一转换为 `CommonResult` 错误响应
- **ruoyi 中参数校验 = `@Valid` + `@RequestBody`**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
