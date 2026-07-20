# 1.1.2 面向对象：类、继承、接口、抽象类

> 掌握 Java 面向对象四大特性：封装、继承、多态、抽象；看懂 ruoyi 的分层架构（DO/VO/DTO/Service）。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分类、抽象类、接口的使用场景
- 理解封装、继承、多态三大特性
- 掌握 `final`、`static` 关键字在 ruoyi 工具类中的用法
- 能看懂 ruoyi 的 `DO`（数据库对象）、`VO`（视图对象）等命名约定

## 📚 前置知识

- Java 基础语法（变量、类型、流程）
- 01-java-syntax.md

## 1. 核心概念

### 1.1 类与对象（封装）

类是对象的模板，对象是类的实例。**封装**就是把数据（字段）和行为（方法）打包到类内部，对外隐藏实现细节。

```java
public class User {
    private Long id;
    private String name;

    public Long getId() { return id; }
    public void setName(String name) { this.name = name; }
}
```

### 1.2 继承（extends）

子类继承父类，复用父类的字段和方法，并且可以扩展自己的行为：

```java
public class AdminUser extends User {
    private String role;
}
```

Java 是**单继承**，但可以通过接口实现多继承的效果（接口多实现）。

### 1.3 多态

父类引用指向子类对象，方法调用在运行时才确定具体实现：

```java
Animal a = new Dog();   // 向上转型
a.cry();                // 调用的是 Dog 重写的方法（动态分派）
```

多态的三个前提：有继承、有方法重写、父类引用指向子类对象。

### 1.4 抽象类 vs 接口

| 特性      | 抽象类（abstract class）      | 接口（interface）              |
|---------|---------------------------|---------------------------|
| 关键字      | `abstract class`          | `interface`               |
| 方法实现    | 可以有具体方法（Java 8+）         | 默认 `default` 方法         |
| 字段       | 可以有普通字段                  | 只能是 `public static final` |
| 单继承     | 一个类只能继承一个抽象类            | 一个类可以实现多个接口             |
| 关系       | "is-a"，强调本质              | "can-do"，强调能力            |

**选用规则**：
- 想表达"父子关系"用抽象类
- 想表达"具备某种能力"用接口

### 1.5 关键修饰符

- `final`：修饰类（不可继承）、方法（不可重写）、变量（不可变）
- `static`：修饰成员属于类，不属于对象；可通过 `类名.成员` 直接访问
- `abstract`：抽象类不能实例化，抽象方法只能由子类实现

## 2. 代码示例

### 2.1 抽象类 + 模板方法模式

> 📌 **Sighting**：完整「模板方法」模式（钩子、与策略模式对比）见 [模板方法](../../_fundamentals/06-design-patterns/14-template-method.md)。此处只把它当作「父类定流程、子类填步骤」的用法。

```java
// 文件：AbstractPayService.java
public abstract class AbstractPayService {
    // 模板方法：定义固定流程，子类实现具体步骤
    public final void pay(Long orderId) {
        validate(orderId);     // 校验
        doPay(orderId);        // 支付（抽象方法，由子类实现）
        notify(orderId);       // 通知
    }

    protected abstract void doPay(Long orderId);   // 子类必须实现

    protected void validate(Long orderId) { /* 默认校验 */ }
    protected void notify(Long orderId) { /* 默认通知 */ }
}

public class AlipayService extends AbstractPayService {
    @Override
    protected void doPay(Long orderId) {
        System.out.println("支付宝支付: " + orderId);
    }
}
```

### 2.2 接口多实现

```java
// 文件：Swimable.java / Flyable.java
public interface Swimable { void swim(); }
public interface Flyable  { void fly(); }

// 类可以实现多个接口
public class Duck implements Swimable, Flyable {
    @Override public void swim() { System.out.println("鸭子游泳"); }
    @Override public void fly()  { System.out.println("鸭子飞行"); }
}
```

### 2.3 `final` 与 `static`（工具类写法）

```java
// 文件：StringUtils.java
public final class StringUtils {           // final：禁止继承
    public static final String EMPTY = ""; // static final：常量

    private StringUtils() {}               // 私有构造器：禁止实例化

    public static boolean isEmpty(String s) {
        return s == null || s.isEmpty();
    }
}
// 调用：StringUtils.isEmpty("abc")
```

## 3. 关键要点总结

- Java 是纯面向对象：除 8 种基本类型外一切皆对象
- `abstract class` 用于"is-a"关系，`interface` 用于"can-do"关系
- 多态三要素：继承、重写、父类引用指向子类对象
- ruoyi 大量使用 Lombok 注解（`@Data` / `@Builder` / `@EqualsAndHashCode`）减少模板代码

---

**文档版本**：v1.0
**最后更新**：2026-07-13
