# 1.1.4 注解（Annotation）原理与自定义

> 掌握 Java 注解的本质、分类与自定义方法，能看懂 ruoyi 中大量使用 `javax.validation.constraints.*` 与 `@TableName` 这类注解。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分内置注解、第三方注解、元注解
- 自定义一个注解（含 `@Retention` 和 `@Target`）
- 用反射机制读取注解信息（反射机制详见 [05-reflection](./05-reflection.md)，此处只当「运行时读元数据」来用）
- 理解 ruoyi 中 MyBatis-Plus、Bean Validation 的注解工作原理

## 📚 前置知识

- 面向对象基础
- 了解什么是接口、反射的概念
- 02-oop.md、[05-reflection.md](./05-reflection.md)（即将阅读）

## 1. 核心概念

### 1.1 注解的本质

注解是 **放在源码上的元数据**，由编译器或运行时框架通过反射读取并执行对应逻辑。本质上，注解是继承自 `java.lang.annotation.Annotation` 的特殊接口。

```java
@Override                // 编译期检查方法重写
@Deprecated              // 标记过期
@SuppressWarnings("all") // 抑制编译器警告
```

### 1.2 元注解

定义注解的注解，控制注解的生命周期和作用目标：

| 元注解         | 作用                                |
|-------------|-----------------------------------|
| `@Retention`| 注解保留范围：`SOURCE` / `CLASS` / `RUNTIME` |
| `@Target`    | 注解允许的位置（方法、字段、类等）               |
| `@Documented`| 是否包含在 Javadoc 中                |
| `@Inherited` | 子类是否能继承父类的注解                  |

### 1.3 注解的保留策略

- `SOURCE`：仅源码存在，编译后丢弃（如 `@Override`）
- `CLASS`：编译进 class 文件，运行时不存在（默认）
- `RUNTIME`：运行时可通过反射读取（如 Spring、MyBatis 大量使用）

### 1.4 注解 vs 注释

- **注释（//, /* */）**：给程序员看的，编译时被丢弃
- **注解（@Xxx）**：给编译器/框架看的，可能在编译期、运行期被读取

## 2. 代码示例

### 2.1 自定义注解

```java
// 文件：PermissionCheck.java
import java.lang.annotation.*;

@Retention(RetentionPolicy.RUNTIME)            // 运行时可通过反射读取
@Target({ElementType.METHOD, ElementType.TYPE}) // 可贴在方法或类上
@Documented
public @interface PermissionCheck {
    // 注解属性：必须在方法签名里以 () 结束
    String[] roles() default "user";
    boolean enabled() default true;
}

// 使用：
@PermissionCheck(roles = {"admin", "manager"})
public void deleteUser(Long id) { ... }
```

### 2.2 用反射读取注解

```java
// 文件：AnnotationReader.java
import java.lang.reflect.Method;

public class AnnotationReader {
    public static void main(String[] args) throws Exception {
        Method method = SampleService.class.getMethod("deleteUser", Long.class);

        if (method.isAnnotationPresent(PermissionCheck.class)) {
            PermissionCheck ann = method.getAnnotation(PermissionCheck.class);
            System.out.println("roles: " + java.util.Arrays.toString(ann.roles()));
            System.out.println("enabled: " + ann.enabled());
        }
    }
}

class SampleService {
    @PermissionCheck(roles = "admin")
    public void deleteUser(Long id) { }
}
```

运行结果：
```
roles: [admin]
enabled: true
```

### 2.3 Bean Validation 注解

ruoyi 中常见的使用方式：

```java
// 文件：UserSaveReqVO.java
import javax.validation.constraints.*;

@Data
public class UserSaveReqVO {
    @NotNull(message = "用户编号不能为空")
    private Long id;

    @Pattern(regexp = "^[A-Za-z0-9]{4,16}$", message = "账号必须是 4-16 位字符")
    private String username;

    @Min(value = 1, message = "年龄最小值为 1")
    @Max(value = 150, message = "年龄最大值为 150")
    private Integer age;
}
```

Spring MVC 接收到请求后，会通过 `RequestMappingHandlerAdapter` 调用校验器自动检查这些注解（参数校验专题见 [21-validation](../02-spring-boot/21-validation.md)）。

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 MyBatis-Plus 表名映射

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
**核心代码**（行 22-23）：

```java
@TableName(value = "system_users", autoResultMap = true) // 由于 SQL Server 的 system_user 是关键字，所以使用 system_users
@KeySequence("system_users_seq") // 用于 Oracle、PostgreSQL、Kingbase、DB2、H2 数据库的主键自增。如果是 MySQL 等数据库，可不写。
@Data
@EqualsAndHashCode(callSuper = true)
```

**解读**：
- 第 1 行：`@TableName` 是 MyBatis-Plus 提供的注解，标记这个实体对应的数据库表
- 第 1 行：`autoResultMap = true` 让 MyBatis 自动映射复杂类型（如 `JSON` 字段）
- 第 2 行：`@KeySequence` 用于非 MySQL 数据库，需要让 MP 知道序列名
- **原理**：MP 在运行期通过反射读取类的注解，生成 SQL 时换成正确的表名/序列名

### 3.2 参数校验注解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/PageParam.java`
**核心代码**（行 25-34）：

```java
@Schema(description = "页码，从 1 开始", requiredMode = Schema.RequiredMode.REQUIRED,example = "1")
@NotNull(message = "页码不能为空")
@Min(value = 1, message = "页码最小值为 1")
private Integer pageNo = PAGE_NO;

@Schema(description = "每页条数，最大值为 200", requiredMode = Schema.RequiredMode.REQUIRED, example = "10")
@NotNull(message = "每页条数不能为空")
@Min(value = 1, message = "每页条数最小值为 1")
@Max(value = 200, message = "每页条数最大值为 200")
private Integer pageSize = PAGE_SIZE;
```

**解读**：
- `@Schema` 是 Swagger/OpenAPI 注解，自动生成 API 文档字段说明
- `@NotNull` / `@Min` / `@Max` 属于 `javax.validation.constraints`（Bean Validation 标准）
- Spring MVC + `MethodValidationPostProcessor` 在 Controller 调用方法时自动执行校验
- 如果 `pageNo = 0`，校验失败时 Spring 会抛 `MethodArgumentNotValidException`，被全局异常处理器捕获（全局异常处理见 [17-exception-handler](../02-spring-boot/17-exception-handler.md)）

## 4. 关键要点总结

- 注解是放在源码上的**元数据**，本质是特殊接口
- 三要素：`@Retention`（保留范围）、`@Target`（作用位置）、`@Documented`（是否生成文档）
- `RUNTIME` 注解能被反射读取，是 Spring/MyBatis 的工作基础
- ruoyi 大量使用 `javax.validation.constraints.*` 做参数校验

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `@Log` 注解，要求只能贴在方法上，保留到运行期，包含 `String value()` 属性。

### 练习 2：进阶

阅读 `AdminUserDO.java`，列出所有注解（包括 MyBatis-Plus 和 Lombok 注解），并说明每个注解的作用。Lombok 见 [14-lombok](./14-lombok.md)。

### 练习 3：挑战（选做）

> 学完 [03-aop](../02-spring-boot/03-aop.md) 与 [05-reflection](./05-reflection.md) 后再做：实现一个简单的"权限校验框架"：自定义 `@RequiresRole("admin")` 注解，用反射在调用方法前检查当前用户角色，模拟 Spring AOP 的拦截功能。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/PageParam.java`
- 《Java 核心技术 卷 II》第 12 章：注解
- 深入理解 Java 注解：https://docs.oracle.com/javase/tutorial/java/annotations/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
