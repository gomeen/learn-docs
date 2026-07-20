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

## 3. 关键要点总结

- `@Cacheable` 读缓存：命中返回，未命中执行
- `@CachePut` 写缓存：执行业务，并把结果写入缓存
- `@CacheEvict` 删缓存：可指定 key 或 `allEntries=true`
- `condition` 前置条件，`unless` 后置排除
- ruoyi 用 `cacheName#ttl` 语法让注解声明更紧凑

---

**文档版本**：v1.0
**最后更新**：2026-07-13
