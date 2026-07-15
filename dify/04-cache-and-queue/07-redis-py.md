# 4.1.7 Redis Python 客户端：redis-py

> redis-py 是 Redis 官方推荐的 Python 客户端，dify 用它做所有 Redis 交互。

## 🎯 学习目标

完成本文档后，你将能够：
- 安装并使用 redis-py 进行基本操作
- 掌握连接池（Connection Pool）的概念
- 使用 Pipeline 批量操作提升性能
- 理解 dify 的 `RedisClientWrapper` 如何在原生客户端上做扩展

## 📚 前置知识

- Python 基础
- Redis 命令行基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- [Redis 事务与 Lua 脚本](./06-redis-transaction.md)（Pipeline / 事务背景）

## 1. 核心概念

### 1.1 为什么用连接池？

每次 `redis.Redis()` 调用不创建新 TCP 连接（默认启用连接池）。**连接池**预创建 N 个连接，重复利用：

```python
# 这两个 client 共享同一个连接池（默认）
r1 = redis.Redis(host="localhost", port=6379)
r2 = redis.Redis(host="localhost", port=6379)

# 显式共享池
pool = redis.ConnectionPool(host="localhost", port=6379, max_connections=50)
r1 = redis.Redis(connection_pool=pool)
r2 = redis.Redis(connection_pool=pool)
```

### 1.2 同步 vs 异步客户端

redis-py 同时提供同步（`redis.Redis`）和异步（`redis.asyncio.Redis`）客户端：

```python
# 同步
import redis
r = redis.Redis(...)
r.set("k", "v")

# 异步（async/await 机制详见 [async/asyncio](../01-fundamentals/12-async-asyncio.md)）
import redis.asyncio as aioredis
r = aioredis.Redis(...)
await r.set("k", "v")
```

dify 主要用**同步**客户端（因为 Celery worker 是同步的）。

### 1.3 哨兵 / 集群客户端

> 📌 **Sighting**：Sentinel / Cluster 的部署与故障转移原理见 [主从复制与 Sentinel](../../_common/01-redis/03-replication-sentinel.md)、[Redis Cluster](../../_common/01-redis/04-cluster.md)；此处只展示客户端如何连接。

```python
# 哨兵
from redis.sentinel import Sentinel
sentinel = Sentinel([("sentinel1", 26379)], socket_timeout=0.5)
master = sentinel.master_for("mymaster")

# 集群
from redis.cluster import RedisCluster
rc = RedisCluster(host="127.0.0.1", port=7000)
```

### 1.4 序列化与编码

- `decode_responses=True`：自动把 bytes 解码为 str
- `decode_responses=False`（默认）：返回 bytes
- dify 默认 `False`，因为部分场景需要二进制安全（如 Lua 脚本）

### 1.5 Pipeline 提升性能

```python
# 单条命令：每次 1 次 RTT
for i in range(1000):
    r.set(f"k{i}", i)

# Pipeline：批量发送，1 次 RTT
pipe = r.pipeline()
for i in range(1000):
    pipe.set(f"k{i}", i)
pipe.execute()
```

**性能提升**：1000 个 SET 从 ~50ms 降到 ~5ms（10 倍）。

## 2. 代码示例

### 2.1 基本操作

```python
import redis

r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    password=None,
    decode_responses=True,  # 自动解码为 str
    socket_timeout=5,       # 单条命令超时
    health_check_interval=30,
)

# 字符串
r.set("user:1:name", "Alice")
print(r.get("user:1:name"))  # "Alice"

# Hash
r.hset("user:1", mapping={"name": "Alice", "age": 30})
print(r.hgetall("user:1"))  # {'name': 'Alice', 'age': '30'}

# List
r.lpush("queue", "task1")
r.lpush("queue", "task2")
print(r.lrange("queue", 0, -1))  # ['task2', 'task1']

# Set
r.sadd("tags", "python", "redis")
print(r.smembers("tags"))  # {'python', 'redis'}

# Sorted Set
r.zadd("scores", {"alice": 100, "bob": 85})
print(r.zrevrange("scores", 0, -1, withscores=True))
```

### 2.2 连接池与性能

```python
import redis
from concurrent.futures import ThreadPoolExecutor

# 创建带连接池的客户端
pool = redis.ConnectionPool(
    host="localhost",
    port=6379,
    max_connections=50,
    decode_responses=True,
)
r = redis.Redis(connection_pool=pool)

# 多线程并发使用
def worker(i):
    r.set(f"thread:{i}", i)
    return r.get(f"thread:{i}")

with ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(worker, range(100)))
```

### 2.3 Pipeline 实战

```python
import time

r = redis.Redis(decode_responses=True)

# 对比 Pipeline vs 单条命令
def benchmark(use_pipeline=False, count=10000):
    start = time.time()
    if use_pipeline:
        with r.pipeline(transaction=False) as pipe:
            for i in range(count):
                pipe.set(f"bench:{i}", i)
            pipe.execute()
    else:
        for i in range(count):
            r.set(f"bench:{i}", i)
    return time.time() - start

print(f"单条命令: {benchmark(False):.2f}s")
print(f"Pipeline: {benchmark(True):.2f}s")
```

### 2.4 常见错误：忘记关闭连接

```python
# ❌ 错误：每次新建客户端（每次都创建连接池）
def process():
    r = redis.Redis(host="localhost")
    r.set("k", "v")  # 连接可能未立即关闭

# ✅ 正确：使用全局连接池
pool = redis.ConnectionPool(host="localhost", max_connections=50)
r = redis.Redis(connection_pool=pool)
r.set("k", "v")
```

### 2.5 常见错误：阻塞式 BRPOP 超时设置不当

