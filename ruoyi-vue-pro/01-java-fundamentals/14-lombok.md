# 1.2.4 Lombok 原理与常用注解

> 掌握 Lombok 的核心注解，理解它如何通过字节码生成消除模板代码；看懂 ruoyi 全仓库近乎疯狂的 `@Data` 使用。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Lombok 通过**编译期注解处理器**生成字节码的原理
- 熟练使用 `@Data` / `@Builder` / `@Slf4j` 等常用注解
- 在 IDE（IntelliJ IDEA）正确配置 Lombok 插件
- 理解 `lombok.config` 文件的作用（如 ruoyi 的 `lombok.tostring.callsuper`）

## 📚 前置知识

- 面向对象基础
- Java 编译基础（javac）
- 02-oop.md

## 1. 核心概念

### 1.1 Lombok 是什么？

Lombok 是**编译期的代码生成器**，通过 JSR-269（Pluggable Annotation Processing API）在 `javac` 编译源码时，根据注解自动生成 `getter/setter/equals/hashCode/toString/构造器` 等模板方法。

```java
// 加 @Data 之前
public class User {
    private Long id;
    private String name;
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    // ... 50 行模板代码
}

// 加 @Data 之后
@Data
public class User {
    private Long id;
    private String name;
}
```

### 1.2 常用注解清单

| 注解                  | 作用                              |
|---------------------|---------------------------------|
| `@Data`             | 自动生成 getter/setter/equals/hashCode/toString |
| `@Getter / @Setter` | 只生成 getter / setter             |
| `@ToString`         | 生成 toString                     |
| `@EqualsAndHashCode`| 生成 equals / hashCode             |
| `@NoArgsConstructor` | 无参构造                          |
| `@AllArgsConstructor`| 全参构造                          |
| `@Builder`          | 建造者模式（详见 [建造者](../../_fundamentals/06-design-patterns/04-builder.md)） |
| `@Slf4j`            | 自动注入 `log` 静态字段（日志框架见 [17-logging](./17-logging.md)） |
| `@RequiredArgsConstructor` | 生成 final 字段的构造器          |

### 1.3 lombok.config

Lombok 支持项目级配置文件，影响所有类：

```properties
# lombok.config
config.stopBubbling = true          # 配置文件不会被子目录继承
lombok.tostring.callsuper = CALL    # toString 调用父类
lombok.equalsandhashcode.callsuper = CALL
lombok.accessors.chain = true       # 生成链式 setter
```

### 1.4 工作原理

```
源代码 (@Data User)
    ↓  javac
注解处理器 (lombok.jar) 看到 @Data
    ↓
生成 getter/setter/equals/hashCode/toString
    ↓
.java 字节码
```

**关键**：Lombok 不修改 .java 源文件，而是在编译期直接修改抽象语法树（AST），生成等价的字节码。所以 IDE 看 .java 源码是"干净的"，但编译产物里已经有完整方法。

## 2. 代码示例

### 2.1 必装依赖与使用

```xml
<!-- 文件：pom.xml -->
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <version>1.18.42</version>
    <scope>provided</scope>     <!-- 编译时使用 -->
</dependency>
```

```java
// 文件：User.java
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {
    private Long id;
    private String name;
    private Integer age;
}
```

```java
// 文件：UserUsage.java
import lombok.extern.slf4j.Slf4j;

@Slf4j                           // 自动注入 log 静态字段
public class UserUsage {
    public static void main(String[] args) {
        // @Builder 提供的建造者模式
        User u = User.builder()
            .id(1L)
            .name("Tom")
            .age(25)
            .build();

        // @Data 提供的 getter/setter
        log.info("name={}", u.getName());

        // @Data 提供的 toString
        log.info("user={}", u);

        // @Data 提供的 equals
        System.out.println(u.equals(User.builder().id(1L).name("Tom").age(25).build()));
    }
}
```

### 2.2 常见错误：父子类继承时 `@Data` 行为

```java
// 文件：Hierarchy.java
import lombok.Data;

class Parent {
    private String parentField;
}

@Data
class Child extends Parent {
    private String childField;
}
// ❌ Child.equals(Child) 只比较 childField，不比较 parentField
```

```java
// ✅ 正确：callSuper=true 才会比较父类字段
@Data
@EqualsAndHashCode(callSuper = true)
class Child extends Parent {
    private String childField;
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 全仓库的 lombok.config

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/lombok.config`
**核心代码**（行 1-4）：

```properties
config.stopBubbling = true
lombok.tostring.callsuper=CALL
lombok.equalsandhashcode.callsuper=CALL
lombok.accessors.chain=true
```

**解读**：
- 第 1 行：`stopBubbling=true` 让配置文件不往下传播到子目录
- 第 2-3 行：统一让 toString/equals/hashCode 调用父类方法（与 `AdminUserDO` 的 `@EqualsAndHashCode(callSuper = true)` 行为一致）
- 第 4 行：生成的 setter 返回 `this` 而不是 `void`，形成"链式调用"（如 `user.setId(1L).setName("Tom")`）

### 3.2 DO 类中的 Lombok 综合使用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
**核心代码**（行 22-28）：

```java
@TableName(value = "system_users", autoResultMap = true) // 由于 SQL Server 的 system_user 是关键字，所以使用 system_users
@KeySequence("system_users_seq") // 用于 Oracle、PostgreSQL、Kingbase、DB2、H2 数据库的主键自增。如果是 MySQL 等数据库，可不写。
@Data
@EqualsAndHashCode(callSuper = true)
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminUserDO extends TenantBaseDO {
```

**解读**：
- 第 4 行：`@Data` 一行代码生成 5 类模板方法，约 100 行模板代码减少
- 第 5 行：`callSuper = true` 让 equals/hashCode 把父类（`TenantBaseDO`）的字段也算上，避免父类字段不参与相等判断的 bug
- 第 6 行：`@Builder` 让创建对象更可读：
  ```java
  AdminUserDO u = AdminUserDO.builder().id(1L).username("admin").build();
  ```
- 第 7-8 行：分别生成无参构造（MyBatis 反序列化用）和全参构造
- 整个 ruoyi 仓库**几乎所有 DO / VO / DTO 都用这一套组合**

## 4. 关键要点总结

- Lombok 通过编译期注解处理器生成字节码，运行时无副作用
- `@Data` = `@Getter` + `@Setter` + `@ToString` + `@EqualsAndHashCode` + `@RequiredArgsConstructor`
- `@Builder` 让对象构造链式可读
- ruoyi 用 `lombok.config` 全局配置 `callSuper=true` 和 `chain=true`

## 5. 练习题

### 练习 1：基础（必做）

手写一个 `UserDTO`，用 `@Data` + `@Builder` 注解，编写一段代码验证 getter/setter/equals/toString/builder 都可用。

### 练习 2：进阶

阅读 `AdminUserDO`，分析它"应该"被 Lombok 编译后生成的方法列表（不需要看字节码，列出方法签名即可）。

### 练习 3：挑战（选做）

模仿 ruoyi 的 `lombok.config`，在你的项目根目录创建该文件并验证：在父类有字段时，`@Data` 的子类 equals 是否会比较父类字段。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/lombok.config`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
- Lombok 官方文档：https://projectlombok.org/features/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
