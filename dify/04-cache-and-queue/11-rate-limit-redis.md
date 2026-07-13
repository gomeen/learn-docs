# 4.2.4 限流：滑动窗口 / 令牌桶

> 高并发系统必须限流。Redis 是实现分布式限流的天然选择（快、原子、TTL）。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握固定窗口、滑动窗口、令牌桶、漏桶四种限流算法
- 用 Redis 实现每种算法
- 理解 dify 在哪些场景使用限流
- 根据业务特点选择合适的算法

## 📚 前置知识

- Redis 基础数据结构（String、Sorted Set、List）
- 01-redis-data-structures.md
- 10-distributed-lock.md

## 1. 核心概念

### 1.1 为什么需要限流？

- 保护下游服务（DB、第三方 API）不被压垮
- 防止恶意请求（爬虫、CC 攻击）
- 保证**公平使用**（每用户/每租户配额）

### 1.2 固定窗口（Fixed Window）

最简单的限流算法：把时间分成固定大小的窗口（如 1 分钟），每个窗口内计数。

```
[0-60s]  [60-120s]  [120-180s]
  ↓         ↓          ↓
 100次    100次      100次
```

**实现**（Redis）：
```lua
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
if current > tonumber(ARGV[2]) then
    return 0
end
return 1
```

**优点**：简单。**缺点**：**窗口边界突刺**——0-60s 最后 1 秒和 60-120s 第 1 秒可能瞬间通过 2 倍请求。

### 1.3 滑动窗口（Sliding Window）

把窗口**细分**为多个小窗口，平滑统计。

```
[0-10s] [10-20s] [20-30s] ... [50-60s]
   10      15       8           12  → 总和 45
```

**实现**（Redis Sorted Set）：
```lua
-- KEYS[1] = sorted set key
-- ARGV[1] = now (ms)
-- ARGV[2] = window (ms)
-- ARGV[3] = limit
-- ARGV[4] = request_id

redis.call("ZREMRANGEBYSCORE", KEYS[1], 0, now - window)
local count = redis.call("ZCARD", KEYS[1])
if count >= limit then return 0 end
redis.call("ZADD", KEYS[1], now, request_id)
return 1
```

**优点**：精确。**缺点**：内存占用大（每请求一个 member）。

### 1.4 令牌桶（Token Bucket）

桶里装**令牌**，每个请求消耗一个，令牌按速率补充。

```
桶（容量 N）→ [T][T][T][T][T]   ← 补充速率 R/s
            ↓
        请求消耗
```

**实现**（Lua 原子）：
```lua
-- KEYS[1] = 桶 key
-- ARGV[1] = 桶容量
-- ARGV[2] = 补充速率（每秒）
-- ARGV[3] = now (ms)
-- ARGV[4] = 请求消耗的令牌

local bucket = redis.call("HMGET", KEYS[1], "tokens", "last_refill")
local tokens = tonumber(bucket[1]) or tonumber(ARGV[1])
local last_refill = tonumber(bucket[2]) or tonumber(ARGV[3])

-- 计算补充
local elapsed = (tonumber(ARGV[3]) - last_refill) / 1000
tokens = math.min(tonumber(ARGV[1]), tokens + elapsed * tonumber(ARGV[2]))

if tokens < tonumber(ARGV[4]) then
    return 0
end

tokens = tokens - tonumber(ARGV[4])
redis.call("HMSET", KEYS[1], "tokens", tokens, "last_refill", ARGV[3])
redis.call("PEXPIRE", KEYS[1], 60000)
return 1
```

**优点**：允许**突发流量**（桶满时可瞬间处理多个请求）。**缺点**：算法略复杂。

### 1.5 漏桶（Leaky Bucket）

请求进入桶，桶以**固定速率**流出处理。桶满则拒绝。

```
   →[ T ][ T ][ T ][ T ]→ → 处理（恒定速率）
   ↓
   桶满 → 拒绝
```

**与令牌桶区别**：漏桶**强制平滑输出**（恒定处理速率），令牌桶允许突发。

### 1.6 算法对比

| 算法 | 精度 | 允许突发 | 复杂度 | 内存 |
|------|------|---------|--------|------|
| 固定窗口 | 低（边界突刺）| ❌ | 简单 | 小 |
| 滑动窗口 | 高 | ❌ | 中 | 中 |
| 令牌桶 | 高 | ✅ | 高 | 小 |
| 漏桶 | 高 | ❌ | 中 | 小 |

## 2. 代码示例

### 2.1 固定窗口（Python 实现）

```python
import redis
import time

r = redis.Redis(decode_responses=True)

def fixed_window_limit(user_id, limit=10, window=60):
    key = f"rate:{user_id}:{int(time.time() // window)}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, window)
    return count <= limit
```

### 2.2 滑动窗口（Sorted Set）

```python
import time
import uuid

sliding_window_script = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local request_id = ARGV[4]

redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
local count = redis.call("ZCARD", key)
if count >= limit then
    return 0
end
redis.call("ZADD", key, now, request_id)
redis.call("PEXPIRE", key, window)
return 1
"""

script = r.register_script(sliding_window_script)

def sliding_window_limit(user_id, limit=10, window_ms=60000):
    now = int(time.time() * 1000)
    request_id = str(uuid.uuid4())
    result = script(
        keys=[f"sliding:{user_id}"],
        args=[now, window_ms, limit, request_id],
    )
    return bool(result)
```

### 2.3 令牌桶（Hash + Lua）

