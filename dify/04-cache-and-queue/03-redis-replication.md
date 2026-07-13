# 4.1.3 Redis 主从复制与 Sentinel

> 单点 Redis 不可靠，主从复制 + Sentinel 自动故障转移是生产环境标配。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis 主从复制的原理（全量同步 + 增量同步）
- 掌握 Sentinel 监控/通知/自动故障转移机制
- 配置 Redis Sentinel 集群
- 理解 dify 的 Redis Sentinel 客户端如何处理 Master 切换

## 📚 前置知识

- Redis 基础
- TCP 网络通信
- 01-redis-data-structures.md、02-redis-persistence.md

## 1. 核心概念

### 1.1 主从复制（Replication）

Redis 的复制是**异步的**，一个 Master 可以有多个 Slave。

```
Client → Master (读写) → Slave1 (只读)
                  └──→ Slave2 (只读)
```

**配置**（Slave 端）：
```conf
replicaof 192.168.1.10 6379
masterauth yourpassword
replica-read-only yes
```

### 1.2 复制原理

**全量同步（Full Sync）**——Slave 首次连接或断开太久重连：
1. Slave 发送 `PSYNC ? -1`
2. Master 执行 `BGSAVE` 生成 RDB
3. Master 把 RDB 发给 Slave
4. Slave 加载 RDB
5. 同步期间 Master 的新写命令放入 **replication buffer**，之后发给 Slave

**增量同步（Partial Sync）**——Slave 重连但 `replid` 匹配：
- Master 通过 **repl_backlog**（固定大小的循环缓冲区）找到 Slave 断开时的位置
- 把断开期间的新写命令发给 Slave

```bash
# 查看复制状态
redis-cli INFO replication
```

### 1.3 Sentinel：自动故障转移

Sentinel 是一个**分布式监控进程**（建议至少 3 个独立节点），负责：
1. **监控**：持续检查 Master/Slave 是否健康
2. **通知**：Master 故障时通过 API 通知管理员
3. **自动故障转移**：选一个 Slave 提升为新 Master
4. **配置提供者**：客户端问 Sentinel 谁是 Master

```
Sentinel1 ─┐
Sentinel2 ─┼─→ 监控 Master / Slave
Sentinel3 ─┘
```

**客观下线（ODOWN）**：超过 quorum 个 Sentinel 认为 Master 不可达时才触发故障转移。

### 1.4 故障转移流程

1. Sentinel 检测到 Master 不可达 → 标记 SDOWN
2. 多个 Sentinel 确认 → 标记 ODOWN
3. 选举 Leader Sentinel（`Raft` 简化版）
4. Leader 从 Slave 中选出**最优从节点**（优先级 → 复制偏移量 → runid）
5. 提升新 Master，命令其他 Slave 复制新 Master
6. 通知客户端新 Master 地址

## 2. 代码示例

### 2.1 配置 Sentinel（最小化）

```bash
# sentinel.conf
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 60000
sentinel auth-pass mymaster yourpassword
```

启动：
```bash
redis-sentinel /path/to/sentinel.conf
```

### 2.2 redis-py 连接 Sentinel

```python
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [("sentinel1", 26379), ("sentinel2", 26379), ("sentinel3", 26379)],
    socket_timeout=0.5,
    password="yourpassword",
)

# 获取 Master 客户端
master = sentinel.master_for("mymaster", socket_timeout=0.5)
master.set("key", "value")

# 获取 Slave 客户端（只读）
slave = sentinel.slave_for("mymaster", socket_timeout=0.5)
print(slave.get("key"))
```

### 2.3 常见错误：客户端没处理 Master 切换

```python
# ❌ 错误：硬编码 Master 地址
r = redis.Redis(host="master.example.com", port=6379)
# Master 挂了，客户端不知道新 Master 是谁

# ✅ 正确：用 Sentinel 自动发现
sentinel = Sentinel([("sentinel1", 26379)], socket_timeout=0.5)
master = sentinel.master_for("mymaster")
# 故障转移后，下次 master_for() 调用会自动返回新 Master
```

## 3. dify 仓库源码解读

### 3.1 Sentinel 客户端创建

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 347-373）：

