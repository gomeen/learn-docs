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
- Spring Boot Cache 入门（详见 [Spring Cache](../02-spring-boot/24-cache.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 CacheManager 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 27-30）：

```java
@AutoConfiguration
@EnableConfigurationProperties({CacheProperties.class, YudaoCacheProperties.class})
@EnableCaching
public class YudaoCacheAutoConfiguration {
```

**解读**：
- `@EnableCaching` 启用 Spring Cache 注解处理（AOP 切面）
- `@AutoConfiguration` 让 Spring Boot 3.x 自动发现该配置
- `@EnableConfigurationProperties` 启用 `application.yml` 里的 `spring.cache.redis.*` 配置

### 3.2 RedisCacheConfiguration 自定义

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
    ...
    return config;
}
```

**解读**：
- 第 40 行：拿到默认配置
- 第 44-51 行：自定义 key 前缀为 `cacheName:` 单冒号，避免 Redis Desktop Manager 显示多余空格
- 第 53 行：VALUE 用 JSON 序列化（与 RedisTemplate 一致）
- 第 58 行：从 `application.yml` 读默认 TTL（`spring.cache.redis.time-to-live`）

### 3.3 启用事务感知的 CacheManager

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 70-84）：

```java
@Bean
public RedisCacheManager redisCacheManager(RedisTemplate<String, Object> redisTemplate,
                                           RedisCacheConfiguration redisCacheConfiguration,
                                           YudaoCacheProperties yudaoCacheProperties) {
    // 创建 RedisCacheWriter 对象
    RedisConnectionFactory connectionFactory = Objects.requireNonNull(redisTemplate.getConnectionFactory());
    RedisCacheWriter cacheWriter = RedisCacheWriter.nonLockingRedisCacheWriter(connectionFactory,
            BatchStrategies.scan(yudaoCacheProperties.getRedisScanBatchSize()));
    // 创建 TimeoutRedisCacheManager 对象
    TimeoutRedisCacheManager cacheManager = new TimeoutRedisCacheManager(cacheWriter, redisCacheConfiguration);
    // 开启事务感知：@Transactional 方法内的 @CacheEvict / @CachePut 自动延迟到 afterCommit，
    //             避免事务未提交就清缓存被并发读穿写脏值；无事务时立即生效，行为不变
    cacheManager.setTransactionAware(true);
    return cacheManager;
}
```

**解读**：
- 第 79 行：用 ruoyi 自定义的 `TimeoutRedisCacheManager` 替代 Spring 默认
- 第 82 行：`setTransactionAware(true)` 让 `@CacheEvict` 在 `@Transactional` 事务中**延迟到事务提交后再执行**
- 这是非常实用的设计：**先改 DB，提交成功后再清缓存**，避免脏数据

## 4. 关键要点总结

- Spring Cache 是抽象层，后端可换 Redis / Caffeine / 内存 Map
- `CacheManager` 管理多个 `Cache`，每个 `Cache` 是一个命名空间
- ruoyi 自定义 `RedisCacheConfiguration`：JSON 序列化 + 自定义 TTL + 事务感知
- `TimeoutRedisCacheManager` 进一步支持 `cacheName#ttl` 语法

## 5. 练习题

### 练习 1：基础（必做）

写一个 `@Cacheable(cacheNames = "user", key = "#id")` 的方法，调用两次看是否第二次打印"查询数据库"。

### 练习 2：进阶

阅读 `YudaoCacheAutoConfiguration.redisCacheManager`，解释 `setTransactionAware(true)` 的作用场景：什么情况下会出现"清缓存了但事务回滚了"？

### 练习 3：挑战（选做）

把 `@Cacheable` 改成 `@Cacheable(cacheNames = "user#5m", key = "#id")`，验证 5 分钟后缓存过期。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- Spring Cache 官方文档：https://docs.spring.io/spring-framework/reference/integration/cache.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13