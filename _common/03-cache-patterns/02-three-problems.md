# 3.2 缓存三大问题：穿透 / 击穿 / 雪崩

> 深入理解缓存系统最常见的三类故障场景及解决方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分缓存穿透 / 击穿 / 雪崩的根本原因
- 为每个问题设计至少 2 种解决方案
- 用 Python 代码实现空值缓存、布隆过滤器等
- 在 dify 系统中识别这些场景

## 📚 前置知识

- 缓存基本概念（`03-cache-patterns/01-strategies.md`）
- Redis 基础操作
- 数据库索引原理

## 1. 核心概念

### 1.1 为什么需要关注这三大问题？

缓存是为了加速，但**缓存也是系统的脆弱点**——任何缓存层的问题都会被放大到整个系统。理解这三大问题是设计高可用缓存系统的基础。

### 1.2 缓存穿透（Cache Penetration）

**定义**：查询**根本不存在的数据**，缓存层永远不命中，请求直达数据库。

**场景**：
- 攻击者故意查询 `-1` 或超大 ID 的数据
- 业务误用（如 Redis 中没有就持续查 DB）

**危害**：
- 缓存形同虚设，所有请求打 DB
- 大量无效查询可能拖垮 DB

**解决方案**：

| 方案 | 实现 | 优缺点 |
|------|------|-------|
| **空值缓存** | 查 DB 返回 None 也缓存（短 TTL） | 简单，但恶意攻击时大量空 key |
| **布隆过滤器** | DB 数据先入布隆过滤器，不在则直接返回 | 高效，但有误判率 |
| **参数校验** | 拦截非法 ID | 治本，但需要业务配合 |

### 1.3 缓存击穿（Cache Breakdown / Hotspot Invalid）

**定义**：**热点 key 突然失效**，大量并发请求同时打到 DB。

**场景**：
- 明星离婚新闻缓存过期，百万 QPS 查 DB
- 秒杀商品库存 key 过期

**危害**：
- 瞬间 DB 请求量激增
- 可能引发雪崩

**解决方案**：

| 方案 | 实现 | 优缺点 |
|------|------|-------|
| **互斥锁（Mutex）** | 只让一个线程重建缓存，其他等待 | 简单可靠，但锁竞争阻塞 |
| **逻辑过期** | 不设 TTL，由后台异步刷新 | 永不阻塞，但有短暂不一致 |
| **永不过期 + 后台刷新** | 缓存不设过期时间 | 最优，但实现复杂 |

### 1.4 缓存雪崩（Cache Avalanche）

**定义**：**大量 key 同时失效**或**缓存层整体宕机**，所有请求直达 DB。

**场景**：
- 凌晨 2 点大量 key 同时过期
- Redis 集群宕机

**危害**：
- 系统瞬时不可用

**解决方案**：

| 方案 | 实现 |
|------|------|
| **过期时间加随机抖动** | TTL = base + random(0, N) |
| **热点数据永不过期** | 后台异步刷新 |
| **多级缓存** | 本地缓存 + Redis + DB |
| **熔断降级** | 缓存宕机时直接返回兜底数据 |

### 1.5 三大问题对比

| 维度 | 穿透 | 击穿 | 雪崩 |
|------|------|------|------|
| **原因** | 查不存在的数据 | 单个热点 key 失效 | 大量 key 同时失效 |
| **影响范围** | 单次请求 | 单个 key | 整个缓存层 |
| **解决思路** | 拦截无效请求 | 单 key 互斥 | 错开过期 / 多级缓存 |

## 2. 代码示例

### 2.1 缓存穿透：布隆过滤器

```python
# 文件：example_bloom_filter.py
import redis
from pybloomfilter import BloomFilter

r = redis.Redis(host="localhost", port=6379)

# 初始化布隆过滤器（10 万元素，1% 误判率）
bf = BloomFilter(100000, 0.01)

# 启动时把所有 user_id 加入布隆过滤器
for user_id in db_get_all_user_ids():
    bf.add(user_id)


def get_user(user_id: str):
    """防穿透"""
    # 1. 先查布隆过滤器
    if user_id not in bf:
        return None   # 不存在，直接返回（不打 DB）

    # 2. 查缓存
    cached = r.get(f"user:{user_id}")
    if cached:
        return eval(cached)

    # 3. 查 DB
    user = db_query_user(user_id)
    if user is None:
        # DB 也没有 → 缓存空值（防二次穿透）
        r.setex(f"user:{user_id}", 60, "NULL")
        return None

    r.setex(f"user:{user_id}", 300, str(user))
    return user
```

### 2.2 缓存击穿：互斥锁重建

```python
# 文件：example_mutex_lock.py
import redis
import time

r = redis.Redis(host="localhost", port=6379)
LOCK_KEY = "lock:user:1001"

def get_hot_user(user_id: str):
    """防击穿：用分布式锁保证只有一个线程重建缓存"""
    cache_key = f"user:{user_id}"

    # 1. 查缓存
    cached = r.get(cache_key)
    if cached:
        return eval(cached)

    # 2. 尝试获取分布式锁（SETNX + EX）
    lock_token = f"{time.time()}"
    if r.set(LOCK_KEY, lock_token, nx=True, ex=10):
        try:
            # 3. 获取锁成功 → 重建缓存
            user = db_query_user(user_id)
            r.setex(cache_key, 300, str(user))
            return user
        finally:
            # 4. 释放锁（Lua 脚本保证原子性）
            release_script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
            """
            r.eval(release_script, 1, LOCK_KEY, lock_token)
    else:
        # 5. 没抢到锁 → 等待并重试
        time.sleep(0.1)
        return get_hot_user(user_id)   # 递归重试（或返回 None）
```

