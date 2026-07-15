# 1.1.9 Optional 与空值处理

> 掌握 `Optional` 的使用，避免无处不在的 `NullPointerException`，看懂 ruoyi 的空安全设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 `Optional` 包装可能为 null 的值
- 区分 `map`、`flatMap`、`orElse`、`orElseThrow` 等场景
- 避免常见的 Optional 反模式（作为方法参数、用作集合元素等）
- 看懂 ruoyi 中 `Optional` 与 `getCheckedData` 的用法

## 📚 前置知识

- 集合基础
- Lambda 表达式
- 07-collections.md、08-stream-lambda.md

## 1. 核心概念

### 1.1 为什么需要 `Optional`？

空指针异常是 Java 最常见的运行时错误之一。传统代码通过"判 null 到处飞"应对，极其啰嗦：

```java
// 传统写法：嵌套判空
String city = user == null ? "未知"
            : user.getAddress() == null ? "未知"
            : user.getAddress().getCity() == null ? "未知"
            : user.getAddress().getCity();
```

`Optional` 是 JDK 给的"可能为空的容器"，强迫你在类型层面处理 null。

### 1.2 `Optional` 的本质

`Optional<T>` 是一个**最多包含一个值**的容器，要么有值，要么为空（`Optional.empty()`）。

```java
// 创建
Optional<String> empty = Optional.empty();                  // 显式空
Optional<String> has = Optional.of("hello");                // 强制非空（null 会抛 NPE）
Optional<String> nullable = Optional.ofNullable(s);         // 允许 null
```

### 1.3 关键 API

| 方法                 | 作用                       |
|--------------------|--------------------------|
| `isPresent()`      | 是否非空（少用）                |
| `ifPresent(Consumer)` | 非空时执行动作              |
| `get()`             | 直接取值（不推荐，丢失安全语义）  |
| `orElse(T)`         | 空时返回给定值（总是求值）        |
| `orElseGet(Supplier)` | 空时调用 Supplier  生成值   |
| `orElseThrow(Supplier) | 空时抛异常                    |
| `map(Function)`     | 转换内部值，返回新 Optional   |
| `flatMap(Function)` | 与 map 类似，但入参返回 Optional |

### 1.4 常见反模式（避免踩坑）

1. **不要** `Optional<User>` 作为方法参数（应该判 null 直接抛异常或返回默认值）
2. **不要** `Optional` 作为集合元素类型（应用 `List<User>` 而不是 `List<Optional<User>>`）
3. **不要** 为了 ForEach 用 `ifPresent` 又把里面逻辑写成块（读不懂）

## 2. 代码示例

### 2.1 Optional 解决深层判空

```java
// 文件：OptionalDemo.java
import java.util.*;

public class OptionalDemo {
    static class City  { public String name; }
    static class Address { public City city; }
    static class User   { public Address address; }

    public static void main(String[] args) {
        // 1. 传统写法：嵌套判 null
        User user = new User();
        String result1 = "未知";
        if (user != null && user.address != null && user.address.city != null) {
            result1 = user.address.city.name;
        }

        // 2. Optional 写法：链式 map，安全简洁
        String result2 = Optional.ofNullable(user)
            .map(u -> u.address)
            .map(a -> a.city)
            .map(c -> c.name)
            .orElse("未知");

        System.out.println(result1);   // 未知
        System.out.println(result2);   // 未知
    }
}
```

### 2.2 `orElse` vs `orElseGet`

```java
// 文件：OrElseDemo.java
import java.util.Optional;
import java.util.UUID;

public class OrElseDemo {

    // ❌ 错误：默认值总是会被创建（即使 Optional 有值）
    public static UUID defaultIdAlways() {
        return Optional.ofNullable(getFromCache()).orElse(UUID.randomUUID());
    }

    // ✅ 正确：只有空时才创建默认值
    public static UUID defaultIdLazily() {
        return Optional.ofNullable(getFromCache())
                       .orElseGet(() -> UUID.randomUUID());
    }

    private static UUID getFromCache() { return UUID.randomUUID(); }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 `CommonResult#getCheckedData`

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
**核心代码**（行 99-115）：

```java
/**
 * 判断是否有异常。如果有，则抛出 {@link ServiceException} 异常
 */
public void checkError() throws ServiceException {
    if (isSuccess()) {
        return;
    }
    // 业务异常
    throw new ServiceException(code, msg);
}

/**
 * 判断是否有异常。如果有，则抛出 {@link ServiceException} 异常
 * 如果没有，则返回 {@link #data} 数据
 */
@JsonIgnore // 避免 jackson 序列化
public T getCheckedData() {
    checkError();
    return data;
}

public static <T> CommonResult<T> error(ServiceException serviceException) {
    return error(serviceException.getCode(), serviceException.getMessage());
}
```

**解读**：
- 第 9-12 行：`getCheckedData` 是空安全数据获取模式——结合"成功返回 data，失败抛异常"的语义
- **为什么不直接用 Optional？** 因为这是 RPC 远程调用场景，错误必须以**异常**抛出（异常能被 Spring MVC 切面捕获，见 [17-exception-handler](../02-spring-boot/17-exception-handler.md)），而不是返回 Optional
- 第 14 行：把异常转换为 `CommonResult` 错误响应
- **设计意图**：业务代码简化写法，避免每个方法都先 `checkError()` 再 `getData()`：
  ```java
  // ❌ 啰嗦
  CommonResult<X> r = remoteService.call();
  r.checkError();
  X data = r.getData();
  
  // ✅ 简洁
  X data = remoteService.call().getCheckedData();
  ```

### 3.2 MyBatis-Plus 的 Optional 模式

**参考位置**：MyBatis-Plus 的 `BaseMapper.selectOne()` 在某些版本中会返回 `Optional<T>`，让调用方强制处理"可能为空"的情况。

> ruoyi 中无直接示例（使用 MyBatis-Plus 的链式查询封装），但 `ServiceException` 设计哲学与 Optional 一致——"强制调用方处理空/错误"。

## 4. 关键要点总结

- `Optional` 是"最多一个值"的容器，强迫你处理 null
- 链式 `map` + `orElse` 解决深层嵌套判空
- `orElseGet`（懒） > `orElse`（饿），性能差距大
- 避免把 `Optional` 作为参数或集合元素

## 5. 练习题

### 练习 1：基础（必做）

写一个 `<T> T requireNotNull(T value, String message)`：当 `value == null` 时抛 `IllegalArgumentException`，否则返回 `value`。

### 练习 2：进阶

阅读 `CommonResult` 的全文，指出**比 `Optional` 更好**的两个地方（提示：业务错误码、异常传播）。

### 练习 3：挑战（选做）

实现一个 `<T, R> Optional<R> safeMap(Optional<T> opt, Function<T, R> mapper)`：与 `Optional.map` 等价，但当 `mapper` 抛异常时，返回 `Optional.empty()` 而不传播异常。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
- 《Java 8 实战》第 10 章：用 Optional 取代 null
- Optional 官方文档：https://docs.oracle.com/javase/8/docs/api/java/util/Optional.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
