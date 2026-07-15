# 1.3 Redis 主从复制与 Sentinel

> 理解 Redis 高可基石：主从架构与 Sentinel 哨兵自动故障转移。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Redis 主从复制的原理（fork / 全量同步 / 增量同步）
- 理解 Sentinel 的监控、选主、通知、配置提供四大职责
- 配置 Sentinel 集群并处理 failover
- 在 dify 中找到 Sentinel 连接配置

## 📚 前置知识

- Redis 基础命令与配置
- 网络 TCP 连接与 socket 超时
- `01-redis/02-persistence.md`（推荐）

## 1. 核心概念

### 1.1 为什么需要主从？

单机 Redis 存在两大风险：
1. **数据丢失风险**：磁盘损坏 / 机器宕机
2. **单点性能瓶颈**：单实例的 QPS 和内存有上限

主从架构通过 **读写分离** + **数据冗余** 同时解决这两个问题。

### 1.2 主从复制的三种角色

- **Master**：唯一可写节点，处理所有写命令
- **Replica（从 Redis 5.0 起替代 slave 称呼）**：只读，异步复制 Master 数据
- **Sentinel**：独立的监控进程，负责 Master 健康检查和自动 failover

### 1.3 复制流程（首次连接）

```
Replica                              Master
  |                                    |
  |----- 1. PSYNC ? -1 ------------->|  (请求全量同步)
  |<---- 2. +FULLRESYNC <replid> ----|  (返回 replid + offset)
  |                                    |
  |----- 3. BGSAVE 生成 RDB（持久化见 [02-persistence](./02-persistence.md)）--------->|
  |<---- 4. 发送 RDB 文件 ------------|
  |<---- 5. 发送缓冲区新写命令 -------|
  |                                    |
  | 加载 RDB + 重放命令，进入一致状态  |
```

**关键点**：
- Master `fork` 子进程生成 RDB，**不阻塞主线程处理写命令**
- 期间的新命令存入 **replication buffer**，全量同步完成后发给 Replica

### 1.4 增量复制（断线重连）

如果 Replica 短暂断线后重连，且 Master 的 `repl_backlog` 缓冲区还包含断线期间的命令，就走**增量复制**（只发送缺失的命令），避免全量同步。

`repl_backlog_size` 默认 1MB，**太小会导致频繁全量同步**。

### 1.5 Sentinel 架构

Sentinel 本身是一个分布式系统（建议至少 3 个实例），提供：

| 能力 | 说明 |
|------|------|
| **监控（Monitoring）** | 持续检查 Master / Replica 健康 |
| **通知（Notification）** | 故障时通过 API 报警 |
| **自动故障转移（Automatic failover）** | Master 宕机时选举新 Master |
| **配置提供（Configuration provider）** | 客户端从 Sentinel 获取当前 Master 地址 |

### 1.6 Sentinel 选举流程

1. 多个 Sentinel 独立检测到 Master 不可达（subjectively down）
2. 达到 quorum 数量后标记为 **ODOWN（objectively down）**
3. 选举一个 Sentinel Leader 进行 failover
4. Sentinel Leader 按规则选新 Master：
   - replica-priority 低的优先
   - 同步进度（offset）大的优先
   - runid 字典序小的兜底
5. 通知其他 Replica 切换 Master，并向客户端广播新地址

## 2. 代码示例

### 2.1 sentinel.conf 配置

```conf
# sentinel monitor <master-name> <ip> <port> <quorum>
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1

# 如果 Master 配置了密码
sentinel auth-pass mymaster yourpassword
```

### 2.2 redis-py 连接 Sentinel

```python
# 文件：example_sentinel.py
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [("sentinel-1", 26379), ("sentinel-2", 26379), ("sentinel-3", 26379)],
    socket_timeout=0.5,
    password="yourpassword",
)

# 获取当前 Master 客户端
master = sentinel.master_for("mymaster", socket_timeout=0.5)
master.set("foo", "bar")
print(master.get("foo"))

# 获取一个 Replica 客户端（只读）
replica = sentinel.slave_for("mymaster", socket_timeout=0.5)
print(replica.get("foo"))

# 发现所有 Master / Replica
print(sentinel.discover_master("mymaster"))
print(sentinel.discover_slaves("mymaster"))
```

### 2.3 常见错误：单点 Sentinel

