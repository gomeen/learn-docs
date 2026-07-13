# 4.1.2 Redis 持久化：RDB / AOF

> Redis 是内存数据库，但生产环境必须考虑崩溃恢复——RDB 和 AOF 是两种持久化机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RDB 和 AOF 的工作原理与差异
- 根据业务场景选择合适的持久化策略
- 配置 Redis 持久化参数
- 理解 dify 后端如何利用 Redis 持久化保证任务不丢失

## 📚 前置知识

- Redis 基础操作
- 文件 I/O 与磁盘写入原理
- 01-redis-data-structures.md

## 1. 核心概念

### 1.1 为什么需要持久化？

Redis 数据在内存中，**进程重启或机器宕机后数据会丢失**。持久化把内存数据保存到磁盘，重启时再加载回内存。

dify 的 Redis 承担两个角色：
1. **缓存**（临时数据，丢了无所谓）→ 不需要持久化
2. **Celery Broker / Result Backend**（任务队列，丢了会丢任务）→ 必须持久化

### 1.2 RDB（Redis Database）

**快照方式**：定时把内存全量数据 dump 到磁盘（`dump.rdb`）。

```bash
# 触发方式
SAVE       # 同步，主线程阻塞
BGSAVE     # 后台，fork 子进程
```

**配置**（`redis.conf`）：
```conf
save 900 1      # 900 秒内至少 1 个 key 变化 → 触发 BGSAVE
save 300 10     # 300 秒内至少 10 个 key 变化
save 60 10000   # 60 秒内至少 10000 个 key 变化
```

**原理**：父进程 `fork()` 子进程，子进程写临时 RDB 文件，完成后原子替换。`fork()` 用 **Copy-On-Write**，所以大数据集也很快。

**优点**：
- 紧凑的单文件，方便备份和迁移
- 启动加载速度快
- 对性能影响小（子进程负责写）

**缺点**：
- 可能丢失最后一次快照后的数据
- `fork()` 时大内存会阻塞（虽然极短）

### 1.3 AOF（Append Only File）

**日志方式**：记录每条**写命令**，重启时回放。

```bash
# 触发方式：每次写操作都 append 到 AOF 文件
SET key value  →  *3\r\n$3\r\nSET\r\n$3\r\nkey\r\n$5\r\nvalue\r\n
```

**配置**：
```conf
appendonly yes
appendfsync everysec  # 每秒 fsync 一次（推荐）
# appendfsync always  # 每次写都 fsync（最慢但最安全）
# appendfsync no      # 由 OS 决定 fsync 时机（最快但可能丢数据）
```

**AOF 重写（Rewrite）**：AOF 文件会越来越大，Redis 启动 BGREWRITEAOF 子进程，根据当前内存数据生成最小命令集。

**优点**：
- 数据安全性高（`everysec` 最多丢 1 秒）
- AOF 文件可读，便于排错

**缺点**：
- 文件体积通常比 RDB 大
- 写性能略低于 RDB（取决于 `appendfsync` 策略）

### 1.4 RDB vs AOF 对比

| 特性 | RDB | AOF |
|------|-----|-----|
| 持久化粒度 | 快照（某个时间点） | 每条写命令 |
| 数据安全 | 可能丢最后一次快照 | `everysec` 最多丢 1 秒 |
| 文件大小 | 紧凑（二进制）| 较大（文本）|
| 恢复速度 | 快 | 慢（需回放）|
| 写性能影响 | 小 | 中等 |
| 适用场景 | 备份、灾难恢复 | 高数据安全要求 |

**推荐方案**：生产环境**同时开启 RDB 和 AOF**。RDB 用于定时备份，AOF 用于实时持久化。

### 1.5 混合模式（Redis 4.0+）

AOF 文件前半段是 RDB 快照，后半段是增量 AOF。这样既快又安全：

```conf
aof-use-rdb-preamble yes
```

## 2. 代码示例

### 2.1 手动触发持久化

```python
import redis

r = redis.Redis(host="localhost", port=6379)

# 设置一些数据
r.set("user:1", "Alice")
r.hset("config", "theme", "dark")

# 手动触发 BGSAVE（异步）
r.bgsave()
print(r.lastsave())  # 上次保存的时间戳

# 手动触发 BGREWRITEAOF
r.bgrewriteaof()

# 检查 AOF 是否启用
print(r.config_get("appendonly"))  # {'appendonly': 'yes'}
```

### 2.2 模拟崩溃恢复

```bash
# 1. 启动 Redis，开启 AOF
redis-server --appendonly yes

# 2. 写入数据
redis-cli SET key1 "hello"

# 3. 强制崩溃（kill -9）
kill -9 $(pgrep redis-server)

# 4. 重启
redis-server --appendonly yes

# 5. 验证数据
redis-cli GET key1  # "hello"
```

### 2.3 常见错误：AOF 文件损坏

