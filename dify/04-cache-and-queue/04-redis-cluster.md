# 4.1.4 Redis Cluster 集群模式

> 当单 Master 写性能不足时，Redis Cluster 提供水平扩展方案——数据自动分片到多个节点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis Cluster 的数据分片原理（16384 哈希槽）
- 掌握节点通信（Gossip）和故障检测机制
- 配置多 Master 集群
- 理解 dify 在大流量场景下如何启用 Redis Cluster

## 📚 前置知识

- Redis 主从复制
- 一致性哈希基础
- 03-redis-replication.md

## 1. 核心概念

### 1.1 为什么需要 Cluster？

Sentinel 解决**高可用**（HA），但不解决**水平扩展**。当：
- 单节点内存达到瓶颈（> 几十 GB）
- 单节点 QPS 达到瓶颈（> 10 万/秒）

就需要把数据分散到多台机器——这就是 Cluster。

### 1.2 哈希槽（Hash Slot）

Redis Cluster 把数据分成 **16384 个槽**，每个 key 通过 CRC16 算法映射到某个槽：

```
slot = CRC16(key) % 16384
```

每个 Master 负责一部分槽（例如 Master A 负责 0-5460，Master B 负责 5461-10922...）。

**关键限制**：
- 多 key 操作必须在**同一个槽**（用 `{tag}` 强制）
- `MSET k1 v1 k2 v2` 默认失败（k1、k2 可能在不同槽）
- 解决：`MSET k1{user:1} v1 k2{user:1} v2`（花括号内是 tag，整个 tag 一起算 CRC）

### 1.3 节点通信：Gossip 协议

每个节点每秒随机 ping 几个其他节点，交换**节点视图**（谁在线、谁负责哪些槽、谁是 Slave）。最终所有节点对集群拓扑达成一致。

```
Node1 ←→ Node2 ←→ Node3
  ↕        ↕        ↕
Node4 ←→ Node5 ←→ Node6
```

### 1.4 故障转移（集群内）

集群内 Master 故障时：
1. 该 Master 的某个 Slave 发现 ping 超时
2. Slave 发起**选举**（类似 Raft，但更简单）
3. 多数 Master 投票通过 → Slave 提升为新 Master
4. 集群重新分配槽位

**不需要 Sentinel**——故障检测和转移内置在集群协议中。

### 1.5 ASK / MOVED 重定向

客户端访问错误节点时，Redis 返回 `MOVED 1234 192.168.1.5:6379`，客户端**重定向**到正确节点。

```
> GET key_in_other_slot
(error) MOVED 1234 192.168.1.5:6379
```

智能客户端（如 `redis-py` Cluster）会自动重定向。

## 2. 代码示例

### 2.1 启动 6 节点集群（3 Master + 3 Slave）

```bash
# 启动 6 个节点（端口 7000-7005）
for port in 7000 7001 7002 7003 7004 7005; do
  mkdir -p /tmp/redis-cluster/$port
  cat > /tmp/redis-cluster/$port/redis.conf <<EOF
port $port
cluster-enabled yes
cluster-config-file nodes-$port.conf
cluster-node-timeout 5000
appendonly yes
EOF
  redis-server /tmp/redis-cluster/$port/redis.conf
done

# 创建集群
redis-cli --cluster create \
  127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
  127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
  --cluster-replicas 1
```

### 2.2 redis-py 连接 Cluster

```python
from redis.cluster import RedisCluster

# 只需连一个节点，客户端会自动发现整个集群
rc = RedisCluster(
    host="127.0.0.1",
    port=7000,
    decode_responses=True,
)

# 自动路由到正确的节点
rc.set("key1", "value1")     # CRC16("key1") % 16384 → 某个节点
rc.set("key2", "value2")     # 可能路由到另一个节点

# 多 key 操作必须用 hash tag
rc.mset({"user:1:name": "Alice", "user:1:age": "30"})
# 错误示例：rc.mset({"user:1:name": "Alice", "user:2:name": "Bob"})
```

### 2.3 查看槽位分布

```bash
redis-cli --cluster check 127.0.0.1:7000

# 输出类似：
# 127.0.0.1:7000 (e7d...) -> 3 keys | 5462 slots | 1 slaves
# 127.0.0.1:7001 (9c1...) -> 2 keys | 5461 slots | 1 slaves
# 127.0.0.1:7002 (4a8...) -> 1 keys | 5461 slots | 1 slaves
```

### 2.4 常见错误：跨槽事务

```python
# ❌ 错误：跨槽的 MULTI/EXEC 失败
with rc.pipeline(transaction=True) as pipe:
    pipe.set("user:1:name", "Alice")  # 槽 1234
    pipe.set("user:2:name", "Bob")    # 槽 5678
    pipe.execute()  # CROSSSLOT error!

# ✅ 正确：用 hash tag 强制同槽
with rc.pipeline(transaction=True) as pipe:
    pipe.set("user:1:name", "Alice")
    pipe.set("user:1:age", "30")      # {user:1} 同槽
    pipe.execute()  # OK
```

## 3. dify 仓库源码解读

