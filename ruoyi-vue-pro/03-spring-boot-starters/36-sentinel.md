# 6.5 接口保护：Sentinel 限流

> 掌握 yudao 接口保护（限流、熔断、幂等、分布式锁）的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao-starter-protection 的 4 大能力
- 理解 Sentinel 流控与熔断
- 能用 `@RateLimiter`、`@Idempotent` 等注解
- 了解 lock4j 分布式锁

## 📚 前置知识

- [17-distributed-lock.md](./17-distributed-lock.md)
- [18-rate-limiter.md](./18-rate-limiter.md)
- Sentinel 基础

## 1. 核心概念

### 1.1 yudao-starter-protection 的 4 大能力

| 能力 | 组件 | 注解 |
|------|------|------|
| 分布式锁 | lock4j | `@Lock4j` |
| 限流 | Redis + Sentinel | `@RateLimiter` |
| 幂等 | Redis | `@Idempotent` |
| 接口签名 | 自研 | `@ApiSignature` |

### 1.2 限流算法

| 算法 | 特点 |
|------|------|
| 固定窗口 | 简单 |
| 滑动窗口 | 平滑 |
| 令牌桶 | 允许突发 |
| 漏桶 | 强制匀速 |

## 2. 代码示例

### 2.1 @RateLimiter 限流

```java
@PostMapping("/create")
@RateLimiter(key = "'order:create:' + #userId", time = 60, count = 10)
public CommonResult<Long> createOrder(@RequestBody OrderCreateReq req) {
    // 1 分钟内最多 10 次
}
```

### 2.2 @Idempotent 幂等

```java
@PostMapping("/pay")
@Idempotent(key = "'pay:' + #req.orderId", message = "请勿重复支付")
public CommonResult<Boolean> payOrder(@RequestBody PayReq req) {
    // 同一订单号只处理一次
}
```

### 2.3 @Lock4j 分布式锁

```java
@Service
public class OrderServiceImpl {
    @Lock4j(keys = "'stock:' + #skuId", expire = 30000, acquireTimeout = 5000)
    public void deductStock(Long skuId, Integer count) {
        // 加锁执行
    }
}
```

### 2.4 Sentinel 流控规则

```java
@GetMapping("/api/data")
@SentinelResource(value = "getData", blockHandler = "handleBlock")
public DataDTO getData() {
    return dataService.getData();
}

public DataDTO handleBlock(BlockException ex) {
    return new DataDTO("限流");
}
```

## 3. ruoyi 仓库源码解读

### 3.1 YudaoRateLimiterConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/config/YudaoRateLimiterConfiguration.java`

```java
@AutoConfiguration
public class YudaoRateLimiterConfiguration {
    @Bean
    public RateLimiterAspect rateLimiterAspect(RedissonClient redissonClient) {
        return new RateLimiterAspect(redissonClient);
    }
}
```

### 3.2 RateLimiterAspect

**核心代码**（节选）：

```java
@Aspect
@Component
public class RateLimiterAspect {
    @Around("@annotation(rateLimiter)")
    public Object around(ProceedingJoinPoint joinPoint, RateLimiter rateLimiter) throws Throwable {
        // 1. 解析 key (SpEL)
        String key = rateLimiter.key();
        // 2. 获取 RRateLimiter
        RRateLimiter limiter = redissonClient.getRateLimiter(key);
        limiter.trySetRate(RateType.OVERALL, rateLimiter.count(), rateLimiter.time(), TimeUnit.SECONDS);
        // 3. 尝试获取令牌
        if (!limiter.tryAcquire()) {
            throw new ServiceException(rateLimiter.message());
        }
        return joinPoint.proceed();
    }
}
```

### 3.3 YudaoIdempotentConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/config/YudaoIdempotentConfiguration.java`

```java
@Aspect
@Component
public class IdempotentAspect {
    @Around("@annotation(idempotent)")
    public Object around(ProceedingJoinPoint joinPoint, Idempotent idempotent) throws Throwable {
        // 1. 解析 key
        String key = idempotent.key();
        // 2. Redis SETNX
        Boolean success = redisTemplate.opsForValue().setIfAbsent(key, "1", idempotent.timeout(), TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(success)) {
            throw new ServiceException(idempotent.message());
        }
        return joinPoint.proceed();
    }
}
```

**解读**：
- 用 Redis `SETNX` 实现幂等
- **第一次**设置成功，**第二次**抛异常

### 3.4 YudaoLock4jConfiguration

```java
@AutoConfiguration
public class YudaoLock4jConfiguration {
    @Bean
    public Lock4jAspect lock4jAspect(RedissonClient redissonClient) {
        return new Lock4jAspect(redissonClient);
    }
}
```

### 3.5 YudaoApiSignatureAutoConfiguration

```java
@Aspect
@Component
public class ApiSignatureAspect {
    @Around("@annotation(apiSignature)")
    public Object around(ProceedingJoinPoint joinPoint, ApiSignature apiSignature) {
        // 1. 拿到 sign 参数
        // 2. 重新计算 sign
        // 3. 比对，不一致抛异常
    }
}
```

## 4. 关键要点总结

- **yudao 提供 4 种接口保护能力**
- **`@RateLimiter`** 用 Redisson 令牌桶
- **`@Idempotent`** 用 Redis SETNX
- **`@Lock4j`** 用 Redisson 分布式锁
- **`@ApiSignature`** 用 HMAC 签名

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中用 `@RateLimiter` 保护一个 Controller 方法，验证限流生效。

### 练习 2：进阶

用 `@Idempotent` 实现"防重复支付"功能。

### 练习 3：挑战（选做）

实现"接口签名"：客户端按规则生成 sign，服务端校验。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
- Sentinel 文档：https://sentinelguard.io/
- Redisson 文档：https://github.com/redisson/redisson

---

**文档版本**：v1.0
**最后更新**：2026-07-13
