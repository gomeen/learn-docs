# 2.3 Redis 作为 Spring Cache 后端

> 深入理解 Redis 作为 Spring Cache 后端时的配置、序列化、TTL 与扫描策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 `spring.cache.type=redis` 启用 Redis 作为 Spring Cache 后端
- 理解 RedisCache 的存储结构和 key 设计
- 掌握 `BatchStrategies.scan` 的批量扫描策略
- 能正确设置 `spring.cache.redis.time-to-live` 等关键属性

## 📚 前置知识

- Spring Cache 抽象（详见 [Spring Cache 抽象](./08-spring-cache.md)）
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 缓存策略与 TTL 思路（详见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)）

## 1. 核心概念

### 1.1 Redis 作为 Cache 后端

Spring Cache 把每个 `Cache` 映射到 Redis 的一个命名空间：
- `Cache name = "user"` → Redis key 前缀 `user:`
- 缓存值用配置的 `RedisSerializer` 序列化（默认 JDK 二进制，ruoyi 改成 JSON）
- 默认 TTL 从 `spring.cache.redis.time-to-live` 读

> 📌 **Sighting**：`cache-null-values` 与穿透/雪崩等缓存问题详见 [缓存三大问题](../../_common/03-cache-patterns/02-three-problems.md)。

### 1.2 application.yml 关键配置

```yaml
spring:
  cache:
    type: redis
    redis:
      time-to-live: 1h         # 默认 TTL
      cache-null-values: false # 不缓存 null
      use-key-prefix: true     # 使用 key 前缀
      key-prefix: "yudao:cache:" # key 前缀
```

### 1.3 存储格式

```bash
# Spring Cache 存的 key 是：
{yudao:cache:}user::123
#         ↑prefix ↑cacheName ↑key
```

ruoyi 配置成单冒号：`user:123`，更干净。

## 2. 代码示例

### 2.1 启用 + 配置

```yaml
# application.yml
spring:
  cache:
    type: redis
    redis:
      time-to-live: 30m
      key-prefix: "yudao:cache:"
```

### 2.2 自定义配置类

```java
// 文件：RedisCacheConfig.java
import org.springframework.boot.autoconfigure.cache.CacheProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.RedisSerializer;

@Configuration
public class RedisCacheConfig {

    @Bean
    public RedisCacheConfiguration cacheConfiguration(CacheProperties cacheProperties) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig();
        config = config.serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(RedisSerializer.json()));
        config = config.entryTtl(cacheProperties.getRedis().getTimeToLive());
        return config;
    }
}
```

## 3. 关键要点总结

- `spring.cache.type=redis` 启用 Redis 后端
- ruoyi 配置 JSON 序列化、单冒号前缀、可配 TTL
- `BatchStrategies.scan` 是生产级关键：避免 `KEYS` 阻塞
- `setTransactionAware(true)` 让 `@CacheEvict` 与事务协同

---

**文档版本**：v1.0
**最后更新**：2026-07-13
