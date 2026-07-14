# 1.3.1 哈希表原理

> 哈希表是 O(1) 时间复杂度的"瑞士军刀"，后端开发最常用的数据结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解哈希函数的原理和设计要求
- 掌握哈希表的插入/查找/删除 O(1) 是怎么来的
- 知道哈希冲突的常见解决方案
- 能用 dify 中 `dict`、`set` 高效解决问题

## 📚 前置知识

- 01-complexity.md
- 14-hash-collision.md（推荐）

## 1. 核心概念

### 1.1 哈希表的核心思想

**数组按下标访问是 O(1)**，哈希表用**哈希函数**把 key 映射到数组下标，从而获得 O(1) 访问。

```
key "name"   → hash("name") = 12345 → 12345 % 16 = 5 → arr[5]
key "age"    → hash("age")  = 67890 → 67890 % 16 = 10 → arr[10]
```

### 1.2 哈希函数的要求

1. **确定性**：相同 key 必须得到相同 hash
2. **均匀分布**：不同 key 应该均匀散列
3. **高效**：计算速度快

**常见哈希函数**：
- **除留余数法**：`h(k) = k mod m`
- **乘法哈希**：`h(k) = floor(m * frac(k * A))`（A 是常数）
- **MurmurHash**、**CityHash**、**xxHash**：工业级

### 1.3 哈希冲突

**鸽巢原理**：两个不同 key 可能算出同一个 hash 值。

```
hash("abc") % 16 = 3
hash("xyz") % 16 = 3   ← 冲突！
```

**解决方式**（详见 14-hash-collision.md）：
1. **链地址法**：每个桶挂一个链表（Java HashMap）
2. **开放地址法**：冲突时找下一个空位（Python dict）

### 1.4 装填因子（Load Factor）

```
装填因子 α = 元素数 / 桶数
```

- α 越大：冲突越多，性能越差
- α 越小：内存浪费

**典型策略**：
- Java HashMap：α > 0.75 时扩容
- Python dict：2/3 满时扩容
- Redis Hash：负载高时扩容

### 1.5 扩容（Rehashing）

当装填因子过大时：
1. 分配更大的数组（2 倍）
2. 重新计算所有元素的 hash 和桶位置
3. 旧数组释放

**扩容复杂度**：O(n) 单次，但**均摊 O(1)**。

### 1.6 哈希表的操作复杂度

| 操作 | 平均 | 最坏 |
|------|------|------|
| 插入 | O(1) | O(n) |
| 查找 | O(1) | O(n) |
| 删除 | O(1) | O(n) |

**最坏情况**：所有 key 哈希到同一个桶 → 退化为链表。

## 2. 代码示例

### 2.1 自己实现哈希表（链地址法）

```python
# 文件：hash_table.py
from typing import Any

class HashTable:
    def __init__(self, capacity: int = 16):
        self._capacity = capacity
        self._size = 0
        self._buckets: list[list[tuple[Any, Any]]] = [
            [] for _ in range(capacity)
        ]

    def _hash(self, key: Any) -> int:
        """简单哈希函数。"""
        return hash(key) % self._capacity

    def put(self, key: Any, value: Any) -> None:
        """插入或更新 - 平均 O(1)。"""
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)  # 更新
                return
        bucket.append((key, value))
        self._size += 1

        # 装填因子 > 0.75 时扩容
        if self._size / self._capacity > 0.75:
            self._resize()

    def get(self, key: Any) -> Any:
        """查找 - 平均 O(1)。"""
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for k, v in bucket:
            if k == key:
                return v
        raise KeyError(key)

    def delete(self, key: Any) -> None:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self._size -= 1
                return
        raise KeyError(key)

    def _resize(self) -> None:
        """扩容为 2 倍。"""
        old_buckets = self._buckets
        self._capacity *= 2
        self._size = 0
        self._buckets = [[] for _ in range(self._capacity)]
        for bucket in old_buckets:
            for k, v in bucket:
                self.put(k, v)
```

### 2.2 实战：两数之和（哈希表优化）

```python
# 文件：two_sum.py
from typing import List

# ❌ O(n²) - 双重循环
def two_sum_brute(nums: List[int], target: int) -> List[int]:
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

# ✅ O(n) - 哈希表
def two_sum_hash(nums: List[int], target: int) -> List[int]:
    seen: dict[int, int] = {}  # value → index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:  # O(1) 查找
            return [seen[complement], i]
        seen[num] = i
    return []

# 测试
nums = [2, 7, 11, 15]
print(two_sum_hash(nums, 9))  # [0, 1]
```

### 2.3 Python dict 性能小技巧

