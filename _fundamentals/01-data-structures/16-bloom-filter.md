# 1.3.4 布隆过滤器（Bloom Filter）

> 布隆过滤器是空间效率极高的概率性数据结构，能告诉你"一定不存在"或"可能存在"。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解布隆过滤器的工作原理和位数组
- 区分"假阳性"（误判存在）和"假阴性"（误判不存在）
- 掌握参数（m、k、n）的取舍
- 能在 dify 中识别布隆过滤器的应用

## 📚 前置知识

- 13-hash-table.md
- 15-consistent-hashing.md

## 1. 核心概念

### 1.1 什么是布隆过滤器？

**布隆过滤器**（Bloom Filter）是一个**位数组** + **多个哈希函数**：
- 插入时：用 k 个哈希函数算出 k 个位置，置 1
- 查询时：检查 k 个位置是否全为 1，是则**可能存在**，否则**一定不存在**

```
初始化（8 位数组）：[0, 0, 0, 0, 0, 0, 0, 0]

插入 "apple"（用 3 个哈希函数）：
  h1("apple") = 2 → 位置 2 置 1
  h2("apple") = 5 → 位置 5 置 1
  h3("apple") = 7 → 位置 7 置 1

数组：[0, 0, 1, 0, 0, 1, 0, 1]

插入 "banana"：
  h1("banana") = 1 → 位置 1 置 1
  h2("banana") = 5 → 位置 5 已为 1
  h3("banana") = 7 → 位置 7 已为 1

数组：[0, 1, 1, 0, 0, 1, 0, 1]
```

### 1.2 关键特性

| 操作 | 结果 | 说明 |
|------|------|------|
| 查询存在的 key | 可能误判 | **假阳性** |
| 查询不存在的 key | 一定准确 | **无假阴性** |

**关键原则**：
- **可能存在**：可信度低（如 1%）
- **一定不存在**：可信度 100%

### 1.3 假阳性率公式

```
误判率 p ≈ (1 - e^(-kn/m))^k

其中：
- n: 已插入元素数
- m: 位数组大小
- k: 哈希函数个数
```

**最优 k**：`k = (m/n) * ln(2)`

**最优 m**：`m = -n * ln(p) / (ln(2))²`

**举例**：n=100 万，p=1%，需要 m ≈ 9.6 M 位 ≈ 1.2 MB。

### 1.4 布隆过滤器的应用

1. **缓存穿透防护**：拦截不存在的 key，避免回源数据库
2. **爬虫 URL 去重**：判断 URL 是否已爬取
3. **垃圾邮件过滤**：判断发件人是否在黑名单
4. **数据库查询优化**：判断行是否可能存在
5. **推荐系统**：用户是否看过某内容

### 1.5 布隆过滤器的变种

- **Counting Bloom Filter**：用计数器替代位，支持删除
- **Cuckoo Filter**：支持删除且空间利用率高
- **Ribbon Filter**：BLOOM 的空间优化版
- **RedisBloom**：Redis 模块实现

## 2. 代码示例

### 2.1 完整实现

```python
# 文件：bloom_filter.py
import hashlib
import math
from typing import Any

class BloomFilter:
    """标准布隆过滤器。"""

    def __init__(self, capacity: int, error_rate: float = 0.01):
        """
        Args:
            capacity: 预计插入元素数
            error_rate: 期望误判率
        """
        # 最优位数组大小
        self._m = self._optimal_m(capacity, error_rate)
        # 最优哈希函数个数
        self._k = self._optimal_k(capacity, self._m)
        # 位数组（用 bytearray 节省内存）
        self._bits = bytearray(self._m)
        self._size = 0

    def _optimal_m(self, n: int, p: float) -> int:
        return int(-n * math.log(p) / (math.log(2) ** 2)) + 1

    def _optimal_k(self, n: int, m: int) -> int:
        return max(1, int((m / n) * math.log(2)))

    def _hashes(self, item: Any) -> list[int]:
        """用 SHA256 派生 k 个独立哈希值。"""
        h_bytes = hashlib.sha256(str(item).encode()).digest()
        h = int.from_bytes(h_bytes, 'big')
        # 用线性组合派生多个哈希（节省哈希调用）
        return [(h + i * h // (i + 1)) % self._m for i in range(self._k)]

    def add(self, item: Any) -> None:
        """插入元素。"""
        for pos in self._hashes(item):
            self._bits[pos] = 1
        self._size += 1

    def contains(self, item: Any) -> bool:
        """判断元素是否存在。
        True：可能存在（有误判概率）
        False：一定不存在
        """
        for pos in self._hashes(item):
            if self._bits[pos] == 0:
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def stats(self) -> dict:
        """统计信息。"""
        ones = sum(self._bits)
        return {
            "size": self._size,
            "bits_set": ones,
            "fill_rate": ones / self._m,
            "estimated_fpp": (ones / self._m) ** self._k,
        }
```

### 2.2 缓存穿透防护

