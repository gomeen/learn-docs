# 21 参数校验：@Valid / @Validated

> 掌握 JSR-303 / Bean Validation 的使用，能在 ruoyi-vue-pro 中正确校验 Controller 入参。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 JSR-303（Bean Validation）规范
- 掌握 `@Valid` 与 `@Validated` 的差异
- 能在 ruoyi-vue-pro 中读懂 `@Valid` + `@RequestBody` 的参数校验
- 掌握常用校验注解：@NotBlank、@NotNull、@Min、@Email 等

## 📚 前置知识

- 15-param-binding.md
- 17-exception-handler.md

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 GlobalExceptionHandler 处理校验异常

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 77-110）：

```java
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
```

**解读**：
- 第 7-9 行：`MethodArgumentNotValidException` 处理 `@RequestBody` + `@Valid` 失败
- 第 10-12 行：`BindException` 处理 `@ModelAttribute` 绑定失败
- 第 13-15 行：`ConstraintViolationException` 处理 `@Validated`（方法级）校验失败
- 第 16-18 行：`ValidationException` 兜底所有校验异常
- **设计模式**：用 `instanceof` 分发到具体处理方法

### 3.2 校验异常处理实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 17-47）：

```java
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.exceptions.ExceptionUtil;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.validation.ObjectError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import javax.validation.ConstraintViolation;
import javax.validation.ConstraintViolationException;
import javax.validation.ValidationException;
import java.util.List;
import java.util.Map;
import java.util.Set;
```

**解读**：
- 第 5 行：`FieldError` 包含校验失败的字段名和错误消息
- 第 10 行：`ConstraintViolation` 包含 JSR-303 校验失败的详细信息
- **设计**：用 Hutool 的 `CollUtil` 工具类简化集合操作
- 这些 import 表明 GlobalExceptionHandler 实现了多个校验异常的处理方法

## 4. 关键要点总结

- **JSR-303 = Bean Validation** = Java 标准的注解式校验
- **`@Valid`（JSR-303）** vs **`@Validated`（Spring）**：后者支持分组校验
- **校验注解**：`@NotBlank`、`@NotNull`、`@Min`、`@Max`、`@Email`、`@Pattern`
- **校验失败抛**：`MethodArgumentNotValidException` / `ConstraintViolationException` / `BindException`
- **ruoyi 中校验失败** → `GlobalExceptionHandler` 统一转换为 `CommonResult` 错误响应
- **ruoyi 中参数校验 = `@Valid` + `@RequestBody`**

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `LoginReqVO`，用 `@NotBlank` 校验用户名和密码，用 `@Email` 校验邮箱，写一个 Controller 方法用 `@Valid @RequestBody` 触发校验。

### 练习 2：进阶

解释 `MethodArgumentNotValidException` 和 `ConstraintViolationException` 的差异。前者什么场景下抛出？后者什么场景下抛出？

### 练习 3：挑战（选做）

实现一个分组校验：`UserReqVO` 的 `id` 字段只在 Update 时校验（`@NotNull(groups = Update.class)`），`username` 在 Create 和 Update 时都校验，并写两个 Controller 方法分别测试。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- Bean Validation 规范：https://beanvalidation.org/
- Spring 校验：https://docs.spring.io/spring-framework/reference/core/validation/beanvalidation.html
- 芋道参数校验：https://doc.iocoder.cn/spring-boot-validation/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
