# 3.4 限流算法：固定窗口 / 滑动窗口 / 令牌桶 / 漏桶

> 理解四种核心限流算法的原理、实现和适用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分四种限流算法的核心思想
- 用 Redis 实现每种限流算法
- 根据业务场景选择合适的算法
- 在 dify 中识别限流的应用

## 📚 前置知识

- Redis ZSet / List 数据结构
- 多线程与并发基础
- HTTP API 设计基础

## 1. 核心概念

### 1.1 为什么需要限流？

**限流（Rate Limiting）**：限制单位时间内允许的请求数。

**作用**：
- **保护下游**：防止 DB / 第三方 API 被瞬时打爆
- **公平分配**：防止单个用户占用所有资源
- **成本控制**：限制 API 调用次数（云服务按调用计费）

### 1.2 四大限流算法

#### 1.2.1 固定窗口（Fixed Window）

**原理**：把时间分成固定大小的窗口（如 1 分钟），每个窗口内计数器累加。

```
[0:00-0:01]  counter=0,1,2,...,99,100 → 100 次通过
[0:01-0:02]  counter=0,1,2,...,99,100 → 100 次通过
```

**实现**：Redis `INCR` + `EXPIRE`

**优点**：实现最简单
**缺点**：**窗口边界突刺**——0:59:59 通过 100 次 + 1:00:01 通过 100 次 = 2 秒内 200 次

#### 1.2.2 滑动窗口（Sliding Window）

**原理**：把大窗口拆成多个小窗口，统计最近 N 个小窗口的总数。

```
[0:00-0:01] 60 次
[0:01-0:02] 60 次
当前时间 0:02:30，统计最近 1 分钟 = 60 + 60 = 120 次
```

**实现**：Redis Sorted Set（member=请求 ID，score=时间戳）

**优点**：更精确，避免边界突刺
**缺点**：存储开销大（每个请求一条记录）

#### 1.2.3 令牌桶（Token Bucket）

**原理**：桶里按固定速率放令牌，每个请求消耗一个令牌。桶满则丢弃令牌。

```
速率 r=10/s，桶容量 burst=20
- 每 100ms 放一个令牌到桶
- 请求消耗一个令牌，桶空则拒绝
- 允许突发（最多 burst 个请求瞬时通过）
```

**实现**：Redis 存储 `(tokens, last_refill_time)`

**优点**：允许突发流量，平滑限流
**缺点**：参数调优复杂（r 和 burst）

#### 1.2.4 漏桶（Leaky Bucket）

**原理**：桶以固定速率漏水（处理请求），请求进入桶排队，桶满则拒绝。

```
速率 r=10/s，桶容量 burst=20
- 请求进入桶排队
- 桶以 10/s 的速率漏水（处理）
- 桶满（超过 20 个等待）则拒绝
```

**实现**：Redis List 做队列

**优点**：强制平滑流量（不允许突发）
**缺点**：无法应对突发（如秒杀）

### 1.3 算法对比

| 维度 | 固定窗口 | 滑动窗口 | 令牌桶 | 漏桶 |
|------|---------|---------|--------|------|
| 精确度 | 低 | 高 | 高 | 高 |
| 允许突发 | 是 | 是 | 是 | 否 |
| 实现复杂度 | 低 | 中 | 中 | 中 |
| 适用场景 | 简单限流 | API 配额 | API 网关 | 流量整形 |

## 2. 代码示例

### 2.1 固定窗口（Redis INCR）

```python
# 文件：example_fixed_window.py
import redis
import time

r = redis.Redis(host="localhost", port=6379)

def is_allowed_fixed_window(user_id: str, limit: int = 100, window: int = 60) -> bool:
    """固定窗口：每用户每分钟最多 100 次"""
    # 用当前时间戳作为窗口 key
    current_window = int(time.time()) // window
    key = f"rate_limit:{user_id}:{current_window}"

    # INCR 并设置过期（首次调用时设置）
    count = r.incr(key)
    if count == 1:
        r.expire(key, window)

    return count <= limit


# 测试
for i in range(150):
    if is_allowed_fixed_window("user-001", limit=100):
        print(f"[{i}] 通过")
    else:
        print(f"[{i}] 限流")
```

### 2.2 滑动窗口（Redis ZSet）

```python
# 文件：example_sliding_window.py
import redis
import time
import uuid

r = redis.Redis(host="localhost", port=6379)


def is_allowed_sliding_window(user_id: str, limit: int = 100, window: int = 60) -> bool:
    """滑动窗口：精确到秒"""
    key = f"sliding:{user_id}"
    now = time.time()
    cutoff = now - window    # 时间窗口起点

    # 1. 删除窗口外的记录
    r.zremrangebyscore(key, 0, cutoff)

    # 2. 统计当前窗口内的请求数
    count = r.zcard(key)

    if count < limit:
        # 3. 通过则记录
        r.zadd(key, {f"{now}-{uuid.uuid4()}": now})
        r.expire(key, window)
        return True

    return False


# 测试
for i in range(150):
    if is_allowed_sliding_window("user-001", limit=100, window=60):
        print(f"[{i}] 通过")
    else:
        print(f"[{i}] 限流")
```

### 2.3 令牌桶（Lua 脚本）

