# 1.1.3 泛型与类型擦除

> 理解 Java 泛型的语法糖本质与类型擦除机制，能看懂 ruoyi 中 `CommonResult<T>` 这类通用返回对象。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用泛型编写类型安全的通用方法/类
- 理解 Java 泛型的**类型擦除**机制
- 解释 PECS 原则（Producer Extends, Consumer Super）
- 看懂 `List<? extends Number>` 与 `List<? super Integer>` 的区别

## 📚 前置知识

- 面向对象基础（接口、继承）
- 集合基础（List / Map）
- 02-oop.md

## 1. 核心概念

### 1.1 为什么需要泛型？

没有泛型时，集合只能存 `Object`，取出时需要强制类型转换，容易 `ClassCastException`：

```java
// 没有泛型：放入任何对象，取出时类型不安全
List list = new ArrayList();
list.add("hello");
Integer n = (Integer) list.get(0);  // ❌ 运行时才报错
```

泛型让编译器在编译期就检查类型：

```java
List<String> list = new ArrayList<>();
list.add("hello");
// list.add(123);  // 编译报错
String s = list.get(0);  // 不需要转型
```

### 1.2 泛型类 / 泛型方法

```java
// 泛型类：在类名后声明类型参数
public class Box<T> {
    private T content;
    public void set(T t) { this.content = t; }
    public T get() { return content; }
}

// 泛型方法：在返回类型前声明类型参数
public static <K, V> Map<K, V> toMap(List<K> keys, List<V> values) { ... }
```

### 1.3 通配符 ? 与上下界

- `?` 表示未知类型
- `? extends T`：上界，元素是 `T` 或 `T` 子类，**只能取不能放**
- `? super T`：下界，元素是 `T` 或 `T` 父类，**可以取也可以放 `T`**

**PECS 原则**：生产者用 `extends`，消费者用 `super`。
- 如果你只是从集合中**读**数据，使用 `? extends T`
- 如果你只是往集合中**写**数据，使用 `? super T`

### 1.4 类型擦除（Type Erasure）

**Java 泛型是编译期概念**，编译后泛型信息会被擦除，替换为 `Object` 或上界类型。例如：

- `List<String>` 在编译后变成 `List`
- `Box<T extends Number>` 编译后变成 `Box`，内部类型用 `Number` 代替 `T`

这就是为什么运行时无法区分 `List<String>` 和 `List<Integer>`，也无法创建泛型数组 `new T[10]`。

## 2. 代码示例

### 2.1 泛型工具类（ruoyi 风格的 `CollectionUtils.convertList`）

```java
// 文件：GenericUtils.java
import java.util.*;
import java.util.stream.Collectors;

public class GenericUtils {

    // 类型转换：把 List<User> 转成 List<String>，提取用户名
    public static <T, R> List<R> convertList(List<T> list, java.util.function.Function<T, R> mapper) {
        if (list == null || list.isEmpty()) {
            return new ArrayList<>();
        }
        return list.stream()
                   .map(mapper)
                   .filter(Objects::nonNull)
                   .collect(Collectors.toList());
    }

    public static void main(String[] args) {
        // 测试：
        List<Integer> numbers = Arrays.asList(1, 2, 3);
        List<String> strings = convertList(numbers, n -> "n=" + n);
        System.out.println(strings); // [n=1, n=2, n=3]
    }
}
```

### 2.2 上界与下界通配符

```java
// 文件：WildcardDemo.java
import java.util.*;

public class WildcardDemo {

    // 生产者：只读取。用 ? extends T
    public static double sum(List<? extends Number> nums) {
        double total = 0;
        for (Number n : nums) {
            total += n.doubleValue();
        }
        return total;
    }

    // 消费者：往里放。用 ? super T
    public static void addIntegers(List<? super Integer> list) {
        for (int i = 0; i < 5; i++) {
            list.add(i);
        }
    }

    public static void main(String[] args) {
        List<Integer> ints = new ArrayList<>();
        addIntegers(ints);
        System.out.println(sum(ints));      // 10.0
        System.out.println(sum(List.of(1.1, 2.2, 3.3))); // 6.6
    }
}
```

## 3. 关键要点总结

- 泛型让编译器检查类型，避免运行时 `ClassCastException`
- Java 泛型是**编译期机制**，运行期被擦除为 `Object` 或上界
- PECS 原则：读用 `extends`，写用 `super`
- ruoyi 的 `CommonResult<T>`、`PageResult<T>`、`CollectionUtils#convertList` 都是泛型的实战范例

---

**文档版本**：v1.0
**最后更新**：2026-07-13
