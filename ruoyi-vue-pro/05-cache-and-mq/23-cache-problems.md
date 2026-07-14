# 4.4 缓存穿透 / 击穿 / 雪崩

> 理解缓存三大经典问题的成因和解决方案，掌握 ruoyi 的应对策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分缓存穿透、击穿、雪崩三个问题
- 掌握每种问题的典型解决方案
- 看懂 ruoyi 中相关的防护代码
- 能为自己的业务设计缓存保护策略

## 📚 前置知识

- Redis 基础（参见 `01-redis-basics.md`）
- Spring Cache（参见 `08-spring-cache.md`）
- Redisson 分布式锁（参见 `03-redisson-lock.md`）

## 1. 核心概念

### 1.1 三大问题对比

| 问题 | 现象 | 根本原因 |
|------|------|---------|
| 穿透 | 查询不存在的数据，每次都打到 DB | 缓存没有保护 |
| 击穿 | 热点 key 突然失效，瞬间大量请求打到 DB | 缓存集中失效 |
| 雪崩 | 大量 key 同时过期，DB 压力剧增 | 缓存集体失效 |

### 1.2 穿透：查不到的数据

**场景**：查询 `user:999999`（不存在的用户）
**结果**：Redis 没有 → 查 DB → DB 没有 → 返回 null → Redis 没有缓存 null
**后果**：每次请求都打 DB

**解决方案**：
- 缓存空值：`SET user:999999 "" EX 60`
- 布隆过滤器：判断 ID 是否存在

### 1.3 击穿：热点 key 失效

**场景**：明星微博热搜 key 突然过期
**后果**：瞬间大量请求打 DB

**解决方案**：
- 永不过期：逻辑过期（带时间戳）
- 分布式锁：只让一个线程查 DB
- 单飞（singleflight）：同进程内只查一次

### 1.4 雪崩：大量 key 同时失效

**场景**：所有缓存都设了 1 小时 TTL，整点集体过期
**后果**：DB 被打爆

**解决方案**：
- 过期时间加随机值：`30min + random(0, 5min)`
- 多级缓存：本地 + Redis
- 熔断降级：超出阈值返回默认值

## 2. 代码示例

### 2.1 缓存空值防穿透

```java
public User getUser(Long id) {
    User user = (User) redisTemplate.opsForValue().get("user:" + id);
    if (user != null) return user;
    user = userMapper.selectById(id);
    if (user == null) {
        // 缓存空值，TTL 短一些
        redisTemplate.opsForValue().set("user:" + id, "", Duration.ofMinutes(2));
        return null;
    }
    redisTemplate.opsForValue().set("user:" + id, user, Duration.ofHours(1));
    return user;
}
```

### 2.2 分布式锁防击穿

```java
public User getUserWithLock(Long id) {
    String key = "user:" + id;
    User user = (User) redisTemplate.opsForValue().get(key);
    if (user != null) return user;

    RLock lock = redissonClient.getLock("lock:user:" + id);
    if (lock.tryLock(5, 30, TimeUnit.SECONDS)) {
        try {
            // 双重检查
            user = (User) redisTemplate.opsForValue().get(key);
            if (user != null) return user;
            user = userMapper.selectById(id);
            redisTemplate.opsForValue().set(key, user, Duration.ofHours(1));
            return user;
        } finally {
            lock.unlock();
        }
    }
    return null; // 拿不到锁返回空
}
```

### 2.3 防雪崩：TTL 加随机

```java
public void setWithRandomTTL(String key, Object value, Duration base) {
    long random = ThreadLocalRandom.current().nextLong(60); // 0-60 秒随机
    Duration ttl = base.plusSeconds(random);
    redisTemplate.opsForValue().set(key, value, ttl);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 默认不缓存 null（防穿透）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 61-63）：

```java
if (!redisProperties.isCacheNullValues()) {
    config = config.disableCachingNullValues();
}
```

**解读**：
- ruoyi 默认**不缓存 null**：`spring.cache.redis.cache-null-values=false`
- 这是 Spring Cache 的默认行为
- 对于"查询不存在"的请求，每次都打 DB——存在**穿透风险**
- 业务层需要额外处理：`@Cacheable(unless = "#result == null")` 让不存在的也缓存（用空值）

### 3.2 ruoyi 自定义 TTL 防雪崩

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
**核心代码**（行 60-74）：

```java
private Duration parseDuration(String ttlStr) {
    String timeUnit = StrUtil.subSuf(ttlStr, -1);
    switch (timeUnit) {
        case "d":
            return Duration.ofDays(removeDurationSuffix(ttlStr));
        case "h":
            return Duration.ofHours(removeDurationSuffix(ttlStr));
        case "m":
            return Duration.ofMinutes(removeDurationSuffix(ttlStr));
        case "s":
            return Duration.ofSeconds(removeDurationSuffix(ttlStr));
        default:
            return Duration.ofSeconds(Long.parseLong(ttlStr));
    }
}
```

**解读**：
- ruoyi 支持 `@Cacheable("user#30m")` 声明精确 TTL
- 业务代码可以用 `#30m` 和 `#35m` 给同一类数据**错开 TTL**
- 这是 ruoyi 防雪崩的"惯用手法"——**业务层主动错峰**

### 3.3 ruoyi 的分布式锁防护

ruoyi 通过 `yudao-spring-boot-starter-redis` 集成 Redisson，业务层可以直接 `@Resource RedissonClient`，自行实现分布式锁防止击穿。

## 4. 关键要点总结

- 穿透：缓存空值、布隆过滤器
- 击穿：分布式锁、逻辑过期、单飞
- 雪崩：TTL 错峰、多级缓存、熔断降级
- ruoyi 默认**不缓存 null**——业务层需用 `unless` 主动缓存
- ruoyi 通过 `cacheName#ttl` 让业务主动错峰 TTL

## 5. 练习题

### 练习 1：基础（必做）

用一段代码实现"防穿透"：查询不存在的用户时，缓存空值 60 秒。

### 练习 2：进阶

阅读 `YudaoCacheAutoConfiguration` 中 `disableCachingNullValues` 的判断，思考：
- 默认不缓存 null 的好处？
- 什么场景下应该覆盖默认行为，改为缓存 null？

### 练习 3：挑战（选做）

为热门文章详情接口设计一个"防穿透+防击穿+防雪崩"的三合一方案。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/core/TimeoutRedisCacheManager.java`
- 缓存三大问题参考：https://coolshell.cn/articles/17416.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13