### 3.1 Cluster 客户端创建

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 376-396）：

```python
def _create_cluster_client() -> Union[redis.Redis, RedisCluster]:
    """Create Redis cluster client."""
    if not dify_config.REDIS_CLUSTERS:
        raise ValueError("REDIS_CLUSTERS must be set when REDIS_USE_CLUSTERS is True")

    nodes = [
        ClusterNode(host=node.split(":")[0], port=int(node.split(":")[1]))
        for node in dify_config.REDIS_CLUSTERS.split(",")
    ]

    cluster_kwargs: dict[str, Any] = {
        "startup_nodes": nodes,
        "password": dify_config.REDIS_CLUSTERS_PASSWORD,
        "protocol": dify_config.REDIS_SERIALIZATION_PROTOCOL,
        "cache_config": _get_cache_configuration(),
        **_get_cluster_connection_health_params(),
    }
    if dify_config.REDIS_MAX_CONNECTIONS:
        cluster_kwargs["max_connections"] = dify_config.REDIS_MAX_CONNECTIONS
    cluster: RedisCluster = RedisCluster(**cluster_kwargs)
    return cluster
```

**解读**：
- 第 382 行：解析 `REDIS_CLUSTERS` 配置，构造多个 `ClusterNode`（启动节点）
- 第 387 行：`startup_nodes` 是**种子节点**，客户端连上去后会自动发现整个集群拓扑
- 第 390 行：`cache_config` 启用客户端侧缓存（需要 RESP3 协议）
- 第 391 行：`_get_cluster_connection_health_params` 排除了 `health_check_interval`——因为 RedisCluster 不支持该参数

### 3.2 init_app 自动选择 Cluster 或 Sentinel

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 438-461）：

```python
def init_app(app: DifyApp):
    """Initialize Redis client and attach it to the app."""
    global redis_client

    # Determine Redis mode and create appropriate client
    if dify_config.REDIS_USE_SENTINEL:
        redis_params = _get_base_redis_params()
        client = _create_sentinel_client(redis_params)
    elif dify_config.REDIS_USE_CLUSTERS:
        client = _create_cluster_client()
    else:
        redis_params = _get_base_redis_params()
        client = _create_standalone_client(redis_params)

    # Initialize the wrapper and attach to app
    redis_client.initialize(client)
    app.extensions["redis"] = redis_client

    global _pubsub_redis_client
    _pubsub_redis_client = client
    if dify_config.normalized_pubsub_redis_url:
        _pubsub_redis_client = _create_pubsub_client(
            dify_config.normalized_pubsub_redis_url, dify_config.PUBSUB_REDIS_USE_CLUSTERS
        )
```

**解读**：
- 第 443-450 行：互斥分支——**Sentinel / Cluster / Standalone** 三选一
- 第 454 行：包装类 `redis_client` 把底层客户端封装起来，业务代码无感切换
- 第 458-461 行：**Pub/Sub** 可以单独用一个 Redis（避免影响主集群），且 Pub/Sub 在 Cluster 模式下需要 Sharded 或 Streams

### 3.3 PubSub 在 Cluster 下的特殊处理

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
**核心代码**（行 49-60）：

```python
def publish(self, payload: bytes) -> None:
    self._client.publish(self._redis_topic, payload)

def as_subscriber(self) -> Subscriber:
    return self

def subscribe(self) -> Subscription:
    return _RedisSubscription(
        client=self._client,
        pubsub=self._client.pubsub(),
        topic=self._redis_topic,
    )
```

**解读**：
- 第 50 行：`PUBLISH` 在 Cluster 模式下会广播到**所有节点**，保证订阅者能收到
- 第 56-59 行：订阅时拿到一个 `pubsub` 对象，普通 Pub/Sub 在 Cluster 下有限制（必须订阅每个节点的 channel），所以 dify 也支持 **Sharded PubSub** 和 **Streams**（详见后续章节）

## 4. 关键要点总结

- Redis Cluster 把数据分成 16384 个哈希槽，每个 Master 负责一段
- 客户端通过 Gossip 协议发现集群拓扑，智能客户端自动路由
- 多 key 操作必须用 `{tag}` 强制同槽
- 故障检测和转移内置，不需要 Sentinel
- dify 通过配置 `REDIS_USE_CLUSTERS=True` 启用 Cluster，自动处理哨兵/集群/单机切换

## 5. 练习题

### 练习 1：基础（必做）

本地用 Docker Compose 启动一个 6 节点 Redis Cluster，用 `redis-cli --cluster info` 查看槽位分布。

### 练习 2：进阶

写一个 Python 脚本，对 10000 个 key 执行 `SET`，统计每个 Master 收到的 key 数量，验证分片均匀性。

### 练习 3：挑战（选做）

阅读 `redis-py` 的 `RedisCluster.execute_command` 源码，理解它如何处理 `MOVED` 重定向。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 376-461 行）
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
- Redis Cluster 官方文档：https://redis.io/docs/management/scaling/
- redis-py Cluster 文档：https://redis.readthedocs.io/en/stable/cluster.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13