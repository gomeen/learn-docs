# 1.1.8 Stream API 与 Lambda

> 掌握 Java 8 函数式编程的两大基石：Lambda 表达式 + Stream 流式操作，能写出 ruoyi 中常见的"集合转集合"代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Lambda 表达式替代匿名内部类
- 用 Stream API 完成"过滤、映射、归约、分组"
- 区分 `Intermediate` 与 `Terminal` 操作
- 看懂 `CollectionUtils.convertList`、`groupingBy` 等常见模式

## 📚 前置知识

- 集合基础（List / Set / Map）（详见 [07-collections](./07-collections.md)）
- Lambda 前置：函数式接口
- [07-collections.md](./07-collections.md)

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 `CollectionUtils#convertList`：Stream 的 map + filter

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/collection/CollectionUtils.java`
**核心代码**（行 64-69）：

```java
public static <T, U> List<U> convertList(Collection<T> from, Function<T, U> func) {
    if (CollUtil.isEmpty(from)) {
        return new ArrayList<>();
    }
    return from.stream().map(func).filter(Objects::nonNull).collect(Collectors.toList());
}
```

**解读**：
- 第 1 行：`Function<T, U>` 是函数式接口，接收 `T` 返回 `U`（Lambda 用到）
- 第 4 行：三步链式调用：`.map()` 转换 → `.filter()` 过滤 null → `.collect()` 收集
- 业务用法：
  ```java
  List<UserVO> voList = CollectionUtils.convertList(userList, user -> {
      UserVO vo = new UserVO();
      BeanUtils.copyProperties(user, vo);
      return vo;
  });
  ```
- `.filter(Objects::nonNull)` 防止 mapper 返回 null，导致下游 NPE

### 3.2 `CollectionUtils#convertMultiMap`：groupingBy 分组

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/collection/CollectionUtils.java`
**核心代码**（行 216-222）：

```java
public static <T, K, V> Map<K, List<V>> convertMultiMap(Collection<T> from, Function<T, K> keyFunc, Function<T, V> valueFunc) {
    if (CollUtil.isEmpty(from)) {
        return new HashMap<>();
    }
    return from.stream()
            .collect(Collectors.groupingBy(keyFunc, Collectors.mapping(valueFunc, Collectors.toList())));
}
```

**解读**：
- 第 1 行：泛型 `<T, K, V>`，输入 `T` 按 `keyFunc` 分组，输出 key=`K`、value=`V`
- 第 5 行：`Collectors.groupingBy` 的下游接 `Collectors.mapping`，把组内 `T` 转换为 `V`
- 业务场景：`List<OrderDO>` 按 `userId` 分组为 `Map<Long, List<Long>>`（订单 ID 列表）
  ```java
  Map<Long, List<Long>> userOrderMap = CollectionUtils.convertMultiMap(
      orderList, OrderDO::getUserId, OrderDO::getId);
  ```

## 4. 关键要点总结

- Lambda 让匿名内部类代码极简化，要求是**函数式接口**
- Stream API 是声明式的数据处理管道（`中间操作 + 终止操作`）
- 常用：`filter`、`map`、`collect(Collectors.toList())`、`groupingBy`
- ruoyi 的 `CollectionUtils` 大量复用 `Collectors.toList()` / `Collectors.toMap()`

## 5. 练习题

### 练习 1：基础（必做）

用一行 Stream API 把 `[1, 2, 3, 4, 5, 6, 7, 8]` 中所有偶数平方后求和。

### 练习 2：进阶

阅读 `CollectionUtils#convertSet`（行 113-118），指出它与 `convertList` 的区别，并说明为什么它要传入 `filter Predicate` 的重载。

### 练习 3：挑战（选做）

实现一个通用方法 `<T, R> List<R> batchProcess(List<T> input, int batchSize, Function<List<T>, List<R>> processor)`：把 `input` 分成 `batchSize` 一批，调用 `processor` 处理每批后合并结果。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/collection/CollectionUtils.java`
- 《Java 8 实战》第 4-6 章：Stream 流
- Java Stream 官方教程：https://docs.oracle.com/javase/technologies/tutorials.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
