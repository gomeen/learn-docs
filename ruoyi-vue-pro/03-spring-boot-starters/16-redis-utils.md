# 3.3 Redis 工具类：RedisUtils / RedisLockUtils

> 掌握 yudao 封装的 Redis 工具类，能用工具类完成 90% 的 Redis 操作。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `RedisUtils` 的所有常用方法
- 理解 `RedisLockUtils` 的分布式锁实现
- 了解 `RedissonUtils` 的高级特性封装
- 能用工具类完成常见缓存场景

## 📚 前置知识

- [14-redis-starter.md](./14-redis-starter.md)
- [15-redisson.md](./15-redisson.md)
- Java 泛型基础（详见 [03-generics](../01-java-fundamentals/03-generics.md)）
- 分布式锁工具见 [17-distributed-lock](./17-distributed-lock.md)

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

## 3. ruoyi 仓库源码解读

### 3.1 RedisUtils 的实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/redis/RedisUtils.java`
**核心代码**（节选）：

```java
public class RedisUtils {

    private RedisTemplate<String, Object> redisTemplate;

    public RedisUtils() {
        this.redisTemplate = SpringUtils.getBean("redisTemplate", RedisTemplate.class);
    }

    public <T> T get(String key, Class<T> clazz) {
        Object value = redisTemplate.opsForValue().get(key);
        return parseValue(value, clazz);
    }

    public void set(String key, Object value, Duration duration) {
        redisTemplate.opsForValue().set(key, value, duration);
    }

    public Long incr(String key, Long delta) {
        return redisTemplate.opsForValue().increment(key, delta);
    }

    public void delete(String key) {
        redisTemplate.delete(key);
    }

    @SuppressWarnings("unchecked")
    private <T> T parseValue(Object value, Class<T> clazz) {
        if (value == null) return null;
        if (clazz.isInstance(value)) return (T) value;
        // 如果类型不匹配，反序列化
        if (value instanceof String) {
            return JsonUtils.parseObject((String) value, clazz);
        }
        return (T) value;
    }
}
```

**解读**：
- 通过 `SpringUtils.getBean` 获取 `RedisTemplate`（**非注入**，更灵活）
- `parseValue` 处理**反序列化异常**——Redis 中的 String 类型与目标类型不匹配时用 JSON 反序列化
- 所有方法都是 `static` 风格的工具方法（实际是实例方法但通过 `SpringUtils` 拿 Bean）

### 3.2 RedisLockUtils

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/redis/RedisLockUtils.java`
**核心代码**（节选）：

```java
public class RedisLockUtils {
    @Resource
    private RedissonClient redissonClient;

    public <T> T executeWithLock(String lockKey, Supplier<T> supplier, long waitTime, long leaseTime) {
        RLock lock = redissonClient.getLock(lockKey);
        try {
            if (lock.tryLock(waitTime, leaseTime, TimeUnit.SECONDS)) {
                return supplier.get();
            }
            throw new ServiceException("获取锁失败");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ServiceException("加锁被中断");
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

**解读**：
- 用 `Supplier<T>` 封装"加锁后执行的逻辑"
- 返回值泛型，**调用方不用关心锁释放**
- 自动 try-finally 释放

### 3.3 CacheUtils（二级缓存）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`
**核心代码**（节选）：

```java
public class CacheUtils {
    private static final Cache<String, Object> LOCAL_CACHE = Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(1))
            .build();

    public static <T> T get(String key, Class<T> clazz, Supplier<T> loader, Duration redisTtl) {
        // 1. 查本地缓存
        T value = (T) LOCAL_CACHE.getIfPresent(key);
        if (value != null) return value;

        // 2. 查 Redis
        value = RedisUtils.get(key, clazz);
        if (value != null) {
            LOCAL_CACHE.put(key, value);
            return value;
        }

        // 3. 查 loader
        value = loader.get();
        if (value != null) {
            RedisUtils.set(key, value, redisTtl);
            LOCAL_CACHE.put(key, value);
        }
        return value;
    }
}
```

**解读**：
- **L1 = Caffeine（本地）** → **L2 = Redis（分布式）** → **DB**
- 大幅减少 Redis 访问，提升性能
- 本地缓存 1 分钟过期

## 4. 关键要点总结

- **`RedisUtils`** 封装 90% 的 RedisTemplate 操作
- **`RedisLockUtils`** 用 Supplier 简化分布式锁
- **`CacheUtils`** 实现 L1 + L2 二级缓存
- **yudao 工具类都用 `SpringUtils.getBean`** 方式获取 Bean（更灵活）

## 5. 练习题

### 练习 1：基础（必做）

用 `redisUtils` 实现一个"用户登录失败次数"统计：失败 5 次锁定账户 30 分钟。

### 练习 2：进阶

用 `RedisLockUtils` 包装一个"扣减库存"方法，确保并发安全。

### 练习 3：挑战（选做）

用 `CacheUtils` 实现字典数据的二级缓存。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/redis/RedisUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/redis/RedisLockUtils.java`
- Spring Data Redis 文档：https://docs.spring.io/spring-data/redis/docs/current/reference/html/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
