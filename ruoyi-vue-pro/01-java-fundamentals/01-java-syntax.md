# 1.1.1 Java 语法基础：变量、类型、控制流

> 掌握 Java 基础语法：八大基本类型、引用类型、分支与循环结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Java 的基本类型与引用类型
- 正确声明变量并理解自动拆装箱机制
- 使用 `if/else`、`switch`、循环语句编写控制流
- 能看懂 ruoyi-vue-pro 业务代码中的简单条件判断和方法调用

## 📚 前置知识

- 无（Java 入门第一课）

## 1. 核心概念

### 1.1 基本类型（Primitive Types）

Java 有 **8 种基本类型**，它们是语言内置的、不是对象，存放在栈上，访问速度极快。

| 类型    | 字节数 | 默认值  | 范围（以 int 为例）       |
|-------|-----|------|---------------------|
| byte  | 1   | 0    | -128 ~ 127          |
| short | 2   | 0    | -32768 ~ 32767      |
| int   | 4   | 0    | -2³¹ ~ 2³¹-1        |
| long  | 8   | 0L   | -2⁶³ ~ 2⁶³-1        |
| float | 4   | 0.0f | 约 7 位精度            |
| double| 8   | 0.0d | 约 15 位精度           |
| char  | 2   | '' | 单个字符（含 Unicode） |
| boolean | - | false | true / false      |

### 1.2 引用类型（Reference Types）

除了 8 种基本类型，其他都是引用类型，例如 `String`、数组、对象。它们存放在堆上，变量持有的是"地址"。

```java
// String 是引用类型，赋值的是引用（地址）
String a = "hello";
String b = a;          // b 和 a 指向同一个对象
b = b.toUpperCase();   // b 指向新对象，a 不受影响
```

### 1.3 自动拆装箱

基本类型与对应的包装类（`Integer`、`Long` 等）可以自动转换：

```java
Integer i = 100;   // 自动装箱：int -> Integer
int n = i;         // 自动拆箱：Integer -> int
```

注意：自动装箱有性能开销，并且容易出现 `NullPointerException`（拆箱 null 包装类）。

### 1.4 控制流

```java
// 分支
if (score >= 60) { ... } else { ... }

// 多分支
switch (day) {
    case MONDAY -> System.out.println("周一");
    default -> System.out.println("其他");
}

// 循环
for (int i = 0; i < 10; i++) { ... }
for (String s : list) { ... }   // for-each 遍历
while (condition) { ... }
```

## 2. 代码示例

### 2.1 基本类型与拆装箱

```java
// 文件：BasicTypes.java
public class BasicTypes {
    public static void main(String[] args) {
        // 1. 基本类型字面量
        int age = 25;
        long phone = 138_0000_0000L;   // 下划线分隔符（Java 7+）
        double price = 19.9;
        boolean enabled = true;
        char c = 'A';

        // 2. 自动装箱：int -> Integer
        Integer boxed = age;
        // 3. 自动拆箱：Integer -> int（null 时会抛 NullPointerException）
        int unboxed = boxed;

        System.out.println("age = " + age);         // 25
        System.out.println("boxed = " + boxed);     // 25
        System.out.println("类型: " + ((Object)boxed).getClass().getSimpleName()); // Integer
    }
}
```

### 2.2 分支与循环

```java
// 文件：ControlFlow.java
import java.util.List;

public class ControlFlow {
    public static void main(String[] args) {
        // 1. if/else
        int score = 85;
        String level = score >= 90 ? "A" : (score >= 60 ? "B" : "C");

        // 2. switch 表达式（Java 14+）
        int day = 3;
        String dayName = switch (day) {
            case 1 -> "Monday";
            case 2 -> "Tuesday";
            default -> "Other";
        };

        // 3. for 与 for-each
        List<String> names = List.of("Tom", "Jack", "Alice");
        for (String name : names) {
            System.out.println(name);
        }

        System.out.println(level + " / " + dayName);
    }
}
```

## 3. 关键要点总结

- Java 有 8 种基本类型，存储在栈上；其他类型都是引用类型，存储在堆上
- 自动装箱/`Objects.equals` 可以避免 NPE
- `switch` 表达式（Java 14+）比传统 `switch` 更紧凑安全
- ruoyi 大量使用"Lombok + 静态工厂方法"构造不可变对象

---

**文档版本**：v1.0
**最后更新**：2026-07-13
