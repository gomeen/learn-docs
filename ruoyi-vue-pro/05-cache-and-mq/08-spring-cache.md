# 2.1 Spring Cache 抽象层

> 理解 Spring Cache 抽象的设计目的，掌握 CacheManager / Cache 接口的体系结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Cache 抽象的设计初衷
- 掌握 `CacheManager` / `Cache` 的核心接口
- 区分 Cache、CacheManager、CacheResolver 的角色
- 看懂 ruoyi 如何在 `YudaoCacheAutoConfiguration` 中扩展 CacheManager

## 📚 前置知识

- Spring IoC / AOP 基础（详见 [IoC](../02-spring-boot/01-ioc.md)、[AOP](../02-spring-boot/03-aop.md)）
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- Spring Boot Cache 入门（详见 [Spring Cache](../02-spring-boot/28-cache.md)）

## 1. 核心概念

### 1.1 为什么需要 Spring Cache 抽象？

如果业务代码直接调 `RedisTemplate`：
- 和 Redis 强耦合，换缓存后端（→ Caffeine / Hazelcast）要改业务
- 缓存逻辑（key 设计、TTL、序列化）和业务代码混在一起

Spring Cache 提供**注解 + 后端解耦**（注解细节详见 [@Cacheable / @CacheEvict / @CachePut](./09-cache-annotation.md)）：
- `@Cacheable` / `@CacheEvict` / `@CachePut` 是和后端无关的语义
- 底层用哪个（Redis / Caffeine / 内存 Map）由 `CacheManager` 决定；Redis 后端配置详见 [Redis 作为 Spring Cache 后端](./10-spring-cache-redis.md)

### 1.2 核心接口

```
CacheManager
  └── getCache(name) → Cache
                          ├── get(key) → 值
                          ├── put(key, value)
                          ├── evict(key)
                          └── clear()
```

- `CacheManager`：缓存容器管理器，按 name 拿 `Cache`
- `Cache`：单个命名空间的缓存对象
- `@Cacheable`：先查缓存，命中返回；未命中执行方法并写入缓存

## 2. 代码示例

### 2.1 启用 Spring Cache

```java
// 文件：CacheConfig.java
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableCaching
public class CacheConfig {
}
```

### 2.2 使用 @Cacheable

```java
// 文件：UserService.java
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Cacheable(cacheNames = "user", key = "#id")
    public User getUser(Long id) {
        System.out.println("查询数据库");
        return userMapper.selectById(id);
    }
}
```

第一次调用查 DB 并缓存；第二次直接返回缓存。

### 2.3 自定义 CacheManager

```java
@Bean
public CacheManager cacheManager() {
    // 用 Caffeine 作为后端
    CaffeineCacheManager manager = new CaffeineCacheManager();
    manager.setCaffeine(Caffeine.newBuilder().expireAfterWrite(10, TimeUnit.MINUTES));
    return manager;
}
```

## 3. 关键要点总结

- Spring Cache 是抽象层，后端可换 Redis / Caffeine / 内存 Map
- `CacheManager` 管理多个 `Cache`，每个 `Cache` 是一个命名空间
- ruoyi 自定义 `RedisCacheConfiguration`：JSON 序列化 + 自定义 TTL + 事务感知
- `TimeoutRedisCacheManager` 进一步支持 `cacheName#ttl` 语法

---

**文档版本**：v1.0
**最后更新**：2026-07-13
