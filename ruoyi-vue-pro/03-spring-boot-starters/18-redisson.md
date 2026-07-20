# 3.2 Redisson 客户端

> 掌握 Redisson 的核心功能，能在 yudao 中使用 Redisson 实现分布式锁和分布式集合。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redisson 与 Jedis/Lettuce 的差异
- 掌握 Redisson 的核心数据结构（RLock、RMap、RQueue）
- 能在 yudao 中使用 Redisson
- 了解 Redisson 的发布/订阅与流式 API

## 📚 前置知识

- [17-redis-starter.md](./17-redis-starter.md)
- Redis 基础命令（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 分布式系统基础

## 1. 核心概念

### 1.1 Redisson 是什么？

**Redisson** 是 Redis 客户端，提供**分布式对象**、**分布式集合**、**分布式锁**等高级 API（分布式锁见 [17-distributed-lock](./20-distributed-lock.md) / [Redis Redlock](../../_common/04-distributed-locks/02-redis-redlock.md)）。yudao 同时使用：
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

## 3. 关键要点总结

- **Redisson = Redis + 分布式对象/集合/锁**
- **yudao 同时用 Spring Data Redis + Redisson**
- **`RLock`** 是 Redisson 最常用的分布式锁（基于 Lua + Watchdog）
- **`RRateLimiter`** 实现分布式限流
- **使用方式**：注入 `RedissonClient` Bean

---

**文档版本**：v1.0
**最后更新**：2026-07-13
