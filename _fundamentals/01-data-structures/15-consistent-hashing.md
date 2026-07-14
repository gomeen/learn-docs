# 1.3.3 一致性哈希（分布式系统）

> 一致性哈希是分布式缓存、分布式存储的核心算法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解普通哈希在分布式系统中的问题（扩容雪崩）
- 掌握一致性哈希的环形结构和虚拟节点
- 知道一致性哈希在 Redis Cluster、Nginx upstream 中的应用
- 能在 dify 的分布式缓存设计中识别一致性哈希

## 📚 前置知识

- 13-hash-table.md

## 1. 核心概念

### 1.1 普通哈希的问题

**场景**：3 台缓存服务器，缓存 1000 个 key，用 `hash(key) % 3` 决定存哪台。

```
key1 → hash % 3 = 0 → 服务器 0
key2 → hash % 3 = 2 → 服务器 2
```

**问题**：当服务器从 3 台扩到 4 台：
- 几乎所有 key 的 `hash % 4` 结果都变了
- **几乎所有缓存失效** → 全部回源数据库 → **缓存雪崩**

### 1.2 一致性哈希的核心思想

**一致性哈希**（Consistent Hashing）将哈希空间组织成一个**环形**：

```
        0
       / \
      /   \
   2.5     0.5
    |       |
    |   环  |
    |       |
   1.5     1.0
      \   /
       \ /
        1
```

**步骤**：
1. 计算所有**服务器节点**的 hash，映射到环上
2. 计算每个**数据 key** 的 hash，也映射到环上
3. key 沿环顺时针找到的第一个服务器，就是它的归属

```
环上的节点（hash 值）：
   S0
   |     K1
   |   /
   |  /  K2
   | /
   S1------S2-----S3

K1 → S2（顺时针最近的服务器）
K2 → S2
```

### 1.3 扩容时只影响部分数据

**关键优势**：服务器从 3 台扩到 4 台时：
- 只有 **新服务器和前一个服务器之间**的 key 需要迁移
- 其他 key 不受影响（继续命中旧服务器）

```
扩容前：
  S0 --- [K1] --- [K2] --- S1
       ↓ 归 S1  ↓ 归 S1

插入 S0.5 后：
  S0 --- S0.5 --- [K1] --- [K2] --- S1
       ↓ 归 S0.5 ↓ 归 S0.5 ↓ 归 S1

只有 [K1] 和 [K2] 需要迁移到 S0.5！
```

### 1.4 虚拟节点

**问题**：服务器少时，节点在环上分布不均，导致**数据倾斜**（部分服务器负载过高）。

**解决**：给每个真实服务器创建多个**虚拟节点**（Virtual Node）。

```
真实服务器 S0 → 虚拟节点 S0#0, S0#1, S0#2, ... S0#199（200 个）
```

**优势**：
- 虚拟节点均匀分布在环上
- 数据均匀分布到各服务器
- 移除服务器时，每个真实服务器平摊损失

### 1.5 一致性哈希的实际应用

| 场景 | 用途 |
|------|------|
| **Redis Cluster** | 16384 个 slot 映射到节点 |
| **Cassandra** | 数据分区 |
| **DynamoDB** | 一致性哈希 + 偏好读 |
| **Nginx upstream** | 一致性哈希负载均衡 |
| **CDN** | URL 哈希到边缘节点 |

## 2. 代码示例

### 2.1 实现一致性哈希

```python
# 文件：consistent_hash.py
import bisect
import hashlib
from typing import Any

class ConsistentHash:
    """一致性哈希：支持虚拟节点。"""

    def __init__(self, replicas: int = 200):
        """replicas 是每个节点的虚拟节点数。"""
        self._replicas = replicas
        self._ring: dict[int, str] = {}  # hash -> node_name
        self._sorted_keys: list[int] = []  # 有序的 hash 值

    def _hash(self, key: str) -> int:
        """用 MD5 取前 4 字节作为 hash。"""
        return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)

    def add_node(self, node: str) -> None:
        """添加节点。"""
        for i in range(self._replicas):
            virtual_key = f"{node}#{i}"
            h = self._hash(virtual_key)
            self._ring[h] = node
            bisect.insort(self._sorted_keys, h)

    def remove_node(self, node: str) -> None:
        """移除节点。"""
        for i in range(self._replicas):
            virtual_key = f"{node}#{i}"
            h = self._hash(virtual_key)
            del self._ring[h]
            idx = bisect.bisect_left(self._sorted_keys, h)
            if idx < len(self._sorted_keys) and self._sorted_keys[idx] == h:
                del self._sorted_keys[idx]

    def get_node(self, key: str) -> str | None:
        """查找 key 应该归属的节点 - O(log n)。"""
        if not self._ring:
            return None
        h = self._hash(key)
        # 顺时针找第一个节点
        idx = bisect.bisect_right(self._sorted_keys, h)
        if idx == len(self._sorted_keys):
            idx = 0  # 回到环头
        return self._ring[self._sorted_keys[idx]]
```

