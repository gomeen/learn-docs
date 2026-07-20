# 2.4 校验规则配置

> 学习 ruoyi 代码生成器如何根据 Java 字段类型自动添加参数校验注解。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出常见 JavaBean Validation 注解
- 解释字段类型与校验注解的对应关系
- 阅读生成的 `SaveReqVO` 看到完整的校验链
- 自定义一个新的校验规则

## 📚 前置知识

- 总览 / 类型映射（详见 [总览](./01-overview.md)、[类型映射](./04-type-mapping.md)）
- Bean Validation（详见 [Validation](../02-spring-boot/25-validation.md)）

## 1. 核心概念

### 1.1 常见校验注解

| 注解 | 用途 | 示例 |
|------|------|------|
| `@NotNull` | 不能为 null | `Long id` |
| `@NotEmpty` | 不能为空（字符串/集合） | `String name` |
| `@NotBlank` | 不能为空白 | `String username` |
| `@Size(min, max)` | 长度范围 | `@Size(max = 50)` |
| `@Pattern(regexp)` | 正则 | 手机号、邮箱 |
| `@Min(value)` | 最小值 | `@Min(0)` |
| `@Max(value)` | 最大值 | `@Max(100)` |
| `@Email` | 邮箱 | `@Email` |
| `@URL` | URL | 头像 |

### 1.2 字段类型 vs 校验

| Java 类型 | 必加校验 | 理由 |
|----------|---------|------|
| `String` 必填 | `@NotBlank` | 排除空白字符 |
| `Long/Integer` 必填 | `@NotNull` | 数字类型没有"空"概念 |
| `List<T>` 必填 | `@NotEmpty` | 集合不能为空 |
| `BigDecimal` | `@Digits` | 限制小数位 |
| `LocalDateTime` | 自定义 | 框架暂无默认 |

## 2. 代码示例

### 2.1 一个典型的 SaveReqVO 片段

```java
@Schema(description = "管理后台 - 用户创建/修改 Request VO")
public class UserSaveReqVO {

    @Schema(description = "用户账号", requiredMode = RequiredMode.REQUIRED)
    @NotBlank(message = "用户账号不能为空")
    @Size(max = 30, message = "用户账号长度不能超过 30 个字符")
    private String username;

    @Schema(description = "用户昵称", requiredMode = RequiredMode.REQUIRED)
    @NotBlank(message = "用户昵称不能为空")
    @Size(max = 30, message = "用户昵称长度不能超过 30 个字符")
    private String nickname;

    @Schema(description = "用户邮箱")
    @Email(message = "邮箱格式不正确")
    @Size(max = 50, message = "邮箱长度不能超过 50 个字符")
    private String email;

    @Schema(description = "手机号码")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;
}
```

## 3. 关键要点总结

- 校验注解由 Velocity 模板根据字段元数据**自动生成**
- 三大规则：
  - `nullable=false` + `String` → `@NotBlank`
  - `nullable=false` + 其他 → `@NotNull`
  - `String` + `columnSize>0` → `@Size(max=N)`
- 模板中通过 `$column.javaField == "email"` 这样的硬编码处理特殊字段
- ruoyi 自己的生成器没有"正则配置"字段，需要扩展 `CodegenColumnDO`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