```python
def _create_sentinel_client(redis_params: RedisBaseParamsDict) -> Union[redis.Redis, RedisCluster]:
    """Create Redis client using Sentinel configuration."""
    if not dify_config.REDIS_SENTINELS:
        raise ValueError("REDIS_SENTINELS must be set when REDIS_USE_SENTINEL is True")

    if not dify_config.REDIS_SENTINEL_SERVICE_NAME:
        raise ValueError("REDIS_SENTINEL_SERVICE_NAME must be set when REDIS_USE_SENTINEL is True")

    sentinel_hosts = [
        (node.split(":")[0], int(node.split(":")[1]))
        for node in dify_config.REDIS_SENTINELS.split(",")
    ]

    sentinel_kwargs = {
        "socket_timeout": dify_config.REDIS_SENTINEL_SOCKET_TIMEOUT,
        "username": dify_config.REDIS_SENTINEL_USERNAME,
        "password": dify_config.REDIS_SENTINEL_PASSWORD,
    }

    if dify_config.REDIS_MAX_CONNECTIONS:
        sentinel_kwargs["max_connections"] = dify_config.REDIS_MAX_CONNECTIONS

    sentinel = Sentinel(
        sentinel_hosts,
        sentinel_kwargs=sentinel_kwargs,
    )

    params: dict[str, Any] = {**redis_params}
    master: redis.Redis = sentinel.master_for(dify_config.REDIS_SENTINEL_SERVICE_NAME, **params)
    return master
```

**解读**：
- 第 355 行：把配置里的 `REDIS_SENTINELS=host1:26379,host2:26379,host3:26379` 解析成列表
- 第 366-369 行：实例化 `Sentinel`，**只连 Sentinel 节点**，不连 Master
- 第 372 行：`master_for(service_name)` 返回一个**动态发现**的 Master 客户端，每次调用都问 Sentinel "谁是 Master"
- **关键设计**：故障转移后，旧客户端持有的连接会失效，但下次调用 `master_for()` 会自动拿到新 Master

### 3.2 Celery 配合 Sentinel

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 70-88）：

```python
def get_celery_broker_transport_options() -> CelerySentinelTransportDict | dict[str, Any]:
    """Get broker transport options (e.g. Redis Sentinel) for Celery connections."""
    transport_options: CelerySentinelTransportDict | dict[str, Any]
    if dify_config.CELERY_USE_SENTINEL:
        transport_options = CelerySentinelTransportDict(
            master_name=dify_config.CELERY_SENTINEL_MASTER_NAME,
            sentinel_kwargs=_CelerySentinelKwargsDict(
                socket_timeout=dify_config.CELERY_SENTINEL_SOCKET_TIMEOUT,
                password=dify_config.CELERY_SENTINEL_PASSWORD,
            ),
        )
    else:
        transport_options = {}

    global_keyprefix = get_celery_redis_global_keyprefix()
    if global_keyprefix:
        transport_options["global_keyprefix"] = global_keyprefix

    return transport_options
```

**解读**：
- 第 73-79 行：当 `CELERY_USE_SENTINEL=True` 时，Celery 的 broker 走 Sentinel
- 第 84 行：`global_keyprefix` 给 Celery 用的 Redis key 也加 dify 前缀，避免多个 dify 实例共享 Redis 时冲突
- **Celery + Sentinel 的好处**：Master 故障时，Celery worker 自动重连新 Master，**正在执行的任务不中断**（已 dispatch 的任务在内存中完成）

## 4. 关键要点总结

- **主从复制**：异步、级联，支持全量同步（RDB）和增量同步（repl_backlog）
- **Sentinel**：至少 3 个节点，quorum ≥ 2 时触发故障转移
- 客户端必须用 `Sentinel.master_for()` 而不是直连 Master
- dify 同时支持**业务 Redis** 和 **Celery broker Redis** 走 Sentinel
- 故障转移后业务可能短暂不可用，dify 用 `redis_fallback` 装饰器降级

## 5. 练习题

### 练习 1：基础（必做）

本地用 Docker Compose 启动 1 Master + 2 Slave + 3 Sentinel，验证故障转移：

```yaml
# docker-compose.yml
services:
  redis-master:
    image: redis:7
    command: redis-server --requirepass mypass
  redis-slave:
    image: redis:7
    command: redis-server --replicaof redis-master 6379 --requirepass mypass
```

### 练习 2：进阶

写 Python 脚本向 Sentinel 注册的 Master 持续写入，`kill -9` Master 后观察客户端行为。

### 练习 3：挑战（选做）

阅读 `redis-py` 的 `SentinelConnectionPool` 源码，理解它如何处理 Master 切换时的连接重建。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 347-373 行）
- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`（第 70-88 行）
- Redis Sentinel 官方文档：https://redis.io/docs/management/sentinel/
- redis-py Sentinel 文档：https://redis.readthedocs.io/en/stable/sentinel.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13