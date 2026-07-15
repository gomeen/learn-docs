# 4.3 Zookeeper / etcd 分布式锁对比

> 理解基于 ZAB 协议和 Raft 协议的强一致分布式锁实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Zookeeper 和 etcd 的一致性协议（ZAB / Raft）
- 用 Zookeeper / etcd 实现分布式锁
- 对比 Redis / Zookeeper / etcd 三种方案的取舍
- 在 dify 中找到对应的实现

## 📚 前置知识

- [分布式锁基本要求](./01-requirements.md)
- [Redis 分布式锁](./02-redis-redlock.md)
- CAP 定理

## 1. 核心概念

### 1.1 为什么需要 Zookeeper / etcd 锁？

**Redis 锁的不足**（即使 RedLock）：
- 异步复制可能导致锁丢失
- 无法解决 GC 停顿
- 时钟跳跃影响锁过期

**强一致方案的诞生**：
- **Zookeeper**（Yahoo 开源）——基于 ZAB 协议
- **etcd**（CNCF）——基于 Raft 协议
- 两者都是 **CP 系统**，保证一致性优先

### 1.2 Zookeeper 锁原理

**核心数据结构**：临时顺序节点（Ephemeral Sequential Node）

```
锁路径：/locks/order_lock

节点结构：
/locks/order_lock/
├── _c_001   (client A 创建，序号 001)
├── _c_002   (client B 创建，序号 002)
└── _c_003   (client C 创建，序号 003)
```

**获取锁流程**：
1. 在 `/locks/order_lock` 下创建**临时顺序节点**（如 `_c_002`）
2. 获取 `/locks/order_lock` 下**所有子节点**并排序
3. 如果自己**序号最小**，获取锁成功
4. 否则**监听前一个节点**（`_c_001`）的删除事件
5. 前一个节点被删除（持锁者释放或崩溃），自己被唤醒，重新检查
6. 重复 2-5 步直到获取锁

**释放锁**：
- 删除自己创建的节点（临时节点，会话断开自动删除）

### 1.3 etcd 锁原理

**核心机制**：Lease（租约）+ Revision（版本号）

```
获取锁流程：
1. 创建租约（Lease），设置 TTL（如 10 秒）
2. 在 etcd 中 put key（带 lease）
3. key 的 revision 是全局递增的
4. 用事务（Txn）实现 CAS：
   - 如果 key 的 revision 是最小的 → 获取锁
   - 否则监听 revision-1 的 key
```

**释放锁**：
- 撤销租约（自动删除 key）

### 1.4 三种锁的对比

| 维度 | Redis SETNX | Zookeeper | etcd |
|------|-------------|-----------|------|
| **一致性协议** | 异步复制 | ZAB（Paxos） | Raft |
| **CAP 取舍** | AP | CP | CP |
| **锁丢失风险** | 有（主从切换） | 极低 | 极低 |
| **性能** | 极高 | 中 | 中 |
| **运维复杂度** | 低 | 高（需 ZK 集群） | 中 |
| **适用场景** | 多数业务 | 关键业务 | 云原生场景 |

### 1.5 ZAB vs Raft

**ZAB（Zookeeper Atomic Broadcast）**：
- 所有写入通过 Leader 串行化
- Follower 收到多数 ACK 后 Leader 提交
- 崩溃恢复时通过 ZXID 同步

**Raft**：
- 与 ZAB 类似，但设计更易理解
- Leader 选举 + 日志复制
- etcd / Consul / TiKV 都用 Raft

### 1.6 在 dify 中的应用

dify **不用** ZK / etcd，而是用 Redis 锁（详见 [02-redis-redlock](./02-redis-redlock.md)）。原因：
- dify 是 SaaS 服务，Redis 已部署
- 锁场景都是**非关键路径**（触发器刷新）
- 引入 ZK/etcd 增加运维成本

## 2. 代码示例

### 2.1 Zookeeper 分布式锁（kazoo 库）

