# 1.3.2 哈希冲突解决：链地址法 / 开放地址法

> 哈希冲突不可避免，如何解决冲突决定了哈希表的实际性能。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解两种主流的哈希冲突解决方案
- 区分链地址法和开放地址法的优劣
- 知道 Java HashMap 和 Python dict 的冲突策略
- 能在 dify 中识别哈希冲突的场景

## 📚 前置知识

- 13-hash-table.md
- 04-linked-list.md

## 1. 核心概念

### 1.1 为什么会有冲突？

**鸽巢原理**：n 个 key 映射到 m 个桶（m < n），必有至少两个 key 冲突。

即使哈希函数均匀分布，n 远大于 m 时冲突不可避免。

### 1.2 链地址法（Separate Chaining）

**思想**：每个桶维护一个链表（或其他结构），冲突的元素都挂到同一个链表上。

```
桶索引： 0    1    2    3    4
       [  ] [  ] [A1] [  ] [  ]
                |
                v
              [A2] → [A3] → ∅
              [B1] → ∅（如果 hash(B)=2）
```

**复杂度**：
- 平均查找：O(1 + α)，α 是装填因子
- 最坏：O(n)（所有 key 冲突到同一个桶）

**实现要点**：
- Java HashMap 用链表 + 红黑树（链表 > 8 转红黑树）
- Java HashMap 的桶数组是 `Node<K,V>[]`

### 1.3 开放地址法（Open Addressing）

**思想**：冲突时按某种规则探测下一个空位。

```
插入 80，hash(80) = 2，但桶 2 已占用：

线性探测：尝试 2, 3, 4, 5... 直到找到空位
       [  ] [  ] [50] [80] [  ] [  ]
        0    1    2    3    4    5
```

**三种探测策略**：

| 策略 | 探测序列 | 优点 | 缺点 |
|------|----------|------|------|
| 线性探测 | h(k), h(k)+1, h(k)+2, ... | 简单 | **聚集现象** |
| 二次探测 | h(k), h(k)+1², h(k)+2², ... | 减少聚集 | 仍有次聚集 |
| 双重哈希 | h(k), h1(k)+h2(k), ... | **最优** | 实现复杂 |

**复杂度**：
- 查找：O(1 / (1-α))，α 越大越慢
- 删除：需要标记"墓碑"（不能直接置空）

### 1.4 链地址 vs 开放地址

| 维度 | 链地址法 | 开放地址法 |
|------|----------|------------|
| 实现难度 | 简单 | 较复杂 |
| 删除操作 | O(1) 直接删 | 需要墓碑标记 |
| 装填因子 | 可 > 1（链表挂载） | 必须 < 1 |
| 缓存友好 | 链表节点分散，**不友好** | 数组连续，**友好** |
| 高 α 性能 | 仍可用（O(1+α)） | 急剧下降 |
| Java | HashMap | ThreadLocalMap |
| Python | - | dict |

### 1.5 Java HashMap 的优化

JDK 1.8 后 HashMap 的桶结构：
- 链表长度 ≤ 8：纯链表
- 链表长度 > 8 且数组 ≥ 64：**链表转红黑树**
- 红黑树节点 ≤ 6：转回链表

**为什么？**
- 链表查找 O(n)，n 大时性能差
- 红黑树查找 O(log n)
- 在 n > 8 时，红黑树开始优于链表

### 1.6 Python dict 的实现

CPython dict 使用**开放地址法**（伪随机探测）：
- 初始容量 8，装填因子 2/3
- 哈希表大小是 2 的幂，用 mask 做位运算
- 删除时设置墓碑位

**特点**：
- 缓存友好（连续数组）
- 内存紧凑（无指针开销）
- 高 α 时性能下降

## 2. 代码示例

### 2.1 链地址法实现

```python
# 文件：chaining.py
class ChainingHashTable:
    """链地址法哈希表。"""

    def __init__(self, capacity: int = 16):
        self._capacity = capacity
        self._size = 0
        self._buckets: list[list[tuple]] = [[] for _ in range(capacity)]

    def _hash(self, key) -> int:
        return hash(key) % self._capacity

    def put(self, key, value) -> None:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1

    def get(self, key):
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for k, v in bucket:
            if k == key:
                return v
        raise KeyError(key)

    def stats(self) -> dict:
        """统计每个桶的链表长度分布。"""
        lengths = [len(b) for b in self._buckets]
        return {
            "size": self._size,
            "capacity": self._capacity,
            "max_chain": max(lengths),
            "avg_chain": self._size / self._capacity,
            "empty_buckets": sum(1 for l in lengths if l == 0),
        }
```

### 2.2 开放地址法实现（线性探测）