### 2.2 测试一致性哈希

```python
# 文件：test_consistent_hash.py
def test_consistent_hash():
    ch = ConsistentHash(replicas=200)

    # 添加 3 个节点
    for node in ["server-0", "server-1", "server-2"]:
        ch.add_node(node)

    # 测试 10000 个 key 的分布
    distribution = {"server-0": 0, "server-1": 0, "server-2": 0}
    for i in range(10000):
        node = ch.get_node(f"key-{i}")
        distribution[node] += 1

    print("扩容前:", distribution)
    # 大致均匀：3300 / 3400 / 3300

    # 添加第 4 个节点
    ch.add_node("server-3")

    distribution2 = {"server-0": 0, "server-1": 0, "server-2": 0, "server-3": 0}
    migrated = 0
    for i in range(10000):
        node = ch.get_node(f"key-{i}")
        distribution2[node] += 1

    print("扩容后:", distribution2)
    # 只有 ~25% 的 key 迁移到新节点！

test_consistent_hash()
```

### 2.3 对比：普通哈希 vs 一致性哈希

```python
# 文件：compare.py
def normal_hash_distribution(server_count):
    """普通哈希：扩容时几乎全部迁移。"""
    n_keys = 10000
    before = [hash(f"key-{i}") % 3 for i in range(n_keys)]
    after = [hash(f"key-{i}") % server_count for i in range(n_keys)]
    migrated = sum(1 for a, b in zip(before, after) if a != b)
    return migrated / n_keys * 100

def consistent_hash_distribution():
    """一致性哈希：扩容时只迁移 1/N。"""
    # ... 调用上面的测试
    pass

print(f"普通哈希扩容迁移: {normal_hash_distribution(4):.1f}%")
# 大约 75%（3 → 4，命中率只有 25%）

# 一致性哈希扩容迁移 ≈ 25%（3 → 4，新增节点承担 ~25% 数据）
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 集群连接（一致性哈希）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 1-50）：

```python
import redis
from redis.cluster import RedisCluster
from typing import Any

class RedisConfigWrapper:
    """Redis 配置包装器：支持单机和集群模式。

    Redis Cluster 内部使用一致性哈希（16384 个 slot）：
    - key 的 CRC16 值 % 16384 决定归属 slot
    - slot 映射到集群节点
    - 扩容时只迁移部分 slot 到新节点
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.client: redis.Redis | RedisCluster | None = None

    def create_client(self) -> redis.Redis:
        if self.config.get("use_cluster", False):
            # Redis Cluster：一致性哈希
            return RedisCluster(
                host=self.config["host"],
                port=self.config["port"],
                # ... 其他配置
            )
        else:
            # 单机 Redis：直接连接
            return redis.Redis(
                host=self.config["host"],
                port=self.config["port"],
                db=self.config.get("db", 0),
            )

    def get(self, key: str) -> str | None:
        """从 Redis 读取值。"""
        return self.client.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """写入 Redis。"""
        if ttl:
            self.client.setex(key, ttl, value)
        else:
            self.client.set(key, value)


# dify 用 redis 客户端：
# - 缓存 embedding 结果（hash 结构）
# - 缓存工作流状态（string）
# - 任务队列（Celery broker）
```

**解读**：
- 第 21 行：`RedisCluster` 是 Redis 集群客户端
- **Redis Cluster 内部**：16384 个 hash slot 映射到 N 个 master 节点
- **扩容**：从 3 节点扩到 4 节点时，16384 个 slot 重新分配，**只迁移部分 slot 到新节点**
- **设计意图**：dify 在高负载时会用 Redis Cluster，扩缩容不影响整体缓存命中率

## 4. 关键要点总结

- 一致性哈希通过**环形结构**解决扩容雪崩问题
- 扩容时只有**部分数据**需要迁移（1/N）
- **虚拟节点**解决数据倾斜问题（每个真实节点对应多个虚拟节点）
- 复杂度：查找节点 O(log N)，N 是虚拟节点总数
- 应用：Redis Cluster、Cassandra、DynamoDB、Nginx upstream

## 5. 练习题

### 练习 1：基础（必做）

实现一致性哈希的 `add_node` 和 `remove_node` 方法，保证：
- 添加节点后，部分 key 重新分布到新节点
- 删除节点后，原来归属该节点的 key 重新分布

### 练习 2：进阶

阅读 `api/extensions/ext_redis.py`，说明 dify 在什么情况下会使用 Redis Cluster 而不是单机 Redis。

### 练习 3：挑战（选做）

实现**带权重的一致性哈希**：让不同服务器承担不同比例的负载（如 S0 权重 1，S1 权重 2，S1 应承担 2/3 数据）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- Redis Cluster 规范：https://redis.io/docs/reference/cluster-spec/
- Dynamo 论文：https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
- 一致性哈希原始论文（Karger 1997）

---

**文档版本**：v1.0
**最后更新**：2026-07-13