# 5.5.1 API 限流：令牌桶 / 漏桶 / 滑动窗口

> 理解 API 限流的三大算法，掌握 dify 的限流实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解令牌桶、漏桶、滑动窗口三种限流算法的差异
- 能用 Python 实现三种限流器
- 理解 dify 在登录、API 调用、知识库等场景的限流策略
- 知道如何选择适合业务的限流方案

## 📚 前置知识

- 01-fundamentals/06-async-asyncio.md
- 04-cache-and-queue/02-redis-cache.md

## 1. 核心概念

### 1.1 为什么需要限流？

- **保护后端**：防止雪崩（某个慢查询拖垮整个服务）
- **公平使用**：防止单个用户霸占资源
- **防滥用**：登录、短信等接口防爆破
- **成本控制**：LLM API 按 token 计费，必须限流

### 1.2 三大算法对比

| 算法 | 核心思想 | 允许突发 | 平滑度 | 复杂度 |
|------|---------|---------|--------|--------|
| 令牌桶 | 桶里攒令牌，拿令牌才能通过 | 是 | 中 | 低 |
| 漏桶 | 请求均匀流出，超量排队 | 否 | 高 | 中 |
| 滑动窗口 | 统计时间窗口内请求数 | 否 | 中 | 中 |

### 1.3 选型建议

- **令牌桶**：API 网关、突发流量（如秒杀）
- **漏桶**：下游需要稳定速率（如数据库写入）
- **滑动窗口**：精确限流（如每分钟 100 次）

dify 在不同场景用了不同策略：
- 登录限流：滑动窗口（Redis 计数）
- 知识库上传：滑动窗口（按 tenant）
- API Key 调用：令牌桶（按 app）

## 2. 代码示例

### 2.1 令牌桶

```python
import time
import threading

class TokenBucket:
    """令牌桶：每秒补充 rate 个令牌，桶容量 capacity。"""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate              # tokens per second
        self.capacity = capacity      # max tokens
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def allow(self) -> bool:
        with self.lock:
            now = time.time()
            # 补充令牌
            self.tokens = min(
                self.capacity,
                self.tokens + (now - self.last_update) * self.rate
            )
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


# 使用：每秒 10 个，桶容量 20
bucket = TokenBucket(rate=10, capacity=20)
for i in range(30):
    print(f"Request {i}: {'OK' if bucket.allow() else 'BLOCKED'}")
```

### 2.2 漏桶

```python
import time

class LeakyBucket:
    """漏桶：均匀流出，容量 capacity。"""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate              # leak rate per second
        self.capacity = capacity
        self.water = 0
        self.last_leak = time.time()

    def allow(self) -> bool:
        now = time.time()
        # 先漏水
        self.water = max(0, self.water - (now - self.last_leak) * self.rate)
        self.last_leak = now

        if self.water < self.capacity:
            self.water += 1
            return True
        return False
```

### 2.3 滑动窗口（Redis 版）

```python
import redis
import time

class SlidingWindowLimiter:
    """滑动窗口：用 Redis ZSET 存储请求时间戳。"""

    def __init__(self, redis_client: redis.Redis, key: str,
                 max_requests: int, window_seconds: int):
        self.redis = redis_client
        self.key = key
        self.max_requests = max_requests
        self.window = window_seconds

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self.window
        # 1. 删除窗口外的旧记录
        self.redis.zremrangebyscore(self.key, 0, cutoff)
        # 2. 统计窗口内请求数
        count = self.redis.zcard(self.key)
        if count >= self.max_requests:
            return False
        # 3. 记录当前请求
        self.redis.zadd(self.key, {f"{now}:{id(object())}": now})
        self.redis.expire(self.key, self.window + 1)
        return True
```

### 2.4 常见错误：限流粒度过粗

```python
# ❌ 错误：全实例共用一个计数器
redis.incr("global_requests")  # 所有用户共用，无法防单用户滥用

# ✅ 正确：按用户 / tenant 分桶
redis.incr(f"rate_limit:tenant:{tenant_id}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的限流装饰器

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/wraps.py`
**核心代码**（行 240-280）：

