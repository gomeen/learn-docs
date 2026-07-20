# 1.4 Redisson 限流：RRateLimiter

> 理解分布式限流的常见算法，掌握 Redisson `RRateLimiter` 的使用方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解令牌桶、漏桶、固定窗口、滑动窗口四种限流算法
- 掌握 Redisson `RRateLimiter` 的核心 API
- 能区分单机限流和分布式限流的差异
- 能用 `RRateLimiter` 在 ruoyi 中实现 API 限流

## 📚 前置知识

- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- Redisson 客户端（详见 [Redisson 客户端](./01-redisson.md)）
- 限流算法通用原理（详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）

## 1. 核心概念

### 1.1 为什么需要限流？

限流（Rate Limiting）是保护系统不被突发流量打垮的手段：
- **防刷**：接口被恶意调用时只放行一定 QPS
- **降级**：超过阈值直接拒绝，保护下游
- **平滑**：把突发流量整形为匀速，避免数据库被打爆

### 1.2 四种限流算法对比

| 算法 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| 固定窗口 | 1 秒内最多 N 次 | 简单 | 窗口边界突刺 |
| 滑动窗口 | 多个小窗口加权 | 平滑 | 存储开销 |
| 令牌桶 | 固定速率放令牌 | 支持突发 | 实现复杂 |
| 漏桶 | 匀速漏水（处理） | 平滑输出 | 无法应对突发 |

### 1.3 Redisson `RRateLimiter`

Redisson 内置**令牌桶**算法的分布式限流器，参数：
- `rate`：每秒生成多少个令牌
- `interval`：多长时间生成一批令牌

`tryAcquire()`：非阻塞获取令牌，拿到就放行，拿不到就拒绝。

## 2. 代码示例

### 2.1 创建限流器

```java
// 文件：RateLimiterDemo.java
import org.redisson.api.RRateLimiter;
import org.redisson.api.RateIntervalUnit;
import org.redisson.api.RateType;
import org.redisson.api.RedissonClient;
import javax.annotation.Resource;
import org.springframework.stereotype.Service;

@Service
public class RateLimiterDemo {

    @Resource
    private RedissonClient redissonClient;

    public boolean tryAcquire() {
        // 获取限流器
        RRateLimiter limiter = redissonClient.getRateLimiter("rate:api:sms");
        // 设置速率：每秒 10 个令牌
        limiter.trySetRate(RateType.OVERALL, 10, 1, RateIntervalUnit.SECONDS);
        // 尝试获取 1 个令牌
        return limiter.tryAcquire(1);
    }
}
```

### 2.2 三种 RateType

```java
// OVERALL：整个集群共享同一个令牌桶（分布式限流）
limiter.trySetRate(RateType.OVERALL, 10, 1, RateIntervalUnit.SECONDS);

// PER_CLIENT：每个 RedissonClient 实例独立的桶（单机限流）
limiter.trySetRate(RateType.PER_CLIENT, 10, 1, RateIntervalUnit.SECONDS);
```

### 2.3 在 Controller 中使用

```java
@RestController
public class SmsController {

    @Resource
    private RedissonClient redissonClient;

    @PostMapping("/sms/send")
    public String send(@RequestParam String phone) {
        RRateLimiter limiter = redissonClient.getRateLimiter("rate:sms:" + phone);
        limiter.trySetRate(RateType.OVERALL, 1, 60, RateIntervalUnit.SECONDS); // 每 60 秒 1 次
        if (!limiter.tryAcquire()) {
            return "请稍后再试";
        }
        // 发短信业务
        return "已发送";
    }
}
```

## 3. 关键要点总结

- 限流算法：固定窗口、滑动窗口、令牌桶、漏桶
- `RRateLimiter` 是 Redisson 的令牌桶实现，`OVERALL` 是分布式限流
- `tryAcquire()` 非阻塞获取令牌，失败直接拒绝
- ruoyi 自研限流器走 AOP + Redis Lua，更适合业务声明式使用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
