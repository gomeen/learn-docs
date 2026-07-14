# 3.5 限流：RRateLimiter

> 掌握 Redisson 分布式限流器的使用，能在 yudao 中实现各种限流场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解限流的核心算法（令牌桶、漏桶、固定窗口、滑动窗口）
- 掌握 Redisson `RRateLimiter` 的用法
- 能在 yudao 中实现接口级、用户级、IP 级限流
- 了解 Sentinel 等更专业的限流组件

## 📚 前置知识

- [15-redisson.md](./15-redisson.md)
- 限流算法基础

## 1. 核心概念

### 1.1 常见限流算法

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

## 3. ruoyi 仓库源码解读

### 3.1 yudao 中的限流应用

yudao-starter-protection 提供了更完整的限流方案（基于 `lock4j` 和自定义注解），但底层也使用 Redisson。

**应用 1：登录接口限流**

```java
@PostMapping("/login")
public CommonResult<LoginRespVO> login(@RequestBody LoginReqVO req) {
    RRateLimiter limiter = redissonClient.getRateLimiter("login:" + req.getUsername());
    limiter.trySetRate(RateType.PER_CLIENT, 5, 1, RateIntervalUnit.MINUTES);
    if (!limiter.tryAcquire()) {
        return CommonResult.error("尝试次数过多，请 1 分钟后再试");
    }
    // 登录逻辑
}
```

**应用 2：短信验证码**

```java
public void sendSmsCode(String phone) {
    RRateLimiter limiter = redissonClient.getRateLimiter("sms:" + phone);
    limiter.trySetRate(RateType.PER_CLIENT, 1, 1, RateIntervalUnit.MINUTES);
    if (!limiter.tryAcquire()) {
        throw new ServiceException("请勿频繁发送短信");
    }
    // 发送逻辑
}
```

### 3.2 yudao 的限流 starter（更专业方案）

yudao-starter-protection 提供了 `@RateLimiter` 注解：

```java
// 通过 yudao 自研注解
@RateLimiter(key = "user:create", time = 60, count = 10)
public CommonResult<Long> createUser(UserSaveReqVO req) {
    // 自动限流
}
```

底层实现位于 `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/`。

## 4. 关键要点总结

- **`RRateLimiter` = Redis + Lua + 令牌桶**
- **`OVERALL` 全局限流** vs **`PER_CLIENT` 单客户端限流**
- **`tryAcquire()`** 非阻塞获取令牌
- **`tryAcquire(timeout)`** 阻塞等待
- **yudao 自研 `@RateLimiter` 注解**用起来更简洁

## 5. 练习题

### 练习 1：基础（必做）

用 `RRateLimiter` 实现"短信发送"限流：每个手机号 1 分钟内最多 1 次。

### 练习 2：进阶

实现"用户注册"接口的 IP 级限流：每个 IP 每小时最多注册 5 个账号。

### 练习 3：挑战（选做）

实现"令牌桶 + 漏桶"的混合限流：突发 1000 个请求后，每秒最多处理 100 个。

## 6. 参考资料

- Redisson 限流：https://github.com/redisson/redisson/wiki/6.-distributed-primitives/#67-rate-limiter
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/`
- Sentinel 限流：https://sentinelguard.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
