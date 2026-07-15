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
- Redisson 客户端（详见 [Redisson 客户端](./02-redisson.md)）
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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 限流模块入口

ruoyi 在 `yudao-spring-boot-starter-protection` 中实现了限流器，基于 Redis 但**不直接用 Redisson**。它通过 AOP + 自定义注解实现，底层用 Redis Lua 脚本保证原子性。

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/config/YudaoRateLimiterConfiguration.java`
**核心代码**（示例片段）：

```java
@AutoConfiguration
public class YudaoRateLimiterConfiguration {

    @Bean
    public RateLimiterRedisDAO rateLimiterRedisDAO(RedisTemplate<String, ?> redisTemplate) {
        return new RateLimiterRedisDAO(redisTemplate);
    }

}
```

**解读**：
- ruoyi 选择自己实现限流（而非 Redisson `RRateLimiter`），是为了能配合 `@RateLimiter` 注解 + AOP 做**声明式限流**
- 这是一种"业务优先"的设计：注解即配置，使用方零感知

### 3.2 ruoyi 限流 Redis DAO（基于 Lua 脚本）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/redis/RateLimiterRedisDAO.java`

```java
public class RateLimiterRedisDAO {
    // 核心：用 Lua 脚本在 Redis 内原子执行 INCR + EXPIRE
    // Lua 脚本略，可直接看源码
}
```

**解读**：
- ruoyi 用 Lua 脚本在 Redis 单线程内做"计数+过期"，避免竞态
- 这是和 Redisson 令牌桶**等价**的实现思路：依赖 Redis 单线程 + Lua 原子性
- 选 Redisson 还是自研？看团队是否需要注解/AOP/分布式 ID 维度等业务定制

## 4. 关键要点总结

- 限流算法：固定窗口、滑动窗口、令牌桶、漏桶
- `RRateLimiter` 是 Redisson 的令牌桶实现，`OVERALL` 是分布式限流
- `tryAcquire()` 非阻塞获取令牌，失败直接拒绝
- ruoyi 自研限流器走 AOP + Redis Lua，更适合业务声明式使用

## 5. 练习题

### 练习 1：基础（必做）

写一段代码创建 `RRateLimiter`，要求每秒最多放行 5 次。

### 练习 2：进阶

思考：为什么 ruoyi 不直接用 `RRateLimiter` 而要自研？看 `YudaoRateLimiterConfiguration` 的设计，回答以下问题：
- 注解式 vs 命令式哪个更适合 Web 场景？
- 如果让你加一个"按用户维度限流"，Redisson 和 ruoyi 方案哪个更容易？

### 练习 3：挑战（选做）

用 `RRateLimiter` 实现"验证码 1 分钟只能发 1 次"，key 用手机号作为后缀。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/config/YudaoRateLimiterConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/redis/RateLimiterRedisDAO.java`
- Redisson 限流文档：https://redisson.org/docs/data-and-services/rate-limiter/

---

**文档版本**：v1.0
**最后更新**：2026-07-13