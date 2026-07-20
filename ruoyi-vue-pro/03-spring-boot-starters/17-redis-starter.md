# 3.1 yudao-spring-boot-starter-redis 架构

> 理解 yudao Redis Starter 的整体架构，掌握其与 Spring Data Redis、Redisson 的关系。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao Redis Starter 的整体设计
- 理解 Redisson 与 Spring Data Redis 的协作
- 掌握 yudao 自定义 `RedisTemplate` 的价值
- 能配置自己的 Redis 序列化策略

## 📚 前置知识

- Spring Data Redis
- Redisson 基础（详见 [15-redisson](./18-redisson.md)）
- Redis 数据结构（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）

## 1. 核心概念

### 1.1 为什么需要 Redis Starter？

Redis 是分布式系统的基石，但**默认配置不够用**：
- 默认 `RedisTemplate` 用 JDK 序列化（不可读）
- 没有 `RedisUtils` 工具类
- 缺少分布式锁、限流等高级特性（锁见 [17-distributed-lock](./20-distributed-lock.md)，限流见 [18-rate-limiter](./21-rate-limiter.md)）
- 多租户场景下缓存需要隔离（多租户见 [多租户](../../_common/08-authorization/05-multi-tenant.md) / [33-tenant](./40-tenant.md)）

yudao 的 Redis Starter 解决了所有这些问题。

### 1.2 yudao Redis Starter 组件

| 组件 | 职责 |
|------|------|
| `YudaoRedisAutoConfiguration` | 装配自定义 `RedisTemplate` |
| `YudaoCacheAutoConfiguration` | 装配 `RedisCacheManager`（Spring Cache 见 [24-cache](../02-spring-boot/28-cache.md)） |
| `TimeoutRedisCacheManager` | 支持自定义 TTL |
| `YudaoCacheProperties` | 缓存配置 |
| `TenantRedisCacheManager` | 多租户缓存隔离（由 tenant starter 提供） |
| `RedisUtils` | 工具类（在 `yudao-common`） |
| `Redisson` 客户端 | 分布式锁、限流（在 yudao-common） |

## 2. 代码示例

### 2.1 基本使用

```java
@Service
public class UserServiceImpl {
    @Resource
    private RedisUtils redisUtils;

    public UserDO getUser(Long id) {
        // 1. 优先读缓存
        UserDO cached = redisUtils.get("user:" + id, UserDO.class);
        if (cached != null) return cached;

        // 2. 查 DB
        UserDO user = userMapper.selectById(id);

        // 3. 写缓存（30 分钟）
        redisUtils.set("user:" + id, user, Duration.ofMinutes(30));
        return user;
    }
}
```

### 2.2 使用 Spring Cache 注解

```java
@Service
public class ConfigServiceImpl {
    @Cacheable(cacheNames = "config", key = "#key")
    public String getConfig(String key) {
        return configMapper.selectByKey(key);
    }

    @CacheEvict(cacheNames = "config", key = "#key")
    public void updateConfig(String key, String value) {
        // ...
    }
}
```

### 2.3 自定义缓存 TTL

```java
// 通过 "key#ttl" 格式：key 名 + # + 过期时间
@Cacheable(cacheNames = "user#30m", key = "#id")  // 30 分钟过期
public UserDO getUser(Long id) { ... }

@Cacheable(cacheNames = "config#1h", key = "#key")  // 1 小时过期
public String getConfig(String key) { ... }
```

## 3. 关键要点总结

- **yudao Redis Starter = Spring Data Redis + Redisson + 大量增强**
- **自定义 `RedisTemplate`**：Key=String, Value=JSON
- **`TimeoutRedisCacheManager`** 通过 `cacheName#ttl` 语法声明 TTL
- **多租户**通过 `TenantRedisCacheManager` 实现 Key 前缀隔离
- **`RedisUtils` 工具类**封装 90% 常用操作

---

**文档版本**：v1.0
**最后更新**：2026-07-13
