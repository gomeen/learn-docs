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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 RedisCacheConfiguration 自定义

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 37-68）：

```java
@Bean
@Primary
public RedisCacheConfiguration redisCacheConfiguration(CacheProperties cacheProperties) {
    RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig();
    // 设置使用 : 单冒号，而不是双 :: 冒号，避免 Redis Desktop Manager 多余空格
    config = config.computePrefixWith(cacheName -> {
        String keyPrefix = cacheProperties.getRedis().getKeyPrefix();
        if (StringUtils.hasText(keyPrefix)) {
            keyPrefix = keyPrefix.lastIndexOf(StrUtil.COLON) == -1 ? keyPrefix + StrUtil.COLON : keyPrefix;
            return keyPrefix + cacheName + StrUtil.COLON;
        }
        return cacheName + StrUtil.COLON;
    });
    // 设置使用 JSON 序列化方式
    config = config.serializeValuesWith(
            RedisSerializationContext.SerializationPair.fromSerializer(buildRedisSerializer()));
    // 设置 CacheProperties.Redis 的属性
    CacheProperties.Redis redisProperties = cacheProperties.getRedis();
    if (redisProperties.getTimeToLive() != null) {
        config = config.entryTtl(redisProperties.getTimeToLive());
    }
    if (!redisProperties.isCacheNullValues()) {
        config = config.disableCachingNullValues();
    }
    if (!redisProperties.isUseKeyPrefix()) {
        config = config.disableKeyPrefix();
    }
    return config;
}
```

**解读**：
- 第 39 行：`@Primary` 让 ruoyi 的配置优先于 Spring Boot 默认
- 第 44-51 行：自定义 key 前缀为单冒号 `prefix:cacheName:`
- 第 53-54 行：JSON 序列化复用 `YudaoRedisAutoConfiguration.buildRedisSerializer()`
- 第 58 行：把 `application.yml` 的 TTL 注入
- 第 61 行：默认不缓存 null，防止缓存穿透

### 3.2 RedisCacheWriter 批量扫描策略

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 70-78）：

```java
@Bean
public RedisCacheManager redisCacheManager(RedisTemplate<String, Object> redisTemplate,
                                           RedisCacheConfiguration redisCacheConfiguration,
                                           YudaoCacheProperties yudaoCacheProperties) {
    // 创建 RedisCacheWriter 对象
    RedisConnectionFactory connectionFactory = Objects.requireNonNull(redisTemplate.getConnectionFactory());
    RedisCacheWriter cacheWriter = RedisCacheWriter.nonLockingRedisCacheWriter(connectionFactory,
            BatchStrategies.scan(yudaoCacheProperties.getRedisScanBatchSize()));
```

**解读**：
- 第 76 行：`nonLockingRedisCacheWriter` 不加锁（写场景 Spring 自身串行化已够）
- 第 77 行：`BatchStrategies.scan(batchSize)` 使用 `SCAN` 命令而非 `KEYS`，避免阻塞 Redis
- 这是大 key 集合场景的**生产级实践**：`KEYS *` 会阻塞，SCAN 不会

### 3.3 ruoyi 私有属性 RedisScanBatchSize

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheProperties.java`

```java
@Data
@ConfigurationProperties(prefix = "yudao.cache")
public class YudaoCacheProperties {
    private Integer redisScanBatchSize = 30;
}
```

**解读**：
- ruoyi 把批量扫描大小做成可配置，默认 30
- yudao.cache.redis-scan-batch-size=100 可调整

## 4. 关键要点总结

- `spring.cache.type=redis` 启用 Redis 后端
- ruoyi 配置 JSON 序列化、单冒号前缀、可配 TTL
- `BatchStrategies.scan` 是生产级关键：避免 `KEYS` 阻塞
- `setTransactionAware(true)` 让 `@CacheEvict` 与事务协同

## 5. 练习题

### 练习 1：基础（必做）

写 `application.yml` 配置 Redis 缓存，TTL 1 小时，key 前缀 `app:cache:`。

### 练习 2：进阶

阅读 `YudaoCacheAutoConfiguration`，解释为什么 ruoyi 不用 Spring Boot 默认的 `CacheManager`，要自己写一遍？

### 练习 3：挑战（选做）

把 `BatchStrategies.scan` 的 batch size 调到 100，用 `redis-cli --scan --pattern "user:*"` 验证是否生效。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheProperties.java`
- Spring Boot Cache 文档：https://docs.spring.io/spring-boot/reference/io/caching.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13