# 4.2.2 缓存穿透 / 击穿 / 雪崩

> 缓存使用不当会引发三类经典问题，理解它们是构建高可用系统的必修课。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分缓存穿透、击穿、雪崩三种问题
- 掌握每种问题的解决方案
- 在 dify 中识别这些问题的应对策略
- 设计高可用的缓存层

## 📚 前置知识

- Redis 基础
- 缓存策略
- 08-redis-cache.md

## 1. 核心概念

### 1.1 缓存穿透（Cache Penetration）

**现象**：查询**不存在的数据**，缓存和 DB 都没有，每次请求都直接打到 DB。

**场景**：
- 攻击者故意查询 `id = -1` 的数据
- 业务逻辑 bug 导致无效查询

**危害**：DB 被打爆。

**解决方案**：
1. **缓存空值**：查 DB 没有结果时也缓存 `null`，TTL 短一些（如 60 秒）
2. **布隆过滤器**：把所有存在的 key 放进 Bloom Filter，不存在的 key 直接拒绝
3. **参数校验**：在 API 层过滤明显非法的参数

### 1.2 缓存击穿（Cache Breakdown）

**现象**：某个**热点 key** 突然失效，大量并发请求同时打到 DB。

**场景**：
- 热点商品缓存 TTL 到期
- 秒杀商品缓存被删除

**危害**：DB 在瞬间承受巨大压力。

**解决方案**：
1. **分布式锁**：只让一个请求查 DB，其他等
2. **永不过期**：缓存不设 TTL，后台异步更新
3. **逻辑过期**：value 带时间戳，逻辑判断是否过期
4. **多级缓存**：本地缓存 + Redis 双层

### 1.3 缓存雪崩（Cache Avalanche）

**现象**：**大量 key 同时失效**或 **Redis 整体宕机**，所有请求直接打到 DB。

**场景**：
- 凌晨 2 点批量缓存 TTL 到期
- Redis 故障

**解决方案**：
1. **TTL 随机化**：避免同时过期（`TTL = 60 + random(0, 30)`）
2. **Redis 高可用**：Sentinel / Cluster
3. **熔断降级**：Redis 故障时直接返回兜底数据
4. **DB 限流**：保护 DB 不被打爆

### 1.4 对比总结

| 问题 | 触发条件 | 表现 | 解决方案 |
|------|---------|------|---------|
| 穿透 | 查不存在的数据 | DB 查不到 | 空值缓存、布隆过滤器 |
| 击穿 | 单个热点 key 失效 | DB 单 key 压力大 | 分布式锁、逻辑过期 |
| 雪崩 | 大量 key 同时失效 / Redis 挂 | DB 整体压力大 | TTL 随机、高可用、降级 |

## 2. 代码示例

### 2.1 缓存穿透：缓存空值

```python
def get_user_safe(user_id):
    cache_key = f"user:{user_id}"

    # 1. 查缓存（包括空值标记）
    cached = r.get(cache_key)
    if cached == "NULL":
        return None  # 直接返回空
    if cached:
        return json.loads(cached)

    # 2. 查 DB
    user = db.query("SELECT * FROM users WHERE id = %s", user_id)

    if user:
        r.setex(cache_key, 300, json.dumps(user))
    else:
        # 缓存空值，TTL 短一些
        r.setex(cache_key, 60, "NULL")

    return user
```

### 2.2 缓存击穿：分布式锁

```python
def get_hot_item_with_lock(item_id):
    cache_key = f"hot:item:{item_id}"
    lock_key = f"lock:{cache_key}"

    # 1. 查缓存
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. 加锁查 DB
    lock = r.lock(lock_key, timeout=10, blocking_timeout=3)
    if lock.acquire():
        try:
            # 双重检查（其他线程可能已经查过了）
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)

            item = db.query("SELECT * FROM items WHERE id = %s", item_id)
            r.setex(cache_key, 60, json.dumps(item))
            return item
        finally:
            lock.release()
    else:
        # 没抢到锁，等一会重试
        time.sleep(0.1)
        return get_hot_item_with_lock(item_id)
```

### 2.3 缓存雪崩：TTL 随机化

```python
import random

def set_cache_random_ttl(key, value, base_ttl=60):
    """设置缓存时 TTL 加随机抖动，避免同时过期"""
    ttl = base_ttl + random.randint(0, 30)
    r.setex(key, ttl, value)

# 批量设置
for user_id in range(10000):
    user = db.get_user(user_id)
    set_cache_random_ttl(f"user:{user_id}", json.dumps(user))
```

### 2.4 缓存穿透：布隆过滤器

