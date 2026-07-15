# 1.4 Redis Cluster 集群模式

> 理解 Redis Cluster 的数据分片、slot 路由与故障转移机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Redis Cluster 的 16384 slot 分片原理
- 理解客户端如何路由到正确的节点
- 区分 Cluster 与 Sentinel 的适用场景
- 在 dify 配置中启用 Cluster 模式

## 📚 前置知识

- Redis 主从复制（`01-redis/03-replication-sentinel.md`）
- 一致性哈希与虚拟节点概念
- TCP 长连接与连接池

## 1. 核心概念

### 1.1 为什么需要 Cluster？

主从 + [Sentinel](./03-replication-sentinel.md) 解决的是**高可用**，但单 Master 的内存和 QPS 仍有上限。Cluster 通过**数据分片**突破单机限制。

### 1.2 核心概念：16384 个 slot

Redis Cluster 把整个 key 空间分成 **16384 个 hash slot**：
- 每个 key 通过 `CRC16(key) % 16384` 映射到一个 slot
- 每个 Master 负责一部分 slot（如 Master A 负责 0-5460，B 负责 5461-10922，...）
- slot 可以在节点间**迁移**（`redis-cli --cluster reshard`）

**为什么是 16384？**
- 太小：节点多时分配不均
- 太大：心跳包携带 slot 位图（2KB）浪费带宽
- 16384 是平衡点：位图 2KB，单节点最多 1000+ 节点，迁移粒度足够细

### 1.3 节点通信：Gossip 协议

每个节点每秒向若干其他节点发送 **PING**，携带自己认识的节点列表和状态。通过 gossip 协议，整个集群状态在几秒内达成一致。

### 1.4 客户端路由

客户端发送命令时：
1. 计算 key 的 slot
2. 通过本地缓存或 `MOVED` 重定向找到该 slot 对应的节点
3. 发送命令

如果客户端连到错误的节点，Redis 返回 `MOVED <slot> <ip>:<port>`，客户端重定向。

### 1.5 Cluster 与 Sentinel 的对比

| 维度 | Sentinel | Cluster |
|------|---------|---------|
| 数据规模 | 单 Master 容量 | 多 Master 分片，理论无限 |
| 高可用 | Sentinel 选主 | 集群内自动选主 |
| 客户端复杂度 | 简单 | 需要支持 MOVED 重定向 |
| 多 key 操作 | 支持 | **限制**：同 slot 才支持事务/MGET |

### 1.6 Cluster 的限制

- **不支持多 key 跨 slot 事务**（Lua 脚本必须所有 key 在同一 slot，可用 hash tag `{user:1001}.profile` 强制同 slot）
- **不支持多数据库**（只有 db 0）
- **批量操作需 hash tag**：MSET / MGET 必须保证 key 在同一 slot
- 部署至少 **3 个 Master + 3 个 Replica** 才能完整测试 failover

## 2. 代码示例

### 2.1 redis-cli 创建集群

```bash
# 启动 6 个节点（3 master + 3 replica）
redis-server --port 7000 --cluster-enabled yes --cluster-config-file nodes-7000.conf --daemonize yes
redis-server --port 7001 --cluster-enabled yes --cluster-config-file nodes-7001.conf --daemonize yes
redis-server --port 7002 --cluster-enabled yes --cluster-config-file nodes-7002.conf --daemonize yes
redis-server --port 7003 --cluster-enabled yes --cluster-config-file nodes-7003.conf --daemonize yes
redis-server --port 7004 --cluster-enabled yes --cluster-config-file nodes-7004.conf --daemonize yes
redis-server --port 7005 --cluster-enabled yes --cluster-config-file nodes-7005.conf --daemonize yes

# 创建集群（一行命令完成）
redis-cli --cluster create 127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
                          127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
                          --cluster-replicas 1
```

### 2.2 redis-py 连接 Cluster