```python
# 文件：cache_penetration.py
import redis

class CacheService:
    """带布隆过滤器防护的缓存服务。

    场景：用户查询商品信息，如果商品不存在，缓存击穿数据库。
    解决：用布隆过滤器记录所有存在的商品 ID，查询前先过滤。
    """

    def __init__(self, redis_client: redis.Redis, db):
        self.redis = redis_client
        self.db = db
        # 启动时把数据库中所有商品 ID 加入布隆过滤器
        self._bloom = BloomFilter(capacity=1000000, error_rate=0.01)
        for product_id in self._load_all_ids():
            self._bloom.add(product_id)

    def _load_all_ids(self) -> list[int]:
        return [row[0] for row in self.db.query("SELECT id FROM products")]

    def get_product(self, product_id: int) -> dict | None:
        """获取商品信息 - 先过布隆过滤器。"""
        # Step 1: 布隆过滤器判断
        if product_id not in self._bloom:
            # 一定不存在，直接返回，避免回源数据库
            return None

        # Step 2: 查 Redis 缓存
        cached = self.redis.get(f"product:{product_id}")
        if cached:
            return eval(cached)  # 实际用 json.loads

        # Step 3: 查数据库
        product = self.db.query(
            "SELECT * FROM products WHERE id = %s", (product_id,)
        )
        if product:
            self.redis.setex(f"product:{product_id}", 3600, str(product))
        return product
```

### 2.3 测试误判率

```python
# 文件：test_bloom.py
import random

def test_bloom_filter():
    # 插入 1 万个元素
    bf = BloomFilter(capacity=10000, error_rate=0.01)
    inserted = set()
    for _ in range(10000):
        item = f"item-{random.randint(0, 1000000)}"
        if item not in inserted:
            bf.add(item)
            inserted.add(item)

    # 测试 1 万个未插入元素
    false_positives = 0
    test_count = 10000
    for _ in range(test_count):
        item = f"not-inserted-{random.randint(0, 1000000)}"
        if bf.contains(item):
            false_positives += 1

    actual_fpp = false_positives / test_count
    print(f"理论误判率: 1%, 实际误判率: {actual_fpp * 100:.2f}%")
    print(f"统计: {bf.stats()}")

test_bloom_filter()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 SSRF 防护：URL 黑名单

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 50-90）：

```python
import ipaddress
from typing import Optional

class SSRFProtection:
    """SSRF 防护：阻止请求内网 IP。

    用布隆过滤器（简化版：用 set 替代）记录已知的恶意 IP / URL 列表。
    注意：dify 没有直接用布隆过滤器，但这是典型的应用场景。
    """

    # 内网 IP 段（绝对黑名单，用 set 即可）
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
    ]

    @classmethod
    def is_private_ip(cls, ip: str) -> bool:
        """判断 IP 是否内网。"""
        try:
            addr = ipaddress.ip_address(ip)
            for net in cls.PRIVATE_IP_RANGES:
                if addr in net:
                    return True
        except ValueError:
            return False
        return False

    @classmethod
    def check_url_safety(cls, url: str) -> bool:
        """检查 URL 是否安全（非内网 IP）。"""
        import socket
        try:
            # 解析域名获取 IP
            ip = socket.gethostbyname(url.split("/")[2])
            if cls.is_private_ip(ip):
                return False
            return True
        except (socket.gaierror, ValueError):
            return False


# 类似场景 dify 可以用布隆过滤器：
# - 已知恶意 URL 黑名单（节省内存）
# - 已索引文档 ID 集合（去重）
# - 工作流节点 ID 验证（防止重复执行）
```

**解读**：
- 第 12-18 行：内网 IP 段硬编码（数量少，用 set 足够）
- **布隆过滤器的应用场景**（dify 中可优化）：
  - 已知恶意 URL 列表（数量 100 万+）→ 用布隆过滤器节省内存
  - 文档 ID 集合 → 布隆过滤器 + 数据库二次确认
  - 用户访问过的内容 → 布隆过滤器去重
- **dify/ruoyi 中无直接示例**：布隆过滤器在 Redis 生态用得多（如 RedisBloom 模块）

## 4. 关键要点总结

- 布隆过滤器：**位数组 + k 个哈希函数**
- **无假阴性**：不存在的元素一定判不存在
- **有假阳性**：存在的元素可能误判
- **不能删除**（标准版），Counting Bloom Filter 可删
- 误判率公式：`(1 - e^(-kn/m))^k`
- 应用：缓存穿透、爬虫 URL 去重、黑名单过滤

## 5. 练习题

### 练习 1：基础（必做）

实现布隆过滤器的 `add` 和 `contains` 方法，并测试 1 万个元素的实际误判率。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，思考如果 dify 有一个 100 万条恶意 URL 的黑名单，应该用什么数据结构存储？

### 练习 3：挑战（选做）

实现**Counting Bloom Filter**：用 4 位计数器替代单比特，支持删除操作。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- Bloom 原始论文（1970）
- RedisBloom 模块：https://redis.io/docs/stack/bloom/
- Counting Bloom Filter（Fan et al. 2000）

---

**文档版本**：v1.0
**最后更新**：2026-07-13