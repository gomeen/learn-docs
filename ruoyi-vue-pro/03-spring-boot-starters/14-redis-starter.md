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
- Redisson 基础（详见 [15-redisson](./15-redisson.md)）
- Redis 数据结构（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）

## 1. 核心概念

### 1.1 为什么需要 Redis Starter？

Redis 是分布式系统的基石，但**默认配置不够用**：
- 默认 `RedisTemplate` 用 JDK 序列化（不可读）
- 没有 `RedisUtils` 工具类
- 缺少分布式锁、限流等高级特性（锁见 [17-distributed-lock](./17-distributed-lock.md)，限流见 [18-rate-limiter](./18-rate-limiter.md)）
- 多租户场景下缓存需要隔离（多租户见 [多租户](../../_common/08-authorization/05-multi-tenant.md) / [33-tenant](./33-tenant.md)）

yudao 的 Redis Starter 解决了所有这些问题。

### 1.2 yudao Redis Starter 组件

| 组件 | 职责 |
|------|------|
| `YudaoRedisAutoConfiguration` | 装配自定义 `RedisTemplate` |
| `YudaoCacheAutoConfiguration` | 装配 `RedisCacheManager`（Spring Cache 见 [24-cache](../02-spring-boot/24-cache.md)） |
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

## 3. ruoyi 仓库源码解读

### 3.1 自定义 RedisTemplate

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
**核心代码**（行 16-44）：

```java
@AutoConfiguration(before = RedissonAutoConfigurationV2.class)
public class YudaoRedisAutoConfiguration {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        // Key 用 String 序列化
        template.setKeySerializer(RedisSerializer.string());
        template.setHashKeySerializer(RedisSerializer.string());
        // Value 用 JSON 序列化
        RedisSerializer<?> redisSerializer = buildRedisSerializer();
        template.setValueSerializer(redisSerializer);
        template.setHashValueSerializer(redisSerializer);
        return template;
    }

    public static RedisSerializer<?> buildRedisSerializer() {
        RedisSerializer<Object> json = RedisSerializer.json();
        // 反射取出 ObjectMapper，注册 JavaTimeModule
        ObjectMapper objectMapper = (ObjectMapper) ReflectUtil.getFieldValue(json, "mapper");
        objectMapper.registerModules(new JavaTimeModule());
        return json;
    }
}
```

**解读**：
- `@AutoConfiguration(before = RedissonAutoConfigurationV2.class)` 先于 Redisson 装配
- Key 用 String 序列化（**可读**）
- Value 用 JSON 序列化（**跨语言、调试友好**）
- **反射 hack**：从 `RedisSerializer.json()` 内部取出 ObjectMapper，注册 `JavaTimeModule`（解决 `LocalDateTime` 序列化）
- 这种反射方式是 yudao 大量使用的模式

### 3.2 TimeoutRedisCacheManager（自定义 TTL）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
**核心代码**（行 29-52）：

```java
@Override
protected RedisCache createRedisCache(String name, RedisCacheConfiguration cacheConfig) {
    if (StrUtil.isEmpty(name)) {
        return super.createRedisCache(name, cacheConfig);
    }
    // 如果使用 # 分隔，大小不为 2，则说明不使用自定义过期时间
    String[] names = StrUtil.splitToArray(name, SPLIT);
    if (names.length != 2) {
        return super.createRedisCache(name, cacheConfig);
    }
    // 核心：通过修改 cacheConfig 的过期时间，实现自定义过期时间
    if (cacheConfig != null) {
        String ttlStr = StrUtil.subBefore(names[1], StrUtil.COLON, false);
        names[1] = StrUtil.subAfter(names[1], ttlStr, false);
        // 解析时间
        Duration duration = parseDuration(ttlStr);
        cacheConfig = cacheConfig.entryTtl(duration);
    }
    // 创建 RedisCache 对象，需要忽略掉 ttlStr
    return super.createRedisCache(names[0] + names[1], cacheConfig);
}

private Duration parseDuration(String ttlStr) {
    String timeUnit = StrUtil.subSuf(ttlStr, -1);
    switch (timeUnit) {
        case "d": return Duration.ofDays(removeDurationSuffix(ttlStr));
        case "h": return Duration.ofHours(removeDurationSuffix(ttlStr));
        case "m": return Duration.ofMinutes(removeDurationSuffix(ttlStr));
        case "s": return Duration.ofSeconds(removeDurationSuffix(ttlStr));
        default:  return Duration.ofSeconds(Long.parseLong(ttlStr));
    }
}
```

**解读**：
- **重写 `createRedisCache`** 拦截缓存创建
- 通过 `cacheName#ttl` 格式（`#` 分隔）声明 TTL
- 支持 `d` / `h` / `m` / `s` 单位
- **优雅设计**：业务方在 `@Cacheable` 中声明 TTL，无需额外配置

### 3.3 YudaoCacheProperties

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheProperties.java`
**核心代码**（节选）：

```java
@Data
@ConfigurationProperties(prefix = "yudao.cache")
public class YudaoCacheProperties {
    private String keyPrefix;
    private Integer redisScanBatchSize = 30;
}
```

## 4. 关键要点总结

- **yudao Redis Starter = Spring Data Redis + Redisson + 大量增强**
- **自定义 `RedisTemplate`**：Key=String, Value=JSON
- **`TimeoutRedisCacheManager`** 通过 `cacheName#ttl` 语法声明 TTL
- **多租户**通过 `TenantRedisCacheManager` 实现 Key 前缀隔离
- **`RedisUtils` 工具类**封装 90% 常用操作

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中使用 `redisUtils.set("user:1", userDO, Duration.ofMinutes(10))`，然后用 Redis CLI 查看实际存储格式。

### 练习 2：进阶

在 `@Cacheable` 中用 `cacheNames = "order#5m"`，观察 Redis 中 key 的过期时间。

### 练习 3：挑战（选做）

> 学完 [缓存三大问题](../../_common/03-cache-patterns/02-three-problems.md) 与 [17-distributed-lock](./17-distributed-lock.md) 后再做：实现"缓存击穿保护"：当缓存失效瞬间，**只有一个线程**能查 DB，其他线程等待。提示：Redisson 的 `RLock`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
- Spring Data Redis 文档：https://docs.spring.io/spring-data/redis/docs/current/reference/html/
- Redisson 文档：https://github.com/redisson/redisson

---

**文档版本**：v1.0
**最后更新**：2026-07-13
