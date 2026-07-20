# 3.5 限流：RRateLimiter

> 掌握 Redisson 分布式限流器的使用，能在 yudao 中实现各种限流场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解限流的核心算法（令牌桶、漏桶、固定窗口、滑动窗口）
- 掌握 Redisson `RRateLimiter` 的用法
- 能在 yudao 中实现接口级、用户级、IP 级限流
- 了解 Sentinel 等更专业的限流组件

## 📚 前置知识

- [18-redisson.md](./18-redisson.md)
- 限流算法基础（详见 [限流](../../_common/03-cache-patterns/04-rate-limiting.md)）

## 1. 核心概念

### 1.1 常见限流算法

> 📌 **Sighting**：更专业的接口保护见 [36-sentinel](./44-sentinel.md)。限流算法详见前置知识中的 `_common` 链接。

| 算法 | 特点 | 适用场景 |
|------|------|---------|
| 固定窗口 | 简单，可能有"双倍突发" | 简单 QPS 限制 |
| 滑动窗口 | 平滑，复杂 | 平滑限流 |
| 令牌桶 | 允许突发，平滑限流 | API 限流（最常用） |
| 漏桶 | 强制匀速 | 流量整形 |

### 1.2 Redisson 的 RRateLimiter

Redisson 用**令牌桶**算法实现分布式限流：

```java
RRateLimiter limiter = redissonClient.getRateLimiter("key");
limiter.trySetRate(RateType.OVERALL, 100, 1, RateIntervalUnit.SECONDS);
// 总速率：100 个/秒
boolean ok = limiter.tryAcquire();  // 尝试获取 1 个令牌
```

## 2. 代码示例

### 2.1 基础限流

```java
@Resource
private RedissonClient redissonClient;

public void doApi() {
    RRateLimiter limiter = redissonClient.getRateLimiter("api:demo");
    // 设置速率：100 个/秒
    limiter.trySetRate(RateType.OVERALL, 100, 1, RateIntervalUnit.SECONDS);

    if (limiter.tryAcquire()) {
        // 执行业务
    } else {
        throw new ServiceException("请求过于频繁");
    }
}
```

### 2.2 每次获取多个令牌

```java
// 一次获取 5 个令牌
if (limiter.tryAcquire(5)) {
    // 业务
}

// 限时等待：等待 1 秒，1 秒内获取不到则失败
if (limiter.tryAcquire(1, 1, TimeUnit.SECONDS)) {
    // 业务
}
```

### 2.3 PerClient 模式

```java
// 每个客户端独立限流（适合按用户/IP）
RRateLimiter limiter = redissonClient.getRateLimiter("api:user:" + userId);
limiter.trySetRate(RateType.PER_CLIENT, 10, 1, RateIntervalUnit.MINUTES);
// 每个用户每分钟 10 次
```

## 3. 关键要点总结

- **`RRateLimiter` = Redis + Lua + 令牌桶**
- **`OVERALL` 全局限流** vs **`PER_CLIENT` 单客户端限流**
- **`tryAcquire()`** 非阻塞获取令牌
- **`tryAcquire(timeout)`** 阻塞等待
- **yudao 自研 `@RateLimiter` 注解**用起来更简洁

---

**文档版本**：v1.0
**最后更新**：2026-07-13
