# 6.5 接口保护：Sentinel 限流

> 掌握 yudao 接口保护（限流、熔断、幂等、分布式锁）的实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao-starter-protection 的 4 大能力
- 理解 Sentinel 流控与熔断
- 能用 `@RateLimiter`、`@Idempotent` 等注解
- 了解 lock4j 分布式锁

## 📚 前置知识

- [20-distributed-lock.md](./20-distributed-lock.md)
- [21-rate-limiter.md](./21-rate-limiter.md)
- 限流算法见 [限流](../../_common/03-cache-patterns/04-rate-limiting.md)
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

## 3. 关键要点总结

- **yudao 提供 4 种接口保护能力**
- **`@RateLimiter`** 用 Redisson 令牌桶
- **`@Idempotent`** 用 Redis SETNX
- **`@Lock4j`** 用 Redisson 分布式锁
- **`@ApiSignature`** 用 HMAC 签名

---

**文档版本**：v1.0
**最后更新**：2026-07-13