```python
from pybloomfilter import BloomFilter

# 启动时加载所有合法 key
bf = BloomFilter(1000000, 0.001)  # 100 万容量，0.1% 误判率
for user_id in db.all_user_ids():
    bf.add(str(user_id))

def get_user_with_bloom(user_id):
    # 1. 布隆过滤器快速判断
    if str(user_id) not in bf:
        return None  # 一定不存在

    # 2. 查缓存
    cached = r.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    # 3. 查 DB
    user = db.query("SELECT * FROM users WHERE id = %s", user_id)
    if user:
        r.setex(f"user:{user_id}", 300, json.dumps(user))
    return user
```

### 2.5 雪崩：Redis 故障降级

```python
def get_user_with_fallback(user_id):
    try:
        cached = r.get(f"user:{user_id}")
        if cached:
            return json.loads(cached)
    except redis.RedisError:
        # Redis 挂了，直接查 DB（限流保护）
        if not check_db_circuit_breaker():
            raise ServiceUnavailable("DB 也限流了")
        return db.query("SELECT * FROM users WHERE id = %s", user_id)

    user = db.query("SELECT * FROM users WHERE id = %s", user_id)
    try:
        r.setex(f"user:{user_id}", 300, json.dumps(user))
    except redis.RedisError:
        pass  # 写失败不影响返回

    return user
```

## 3. dify 仓库源码解读

### 3.1 redis_fallback：通用降级机制

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 476-496）：

```python
def redis_fallback[T](default_return: T | None = None):  # type: ignore
    """
    decorator to handle Redis operation exceptions and return a default value when Redis is unavailable.
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
- 这是 dify 应对**缓存雪崩**（Redis 整体宕机）的核心策略
- 任何 Redis 操作失败都返回默认值，业务继续运行
- **例子**：
  - 限流：返回 `False`（不限流），让用户继续访问
  - 登录计数：返回 `None`（不计数），用户能正常登录
  - **权衡**：Redis 故障时，限流、缓存都失效，**安全性降低但可用性提高**
- **生产建议**：Redis 故障时应该有**降级告警**，让运维及时处理

### 3.2 限流：防止雪崩扩散

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
- dify 用 Redis 做**两层限流**：每 10 分钟 N 次 + 每小时 N 次
- **TTL 避免雪崩**：每个 key 都自动过期，不用担心累积
- **防止恶意登录**：连续失败冻结账号 1 小时
- **多维度防护**：邮箱 + IP + 设备指纹（代码未完整展示）

### 3.3 Celery 队列：限流保护 DB

**文件位置**：`/Users/xu/code/github/dify/api/tasks/clean_dataset_task.py`
**核心代码**（行 32-52）：

```python
@shared_task(queue="dataset")
def clean_dataset_task(
    dataset_id: str,
    tenant_id: str,
    indexing_technique: str,
    index_struct: str,
    collection_binding_id: str,
    doc_form: str,
    pipeline_id: str | None = None,
):
    """
    Clean dataset when dataset deleted.
    Usage: clean_dataset_task.delay(dataset_id, tenant_id, indexing_technique, index_struct)
    """
    logger.info(click.style(f"Start clean dataset when dataset deleted: {dataset_id}", fg="green"))
    start_at = time.perf_counter()
```

**解读**：
- `queue="dataset"`：所有 dataset 相关任务进入同一队列
- Celery worker 并发数限制（如 `--concurrency=4`），**自动限流**
- **避免雪崩到 DB**：即使 1 万个数据集同时删除，也只会有 4 个任务同时跑
- **TTL 不在这里**：Celery 任务本身没有 TTL，DB 才是真相（删除成功的标志）

## 4. 关键要点总结

- **缓存穿透**：查不存在的数据。**空值缓存 + 布隆过滤器**
- **缓存击穿**：热点 key 失效。**分布式锁 + 逻辑过期**
- **缓存雪崩**：大量 key 失效 / Redis 挂。**TTL 随机 + 高可用 + 降级**
- dify 的 `redis_fallback` 是**通用降级**机制，保证 Redis 故障时业务不崩
- **分层防护**：Redis 限流 + Celery 队列限流 + DB 自身连接池限流
- **监控必不可少**：Redis 故障、降级次数需要告警

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 实现"缓存穿透"防护：
- 查询不存在的 key 时，缓存 "NULL" 标记
- TTL 设置为 60 秒

### 练习 2：进阶

用 `r.lock()` 实现分布式锁防击穿，模拟 10 个并发线程同时查热点 key，观察只有 1 个线程查 DB。

### 练习 3：挑战（选做）

写一个压测脚本（用 `locust` 或 `wrk`），对比开启/关闭 redis_fallback 时 DB 的 QPS，验证降级效果。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 476-496 行）
- `/Users/xu/code/github/dify/api/services/account_service.py`（第 1210-1222 行）
- `/Users/xu/code/github/dify/api/tasks/clean_dataset_task.py`
- 缓存三大问题详解：https://coolshell.cn/articles/17416.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13