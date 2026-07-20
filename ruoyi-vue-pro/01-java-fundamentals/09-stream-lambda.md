# 1.1.8 Stream API 与 Lambda

> 掌握 Java 8 函数式编程的两大基石：Lambda 表达式 + Stream 流式操作，能写出 ruoyi 中常见的"集合转集合"代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Lambda 表达式替代匿名内部类
- 用 Stream API 完成"过滤、映射、归约、分组"
- 区分 `Intermediate` 与 `Terminal` 操作
- 看懂 `CollectionUtils.convertList`、`groupingBy` 等常见模式

## 📚 前置知识

- 集合基础（List / Set / Map）（详见 [07-collections](./08-collections.md)）
- Lambda 前置：函数式接口
- [08-collections.md](./08-collections.md)

## 1. 核心概念

### 1.1 Lambda 表达式

Lambda 是匿名函数，让代码更简洁。语法：`(参数) -> { 方法体 }`

```java
// 传统匿名内部类
new Runnable() {
    @Override public void run() { System.out.println("run"); }
};

// Lambda
Runnable r = () -> System.out.println("run");
```

**使用前提**：必须是**函数式接口**（只有一个抽象方法的接口），如 `Runnable`、`Function<T, R>`、`Predicate<T>` 等。

### 1.2 Stream 流

Stream 不是集合，是一种"流水线"，对数据做声明式处理：

```
数据源 → 过滤 → 转换 → 归约 → 结果
 (List)   filter  map    collect
```

特点：
- **不存储数据**：只对源数据做计算
- **不修改源数据**：产生新 Stream
- **惰性执行**：中间操作不执行，只有遇到终止操作才执行

### 1.3 两类操作

| 类型            | 例子                            | 是否触发计算       |
|---------------|-------------------------------|--------------|
| Intermediate  | `filter`, `map`, `sorted`     | 否（懒）         |
| Terminal      | `count`, `collect`, `forEach` | 是（触发）        |

### 1.4 常用 API

- `filter(Predicate)`：过滤
- `map(Function)`：转换
- `flatMap(Function)`：扁平化嵌套集合
- `sorted(Comparator)`：排序
- `distinct()`：去重
- `limit(n)` / `skip(n)`：截断
- `collect(Collectors.toList())`：收集为 List
- `groupingBy(Function)`：分组
- `reduce(...)`：归约（求和等）

## 2. 代码示例

### 2.1 Lambda 简化排序

```java
// 文件：LambdaSort.java
import java.util.*;

public class LambdaSort {
    public static void main(String[] args) {
        List<String> names = Arrays.asList("Tom", "Jack", "Alice");

        // 1. 传统：匿名内部类排序
        names.sort(new Comparator<String>() {
            @Override
            public int compare(String a, String b) {
                return a.compareTo(b);
            }
        });

        // 2. Lambda：方法引用更简洁
        names.sort(String::compareTo);

        System.out.println(names);  // [Alice, Jack, Tom]
    }
}
```

### 2.2 Stream API 综合示例

```java
// 文件：StreamDemo.java
import java.util.*;
import java.util.stream.Collectors;

public class StreamDemo {
    public static void main(String[] args) {
        record Person(String name, int age, String city) {}

        List<Person> persons = List.of(
            new Person("Tom", 25, "上海"),
            new Person("Jack", 30, "北京"),
            new Person("Alice", 25, "上海"),
            new Person("Bob", 35, "深圳")
        );

        // 1. 过滤 + 转换
        List<String> names = persons.stream()
            .filter(p -> p.age() > 25)
            .map(Person::name)
            .collect(Collectors.toList());
        System.out.println("年龄>25: " + names);  // [Jack, Bob]

        // 2. 分组
        Map<String, List<Person>> byCity = persons.stream()
            .collect(Collectors.groupingBy(Person::city));
        System.out.println(byCity);

        // 3. 求和
        int totalAge = persons.stream().mapToInt(Person::age).sum();
        System.out.println("年龄总和: " + totalAge);  // 115
    }
}
```

## 3. 关键要点总结

- Lambda 让匿名内部类代码极简化，要求是**函数式接口**
- Stream API 是声明式的数据处理管道（`中间操作 + 终止操作`）
- 常用：`filter`、`map`、`collect(Collectors.toList())`、`groupingBy`
- ruoyi 的 `CollectionUtils` 大量复用 `Collectors.toList()` / `Collectors.toMap()`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
