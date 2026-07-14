# 1.5 Redis 内存淘汰策略

> 掌握 Redis 内存满时的 8 种淘汰策略，正确选择适合业务场景的方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 LRU / LFU / TTL / 随机等淘汰策略的差异
- 理解 `maxmemory` 配置和惰性删除的交互
- 为不同业务（缓存、计数器、Session）选择合适的策略
- 监控 Redis 内存使用和淘汰命中

## 📚 前置知识

- Redis 基础数据结构（`01-redis/01-data-structures.md`）
- 缓存的基本概念（命中率、淘汰）
- 操作系统虚拟内存与内存压力

## 1. 核心概念

### 1.1 为什么需要淘汰策略？

Redis 是**内存数据库**，所有数据都在内存中。当 `maxmemory`（默认无限制）达到上限时：
- 如果**没有配置淘汰策略**，所有写命令报错（OOM）
- 如果**配置了淘汰策略**，Redis 按规则主动删除一些 key，为新数据腾出空间

### 1.2 八种淘汰策略详解

`maxmemory-policy` 配置项，可选值：

| 策略 | 含义 | 适用场景 |
|------|------|---------|
| `noeviction`（默认） | 不淘汰，写命令直接报错 | 数据不能丢的场景 |
| `allkeys-lru` | 所有 key 中淘汰最近最少使用 | **通用缓存**（最常用） |
| `allkeys-lfu` | 所有 key 中淘汰最不经常使用 | 热点数据明显，访问分布不均 |
| `allkeys-random` | 所有 key 中随机淘汰 | 数据热度均匀 |
| `volatile-lru` | 在带 TTL 的 key 中 LRU | 部分数据可丢，部分不能丢 |
| `volatile-lfu` | 在带 TTL 的 key 中 LFU | 同上 |
| `volatile-random` | 在带 TTL 的 key 中随机淘汰 | 同上 |
| `volatile-ttl` | 在带 TTL 的 key 中淘汰最快过期的 | Session、临时 token |

### 1.3 LRU vs LFU 的区别

- **LRU（Least Recently Used）**：淘汰**最近最少使用**，关注的是"时间最近"
- **LFU（Least Frequently Used）**：淘汰**访问频率最低**，关注的是"次数"

**例子**：
- key A 在 1 秒前被访问 1 次
- key B 在 100 秒前被访问 1000 次
- LRU 会淘汰 B（最近没访问）
- LFU 会淘汰 A（访问次数少）

**Redis 4.0+** 引入 LFU 计数器（用 morris counter 节省内存）。

### 1.4 近似 LRU 实现

Redis 不用真正的 LRU（维护链表成本高），而是用**近似 LRU**：
- 每个 key 维护 24-bit 的 `lru` 字段（最近一次访问时间）
- 淘汰时随机采样 N 个 key（默认 5，可配置），淘汰最久未访问的
- 采样数越大，越接近真实 LRU，性能略差

### 1.5 与 TTL 的关系

- `volatile-*` 策略只在带 TTL 的 key 中淘汰
- 如果所有 key 都没 TTL 或 TTL key 不够腾出空间，`volatile-*` 会退化为 `noeviction`（写报错）

### 1.6 监控关键指标

```bash
INFO memory        # 内存总量、碎片率
INFO stats          # evicted_keys（累计淘汰数）
CONFIG GET maxmemory
```

## 2. 代码示例

### 2.1 redis.conf 配置

```conf
# 设置最大内存为 4GB
maxmemory 4gb

# 选择淘汰策略
maxmemory-policy allkeys-lru

# 调整 LRU 采样数（默认 5，越大越精确）
maxmemory-samples 10

# 是否启用 LFU（Redis 4.0+）
# LFU 的两个参数：
#   lfu-log-factor 10       (计数器增长速度)
#   lfu-decay-time 1        (计数器衰减时间，单位分钟)
```

### 2.2 查看淘汰统计

```python
# 文件：example_eviction.py
import redis

r = redis.Redis(host="localhost", port=6379)

# 写入大量 key 触发淘汰
for i in range(100000):
    r.set(f"k:{i}", "x" * 100)

# 查看淘汰统计
stats = r.info("stats")
print(f"累计淘汰 key 数: {stats['evicted_keys']}")
print(f"keyspace 命中: {stats['keyspace_hits']}")
print(f"keyspace 未命中: {stats['keyspace_misses']}")

# 查看当前内存使用
memory = r.info("memory")
print(f"used_memory_human: {memory['used_memory_human']}")
print(f"maxmemory_human: {memory['maxmemory_human']}")
```