```python
# 文件：example_zk_lock.py
from kazoo.client import KazooClient
from kazoo.recipe.lock import Lock
import time

# 1. 连接 Zookeeper
zk = KazooClient(hosts="localhost:2181")
zk.start()

# 2. 创建锁
lock_path = "/locks/order_lock"
lock = Lock(zk, lock_path)

# 3. 获取锁（阻塞）
with lock:    # 自动 acquire / release
    print("获取 ZK 锁成功")
    # 执行业务...
    time.sleep(2)
    print("释放锁")

zk.stop()
```

### 2.2 Zookeeper 锁的底层实现

```python
# 文件：example_zk_sequential.py
from kazoo.client import KazooClient
import time

zk = KazooClient(hosts="localhost:2181")
zk.start()

# 确保父节点存在
zk.ensure_path("/locks/order_lock")


def acquire_zk_lock(lock_path: str) -> str:
    """Zookeeper 顺序节点锁"""
    # 1. 创建临时顺序节点
    node_path = zk.create(
        f"{lock_path}/_c_",   # 路径前缀
        ephemeral=True,         # 临时节点（会话断开自动删除）
        sequence=True,          # 顺序节点（自动追加序号）
    )
    node_name = node_path.split("/")[-1]   # "_c_00000001"

    # 2. 列出所有子节点
    while True:
        children = zk.get_children(lock_path)
        children.sort()

        if node_name == children[0]:
            # 序号最小 → 获取锁
            return node_name

        # 监听前一个节点
        prev_node = children[children.index(node_name) - 1]
        prev_path = f"{lock_path}/{prev_node}"

        # 阻塞等待前一个节点删除
        if zk.exists(prev_path):
            @zk.DataWatch(prev_path)
            def watch_change(data, stat):
                # 触发后跳出循环
                pass

            # 简单实现：等 0.5 秒重试
            time.sleep(0.5)
        else:
            continue


# 使用
try:
    my_node = acquire_zk_lock("/locks/order_lock")
    print(f"获取锁: {my_node}")
    try:
        time.sleep(2)   # 业务处理
    finally:
        zk.delete(f"/locks/order_lock/{my_node}")
        print("释放锁")
finally:
    zk.stop()
```

### 2.3 etcd 分布式锁（python-etcd3）

```python
# 文件：example_etcd_lock.py
import etcd3
import time

# 1. 连接 etcd
client = etcd3.client(host="localhost", port=2379)

# 2. 创建租约（Lease）
lease = client.lease(10)   # 10 秒 TTL

# 3. 获取锁
lock_key = "/locks/order_lock"
acquired = client.put_if_not_exists(lock_key, b"locked", lease=lease)

if acquired:
    try:
        print("获取 etcd 锁成功")
        time.sleep(2)
        # 执行业务
    finally:
        # 释放锁（删除 key + 撤销租约）
        client.delete(lock_key)
        lease.revoke()
        print("释放锁")
else:
    print("锁被占用")

client.close()
```

### 2.4 常见错误：忘了设置 Lease

```python
# ❌ 反例：etcd put 不带 lease
client.put("/locks/order", b"locked")

# 问题：key 永不过期 → 客户端崩溃后锁永远不释放

# ✅ 正例：带 lease（自动过期）
lease = client.lease(10)   # 10 秒过期
client.put_if_not_exists("/locks/order", b"locked", lease=lease)
```

## 3. dify 仓库源码解读

### 3.1 dify 用 Redis 锁，不用 ZK/etcd

**说明**：dify 是 SaaS 应用，**全部锁用 Redis**（用 `SETNX`），核心代码在 [01-requirements](./01-requirements.md) 中已分析。

**文件位置**：`/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
**核心代码**（行 5-12）：

```python
def build_trigger_refresh_lock_key(tenant_id: str, subscription_id: str) -> str:
    """Build the Redis lock key for trigger subscription refresh in-flight protection."""
    return f"trigger_provider_refresh_lock:{tenant_id}_{subscription_id}"


def build_trigger_refresh_lock_keys(pairs: Sequence[tuple[str, str]]) -> list[str]:
    """Build Redis lock keys for a sequence of (tenant_id, subscription_id) pairs."""
    return list(starmap(build_trigger_refresh_lock_key, pairs))
