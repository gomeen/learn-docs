# 1.7 ruoyi 的 RedisUtils 工具类

> 介绍 ruoyi 在 Redis 抽象层的核心工具类与配置，掌握业务层如何使用 Redis。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 通过 `RedisTemplate` + JSON 序列化使用 Redis
- 了解 `TimeoutRedisCacheManager` 的自定义过期能力
- 掌握 `CacheUtils` 的本地缓存使用
- 在 ruoyi 业务代码中正确使用 Redis

## 📚 前置知识

- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- Redisson 客户端（详见 [Redisson 客户端](./02-redisson.md)）
- Spring Data Redis / Spring Cache（详见 [Spring Cache 抽象](./08-spring-cache.md)）

## 1. 核心概念

### 1.1 ruoyi 的 Redis 抽象层

ruoyi 没有提供业务层的 `RedisUtils`（像 Hutool 那样），而是直接用 Spring Data Redis 的 `RedisTemplate`。ruoyi 在框架层做的事：
1. **配置 RedisTemplate**：JSON 序列化 + String key
2. **扩展 RedisCacheManager**：支持自定义过期时间（与 Spring Cache 后端配置详见 [Redis 作为 Spring Cache 后端](./10-spring-cache-redis.md)）
3. **提供本地缓存工具**：用于不跨 JVM 的高速缓存

### 1.2 业务层调用方式

```java
@Resource
private RedisTemplate<String, Object> redisTemplate;

redisTemplate.opsForValue().set("name", "yudao");
redisTemplate.opsForHash().putAll("user:1", map);
redisTemplate.opsForValue().increment("article:1:view");
```

## 2. 代码示例

### 2.1 RedisTemplate 基本用法

```java
// 文件：RedisTemplateDemo.java
import org.springframework.data.redis.core.RedisTemplate;
import javax.annotation.Resource;
import org.springframework.stereotype.Service;
import java.time.Duration;

@Service
public class RedisTemplateDemo {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    public void demo() {
        // String
        redisTemplate.opsForValue().set("name", "yudao", Duration.ofMinutes(10));
        String name = (String) redisTemplate.opsForValue().get("name");

        // Hash
        redisTemplate.opsForHash().put("user:1", "name", "yudao");
        Object userName = redisTemplate.opsForHash().get("user:1", "name");

        // 原子自增
        Long count = redisTemplate.opsForValue().increment("view:1");
    }
}
```

### 2.2 本地缓存 CacheUtils

```java
// 文件：LocalCacheDemo.java
import cn.iocoder.yudao.framework.common.util.cache.CacheUtils;
import com.google.common.cache.CacheLoader;
import java.time.Duration;

public class LocalCacheDemo {
    public static void demo() throws Exception {
        var cache = CacheUtils.buildAsyncReloadingCache(
                Duration.ofMinutes(5),
                new CacheLoader<String, String>() {
                    @Override
                    public String load(String key) {
                        return "loaded-" + key;
                    }
                });
        System.out.println(cache.get("k1"));
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 RedisTemplate 自定义序列化

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
**核心代码**（行 22-36）：

```java
@Bean
public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
    // 创建 RedisTemplate 对象
    RedisTemplate<String, Object> template = new RedisTemplate<>();
    // 设置 RedisConnection 工厂。😈 它就是实现多种 Java Redis 客户端接入的秘密工厂。感兴趣的胖友，可以自己去撸下。
    template.setConnectionFactory(factory);
    // 使用 String 序列化方式，序列化 KEY 。
    template.setKeySerializer(RedisSerializer.string());
    template.setHashKeySerializer(RedisSerializer.string());
    // 使用 JSON 序列化方式，序列化 VALUE
    RedisSerializer<?> redisSerializer = buildRedisSerializer();
    template.setValueSerializer(redisSerializer);
    template.setHashValueSerializer(redisSerializer);
    return template;
}
```

**解读**：
- 第 28 行：KEY 序列化为 String，Redis 里可读（避免 JDK 序列化的 `\xac\xed` 前缀）
- 第 33 行：VALUE 用 JSON 序列化，对象可读、可跨语言
- 这套配置是 ruoyi 与 Spring Boot 默认 `RedisTemplate` 的最大差异

### 3.2 自定义过期 RedisCacheManager

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
        // 移除 # 后面的 : 以及后面的内容，避免影响解析
        String ttlStr = StrUtil.subBefore(names[1], StrUtil.COLON, false); // 获得 ttlStr 时间部分
        names[1] = StrUtil.subAfter(names[1], ttlStr, false); // 移除掉 ttlStr 时间部分
        // 解析时间
        Duration duration = parseDuration(ttlStr);
        cacheConfig = cacheConfig.entryTtl(duration);
    }

    // 创建 RedisCache 对象，需要忽略掉 ttlStr
    return super.createRedisCache(names[0] + names[1], cacheConfig);
}
```

**解读**：
- ruoyi 自定义 cacheManager 让 `@Cacheable(cacheNames = "user#30m")` 这种写法生效：缓存名 `user`、过期 30 分钟
- 第 34 行：用 `#` 分隔缓存名和过期时间
- 第 47 行：覆盖原配置，注入新的 TTL
- **设计意图**：让 `@Cacheable` 既支持注解默认 TTL，又支持"特定 key 用特定 TTL"

### 3.3 本地缓存工具类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`
**核心代码**（行 37-44）：

```java
public static <K, V> LoadingCache<K, V> buildAsyncReloadingCache(Duration duration, CacheLoader<K, V> loader) {
    return CacheBuilder.newBuilder()
            .maximumSize(CACHE_MAX_SIZE)
            // 只阻塞当前数据加载线程，其他线程返回旧值
            .refreshAfterWrite(duration)
            // 通过 asyncReloading 实现全异步加载，包括 refreshAfterWrite 被阻塞的加载线程
            .build(CacheLoader.asyncReloading(loader, Executors.newCachedThreadPool())); // TODO 芋艿：可能要思考下，未来要不要做成可配置
}
```

**解读**：
- 第 39 行：最大 10000 条，超出按 LRU 淘汰
- 第 41 行：`refreshAfterWrite` 在写入 N 时间后下次访问异步刷新
- 第 43 行：`asyncReloading` 让刷新在独立线程进行，避免阻塞读线程
- **适用场景**：和"人/线程"无关的全局缓存，如字典项

## 4. 关键要点总结

- ruoyi 通过 `YudaoRedisAutoConfiguration` 自定义 `RedisTemplate`（String KEY + JSON VALUE）
- `TimeoutRedisCacheManager` 让 `@Cacheable("name#30m")` 自定义 TTL 生效
- `CacheUtils` 基于 Guava 提供异步刷新本地缓存，单 JVM 高性能
- 业务层直接注入 `RedisTemplate` 即可使用

## 5. 练习题

### 练习 1：基础（必做）

写代码：用 `redisTemplate.opsForValue()` 存一个 10 分钟过期的字符串，再读取。

### 练习 2：进阶

阅读 `TimeoutRedisCacheManager.createRedisCache`，解释 `cacheNames = "user#30m"` 的完整解析过程：
1. `#` 分隔后 parts 是？
2. TTL 是？
3. 实际缓存名是？

### 练习 3：挑战（选做）

用 `CacheUtils.buildAsyncReloadingCache` 实现"字典项缓存"：key = dictType，value = list。TTL 5 分钟。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13