```python
# 文件：dict_tips.py
import time

# ✅ 用 dict.get(key, default) 避免 KeyError
def count_words_safe(words):
    counter = {}
    for w in words:
        counter[w] = counter.get(w, 0) + 1
    return counter

# ✅ 用 setdefault 处理缺失 key
def group_words(words):
    groups = {}
    for w in words:
        groups.setdefault(w[0], []).append(w)
    return groups

# ✅ 用 collections.Counter 自动计数
from collections import Counter

def count_words_counter(words):
    return Counter(words)

# 性能对比
words = ["apple"] * 100000 + ["banana"] * 100000

start = time.perf_counter()
count_words_safe(words)
t1 = time.perf_counter() - start

start = time.perf_counter()
count_words_counter(words)
t2 = time.perf_counter() - start

print(f"手动: {t1:.4f}s, Counter: {t2:.4f}s")
```

## 3. dify 仓库源码解读

### 3.1 dify 的 dict 做 embedding 缓存

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/embedding/embedding_cache.py`
**核心代码**（行 1-50）：

```python
import hashlib
from typing import Any

class EmbeddingCache:
    """Embedding 缓存：避免重复调用昂贵的 embedding API。

    底层是 Python dict，hash 表的工业级实现。
    """

    def __init__(self, max_size: int = 10000):
        self._cache: dict[str, list[float]] = {}
        self._max_size = max_size

    def _hash_key(self, text: str, model: str) -> str:
        """组合 key：text + model（不同模型不能混用缓存）。"""
        raw = f"{model}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, text: str, model: str) -> list[float] | None:
        """查找缓存 - O(1)。"""
        key = self._hash_key(text, model)
        return self._cache.get(key)

    def set(self, text: str, model: str, embedding: list[float]) -> None:
        """写入缓存 - O(1)，满了就清理最旧的。"""
        if len(self._cache) >= self._max_size:
            # 简单策略：清空一半
            keys_to_remove = list(self._cache.keys())[:self._max_size // 2]
            for k in keys_to_remove:
                del self._cache[k]

        key = self._hash_key(text, model)
        self._cache[key] = embedding

    def get_batch(
        self,
        texts: list[str],
        model: str,
        embedding_func: callable,
    ) -> list[list[float]]:
        """批量获取，自动处理缓存命中。"""
        results = [None] * len(texts)
        miss_indices = []
        miss_texts = []

        # 第一次扫描：找出未命中的
        for i, text in enumerate(texts):
            emb = self.get(text, model)
            if emb is not None:
                results[i] = emb
            else:
                miss_indices.append(i)
                miss_texts.append(text)

        # 第二次扫描：填充未命中的
        if miss_texts:
            new_embeddings = embedding_func(miss_texts)
            for idx, emb in zip(miss_indices, new_embeddings):
                results[idx] = emb
                self.set(texts[idx], model, emb)

        return results
```

**解读**：
- 第 17 行：`hashlib.sha256` 是工业级哈希函数，输出 256 位（64 字符十六进制）
- 第 24 行：`self._cache.get(key)` 是 O(1) 哈希查找
- 第 34 行：`dict[key] = value` 是 O(1) 哈希插入
- 第 41 行：`get_batch` 两次扫描：第一次查缓存 O(n)，第二次填缓存 O(k)
- **整体复杂度**：O(n)，其中 n 是文本数
- **设计意图**：embedding API 调用昂贵（耗时 1-2 秒），缓存能避免重复计算，大幅降低成本

## 4. 关键要点总结

- 哈希表通过**哈希函数**将 key 映射到桶，实现 **O(1)** 增删改查
- 哈希冲突不可避免，需要冲突解决（链地址法 / 开放地址法）
- 装填因子过大时需要扩容（rehashing），均摊 O(1)
- Python `dict` 和 `set` 都是哈希表，工业级实现
- dify 用 `dict` 做 embedding 缓存，大幅减少 API 调用

## 5. 练习题

### 练习 1：基础（必做）

判断下列场景应该用 `list`、`dict` 还是 `set`：
1. 存储 100 万个用户的 ID，要快速判断某个 ID 是否存在
2. 存储 100 万个用户的 (id, name) 映射，要按 id 查找
3. 存储 100 万个整数，要排序后遍历

### 练习 2：进阶

阅读 `api/core/rag/embedding/embedding_cache.py`，分析为什么 dify 用 `sha256` 而不是直接用字符串作为 dict 的 key。

### 练习 3：挑战（选做）

实现一个**布谷鸟哈希**（Cuckoo Hashing），保证最坏 O(1) 查找。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/embedding/embedding_cache.py`
- Python dict 实现：https://docs.python.org/3/faq/design.html#how-are-dictionaries-implemented-in-cpython
- 《算法导论》第 11 章 哈希表

---

**文档版本**：v1.0
**最后更新**：2026-07-13