# 4.1.5 Redis 内存淘汰策略

> 当 Redis 内存用完时，谁应该被淘汰？正确的淘汰策略决定系统稳定性。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis 内存淘汰的 8 种策略（LRU/LFU/random/TTL）
- 根据业务场景选择合适的策略
- 配置 `maxmemory` 和 `maxmemory-policy`
- 在 dify 中识别哪些 key 应该永不过期，哪些可以淘汰

## 📚 前置知识

- Redis 基础数据结构
- 01-redis-data-structures.md

## 1. 核心概念

### 1.1 为什么需要淘汰策略？

Redis 数据都在内存里。如果不加限制，最终会 OOM。`maxmemory` 参数限制最大内存，达到上限后必须**按策略淘汰**部分 key 才能继续写入。

```conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 1.2 八大淘汰策略

Redis 6.0 提供 8 种策略，前缀分两类：

| 策略 | 范围 | 算法 |
|------|------|------|
| `noeviction` | 不淘汰 | 写入报错（默认） |
| `allkeys-lru` | 所有 key | LRU（最近最少使用） |
| `allkeys-lfu` | 所有 key | LFU（最不经常使用） |
| `allkeys-random` | 所有 key | 随机 |
| `volatile-lru` | 仅过期 key | LRU |
| `volatile-lfu` | 仅过期 key | LFU |
| `volatile-random` | 仅过期 key | 随机 |
| `volatile-ttl` | 仅过期 key | 优先淘汰剩余 TTL 短的 |

**`volatile-*` vs `allkeys-*`**：
- `volatile-*`：只淘汰**设置了过期时间**的 key，没有 TTL 的 key 永不过期
- `allkeys-*`：所有 key 都可能被淘汰，包括没设 TTL 的

### 1.3 LRU vs LFU

**LRU（Least Recently Used）**：淘汰最近最少访问的。Redis 用**近似 LRU**：每个 key 维护一个 24 位时间戳 + 随机采样（默认 5 个），从样本中淘汰最久未访问的。

**LFU（Least Frequently Used）**：淘汰访问频率最低的。Redis 4.0+ 引入，用 **Morris counter** 计数器 + 衰减因子（时间越久访问权重越低）。

```conf
# 调整 LRU 采样精度（越大越接近真实 LRU，性能略降）
maxmemory-samples 10
```

**选择建议**：
- 缓存场景：热点数据重要 → **`allkeys-lru`**
- 计算频次重要（如推荐系统）：用 **`allkeys-lfu`**
- 临时数据（session）：设 TTL + **`volatile-ttl`**

### 1.4 内存碎片问题

即使淘汰策略正确，Redis 内存仍然可能持续增长——这是**内存碎片**：
- 频繁写入/删除不同大小的 key 会产生碎片
- 碎片率 = `used_memory_rss / used_memory`
- 碎片率 > 1.5 时考虑 `activedefrag yes`

```bash
redis-cli INFO memory
# used_memory:134884544
# used_memory_rss:206307328
# mem_fragmentation_ratio:1.53
```

## 2. 代码示例

### 2.1 配置淘汰策略

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
maxmemory-samples 5
```

或者运行时设置：
```bash
CONFIG SET maxmemory-policy allkeys-lfu
```

### 2.2 监控淘汰情况

```python
import redis

r = redis.Redis(decode_responses=True)

# 查看当前策略
print(r.config_get("maxmemory-policy"))

# 写入测试数据，触发淘汰
for i in range(100000):
    r.set(f"key:{i}", "x" * 100)

# 监控淘汰次数
info = r.info("stats")
print(f"evicted_keys: {info['evicted_keys']}")
```

### 2.3 常见错误：默认 noeviction 导致写入失败

```python
# 默认 maxmemory-policy=noeviction
r.set("new_key", "value")  # 内存满时 → redis.exceptions.ResponseError: OOM
# 用户体验：接口突然 500 错误

# 解决：显式设置淘汰策略
# CONFIG SET maxmemory-policy allkeys-lru
```

