# 3.2 Redisson 客户端

> 掌握 Redisson 的核心功能，能在 yudao 中使用 Redisson 实现分布式锁和分布式集合。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redisson 与 Jedis/Lettuce 的差异
- 掌握 Redisson 的核心数据结构（RLock、RMap、RQueue）
- 能在 yudao 中使用 Redisson
- 了解 Redisson 的发布/订阅与流式 API

## 📚 前置知识

- [14-redis-starter.md](./14-redis-starter.md)
- Redis 基础命令
- 分布式系统基础

## 1. 核心概念

### 1.1 Redisson 是什么？

**Redisson** 是 Redis 客户端，提供**分布式对象**、**分布式集合**、**分布式锁**等高级 API。yudao 同时使用：
- **Spring Data Redis**（RedisTemplate）— 普通 KV
- **Redisson**（RedissonClient）— 高级特性

### 1.2 Redisson vs Jedis vs Lettuce

| 客户端 | 线程安全 | 性能 | 分布式特性 |
|--------|---------|------|-----------|
| Jedis | 不安全 | 一般 | 弱 |
| Lettuce | 安全 | 高 | 弱 |
| Redisson | 安全 | 高 | 强（推荐） |

### 1.3 yudao 用 Redisson 做什么

- 分布式锁（`RLock`）
- 分布式限流（`RRateLimiter`）
- 分布式集合（`RMap`、`RList`、`RSet`）
- 分布式队列（`RQueue`、`RStream`）
- 分布式发布订阅（`RTopic`）

## 2. 代码示例

### 2.1 Redisson 基础配置

```yaml
# application.yml
spring:
  redis:
    host: localhost
    port: 6379
    password:  # 可选
    database: 0
```

Redisson 自动装配（`RedissonAutoConfigurationV2`）会基于上述配置创建 `RedissonClient`。

### 2.2 使用分布式锁

```java
@Resource
private RedissonClient redissonClient;

public void doBusiness() {
    RLock lock = redissonClient.getLock("order:create:" + orderId);
    try {
        // 尝试加锁：等待 5 秒，锁自动释放时间 30 秒
        if (lock.tryLock(5, 30, TimeUnit.SECONDS)) {
            // 业务逻辑
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    } finally {
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

### 2.3 使用分布式限流

```java
RRateLimiter limiter = redissonClient.getRateLimiter("api:user:create");
limiter.trySetRate(RateType.OVERALL, 100, 1, RateIntervalUnit.MINUTES);

if (limiter.tryAcquire()) {
    // 通过限流
} else {
    throw new ServiceException("请求过于频繁");
}
```

## 3. ruoyi 仓库源码解读

### 3.1 Redisson 自动装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/pom.xml`
**核心依赖**：

```xml
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
</dependency>
```

`@AutoConfiguration(before = RedissonAutoConfigurationV2.class)` 在 yudao 配置类中**先于** Redisson 自动装配。

### 3.2 yudao-common 中的 RedisUtils

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/redisson/RedissonUtils.java`
**核心代码**（节选）：

```java
public class RedissonUtils {

    public static <T> T get(String key) {
        return (T) RedisUtils.get(key);
    }

    public static void set(String key, Object value, Duration duration) {
        RedisUtils.set(key, value, duration);
    }

    public static <T> T getCache(String key, Class<T> clazz) {
        // ...
    }
}
```

**解读**：
- yudao 封装了**两层** Redis 操作 API：
  - `RedisUtils`（基于 RedisTemplate）— 普通 KV
  - `RedissonUtils`（基于 RedissonClient）— 高级特性
- 业务方使用工具类，不直接用底层 API

### 3.3 yudao 中的分布式锁应用

**应用场景**：防止重复提交、扣减库存、超时关单。

```java
@Service
public class OrderServiceImpl {
    @Resource
    private RedissonClient redissonClient;

    public void closeExpiredOrder(Long orderId) {
        RLock lock = redissonClient.getLock("order:close:" + orderId);
        if (lock.tryLock()) {
            try {
                // 关单逻辑
            } finally {
                lock.unlock();
            }
        }
    }
}
```

## 4. 关键要点总结

- **Redisson = Redis + 分布式对象/集合/锁**
- **yudao 同时用 Spring Data Redis + Redisson**
- **`RLock`** 是 Redisson 最常用的分布式锁（基于 Lua + Watchdog）
- **`RRateLimiter`** 实现分布式限流
- **使用方式**：注入 `RedissonClient` Bean

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中注入 `RedissonClient`，调用 `redissonClient.getKeys().getKeys()` 列出所有 key。

### 练习 2：进阶

用 `RLock` 实现一个"防止用户重复点击"功能（key = `user:click:{userId}`），TTL 5 秒。

### 练习 3：挑战（选做）

用 `RRateLimiter` 实现接口级限流（如 `/api/order/create` 限制 100 QPS）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- Redisson 官方文档：https://github.com/redisson/redisson
- Redisson 数据结构：https://github.com/redisson/redisson/wiki/8.-distributed-objects

---

**文档版本**：v1.0
**最后更新**：2026-07-13