```python
# 文件：example_cluster.py
from redis.cluster import RedisCluster

# 方式 1：直接连接所有节点
rc = RedisCluster(
    startup_nodes=[
        {"host": "127.0.0.1", "port": 7000},
        {"host": "127.0.0.1", "port": 7001},
        {"host": "127.0.0.1", "port": 7002},
    ],
    decode_responses=True,
    skip_full_coverage_check=True,  # 启动时不需要所有节点在线
)

rc.set("foo", "bar")
print(rc.get("foo"))

# 查看 key 在哪个 slot
slot = rc.connection_pool.nodes.keyslot("foo")
print(f"key 'foo' 在 slot {slot}")

# 跨节点操作（每个 key 单独路由）
rc.mset({"k1": "v1", "k2": "v2"})  # 内部会拆分到不同节点

# 用 hash tag 强制同 slot
rc.mset({"{user:1001}.name": "alice", "{user:1001}.age": "30"})  # 都在同一 slot
```

### 2.3 常见错误：跨 slot 事务

```python
# ❌ 反例：跨 slot 事务
with rc.pipeline(transaction=True) as pipe:
    pipe.set("a", 1)
    pipe.set("b", 2)
    pipe.execute()
# 报错：CROSSSLOT Keys in request don't hash to the same slot

# ✅ 正例：用 hash tag
with rc.pipeline(transaction=True) as pipe:
    pipe.set("{trx:1}.a", 1)
    pipe.set("{trx:1}.b", 2)
    pipe.execute()
# OK，两个 key 都在 slot 16230
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Cluster 客户端创建

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
- 第 3-5 行：与 Sentinel 相同的硬性校验，缺失必填参数直接报错
- 第 7-9 行：解析 `host1:port1,host2:port2` 字符串为 `ClusterNode` 列表
- 第 11-17 行：Cluster 不支持 `health_check_interval`（在 `RedisClusterHealthParamsDict` 中被故意剔除，注释解释原因）
- 第 19 行：`RedisCluster(**kwargs)` 创建集群客户端，内部维护每个节点的连接池

**整体设计意图**：通过 `REDIS_USE_CLUSTERS` 标志统一 Sentinel 和 Cluster 的初始化路径，调用方拿到的 `redis.Redis | RedisCluster` 都是 Union 类型，调用语法完全一致。

### 3.2 ruoyi 的 Redis Cluster（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// YudaoRedisClusterConfiguration.java
@Bean
@ConfigurationProperties(prefix = "spring.redis.cluster")
public ClusterConfiguration clusterConfig() {
    return new ClusterConfiguration();
}

@Bean
public RedisConnectionFactory redisConnectionFactory(ClusterConfiguration config) {
    RedisClusterConfiguration clusterCfg = new RedisClusterConfiguration();
    clusterCfg.setClusterNodes(config.getNodes());
    clusterCfg.setPassword(config.getPassword());
    clusterCfg.setMaxRedirects(3);  // MOVED 重定向最多 3 次
    return new LettuceConnectionFactory(clusterCfg);
}
```

**解读**：
- 第 11 行：`setMaxRedirects(3)` 限制客户端跟随 MOVED 重定向的最大次数，防止错误配置导致无限循环

## 4. 关键要点总结

- Cluster 通过 **16384 个 slot** 把 key 空间分散到多个 Master
- 客户端计算 `CRC16(key) % 16384` 定位 slot，必要时跟随 `MOVED` 重定向
- **不支持跨 slot 事务**，必须用 hash tag `{xxx}` 强制同 slot
- 至少 **3 Master + 3 Replica** 才能完整测试 failover
- dify 通过 `REDIS_USE_CLUSTERS=true` 启用，客户端代码无感知

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 启动一个伪 Cluster（`RedisCluster` + 3 个本地端口），验证：
1. `SET k1 v1` 后 `KEYSLOT k1` 返回的 slot 编号
2. 不同 key 落到不同节点

### 练习 2：进阶

解释 hash tag 的工作原理：`{user:1001}.profile` 和 `{user:1001}.age` 为什么一定在同一个 slot？

### 练习 3：挑战（选做）

设计一个场景：如果 Redis Cluster 中某个 Master 宕机（但 Replica 还在），Cluster 是如何自动选主并通知客户端的？写出关键时间点和 gossip 消息。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- Redis Cluster 官方教程：https://redis.io/docs/management/scaling/
- Redis Cluster 规范：https://redis.io/docs/reference/cluster-spec/

---

**文档版本**：v1.0
**最后更新**：2026-07-14