### 2.4 常见错误：volatile-* 误用

```python
# 假设想淘汰 session 数据
# 但有些用户没设 TTL（比如 VIP 用户的 session 永久）
# 用 volatile-ttl 会保留这些永不过期的 key

# ✅ 正确：session 类数据应该 SETEX
r.setex("session:user:1", 3600, "data")  # 1 小时后过期
```

## 3. dify 仓库源码解读

### 3.1 客户端侧缓存（Cache Config）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 282-291）：

```python
def _get_cache_configuration() -> CacheConfig | None:
    """Get client-side cache configuration if enabled."""
    if not dify_config.REDIS_ENABLE_CLIENT_SIDE_CACHE:
        return None

    resp_protocol = dify_config.REDIS_SERIALIZATION_PROTOCOL
    if resp_protocol < 3:
        raise ValueError("Client side cache is only supported in RESP3")

    return CacheConfig()
```

**解读**：
- **客户端侧缓存**（RESP3 特性）让 Redis 服务端**主动推送 key 失效消息**给客户端，客户端本地缓存命中时直接返回，不必发请求
- 减少网络 RTT，提高缓存命中场景的性能
- 第 288 行：要求 `REDIS_SERIALIZATION_PROTOCOL >= 3`（RESP3 才有失效推送）

### 3.2 健康参数控制重试

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 305-312）：

```python
def _get_connection_health_params() -> RedisHealthParamsDict:
    """Get connection health and retry parameters for standalone and Sentinel Redis clients."""
    return RedisHealthParamsDict(
        retry=_get_retry_policy(),
        socket_timeout=dify_config.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=dify_config.REDIS_SOCKET_CONNECT_TIMEOUT,
        health_check_interval=dify_config.REDIS_HEALTH_CHECK_INTERVAL,
    )
```

**解读**：
- `socket_timeout`：单条命令超时，避免慢查询挂死业务
- `health_check_interval`：定期 PING 检测，淘汰时短暂阻塞也能恢复
- **背景**：Redis 在淘汰大量 key 时会短暂阻塞（`maxmemory-samples` 越大阻塞越长），这些参数保证客户端不永久卡死

### 3.3 Redis 故障时的降级

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
- 装饰器捕获 `RedisError`（包括 OOM 触发的写入错误）
- 返回 `default_return` 而非抛异常——**业务不因 Redis 故障崩溃**
- **设计哲学**：Redis 是 dify 的"加速器"，不是"主存"。真正的数据在 PostgreSQL，Redis 挂了业务仍可降级运行

## 4. 关键要点总结

- 默认策略是 `noeviction`（写入失败），生产环境**必须修改**
- 通用缓存推荐 `allkeys-lru`，热点场景 `allkeys-lfu`
- 临时数据用 `volatile-ttl` 配合 `SETEX`
- 监控 `evicted_keys` 和 `mem_fragmentation_ratio`
- dify 的 `redis_fallback` 装饰器让业务在 Redis 故障时优雅降级

## 5. 练习题

### 练习 1：基础（必做）

本地启动 Redis，配置 `maxmemory 100mb` + `allkeys-lru`，写入大量 key 观察淘汰日志：

```bash
redis-cli CONFIG SET maxmemory 100mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

for i in {1..100000}; do redis-cli SET key:$i value$i; done
redis-cli INFO stats | grep evicted
```

### 练习 2：进阶

对比 `allkeys-lru` 和 `allkeys-lfu` 在不同访问模式（热点 vs 均匀）下的命中率，写一个 benchmark 脚本。

### 练习 3：挑战（选做）

写一个监控脚本：当 `used_memory / maxmemory > 0.8` 时发送告警，建议运维扩容或调整策略。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 282-291、305-312、476-496 行）
- Redis 淘汰策略文档：https://redis.io/docs/reference/eviction/
- Redis LFU 论文解读：https://redis.io/blog/redis-4-0-rc1/

---

**文档版本**：v1.0
**最后更新**：2026-07-13