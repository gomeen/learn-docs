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
- Bean Validation（详见 [Validation](../02-spring-boot/21-validation.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 SaveReqVO 模板

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/vo/saveReqVO.vm`
**核心代码**（行 30-90，简化）：

```velocity
@Schema(description = "${sceneEnum.name} - ${table.classComment}创建/修改 Request VO")
@Data
public class ${sceneEnum.prefixClass}${table.className}SaveReqVO {

#foreach($column in $columns)
#if ($column.createOperation || $column.updateOperation)
    @Schema(description = "$column.columnComment", example = "$column.example")
## 根据 nullable 决定是否加 @NotNull
#if(!$column.nullable)
#if($column.javaType == "String")
    @NotBlank(message = "$column.columnComment不能为空")
#else
    @NotNull(message = "$column.columnComment不能为空")
#end
#end
## String 字段根据长度自动加 @Size
#if($column.javaType == "String" && $column.columnSize > 0)
    @Size(max = $column.columnSize, message = "$column.columnComment长度不能超过 $column.columnSize")
#end
    private $column.javaType $column.javaField;

#end
#end
}
```

**解读**：
- 模板中 `#if(!$column.nullable)` 控制是否加 `@NotNull` / `@NotBlank`
- 区分 `String` 与其他类型：`String` 用 `@NotBlank`（更严格）
- 字符串长度从 `$column.columnSize` 读取（数据库 `VARCHAR(N)` 的 N）
- `$column.createOperation || $column.updateOperation` 决定字段是否出现

### 3.2 字段大小在元数据中的位置

**位置**：`CodegenColumnDO` 没有显式 `columnSize` 字段！实际上取自 `TableField` 反射：

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/convert/codegen/CodegenConvert.java`
**核心代码**（简化）：

```java
// CodegenConvert 将 MyBatis-Plus 的 TableField 转为 CodegenColumnDO
@Mapping(target = "columnSize", source = "length")
@Mapping(target = "columnComment", source = "comment")
@Mapping(target = "javaType", source = "propertyType")
// ...
CodegenColumnDO convert(TableField field);
```

**解读**：
- `columnSize` 来自数据库 `VARCHAR(N)` 的 N
- 通过 MapStruct 的 `@Mapping` 注解自动映射

### 3.3 自定义校验规则位置

如果想加新的规则（如 `@Pattern` 邮箱校验），有两种方案：

**方案 1：扩展 `CodegenColumnDO` 加 `pattern` 字段**（推荐用于通用规则）

**方案 2：直接改 `saveReqVO.vm`**（用于 ruoyi 项目内硬编码）

```velocity
## 邮箱字段自动加 @Email
#if($column.javaField == "email")
    @Email(message = "邮箱格式不正确")
#end
## 手机号自动加正则
#if($column.javaField == "phone" || $column.javaField == "mobile")
    @Pattern(regexp = "^1[3-9]\d{9}$", message = "手机号格式不正确")
#end
```

## 4. 关键要点总结

- 校验注解由 Velocity 模板根据字段元数据**自动生成**
- 三大规则：
  - `nullable=false` + `String` → `@NotBlank`
  - `nullable=false` + 其他 → `@NotNull`
  - `String` + `columnSize>0` → `@Size(max=N)`
- 模板中通过 `$column.javaField == "email"` 这样的硬编码处理特殊字段
- ruoyi 自己的生成器没有"正则配置"字段，需要扩展 `CodegenColumnDO`

## 5. 练习题

### 练习 1：基础（必做）

对以下字段，写出模板会生成的注解（`name VARCHAR(50) NOT NULL` / `age INT NULL` / `email VARCHAR(100) NULL`）。

### 练习 2：进阶

修改 `saveReqVO.vm`，让 `email` 字段自动加 `@Email` 校验。写出修改后的 `#if` 块。

### 练习 3：挑战（选做）

设计一个完整的"自定义校验"功能：在 `CodegenColumnDO` 加 `pattern` 字段，在前端编辑页可配置正则，然后修改 `saveReqVO.vm` 使用它。列出所有需要修改的文件。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/vo/saveReqVO.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/convert/codegen/CodegenConvert.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenColumnDO.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