```python
# 文件：open_addressing.py
class OpenAddressingHashTable:
    """开放地址法（线性探测）哈希表。"""

    EMPTY = None
    TOMBSTONE = object()  # 墓碑标记

    def __init__(self, capacity: int = 16):
        self._capacity = capacity
        self._size = 0
        self._keys: list = [self.EMPTY] * capacity
        self._values: list = [self.EMPTY] * capacity

    def _hash(self, key) -> int:
        return hash(key) % self._capacity

    def _find_slot(self, key, for_insert: bool = False) -> int:
        """线性探测找 key 的位置（插入或查找）。"""
        idx = self._hash(key)
        first_tombstone = -1

        for _ in range(self._capacity):
            if self._keys[idx] is self.EMPTY:
                # 桶为空
                if for_insert and first_tombstone != -1:
                    return first_tombstone  # 复用墓碑位置
                return idx
            elif self._keys[idx] is self.TOMBSTONE:
                # 墓碑位，记录首次墓碑
                if first_tombstone == -1:
                    first_tombstone = idx
            elif self._keys[idx] == key:
                return idx  # 找到
            idx = (idx + 1) % self._capacity

        if for_insert:
            return first_tombstone  # 表满
        raise KeyError(key)

    def put(self, key, value) -> None:
        if self._size / self._capacity >= 0.7:
            self._resize()

        idx = self._find_slot(key, for_insert=True)
        if self._keys[idx] is self.EMPTY or self._keys[idx] is self.TOMBSTONE:
            self._size += 1
        self._keys[idx] = key
        self._values[idx] = value

    def get(self, key):
        idx = self._find_slot(key)
        return self._values[idx]

    def delete(self, key) -> None:
        idx = self._find_slot(key)
        self._keys[idx] = self.TOMBSTONE
        self._values[idx] = self.TOMBSTONE
        self._size -= 1

    def _resize(self) -> None:
        old_keys, old_values = self._keys, self._values
        self._capacity *= 2
        self._keys = [self.EMPTY] * self._capacity
        self._values = [self.EMPTY] * self._capacity
        self._size = 0
        for k, v in zip(old_keys, old_values):
            if k is not self.EMPTY and k is not self.TOMBSTONE:
                self.put(k, v)
```

### 2.3 性能对比

```python
# 文件：compare.py
import time

def benchmark():
    """对比链地址法 vs 开放地址法。"""
    n = 100000

    # 链地址法
    ht1 = ChainingHashTable(16)
    start = time.perf_counter()
    for i in range(n):
        ht1.put(i, i)
    for i in range(n):
        ht1.get(i)
    t_chaining = time.perf_counter() - start

    # 开放地址法
    ht2 = OpenAddressingHashTable(16)
    start = time.perf_counter()
    for i in range(n):
        ht2.put(i, i)
    for i in range(n):
        ht2.get(i)
    t_open = time.perf_counter() - start

    print(f"链地址法: {t_chaining:.4f}s")
    print(f"开放地址法: {t_open:.4f}s")

benchmark()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 LRU 缓存：OrderedDict（链地址+双向链表）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/embedding/cached_embedding.py`
**核心代码**（行 1-50）：

```python
from collections import OrderedDict
from threading import Lock
from typing import Any

class CachedEmbedding:
    """Embedding 缓存 + LRU 淘汰。

    用 OrderedDict 实现：
    - dict 部分是哈希表（开放地址法，CPython 内部）
    - 维护插入顺序的双向链表（链地址法的链表思想）
    - 满了淘汰头部（最久未用）
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = Lock()

    def get(self, text: str, model: str) -> list[float] | None:
        """O(1) 查找 + 标记最近使用。"""
        key = f"{model}:{text}"
        with self._lock:
            if key not in self._cache:  # dict 查找 O(1)
                return None
            # move_to_end 是 O(1)（双向链表操作）
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, text: str, model: str, embedding: list[float]) -> None:
        with self._lock:
            key = f"{model}:{text}"
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = embedding
            if len(self._cache) > self._max_size:
                # 弹出头部（最久未用）- O(1)
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
```

**解读**：
- 第 21 行：`OrderedDict` 是 CPython 的**双向链表 + 字典**实现
- 第 27 行：`move_to_end` 操作双向链表，O(1)
- 第 35 行：`popitem(last=False)` 弹出头部（最久未用），O(1)
- **整体复杂度**：所有操作 O(1)
- **设计意图**：dify 的 embedding 缓存需要淘汰最久未用的条目（LRU），OrderedDict 天然支持

## 4. 关键要点总结

- **链地址法**：每个桶挂链表，易实现但缓存不友好
- **开放地址法**：冲突时探测下一个空位，缓存友好但装填因子必须 < 1
- Java HashMap：链地址 + 红黑树（n > 8 时）
- Python dict：开放地址 + 墓碑删除
- LRU 缓存 = 哈希表 + 双向链表 = O(1) 操作

## 5. 练习题

### 练习 1：基础（必做）

实现开放地址法的**双重哈希**版本：探测序列 `h(k, i) = (h1(k) + i * h2(k)) mod m`。

### 练习 2：进阶

阅读 `api/core/rag/embedding/cached_embedding.py`，说明 dify 为什么要用 `OrderedDict` 而不是普通 `dict` + 自己维护一个 `list`。

### 练习 3：挑战（选做）

实现**Robin Hood 哈希**：插入时如果新元素探测次数比当前位置元素多，"抢走"对方位置（减少方差）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/embedding/cached_embedding.py`
- JDK HashMap 源码：https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashMap.java
- 《算法导论》第 11 章 哈希冲突

---

**文档版本**：v1.0
**最后更新**：2026-07-13