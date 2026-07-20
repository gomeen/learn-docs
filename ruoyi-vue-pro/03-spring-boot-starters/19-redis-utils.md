# 3.3 Redis 工具类：RedisUtils / RedisLockUtils

> 掌握 yudao 封装的 Redis 工具类，能用工具类完成 90% 的 Redis 操作。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `RedisUtils` 的所有常用方法
- 理解 `RedisLockUtils` 的分布式锁实现
- 了解 `RedissonUtils` 的高级特性封装
- 能用工具类完成常见缓存场景

## 📚 前置知识

- [17-redis-starter.md](./17-redis-starter.md)
- [18-redisson.md](./18-redisson.md)
- Java 泛型基础（详见 [03-generics](../01-java-fundamentals/03-generics.md)）
- 分布式锁工具见 [17-distributed-lock](./20-distributed-lock.md)

## 1. 核心概念

### 1.1 yudao 提供的 Redis 工具类

| 工具类 | 来源 | 职责 |
|--------|------|------|
| `RedisUtils` | yudao-common | 普通 KV 操作 |
| `RedissonUtils` | yudao-common | Redisson 高级 API 包装 |
| `RedisLockUtils` | yudao-common | 分布式锁封装 |
| `CacheUtils` | yudao-common | 本地缓存 + Redis 二级缓存 |

### 1.2 RedisUtils 的设计原则

- **简单直接**：方法名与 Redis 命令一一对应
- **类型安全**：用 `Class<T>` 替代 `Object`
- **异常透明**：用 Hutool 工具类，不抛 checked 异常

## 2. 代码示例

### 2.1 基本 KV 操作

```java
@Resource
private RedisUtils redisUtils;  // 注意是 yudao 的 RedisUtils

// String
redisUtils.set("user:1", userDO);
redisUtils.set("user:1", userDO, Duration.ofMinutes(30));
UserDO user = redisUtils.get("user:1", UserDO.class);
String str = redisUtils.get("counter", String.class);

// 删除
redisUtils.delete("user:1");
redisUtils.delete(Arrays.asList("user:1", "user:2"));

// 存在
boolean exists = redisUtils.hasKey("user:1");

// 自增
Long count = redisUtils.incr("counter", 1L);

// 设置过期
redisUtils.expire("user:1", Duration.ofHours(1));
```

### 2.2 Hash 操作

```java
redisUtils.hSet("user:profile:1", "name", "张三");
redisUtils.hSet("user:profile:1", "age", "18");
String name = redisUtils.hGet("user:profile:1", "name", String.class);
Map<String, String> profile = redisUtils.hGetAll("user:profile:1");
```

### 2.3 集合与有序集合

```java
// Set
redisUtils.sAdd("tags:1", "java", "redis", "mysql");
Set<String> tags = redisUtils.sMembers("tags:1", String.class);

// ZSet（排行榜）
redisUtils.zAdd("rank:score", userDO, 99.5);
Set<UserDO> top = redisUtils.zRange("rank:score", 0, 9);
```

## 3. 关键要点总结

- **`RedisUtils`** 封装 90% 的 RedisTemplate 操作
- **`RedisLockUtils`** 用 Supplier 简化分布式锁
- **`CacheUtils`** 实现 L1 + L2 二级缓存
- **yudao 工具类都用 `SpringUtils.getBean`** 方式获取 Bean（更灵活）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