### 2.3 常见错误：缓存全部不带 TTL

```python
# ❌ 反例：所有 key 都用 SET（不带 EX），再配置 volatile-lru
for user in users:
    r.set(f"user:{user.id}", user.json())

# 问题：没有 key 带 TTL，volatile-lru 退化为 noeviction
# 内存写满后所有 SET 报错

# ✅ 正例 1：所有缓存都带 TTL
for user in users:
    r.setex(f"user:{user.id}", 3600, user.json())

# ✅ 正例 2：使用 allkeys-lru 策略
# CONFIG SET maxmemory-policy allkeys-lru
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 内存配置

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 282-302）：

```python
def _get_cache_configuration() -> CacheConfig | None:
    """Get client-side cache configuration if enabled."""
    if not dify_config.REDIS_ENABLE_CLIENT_SIDE_CACHE:
        return None

    resp_protocol = dify_config.REDIS_SERIALIZATION_PROTOCOL
    if resp_protocol < 3:
        raise ValueError("Client side cache is only supported in RESP3")

    return CacheConfig()


def _get_retry_policy() -> Retry:
    """Build the shared retry policy for Redis connections."""
    return Retry(
        backoff=ExponentialWithJitterBackoff(
            base=dify_config.REDIS_RETRY_BACKOFF_BASE,
            cap=dify_config.REDIS_RETRY_BACKOFF_CAP,
        ),
        retries=dify_config.REDIS_RETRY_RETRIES,
    )
```

**解读**：
- 第 3-5 行：通过 `REDIS_ENABLE_CLIENT_SIDE_CACHE` 配置启用**客户端缓存**（Redis 6+ 的 RESP3 协议特性），减少重复 GET 的网络开销
- 第 7-9 行：客户端缓存要求 `RESP3` 协议，RESP2 不支持——这是硬性约束
- **业务关联**：dify 用客户端缓存减少元数据访问（如 feature flag、配置中心），但**真正的缓存淘汰由服务端 Redis 的 `maxmemory-policy` 控制**

### 3.2 ruoyi 的缓存淘汰配置（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// application.yml - Redis 配置
spring:
  redis:
    host: 127.0.0.1
    port: 6379
    lettuce:
      pool:
        max-active: 200
        max-idle: 50
        min-idle: 10

// RedisCacheManager.java - Spring Cache 抽象
@Configuration
public class CacheConfig {
    @Bean
    public RedisCacheConfiguration cacheConfiguration() {
        return RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofHours(2))           // 默认 2 小时 TTL
                .serializeValuesWith(...)
                .disableCachingNullValues()
                .computePrefixWith(cacheName -> "ruoyi:cache:" + cacheName + ":");
    }
}
```

**解读**：
- 第 14 行：`entryTtl(Duration.ofHours(2))` 给所有 Spring Cache 写入的 key 设置默认 TTL，避免出现 `volatile-lru` 退化
- 第 17 行：统一加 `ruoyi:cache:` 前缀，方便按业务隔离

## 4. 关键要点总结

- **`allkeys-lru` 是通用缓存的最佳起点**（最常用且稳定）
- **`volatile-*` 必须配合 TTL**，否则退化为 `noeviction`
- **LFU 适合热点分布不均的场景**（如排行榜、爆款商品）
- 监控关键指标：`used_memory`、`maxmemory`、`evicted_keys`
- 生产环境务必设置 `maxmemory` 和 `maxmemory-policy`，避免 OOM 影响业务

## 5. 练习题

### 练习 1：基础（必做）

写一个 Python 脚本：
1. 设置 `maxmemory 100mb`
2. 设置 `maxmemory-policy allkeys-lru`
3. 循环写入 1000 个 1MB 的 key
4. 用 `INFO stats` 查看 `evicted_keys`

### 练习 2：进阶

对比 LRU 和 LFU 在以下场景的表现：
- 一个 key 每天被访问 1 次，持续 100 天（共 100 次）
- 一个 key 在 1 天内被访问 100 次，之后永不访问
- 哪个会被 LRU 淘汰？哪个会被 LFU 淘汰？

### 练习 3：挑战（选做）

阅读 Redis 源码（`src/evict.c`）的 `evictionPoolPopulate()`，解释近似 LRU 的采样算法为什么用 `pow(rand(), lfu_log_factor)` 计算访问频率？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- Redis 淘汰策略文档：https://redis.io/docs/reference/eviction/
- Redis LFU 实现解析：https://redis.io/blog/post/redis-eviction-policies-the-ones-you-need-to-know/

---

**文档版本**：v1.0
**最后更新**：2026-07-14