```python
# 文件：example_token_bucket.py
import redis
import time

r = redis.Redis(host="localhost", port=6379)

# Lua 脚本保证令牌桶原子性
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])         -- 每秒放入令牌数
local capacity = tonumber(ARGV[2])     -- 桶容量
local now = tonumber(ARGV[3])          -- 当前时间（秒）
local requested = tonumber(ARGV[4])    -- 请求消耗令牌数

local data = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(data[1])
local last_refill = tonumber(data[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

-- 按时间差补充令牌
local elapsed = now - last_refill
tokens = math.min(capacity, tokens + elapsed * rate)

-- 判断是否允许
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return 1   -- 允许
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return 0   -- 限流
end
"""


def is_allowed_token_bucket(user_id: str, rate: float = 10, capacity: int = 20) -> bool:
    """令牌桶：每秒 10 个令牌，桶容量 20"""
    key = f"token_bucket:{user_id}"
    result = r.eval(TOKEN_BUCKET_SCRIPT, 1, key, rate, capacity, time.time(), 1)
    return result == 1


# 测试突发流量
for i in range(30):
    if is_allowed_token_bucket("user-001", rate=10, capacity=20):
        print(f"[{i}] 通过")
    else:
        print(f"[{i}] 限流")
# 前 20 个通过（用尽令牌），后续限流
# 1 秒后会有 ~10 个令牌补充
```

### 2.4 常见错误：限流粒度太粗

```python
# ❌ 反例：全局限流（不分用户）
def global_rate_limit():
    count = r.incr("api:global:count")
    return count <= 10000

# 问题：1 个用户消耗完所有配额，其他用户都进不来

# ✅ 正例：按用户 ID 限流
def per_user_rate_limit(user_id):
    return is_allowed_sliding_window(user_id, limit=100)
```

## 3. dify 仓库源码解读

### 3.1 dify 的限流配置（knowledge_rate_limit）

**文件位置**：`/Users/xu/code/github/dify/api/services/feature_service.py`
**核心代码**（行 132-149）：

```python
class FeatureModel(FeatureResponseModel):
    billing: BillingModel = BillingModel()
    education: EducationModel = EducationModel()
    members: LimitationModel = LimitationModel(size=0, limit=1)
    apps: LimitationModel = LimitationModel(size=0, limit=10)
    vector_space: LimitationModel | None = LimitationModel(size=0, limit=5)
    knowledge_rate_limit: int = 10      # ← 知识库限流
    annotation_quota_limit: LimitationModel = LimitationModel(size=0, limit=10)
    documents_upload_quota: LimitationModel = LimitationModel(size=0, limit=50)
    docs_processing: str = "standard"
```

**解读**：
- 第 6 行 `knowledge_rate_limit: int = 10`：**知识库调用限流**，默认 10 次/单位时间
- **应用位置**：dify 在每次 knowledge API 调用前检查 `knowledge_rate_limit`
- **底层实现**：dify 通常用 Redis `INCR` + EXPIRE 实现固定窗口限流（最简单可靠）
- **业务关联**：不同套餐（SANDBOX / PROFESSIONAL / TEAM）的限额不同，从 `BillingService` 加载

### 3.2 ruoyi 的 Redisson 限流（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**（简化）：

```java
// RateLimiterAspect.java - AOP 切面限流
@Aspect
@Component
public class RateLimiterAspect {
    @Around("@annotation(rateLimiter)")
    public Object around(ProceedingJoinPoint pjp, RateLimiter rateLimiter) throws Throwable {
        String key = rateLimiter.key();
        int time = rateLimiter.time();
        int count = rateLimiter.count();

        RRateLimiter limiter = redissonClient.getRateLimiter(key);
        limiter.trySetRate(RateType.OVERALL, count, time, RateIntervalUnit.SECONDS);

        if (limiter.tryAcquire()) {
            return pjp.proceed();   // 允许
        } else {
            throw new RateLimitException("访问过于频繁");
        }
    }
}

// 使用
@RateLimiter(key = "api:user:create", time = 60, count = 10)
public Result createUser(UserDTO dto) {
    // ...
}
```

**解读**：
- 第 7 行：Redisson `RRateLimiter` 底层是**令牌桶**算法（Lua 脚本保证原子性）
- 第 8 行：`RateType.OVERALL` 全局限流，`RateType.PER_CLIENT` 按客户端限流
- 第 17 行：`@RateLimiter` 注解 + AOP 实现**声明式限流**，业务代码无感知

## 4. 关键要点总结

- **固定窗口**：最简单，但有边界突刺问题
- **滑动窗口**：精确，适合 API 配额
- **令牌桶**：允许突发，适合 API 网关
- **漏桶**：强制平滑，适合流量整形
- 生产环境推荐**令牌桶**（Redisson）和**滑动窗口**（Redis ZSet）
- dify 的 `knowledge_rate_limit` 用简单的固定窗口限流
- **限流粒度必须到用户**，不能全局共享

## 5. 练习题

### 练习 1：基础（必做）

实现 `fixed_window_limit(user_id, limit=10, window=1)`：
- 用 Redis `INCR` + `EXPIRE` 实现
- 每秒最多 10 次请求

### 练习 2：进阶

阅读 `dify/api/services/feature_service.py`，分析 `knowledge_rate_limit`：
- 这是哪种限流算法？
- dify 怎么区分不同套餐的限额？

### 练习 3：挑战（选做）

用 Redis Lua 脚本实现一个**分布式令牌桶**：
1. 参数：rate（令牌/s）、capacity（桶容量）
2. 保证多进程并发下原子性
3. 测试突发流量（先瞬间发 capacity 个，再持续发）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/feature_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
- 限流算法对比：https://stripe.com/blog/rate-limiters
- Redisson 限流：https://redisson.org/docs/data-and-services/data-sources/

---

**文档版本**：v1.0
**最后更新**：2026-07-14