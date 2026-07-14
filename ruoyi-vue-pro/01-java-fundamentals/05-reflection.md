# 1.1.5 反射（Reflection）

> 理解 Java 反射机制，能看懂 Spring、MyBatis、Lombok 等框架如何运行时操作类的字段、方法和构造器。

## 🎯 学习目标

完成本文档后，你将能够：
- 通过 `Class` 对象获取类的字段、方法、构造器
- 用反射动态创建对象、调用方法、读写字段
- 了解反射的性能开销与安全限制
- 理解 ruoyi 中 MapStruct、Lombok 等工具背后的反射原理

## 📚 前置知识

- 面向对象基础（类、对象、构造器）
- 异常体系
- 02-oop.md、04-annotation.md、06-exception.md

## 1. 核心概念

### 1.1 什么是反射？

反射是 Java 在**运行期**动态获取类的信息并操作对象的能力：
- 运行时获取一个类的所有字段、方法、父类、接口
- 运行时创建对象、调用方法、读写字段
- 运行时读取 `@Annotation` 信息

反射的核心是 `java.lang.Class` 类，代表一个类或接口的类型信息。

### 1.2 三种获取 `Class` 对象的方式

```java
// 1. 类名.class（编译期常量，最快）
Class<User> c1 = User.class;

// 2. 对象.getClass()（运行时）
Class<?> c2 = new User().getClass();

// 3. Class.forName("全限定类名")（最灵活）
Class<?> c3 = Class.forName("cn.iocoder.yudao.entity.User");
```

### 1.3 反射 API 主要类

| 类                  | 用途                |
|--------------------|-------------------|
| `Class`            | 类本身的信息（名称、父类、字段） |
| `Field`            | 字段信息              |
| `Method`           | 方法信息              |
| `Constructor`      | 构造器信息             |
| `Modifier`         | 修饰符信息（public 等）  |

### 1.4 反射的优缺点

**优点**：
- 编写通用框架（如 Spring、MyBatis）
- 动态扩展功能、动态代理

**缺点**：
- 性能开销大（比直接调用慢 10-100 倍）
- 破坏封装性（可访问 private 成员）
- 安全限制：模块化（Java 9+）下需要 `setAccessible(true)` 才能访问私有成员

## 2. 代码示例

### 2.1 反射读写字段

```java
// 文件：ReflectionDemo.java
public class ReflectionDemo {

    public static void main(String[] args) throws Exception {
        // 1. 获取 Class 对象
        Class<?> clazz = Class.forName("com.example.User");
        Object user = clazz.getDeclaredConstructor().newInstance();

        // 2. 获取并写入私有字段
        java.lang.reflect.Field nameField = clazz.getDeclaredField("name");
        nameField.setAccessible(true);              // 突破 private 限制
        nameField.set(user, "Tom");

        // 3. 读取私有字段
        System.out.println(nameField.get(user));    // Tom

        // 4. 调用私有方法
        java.lang.reflect.Method greet = clazz.getDeclaredMethod("greet");
        greet.setAccessible(true);
        greet.invoke(user);                         // 调用 greet()
    }
}

class User {
    private String name = "default";
    private void greet() { System.out.println("Hello, I'm " + name); }
}
```

### 2.2 读取方法上的注解

```java
// 文件：ReadAnnotation.java
import java.lang.reflect.Method;

public class ReadAnnotation {
    public static void main(String[] args) throws Exception {
        Method method = AdminService.class.getMethod("save");

        // 获取方法上 @Deprecated 注解
        if (method.isAnnotationPresent(Deprecated.class)) {
            System.out.println("方法已过时: " + method.getName());
        }
    }
}

class AdminService {
    @Deprecated
    public void save() { System.out.println("save"); }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Bean Validation 反射机制

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/validation/InEnumValidator.java`
**核心代码**（典型实现，未直接展示，需参考 Bean Validation）：
- Bean Validation 引擎使用 `Class#getDeclaredFields()` 反射遍历所有字段
- 字段上的 `@NotNull` / `@Pattern` 等约束通过运行时注解读取并逐个校验

**解读**：
- Spring Boot 启动时会注册 `MethodValidationPostProcessor`，对所有 `@Validated` 的 Bean 做 AOP 增强
- 收到请求时，框架通过反射读取方法参数类（如 `AdminUserSaveReqVO`）的所有字段
- 检查每个字段上的约束注解，调用对应的 `Validator#isValid()` 方法
- ruoyi 的 `InEnum`、`Mobile`、`Telephone` 都是自定义约束，配合 `ConstraintValidator` 完成

### 3.2 DO 字段反射映射（MyBatis-Plus 思路）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
**核心代码**（行 33-43）：

```java
@TableId
private Long id;
/**
 * 用户账号
 */
private String username;
/**
 * 加密后的密码
 *
 * 因为目前使用 {@link BCryptPasswordEncoder} 加密器，所以无需自己处理 salt 盐
 */
private String password;
```

**解读**：
- MyBatis-Plus 通过反射读取 `AdminUserDO.class.getDeclaredFields()` 获取所有字段
- 字段上的 `@TableId`、`@TableField(typeHandler = ...)` 在运行时被读取，决定主键策略 / 自定义转换器
- **典型应用场景**：数据库列名是 `username`，Java 字段也是 `username` 时，MP 自动转换为下划线风格 `username`（无需任何映射配置）

## 4. 关键要点总结

- 反射是 Java 在**运行期**操作类信息的能力，核心是 `Class` 对象
- `getDeclaredField()` + `setAccessible(true)` 突破 private 限制
- 反射性能比直接调用慢得多，慎用于性能敏感路径
- Spring、MyBatis、Lombok 等框架的核心都是反射

## 5. 练习题

### 练习 1：基础（必做）

写一个工具方法 `copyFields(Object source, Object target)`：用反射将 `source` 的所有字段值复制到 `target` 同名字段（无需 getter/setter）。

### 练习 2：进阶

阅读 `Bean Validation` 官方文档，模仿实现一个 `InEnum` 注解 + `InEnumValidator`（要求输入是枚举值之一）。

### 练习 3：挑战（选做）

阅读 MyBatis-Plus 的核心类 `TableInfoHelper`，理解它是如何在 `Bean 初始化阶段` 通过反射一次性缓存表结构信息的（这样 SQL 执行阶段就不需要反复反射）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/PageParam.java`
- 《Java 核心技术 卷 I》第 9 章：反射
- Java 反射官方教程：https://docs.oracle.com/javase/tutorial/reflect/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
