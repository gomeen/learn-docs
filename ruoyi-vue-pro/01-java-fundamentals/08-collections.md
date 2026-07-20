# 1.1.7 集合框架：List / Set / Map

> 掌握 Java 集合框架的核心接口与常用实现，能看懂 ruoyi 中复杂的数据转换与业务代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `List`、`Set`、`Map` 的特点与适用场景
- 选择正确的实现类（`ArrayList` vs `LinkedList`，`HashMap` vs `TreeMap`）
- 使用 `List.of()` / `Map.of()` 创建不可变集合
- 理解 ruoyi 中 `CollectionUtils` 工具类的方法实现

## 📚 前置知识

- 面向对象基础（接口、泛型）
- 02-oop.md、03-generics.md

## 1. 核心概念

### 1.1 集合框架整体结构

```
        Collection (interface)
        /          |          \
    List          Set         Queue
    |             |           |
 ArrayList      HashSet     LinkedList
 LinkedList     TreeSet
 Vector         LinkedHashSet

        Map (interface, 不继承 Collection)
        /      |        \
    HashMap    TreeMap    LinkedHashMap
    Hashtable
    ConcurrentHashMap
```

### 1.2 List：有序可重复

| 实现           | 底层     | 特点                |
|--------------|--------|-------------------|
| `ArrayList`  | 数组     | 随机访问快，增删慢         |
| `LinkedList` | 双向链表   | 增删快，随机访问慢         |
| `Vector`     | 数组（同步） | 线程安全，但已过时        |

### 1.3 Set：无序不重复

| 实现                | 特点                |
|-------------------|-------------------|
| `HashSet`         | 基于 `HashMap`，无序   |
| `LinkedHashSet`   | 保留插入顺序            |
| `TreeSet`         | 按元素自然顺序排序（红黑树）   |

### 1.4 Map：键值对

| 实现                   | 特点                       |
|----------------------|--------------------------|
| `HashMap`            | 基于哈希表，最常用，允许 null key/值  |
| `TreeMap`            | 按 key 排序，红黑树             |
| `LinkedHashMap`      | 保留插入顺序                   |
| `Hashtable`          | 线程安全（已过时）                |
| `ConcurrentHashMap`  | 线程安全，高并发推荐（原理与分段锁/CAS 详见 [26-concurrent-collections](./31-concurrent-collections.md)） |

### 1.5 不可变集合（Java 9+）

```java
List<String> list = List.of("A", "B", "C");          // 不可变
Map<String, Integer> map = Map.of("Tom", 1, "Jack", 2);
Set<Integer> set = Set.of(1, 2, 3);
```

## 2. 代码示例

### 2.1 List / Set / Map 基础操作

```java
// 文件：CollectionBasics.java
import java.util.*;

public class CollectionBasics {
    public static void main(String[] args) {
        // 1. List：有序、可重复
        List<String> list = new ArrayList<>();
        list.add("a"); list.add("b"); list.add("a");
        System.out.println("list: " + list + " size=" + list.size());

        // 2. Set：自动去重
        Set<String> set = new HashSet<>(list);
        System.out.println("set: " + set);                      // [a, b]

        // 3. Map：键值对
        Map<String, Integer> map = new HashMap<>();
        map.put("Tom", 18);
        map.put("Jack", 20);
        System.out.println("Tom's age: " + map.get("Tom"));

        // 4. 遍历
        list.forEach(System.out::println);
        map.forEach((k, v) -> System.out.println(k + " -> " + v));
    }
}
```

### 2.2 常见错误：用 List.contains() 查大数据量

```java
// 文件：WrongLookup.java
import java.util.*;

public class WrongLookup {

    // ❌ 错误：O(N) 查找，1 万次循环 = 1 亿次比较
    public boolean isAdmin(Long userId, List<Long> adminIds) {
        return adminIds.contains(userId);
    }

    // ✅ 正确：转换为 Set，O(1) 查找
    public boolean isAdminFast(Long userId, List<Long> adminIds) {
        Set<Long> adminSet = new HashSet<>(adminIds);
        return adminSet.contains(userId);
    }
}
```

## 3. 关键要点总结

- `List` 是有序集合，`Set` 是去重集合，`Map` 是键值对集合
- 大量数据查找用 `HashMap` / `HashSet` 而非 `List`，性能差距巨大
- 集合操作前要判空，避免 NPE
- ruoyi 的 `CollectionUtils` 提供 50+ 工具方法，业务代码大量复用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
