# 2.2 @Cacheable / @CacheEvict / @CachePut

> 掌握 Spring Cache 三个核心注解的用法，理解它们之间的差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 `@Cacheable` / `@CacheEvict` / `@CachePut`
- 理解 `key` / `condition` / `unless` 的语法
- 区分"读缓存"和"写缓存"的语义
- 能在 ruoyi 中合理使用这三种注解

## 📚 前置知识

- Spring Cache 抽象层（详见 [Spring Cache 抽象](./08-spring-cache.md)）
- SpEL 表达式基础
- AOP 代理原理（详见 [AOP](../02-spring-boot/03-aop.md)，缓存注解依赖方法级代理）

## 1. 核心概念

### 1.1 三个注解的语义对比

| 注解 | 语义 | 命中缓存时 | 未命中缓存时 |
|------|------|----------|------------|
| `@Cacheable` | 读 | 直接返回缓存值 | 执行业务，写入缓存 |
| `@CachePut` | 写 | 更新缓存 | 执行业务，写入缓存 |
| `@CacheEvict` | 删 | 删除指定 key | 删除指定 key |

### 1.2 共同参数

- `cacheNames` / `value`：缓存命名空间
- `key`：SpEL 表达式，默认是 `SimpleKey`，所有参数组合
- `condition`：执行条件（前置），如 `#id > 0`
- `unless`：不缓存条件（后置），如 `#result == null`

## 2. 代码示例

### 2.1 @Cacheable 读缓存

```java
@Cacheable(cacheNames = "user", key = "#id")
public User getUser(Long id) {
    return userMapper.selectById(id);
}
```

### 2.2 @CachePut 写缓存

```java
@CachePut(cacheNames = "user", key = "#user.id")
public User updateUser(User user) {
    userMapper.updateById(user);
    return user;
}
```

注意：必须返回对象，否则缓存的是 `null`。

### 2.3 @CacheEvict 删除缓存

```java
// 删除单个 key
@CacheEvict(cacheNames = "user", key = "#id")
public void deleteUser(Long id) {
    userMapper.deleteById(id);
}

// 删除整个命名空间
@CacheEvict(cacheNames = "user", allEntries = true)
public void clearAllUsers() {
    userMapper.deleteAll();
}
```

### 2.4 condition 与 unless

```java
// id > 0 才缓存
@Cacheable(cacheNames = "user", key = "#id", condition = "#id > 0")
public User getUser(Long id) { ... }

// 结果非空才缓存
@Cacheable(cacheNames = "user", key = "#id", unless = "#result == null")
public User getUser(Long id) { ... }
```

## 3. ruoyi 仓库源码解读

### 3.1 TimeoutRedisCacheManager 的 key 解析

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
**核心代码**（行 23-27）：

```java
public class TimeoutRedisCacheManager extends RedisCacheManager {

    private static final String SPLIT = "#";

    public TimeoutRedisCacheManager(RedisCacheWriter cacheWriter, RedisCacheConfiguration defaultCacheConfiguration) {
        super(cacheWriter, defaultCacheConfiguration);
    }
```

**解读**：
- ruoyi 的 `#` 分隔符：让 `@Cacheable(cacheNames = "user#30m")` 既指定名字又指定 TTL
- `#` 是 Spring EL 不会用到的字符，所以可以放心用

### 3.2 自定义 TTL 的解析逻辑

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
**核心代码**（行 60-74）：

```java
private Duration parseDuration(String ttlStr) {
    String timeUnit = StrUtil.subSuf(ttlStr, -1);
    switch (timeUnit) {
        case "d":
            return Duration.ofDays(removeDurationSuffix(ttlStr));
        case "h":
            return Duration.ofHours(removeDurationSuffix(ttlStr));
        case "m":
            return Duration.ofMinutes(removeDurationSuffix(ttlStr));
        case "s":
            return Duration.ofSeconds(removeDurationSuffix(ttlStr));
        default:
            return Duration.ofSeconds(Long.parseLong(ttlStr));
    }
}
```

**解读**：
- `30m` → 30 分钟；`2h` → 2 小时；`1d` → 1 天
- 数字默认是秒（`30` → 30 秒）
- 这就是 ruoyi 业务代码里常看到的 `@Cacheable(cacheNames = "dict#1h")` 写法

### 3.3 配合事务感知的使用

ruoyi 业务代码中常见的"先改 DB 再清缓存"模式：

```java
@Service
public class UserService {
    @Transactional
    @CacheEvict(cacheNames = "user", key = "#user.id")
    public void updateUser(User user) {
        userMapper.updateById(user);
    }
}
```

配合 `cacheManager.setTransactionAware(true)`，缓存 evict 会延迟到事务 commit 后才执行，避免脏数据。

## 4. 关键要点总结

- `@Cacheable` 读缓存：命中返回，未命中执行
- `@CachePut` 写缓存：执行业务，并把结果写入缓存
- `@CacheEvict` 删缓存：可指定 key 或 `allEntries=true`
- `condition` 前置条件，`unless` 后置排除
- ruoyi 用 `cacheName#ttl` 语法让注解声明更紧凑

## 5. 练习题

### 练习 1：基础（必做）

写三个方法：
```java
@Cacheable(cacheNames = "user", key = "#id")
public User get(Long id);

@CachePut(cacheNames = "user", key = "#user.id")
public User save(User user);

@CacheEvict(cacheNames = "user", key = "#id")
public void delete(Long id);
```

测试：get → save → get 看缓存是否更新；get → delete → get 看是否回源。

### 练习 2：进阶

解释 `@CachePut` 和 `@Cacheable` 同时标注在 `updateUser` 上会怎样？哪个生效？

### 练习 3：挑战（选做）

用 `@Cacheable` + SpEL 实现"按多个字段组合做缓存 key"：
```java
@Cacheable(cacheNames = "user", key = "#tenantId + ':' + #name")
public User getByName(Long tenantId, String name);
```

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
- Spring Cache 注解文档：https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13