```bash
# AOF 文件可能在写入过程中损坏
# 用 redis-check-aof 修复
redis-check-aof --fix appendonly.aof
```

## 3. dify 仓库源码解读

### 3.1 Celery 配置：Redis 作为 Broker

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 39-88）：

```python
def get_celery_ssl_options() -> CelerySSLOptionsDict | None:
    """Get SSL configuration for Celery broker/backend connections."""
    # Only apply SSL if we're using Redis as broker/backend
    if not dify_config.BROKER_USE_SSL:
        return None

    # Check if Celery is actually using Redis
    broker_is_redis = dify_config.CELERY_BROKER_URL and (
        dify_config.CELERY_BROKER_URL.startswith("redis://") or dify_config.CELERY_BROKER_URL.startswith("rediss://")
    )

    if not broker_is_redis:
        return None

    cert_reqs_map = {
        "CERT_NONE": ssl.CERT_NONE,
        "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
        "CERT_REQUIRED": ssl.CERT_REQUIRED,
    }

    ssl_cert_reqs = cert_reqs_map.get(dify_config.REDIS_SSL_CERT_REQS, ssl.CERT_NONE)

    return CelerySSLOptionsDict(
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=dify_config.REDIS_SSL_CA_CERTS,
        ssl_certfile=dify_config.REDIS_SSL_CERTFILE,
        ssl_keyfile=dify_config.REDIS_SSL_KEYFILE,
    )


def get_celery_broker_transport_options() -> CelerySentinelTransportDict | dict[str, Any]:
    """Get broker transport options (e.g. Redis Sentinel) for Celery connections."""
    transport_options: CelerySentinelTransportDict | dict[str, Any]
    if dify_config.CELERY_USE_SENTINEL:
        transport_options = CelerySentinelTransportDict(
            master_name=dify_config.CELERY_SENTINEL_MASTER_NAME,
            sentinel_kwargs=_CelerySentinelKafkaDict(...),
        )
    else:
        transport_options = {}
    ...
```

**解读**：
- Celery 用 Redis 做 Broker 和 Result Backend，**必须开启 AOF 持久化**才能保证任务不丢
- 第 47-48 行：`broker_is_redis` 检查 Celery 是否真的用 Redis（也可能是 RabbitMQ）
- 第 91-96 行：`global_keyprefix` 让 Celery 的 Redis key 也加上 dify 前缀，避免多实例冲突
- **生产建议**：dify 部署 Redis 时应该 `appendonly yes` + `appendfsync everysec`

### 3.2 Redis 健康检查与重试

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 294-312）：

```python
def _get_retry_policy() -> Retry:
    """Build the shared retry policy for Redis connections."""
    return Retry(
        backoff=ExponentialWithJitterBackoff(
            base=dify_config.REDIS_RETRY_BACKOFF_BASE,
            cap=dify_config.REDIS_RETRY_BACKOFF_CAP,
        ),
        retries=dify_config.REDIS_RETRY_RETRIES,
    )


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
- 第 296-302 行：`ExponentialWithJitterBackoff`（指数退避 + 抖动）防止重试风暴
- 第 311 行：`health_check_interval` 让客户端定期发 `PING` 检测连接健康
- **背景**：当 Redis 正在 **BGSAVE / BGREWRITEAOF** 时，可能短暂不响应，这些重试参数保证客户端不会因为瞬时阻塞而永久失败

## 4. 关键要点总结

- **RDB**：定时快照，文件小、启动快，但可能丢数据
- **AOF**：记录每条写命令，安全性高（`everysec` 模式最多丢 1 秒）
- 生产环境**同时开启 RDB + AOF**（混合模式）
- Celery 用 Redis 做 Broker 时**必须开 AOF**
- `redis-check-aof --fix` 可修复损坏的 AOF 文件
- dify 用指数退避 + 健康检查应对 Redis 短暂阻塞（如持久化期间）

## 5. 练习题

### 练习 1：基础（必做）

本地启动 Redis，分别用 `SAVE` 和 `BGSAVE` 触发持久化，对比阻塞情况：

```bash
# 终端 1
redis-cli
> SET k1 v1
> BGSAVE    # 不阻塞
> SAVE      # 阻塞（观察 redis-cli 是否卡住）

# 终端 2：监控延迟
redis-cli --latency
```

### 练习 2：进阶

配置 Redis 开启混合持久化（AOF + RDB preamble），写入 100 万个 key 后重启，验证数据完整性。

### 练习 3：挑战（选做）

写一个脚本，监控 Redis 的 `rdb_last_bgsave_status` 和 `aof_last_rewrite_time_sec`，持久化失败时发送告警（邮件/Slack）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`
- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- Redis 持久化官方文档：https://redis.io/docs/management/persistence/
- Redis 混合模式说明：https://redis.io/docs/management/persistence/#log-only-rewrite

---

**文档版本**：v1.0
**最后更新**：2026-07-13