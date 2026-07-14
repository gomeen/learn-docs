# 34 限流与防刷

> 详解限流（Rate Limit）的原理、算法，以及 ruoyi 的限流实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握限流的 4 种算法：计数器 / 滑动窗口 / 令牌桶 / 漏桶
- 知道 ruoyi 用什么限流方案
- 能为关键接口实现限流
- 区分"限流"和"防重放"的不同

## 📚 前置知识

- Redis 基础
- 算法基础

## 1. 核心概念

### 1.1 为什么需要限流？

| 风险 | 描述 |
|------|------|
| 恶意刷接口 | 攻击者用脚本调用短信、登录等接口 |
| 突发流量 | 大促、秒杀导致系统崩溃 |
| 资源耗尽 | 大量请求耗尽 DB 连接、CPU |
| 公平性 | 防止少数用户占用所有资源 |

### 1.2 4 种限流算法

**1. 固定窗口计数器**：
```
1 秒内允许 1000 次请求
  ↓
计数器 = 0
请求 +1
  ↓
计数器 > 1000 → 拒绝
窗口结束 → 计数器 = 0
```

**2. 滑动窗口**：
```
把窗口分成多个小格
如 1 秒 = 10 个 100ms 的小格
每个小格有独立计数器
当前请求时间所在小格 = (now / 100ms) % 10
```

**3. 令牌桶**（guava RateLimiter）：
```
桶容量 100，每秒补充 10 个令牌
请求需要 1 个令牌
  ├─ 有令牌 → 放行
  └─ 无令牌 → 等待/拒绝
```

**4. 漏桶**：
```
请求先进入桶（队列）
桶以固定速率漏水（处理）
桶满 → 拒绝
```

| 算法 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| 固定窗口 | 简单 | 突发流量（边界） | 一般场景 |
| 滑动窗口 | 精确 | 实现复杂 | 精确限流 |
| 令牌桶 | 允许突发 | 需要令牌生成器 | API 限流 |
| 漏桶 | 流量整形 | 吞吐固定 | 流量整形 |

## 2. 代码示例

### 2.1 Redis 固定窗口（简单）

```java
// 文件：RateLimiter.java
public boolean tryAcquire(String key, int limit, int windowSeconds) {
    Long count = redis.opsForValue().increment("rate:" + key);
    if (count == 1) {
        redis.expire("rate:" + key, windowSeconds);
    }
    return count <= limit;
}
```

### 2.2 Redis 滑动窗口（Lua 脚本）

```lua
-- 滑动窗口 Lua 脚本
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- 删除窗口外的记录
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
-- 查当前窗口内的数量
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window)
    return 1
else
    return 0
end
```

### 2.3 注解 + AOP

```java
// 文件：RateLimiter.java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RateLimiter {
    int time() default 60;       // 时间窗口（秒）
    int count() default 100;     // 允许次数
    String key() default "";     // 限流维度
}

// 文件：RateLimiterAspect.java
@Aspect
@Component
public class RateLimiterAspect {

    @Around("@annotation(rateLimiter)")
    public Object around(ProceedingJoinPoint joinPoint, RateLimiter rateLimiter) throws Throwable {
        String key = buildKey(rateLimiter.key(), joinPoint);
        if (!tryAcquire(key, rateLimiter.count(), rateLimiter.time())) {
            throw new ServiceException("访问过于频繁，请稍后再试");
        }
        return joinPoint.proceed();
    }
}
```

## 3. ruoyi 的限流实现

### 3.1 RateLimiterAspect

ruoyi 在 `yudao-framework/yudao-spring-boot-starter-protection` 中提供限流：

```java
// 推测位置：yudao-framework/yudao-spring-boot-starter-protection/.../RateLimiterAspect.java
@Aspect
@Slf4j
public class RateLimiterAspect {

    @Resource
    private StringRedisTemplate redisTemplate;

    @Around("@annotation(rateLimiter)")
    public Object around(ProceedingJoinPoint joinPoint, RateLimiter rateLimiter) throws Throwable {
        // 1. 解析限流 key
        String key = parseKey(joinPoint, rateLimiter);

        // 2. 用 Lua 脚本实现原子限流
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptText(LUA_SCRIPT);
        script.setResultType(Long.class);

        Long result = redisTemplate.execute(script, Collections.singletonList(key),
                rateLimiter.count(), rateLimiter.time());

        // 3. result = 1 放行，= 0 拒绝
        if (result == 0) {
            throw new ServiceException("访问过于频繁");
        }
        return joinPoint.proceed();
    }
}
```

### 3.2 用法示例

```java
// 文件：AuthController.java
@PostMapping("/sms-login")
@PermitAll
@Operation(summary = "使用短信验证码登录")
// 60 秒内最多 6 次
@RateLimiter(time = 60, count = 6, keyResolver = ExpressionRateLimiterKeyResolver.class, keyArg = "#reqVO.mobile")
public CommonResult<AuthLoginRespVO> smsLogin(@RequestBody @Valid AuthSmsLoginReqVO reqVO) {
    return success(authService.smsLogin(reqVO));
}
```

**关键**：`keyArg = "#reqVO.mobile"` — 按手机号限流（不同手机号独立计数）

### 3.3 KeyResolver 策略

ruoyi 提供多种 `KeyResolver`：
- `DefaultRateLimiterKeyResolver`：按 IP
- `ExpressionRateLimiterKeyResolver`：按 SpEL 表达式
- `UserRateLimiterKeyResolver`：按登录用户

## 4. 关键要点总结

- 限流 4 种算法：固定窗口、滑动窗口、令牌桶、漏桶
- ruoyi 用 Redis + Lua 脚本实现（**原子性**）
- 支持 3 种 KeyResolver：IP / SpEL / User
- 关键 API 必须限流：登录、短信、支付
- 限流和防重放的区别：限流是"频次"控制，防重放是"重复"控制

## 5. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`（注释中提到 RateLimiter）
- Redis Lua 脚本：https://redis.io/docs/manual/programmability/eval-intro/
- guava RateLimiter：https://guava.dev/releases/19.0/api/docs/com/google/common/util/concurrent/RateLimiter.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