```

**解读**：
- **为什么不用 ZK/etcd**：
  1. **运维成本**：ZK 集群至少 3 节点 + etcd 集群，对 SaaS 是负担
  2. **场景非关键**：触发器刷新失败只是"少了一次刷新"，不是"业务数据错误"
  3. **Redis 已部署**：复用现有基础设施
- **简化原则**：dify 倾向"够用就好"的工程哲学

### 3.2 ruoyi 的 Redisson + ZK 多重支持（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**（简化）：

```java
// Lock4jProperties.java - 多锁源配置
@Data
@ConfigurationProperties(prefix = "lock4j")
public class Lock4jProperties {
    private LockType lockType = LockType.REDLOCK;   // 默认为 RedLock
    private ZookeeperConfig zookeeper;
    private RedisConfig redis;
}

public enum LockType {
    REDIS, REDLOCK, ZOOKEEPER, CUSTOM
}

// RedisLock4j.java - 抽象锁接口
public interface DistributedLock {
    <T> T executeWithLock(String key, int waitSeconds, Supplier<T> action);
}

// ZookeeperLockImpl.java - ZK 实现
@Service
@ConditionalOnProperty(prefix = "lock4j", name = "lock-type", havingValue = "zookeeper")
public class ZookeeperLockImpl implements DistributedLock {
    @Resource
    private CuratorFramework curator;

    @Override
    public <T> T executeWithLock(String key, int waitSeconds, Supplier<T> action) {
        InterProcessMutex lock = new InterProcessMutex(curator, "/locks/" + key);
        try {
            if (lock.acquire(waitSeconds, TimeUnit.SECONDS)) {
                try {
                    return action.get();
                } finally {
                    lock.release();
                }
            }
            throw new LockException("获取 ZK 锁超时");
        } catch (Exception e) {
            throw new LockException("ZK 锁异常", e);
        }
    }
}
```

**解读**：
- 第 7 行：通过 `lock-type` 配置切换 Redis / RedLock / Zookeeper
- 第 22-23 行：Curator 的 `InterProcessMutex` 是 ZK 分布式锁的标准实现（Apache Curator）
- **设计优势**：业务代码用同一个接口（`DistributedLock`），切换锁源无需改业务代码

## 4. 关键要点总结

- **Zookeeper 用临时顺序节点**实现分布式锁，崩溃时自动释放
- **etcd 用 Lease + Revision**实现，配合 Raft 强一致
- **ZK/etcd 适合关键业务**（金融、支付），Redis 锁适合多数场景
- **dify 用 Redis 锁**（简化优先）；ruoyi 支持多锁源切换（灵活优先）
- **选择策略**：
  - 性能优先 + 容忍偶尔问题 → Redis
  - 强一致要求 → ZK / etcd
  - 灵活切换 → 抽象接口 + 多实现

## 5. 练习题

### 练习 1：基础（必做）

用 Python 的 `kazoo` 库实现 ZK 锁：
1. 连接 ZK（可用 `docker run zookeeper`）
2. 创建临时顺序节点
3. 实现"序号最小获取锁，否则监听前一个"
4. 测试两个客户端竞争

### 练习 2：进阶

对比 ZK、etcd、Redis 三种锁的**故障恢复时间**：
- Redis 主从切换需要多久？
- ZK/etcd 选举新 Leader 需要多久？
- 业务不可用时间分别是多少？

### 练习 3：挑战（选做）

设计一个**统一锁接口**（伪代码）：
1. 定义 `Lock` 接口（acquire / release）
2. 实现 RedisLock / ZkLock / EtcdLock
3. 业务代码通过配置切换锁源
4. 对比 dify 和 ruoyi 的设计哲学

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
- Zookeeper 分布式锁：https://zookeeper.apache.org/doc/current/recipes.html#sc_recipes_Locks
- etcd 分布式锁：https://etcd.io/docs/v3.5/learning/why/
- Raft 算法可视化：https://raft.github.io/raftscope/

---

**文档版本**：v1.0
**最后更新**：2026-07-14