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
- 02-oop.md、04-annotation.md、07-exception.md

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
- 动态扩展功能、动态代理（代理模式详见 [代理](../../_fundamentals/06-design-patterns/08-proxy.md)；Spring AOP 里的 JDK/CGLIB 代理见 [03-aop](../02-spring-boot/03-aop.md)）

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

## 3. 关键要点总结

- 反射是 Java 在**运行期**操作类信息的能力，核心是 `Class` 对象
- `getDeclaredField()` + `setAccessible(true)` 突破 private 限制
- 反射性能比直接调用慢得多，慎用于性能敏感路径
- Spring、MyBatis、Lombok 等框架的核心都是反射（Lombok 编译期注解处理见 [14-lombok](./17-lombok.md)）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