```python
# ❌ 反例：只部署 1 个 Sentinel
sentinel = Sentinel([("sentinel-1", 26379)], ...)

# 风险：Sentinel 本身宕机 → 无法触发 failover

# ✅ 正例：至少 3 个 Sentinel，奇数个，分布在不同机器
sentinel = Sentinel(
    [("sentinel-1", 26379), ("sentinel-2", 26379), ("sentinel-3", 26379)],
    ...
)
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Sentinel 客户端创建

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 347-373）：

```python
def _create_sentinel_client(redis_params: RedisBaseParamsDict) -> Union[redis.Redis, RedisCluster]:
    """Create Redis client using Sentinel configuration."""
    if not dify_config.REDIS_SENTINELS:
        raise ValueError("REDIS_SENTINELS must be set when REDIS_USE_SENTINEL is True")

    if not dify_config.REDIS_SENTINEL_SERVICE_NAME:
        raise ValueError("REDIS_SENTINEL_SERVICE_NAME must be set when REDIS_USE_SENTINEL is True")

    sentinel_hosts = [(node.split(":")[0], int(node.split(":")[1]))
                      for node in dify_config.REDIS_SENTINELS.split(",")]

    sentinel_kwargs = {
        "socket_timeout": dify_config.REDIS_SENTINEL_SOCKET_TIMEOUT,
        "username": dify_config.REDIS_SENTINEL_USERNAME,
        "password": dify_config.REDIS_SENTINEL_PASSWORD,
    }

    if dify_config.REDIS_MAX_CONNECTIONS:
        sentinel_kwargs["max_connections"] = dify_config.REDIS_MAX_CONNECTIONS

    sentinel = Sentinel(sentinel_hosts, sentinel_kwargs=sentinel_kwargs)
    params: dict[str, Any] = {**redis_params}
    master: redis.Redis = sentinel.master_for(dify_config.REDIS_SENTINEL_SERVICE_NAME, **params)
    return master
```

**解读**：
- 第 3-7 行：硬性校验——若开启 Sentinel 但未配置 `REDIS_SENTINELS` 或 `REDIS_SENTINEL_SERVICE_NAME`，**直接抛错而不是用默认值**，避免错误配置导致生产事故
- 第 8-9 行：解析 `host1:port1,host2:port2` 字符串为 `(host, port)` 元组列表
- 第 11-15 行：Sentinel 自身的认证参数独立于 Redis 业务密码
- 第 22 行：`master_for()` 返回的客户端会在每次操作时**通过 Sentinel 查询当前 Master 地址**，failover 后无需重启应用

**整体设计意图**：dify 把 Sentinel 配置抽到环境变量，应用启动时根据 `REDIS_USE_SENTINEL` 标志动态选择连接方式，零代码改动支持多种部署模式。

### 3.2 ruoyi 的 Redis Sentinel（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// YudaoRedisAutoConfiguration.java
@Bean
@ConfigurationProperties(prefix = "spring.redis.sentinel")
public SentinelConfiguration sentinelConfig() {
    return new SentinelConfiguration();
}

@Bean
public RedisConnectionFactory redisConnectionFactory(SentinelConfiguration config) {
    RedisSentinelConfiguration sentinelCfg = new RedisSentinelConfiguration();
    sentinelCfg.setMaster(config.getMaster());
    sentinelCfg.setSentinels(config.getNodes());
    sentinelCfg.setPassword(config.getPassword());
    return new LettuceConnectionFactory(sentinelCfg);
}
```

**解读**：
- 第 2-6 行：把 `spring.redis.sentinel.*` 配置绑定到 `SentinelConfiguration`
- 第 9 行：`RedisSentinelConfiguration` 是 Spring Data Redis 提供的哨兵配置类
- 同样通过 `LettuceConnectionFactory` 实现 failover 后的自动重连

## 4. 关键要点总结

- **主从复制**是异步的，存在最终一致性窗口
- **首次连接走全量（RDB）**，**断线重连走增量（backlog）**
- **Sentinel 至少 3 节点**部署，避免单点
- 客户端通过 `sentinel.master_for()` 自动感知 Master 变更，无需重启
- dify 中通过 `REDIS_USE_SENTINEL=true` 启用，无需改代码

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 启动一个伪 Sentinel 场景：
1. 启动 master（6379）和 replica（6380，配置 `replicaof 127.0.0.1 6379`）
2. 在 master 写入 `SET k v`，验证 replica 能读到

### 练习 2：进阶

阅读 `dify/api/extensions/ext_redis.py` 的 `init_app()` 函数，画出从 `REDIS_USE_SENTINEL=true` 到 `redis_client.initialize(client)` 的完整调用链。

### 练习 3：挑战（选做）

解释 Sentinel 的 **Raft-like 选举**：为什么 Sentinel Leader 需要大多数投票才能执行 failover？这与 Redis Cluster 的 gossip 协议有何本质区别？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- Redis Sentinel 官方文档：https://redis.io/docs/management/sentinel/
- Redis 复制详解：https://redis.io/docs/management/replication/

---

**文档版本**：v1.0
**最后更新**：2026-07-14