### 2.3 缓存雪崩：过期时间加抖动

```python
# 文件：example_ttl_jitter.py
import redis
import random

r = redis.Redis(host="localhost", port=6379)

def cache_set_with_jitter(key, value, base_ttl=3600, jitter=600):
    """设置缓存时加随机抖动，避免同时过期"""
    # 实际 TTL = 基础 TTL + 随机 [-jitter, +jitter]
    ttl = base_ttl + random.randint(-jitter, jitter)
    r.setex(key, ttl, value)


# 1 万个 key 不会同时过期
for i in range(10000):
    cache_set_with_jitter(f"item:{i}", f"value-{i}", base_ttl=3600, jitter=600)
    # 实际 TTL 在 3000~4200 秒之间均匀分布
```

### 2.4 常见错误：未识别击穿用普通 SET

```python
# ❌ 反例：热点 key 用普通 SETEX
def get_hot_item(item_id):
    cached = r.get(f"item:{item_id}")
    if cached:
        return cached
    item = db_query_item(item_id)
    r.setex(f"item:{item_id}", 300, str(item))
    return item

# 问题：300 秒后过期瞬间，1000 个并发请求都查 DB → 击穿

# ✅ 正例：用互斥锁
def get_hot_item_v2(item_id):
    # ... 用上面 2.2 的逻辑
    pass
```

## 3. dify 仓库源码解读

### 3.1 dify 的 redis_fallback 装饰器（防雪崩）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 476-496）：

```python
def redis_fallback[T](default_return: T | None = None):  # type: ignore
    """
    decorator to handle Redis operation exceptions and return a default value when Redis is unavailable.

    Args:
        default_return: The value to return when a Redis operation fails. Defaults to None.
    """

    def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R | T | None]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | T | None:
            try:
                return func(*args, **kwargs)
            except RedisError as e:
                func_name = getattr(func, "__name__", "Unknown")
                logger.warning("Redis operation failed in %s: %s", func_name, str(e), exc_info=True)
                return default_return

        return wrapper

    return decorator
```

**解读**：
- 第 8 行：`except RedisError`：捕获所有 Redis 异常（连接超时、OOM、Cluster failover 等）
- 第 11 行：失败时返回默认值（如 `None`），**不让 Redis 故障拖垮整个应用**
- **对应问题**：缓存层宕机（雪崩场景）时，业务优雅降级到"无缓存"模式继续运行
- **典型用法**：
  ```python
  @redis_fallback(default_return=False)
  def is_feature_enabled(feature: str) -> bool:
      return r.get(f"feature:{feature}") == b"1"
  ```
  即使 Redis 宕机，`is_feature_enabled` 仍返回 False，**应用不会崩溃**

**整体设计意图**：dify 把"Redis 不可用"当成可恢复的异常处理，是分布式系统的**容错哲学**——fail-soft 而非 fail-fast。

### 3.2 ruoyi 的布隆过滤器（防穿透）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// RedissonBloomFilterConfig.java - Redisson 布隆过滤器
@Configuration
public class RedissonBloomFilterConfig {
    @Bean
    public RBloomFilter<Long> userBloomFilter(RedissonClient redisson) {
        RBloomFilter<Long> filter = redisson.getBloomFilter("user-id-filter");
        filter.tryInit(1000000L, 0.01);   // 100 万元素，1% 误判
        return filter;
    }
}

// UserServiceImpl.java - 防穿透
public User getUser(Long userId) {
    // Step 1: 布隆过滤器
    if (!userBloomFilter.contains(userId)) {
        return null;    // 不存在，直接返回
    }

    // Step 2: Redis 缓存
    User cached = redisTemplate.opsForValue().get("user:" + userId);
    if (cached != null) {
        return cached;
    }

    // Step 3: DB
    User user = userMapper.selectById(userId);
    if (user == null) {
        redisTemplate.opsForValue().set("user:" + userId, "NULL", 60, TimeUnit.SECONDS);
        return null;
    }
    redisTemplate.opsForValue().set("user:" + userId, user, 300, TimeUnit.SECONDS);
    return user;
}
```

**解读**：
- 第 8 行：Redisson 内置布隆过滤器（基于 Redis BitMap）
- 第 17-18 行：防穿透三件套——布隆过滤器 + 缓存 + 空值缓存

## 4. 关键要点总结

- **穿透**：用布隆过滤器 / 空值缓存拦截无效请求
- **击穿**：用互斥锁 / 逻辑过期保护单个热点 key
- **雪崩**：用过期时间抖动 + 多级缓存 + 熔断降级
- dify 的 `redis_fallback` 装饰器是**雪崩容错**的标准实现
- **三大问题往往叠加出现**，必须综合防护

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `safe_get_user(user_id)` 函数：
1. 用 Redis SETNX 实现分布式锁
2. 防止缓存击穿（单 key 并发重建）
3. 防止缓存穿透（DB 返回 None 时缓存空值）

### 练习 2：进阶

阅读 `dify/api/extensions/ext_redis.py` 的 `redis_fallback`：
- 它能防止"穿透 / 击穿 / 雪崩"中的哪些问题？
- 它**不能**防止哪些问题？

### 练习 3：挑战（选做）

设计一个完整的高可用缓存系统：
1. 启动时把 DB 全量数据加载到本地 Caffeine + Redis
2. 用布隆过滤器防穿透
3. 用分布式锁防击穿
4. 用多级缓存 + 熔断防雪崩
5. 画出架构图并标注数据流向

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- 缓存三大问题：https://coolshell.cn/articles/17416.html
- Redisson 布隆过滤器：https://redisson.org/docs/data-and-services/data-sources/

---

**文档版本**：v1.0
**最后更新**：2026-07-14