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
- Redisson 客户端（详见 [Redisson 客户端](./01-redisson.md)）
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

## 3. 关键要点总结

- ruoyi 通过 `YudaoRedisAutoConfiguration` 自定义 `RedisTemplate`（String KEY + JSON VALUE）
- `TimeoutRedisCacheManager` 让 `@Cacheable("name#30m")` 自定义 TTL 生效
- `CacheUtils` 基于 Guava 提供异步刷新本地缓存，单 JVM 高性能
- 业务层直接注入 `RedisTemplate` 即可使用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