```python
# ❌ 错误：超时 0 表示永久阻塞，Celery worker 永远卡住
task = r.brpop("queue", timeout=0)

# ✅ 正确：合理超时 + 心跳
task = r.brpop("queue", timeout=5)
```

## 3. dify 仓库源码解读

### 3.1 RedisClientWrapper 包装类

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 41-74）：

```python
class RedisClientWrapper:
    """
    A wrapper class for the Redis client that addresses the issue where the global
    `redis_client` variable cannot be updated when a new Redis instance is returned
    by Sentinel.
    """

    _client: Union[redis.Redis, RedisCluster, None]

    def __init__(self) -> None:
        self._client = None

    def initialize(self, client: Union[redis.Redis, RedisCluster]) -> None:
        if self._client is None:
            self._client = client

    def _require_client(self) -> redis.Redis | RedisCluster:
        if self._client is None:
            raise RuntimeError("Redis client is not initialized. Call init_app first.")
        return self._client

    def _get_prefix(self) -> str:
        return dify_config.REDIS_KEY_PREFIX
```

**解读**：
- **延迟初始化**：`_client` 先为 `None`，`init_app` 时才赋值。这样可以处理**Sentinel 切换 Master 时客户端重建**的场景
- **线程安全**：`initialize` 用 `if self._client is None` 保证只初始化一次
- **统一前缀**：所有方法通过 `_serialize_redis_name_arg` 加 `REDIS_KEY_PREFIX`，业务代码用裸 key 即可

### 3.2 __getattr__ 委托模式

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 217-218）：

```python
def __getattr__(self, item: str) -> Any:
    return getattr(self._require_client(), item)
```

**解读**：
- `redis_client.xxx` 调用会**自动转发**到底层客户端
- 但 dify **没有用这个机制**，而是显式定义了 `get`/`set`/`hset`/`lock` 等方法
- **原因**：显式方法可以**加 key 前缀**，而 `__getattr__` 直接转发拿不到包装逻辑
- 如果要调用 dify 没显式支持的方法（如 `r.zpopmin`），就会走到 `__getattr__`，此时 key 不会有前缀

### 3.3 同步连接池配置

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 399-418）：

```python
def _create_standalone_client(redis_params: RedisBaseParamsDict) -> Union[redis.Redis, RedisCluster]:
    """Create standalone Redis client."""
    connection_class, ssl_kwargs = _get_ssl_configuration()

    params: dict[str, Any] = {
        **redis_params,
        "host": dify_config.REDIS_HOST,
        "port": dify_config.REDIS_PORT,
        "connection_class": connection_class,
    }

    if dify_config.REDIS_MAX_CONNECTIONS:
        params["max_connections"] = dify_config.REDIS_MAX_CONNECTIONS

    if ssl_kwargs:
        params.update(ssl_kwargs)

    pool = redis.ConnectionPool(**params)
    client: redis.Redis = redis.Redis(connection_pool=pool)
    return client
```

**解读**：
- 第 416-417 行：显式创建 `ConnectionPool`，再传给 `redis.Redis`
- `max_connections` 限制最大并发连接数（防止 Redis 因客户端过多崩溃）
- `socket_timeout` 在 `_get_base_redis_params` 里设置，避免慢查询永久阻塞

### 3.4 Pub/Sub 客户端（独立连接）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 421-435）：

```python
def _create_pubsub_client(pubsub_url: str, use_clusters: bool) -> redis.Redis | RedisCluster:
    max_conns = dify_config.REDIS_MAX_CONNECTIONS

    if use_clusters:
        health_params = _get_cluster_connection_health_params()
        kwargs: dict[str, Any] = {**health_params}
        if max_conns:
            kwargs["max_connections"] = max_conns
        return RedisCluster.from_url(pubsub_url, **kwargs)

    standalone_health_params: dict[str, Any] = dict(_get_connection_health_params())
    kwargs = {**standalone_health_params}
    if max_conns:
        kwargs["max_connections"] = max_conns
    return redis.Redis.from_url(pubsub_url, **kwargs)
```

**解读**：
- Pub/Sub 用**独立的 Redis 实例**（可以与业务 Redis 不同）
- **原因**：Pub/Sub 是长连接（订阅后阻塞），不应该占用业务 Redis 的连接池
- 用 `from_url` 直接解析 `redis://host:port/db` 字符串，方便配置

## 4. 关键要点总结

- redis-py 提供同步和异步两种客户端
- **ConnectionPool** 复用 TCP 连接，避免每次新建
- **Pipeline** 批量发送命令，10x 性能提升
- dify 的 `RedisClientWrapper` 加 key 前缀，延迟初始化支持 Sentinel 切换
- Pub/Sub 用独立连接池，避免占用业务连接

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 实现一个简单的 Key-Value 缓存类，支持：
- 设置带 TTL 的值
- 获取值
- 删除值

```python
class Cache:
    def __init__(self):
        self.r = redis.Redis(decode_responses=True)

    def set(self, key, value, ttl=300):
        # TODO
        pass

    def get(self, key):
        # TODO
        pass

    def delete(self, key):
        # TODO
        pass
```

### 练习 2：进阶

对比**单条命令 vs Pipeline** 写入 10000 个 key 的耗时，画出性能对比图。

### 练习 3：挑战（选做）

实现一个**简单的分布式爬虫队列**：
- Master 用 `LPUSH` 推 URL
- 多个 Worker 用 `BRPOPLPUSH` 取 URL
- 处理完成用 `LREM` 从 processing 队列删除

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 41-218、399-435 行）
- redis-py 官方文档：https://redis.readthedocs.io/en/stable/
- redis-py GitHub：https://github.com/redis/redis-py

---

**文档版本**：v1.0
**最后更新**：2026-07-13