```python
def knowledge_rate_limit[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    """限流：知识库相关操作。"""
    @wraps(view)
    def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
        if not dify_config.BILLING_ENABLED:
            return view(*args, **kwargs)

        _, current_tenant_id = current_account_with_tenant()
        knowledge_rate_limit = FeatureService.get_knowledge_rate_limit(current_tenant_id)

        if knowledge_rate_limit.enabled:
            current_time = int(time.time() * 1000)
            key = f"rate_limit_{current_tenant_id}"

            # 用 Redis ZSET 实现滑动窗口
            redis_client.zremrangebyscore(key, 0, current_time - 60_000)
            request_count = redis_client.zcard(key)

            if request_count >= knowledge_rate_limit.limit:
                raise RateLimitExceededError()

            redis_client.zadd(key, {f"{current_time}:{secrets.token_hex(8)}": current_time})
            redis_client.expire(key, 120)

        return view(*args, **kwargs)

    return decorated
```

**解读**：
- 第 5-6 行：未启用计费时不限制
- 第 8 行：从 FeatureService 取当前 tenant 的限流配额（不同付费级别不同）
- 第 10 行：`enabled` 开关
- 第 13 行：Redis key 按 tenant 隔离
- 第 16 行：删除 60 秒前的请求
- 第 17 行：统计当前窗口内请求数
- 第 19-20 行：超限抛 `RateLimitExceededError`
- 第 22 行：用 `secrets.token_hex(8)` 作为 member 防止 ZADD 同分冲突
- **算法**：滑动窗口（60 秒内最多 N 次）

### 3.2 登录错误次数限流

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`（典型结构）
**核心代码**（说明）：

```python
class AccountService:
    @staticmethod
    def is_login_error_rate_limit(email: str) -> bool:
        """检查邮箱是否触发登录错误限流。"""
        key = f"login_error_rate_limit:{email}"
        count = redis_client.get(key)
        return int(count or 0) >= LOGIN_LOCKOUT_THRESHOLD

    @staticmethod
    def add_login_error_rate_limit(email: str) -> None:
        """记录一次登录失败，触发自动过期。"""
        key = f"login_error_rate_limit:{email}"
        redis_client.incr(key)
        redis_client.expire(key, LOGIN_LOCKOUT_DURATION_MINUTES * 60)
```

**解读**：
- 用 Redis `INCR + EXPIRE` 实现计数器限流
- 超过阈值后拒绝登录 `LOGIN_LOCKOUT_DURATION_MINUTES` 分钟
- **算法**：固定窗口（简单计数 + 过期）
- **设计意图**：防爆破攻击，错误次数累积后锁定账号

## 4. 关键要点总结

- 三大算法：**令牌桶**（突发友好）、**漏桶**（平滑）、**滑动窗口**（精确）
- dify 知识库用 **Redis ZSET 滑动窗口**
- dify 登录用 **Redis 计数器** + 过期
- 限流 key 必须按用户/tenant 隔离，否则单用户可滥用全局配额
- **超限响应**：429 Too Many Requests + Retry-After 头

## 5. 练习题

### 练习 1：基础（必做）

用 Python 实现一个内存版 `TokenBucket(rate=10, capacity=20)`，并写一个并发测试：100 个请求同时打过去，看通过率。

### 练习 2：进阶

阅读 `api/controllers/console/wraps.py:240-280`，解释 dify 为什么用 `secrets.token_hex(8)` 作为 ZSET member？不用会发生什么？

### 练习 3：挑战（选做）

实现一个**分层限流器**：全局 QPS 100 + 每用户 QPS 10，两个都通过才放行。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/wraps.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`
- Stripe 限流设计：https://stripe.com/blog/rate-limiters
- Redis 限流模式：https://redis.io/glossary/rate-limiting/

---

**文档版本**：v1.0
**最后更新**：2026-07-13