```python
token_bucket_script = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])  -- tokens per second
local now = tonumber(ARGV[3])    -- ms
local cost = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "ts")
local tokens = tonumber(bucket[1]) or capacity
local ts = tonumber(bucket[2]) or now

-- 补充令牌
local elapsed_sec = (now - ts) / 1000
tokens = math.min(capacity, tokens + elapsed_sec * rate)

if tokens < cost then
    redis.call("HMSET", key, "tokens", tokens, "ts", now)
    redis.call("PEXPIRE", key, 60000)
    return 0
end

tokens = tokens - cost
redis.call("HMSET", key, "tokens", tokens, "ts", now)
redis.call("PEXPIRE", key, 60000)
return 1
"""

script = r.register_script(token_bucket_script)

def token_bucket_limit(user_id, capacity=10, rate=1):
    """容量 10，每秒补充 1 个"""
    now = int(time.time() * 1000)
    return bool(script(
        keys=[f"token:{user_id}"],
        args=[capacity, rate, now, 1],
    ))
```

### 2.4 常见错误：计数器竞态

```python
# ❌ 错误：GET + INCR 非原子
count = r.get(key)  # 当前 9
if count < 10:
    count = r.incr(key)  # 并发下变成 11，超限！

# ✅ 正确：用 Lua 脚本保证原子
```

## 3. dify 仓库源码解读

### 3.1 登录失败限流（固定窗口）

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1052-1073）：

```python
@staticmethod
@redis_fallback(default_return=None)
def add_login_error_rate_limit(email: str):
    key = f"login_error_rate_limit:{email}"
    count = redis_client.get(key)
    if count is None:
        count = 0
    count = int(count) + 1
    redis_client.setex(key, dify_config.LOGIN_LOCKOUT_DURATION, count)

@staticmethod
@redis_fallback(default_return=False)
def is_login_error_rate_limit(email: str) -> bool:
    key = f"login_error_rate_limit:{email}"
    count = redis_client.get(key)
    if count is None:
        return False

    count = int(count)
    if count > AccountService.LOGIN_MAX_ERROR_LIMITS:
        return True
    return False
```

**解读**：
- dify 用 **固定窗口 + TTL** 实现登录失败限流
- key 是 `login_error_rate_limit:{email}`，TTL = `LOGIN_LOCKOUT_DURATION`（如 10 分钟）
- **缺点**：GET + SETEX 非原子（高并发可能少计），但**实际影响小**（连续失败 N 次就限流）
- **优点**：简单可读，业务风险低

### 3.2 多层限流（冻结 + 每小时计数）

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1210-1222）：

```python
freeze_key = f"account_frozen:{email}"
hour_limit_key = f"account_hour_limit:{email}"

# 检查是否冻结
frozen = redis_client.get(freeze_key)
if frozen:
    raise AccountPasswordLoginLimitError()

# 每小时计数
hour_limit_count = int(redis_client.get(hour_limit_key) or 0)
if hour_limit_count >= MAX_HOUR_LIMIT:
    raise AccountPasswordLoginLimitError()

# 增加计数
redis_client.setex(freeze_key, 60 * 60, 1)
redis_client.setex(hour_limit_key, 60 * 10, hour_limit_count + 1)  # first time limit 10 minutes
```

**解读**：
- **两层限流**：每 10 分钟（短）+ 每小时（长）
- `freeze_key` TTL 60 分钟（长时间冻结）
- `hour_limit_key` TTL 10 分钟（短时间计数）
- **设计思想**：10 分钟内超限 → 立即冻结；10 分钟后自动恢复部分尝试
- **滑动窗口近似**：虽然用了固定窗口，但**两次不同 TTL** 实现了**半滑动**效果

### 3.3 Celery 队列限流

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 163-175）：

```python
beat_schedule: dict[str, CeleryBeatScheduleEntry] = {}
if dify_config.ENABLE_CLEAN_EMBEDDING_CACHE_TASK:
    imports.append("schedule.clean_embedding_cache_task")
    beat_schedule["clean_embedding_cache_task"] = {
        "task": "schedule.clean_embedding_cache_task.clean_embedding_cache_task",
        "schedule": crontab(minute="0", hour="2", day_of_month=f"*/{day}"),
    }
```

**解读**：
- Celery 任务通过 `queue` 参数分配到不同队列
- Worker 可以为不同队列设置不同并发数：
  ```bash
  celery worker -Q dataset --concurrency=4
  celery worker -Q workflow --concurrency=10
  ```
- **天然限流**：队列消费速率 = Worker 并发数 × 任务平均耗时
- dify 把重任务（数据清理）放到 `dataset` 队列，控制并发避免 DB 压力

## 4. 关键要点总结

- **固定窗口**：简单但有边界突刺
- **滑动窗口**：精确但内存大
- **令牌桶**：允许突发，适合 API 限流
- **漏桶**：强制平滑，适合流量整形
- dify 主要用 **固定窗口**（登录限流）+ **TTL 多层**（10 分钟 + 1 小时）
- Celery 队列也是一种**分布式限流**

## 5. 练习题

### 练习 1：基础（必做）

用 Redis 实现固定窗口限流：每用户每分钟 10 次。

### 练习 2：进阶

用 Sorted Set 实现滑动窗口限流：每用户每 60 秒 10 次（精确到毫秒）。

### 练习 3：挑战（选做）

实现令牌桶限流器（用 Hash + Lua），支持突发流量（桶容量 20，补充速率 5/s）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`（第 1052-1073、1210-1222 行）
- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`
- Redis 限流模式：https://redis.io/glossary/rate-limiting/
- 令牌桶算法：https://en.wikipedia.org/wiki/Token_bucket

---

**文档版本**：v1.0
**最后更新**：2026-07-13