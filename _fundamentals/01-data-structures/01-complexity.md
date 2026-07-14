# 1.1.1 时间复杂度与空间复杂度

> 理解算法效率的两个核心维度：时间（执行快慢）和空间（占用内存多少）。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分时间复杂度和空间复杂度
- 理解 O(1) / O(log n) / O(n) / O(n log n) / O(n²) 的实际差异
- 能够分析一段代码的复杂度
- 能看懂 dify 中为什么用 `set` 代替 `list` 做去重

## 📚 前置知识

- Python 基础语法
- 简单的循环和函数

## 1. 核心概念

### 1.1 时间复杂度（Time Complexity）

**定义**：算法执行时间随数据规模增长的变化趋势。

我们关注的是**增长趋势**，而不是具体的执行秒数（因为这取决于硬件）。

```
数据规模 n     O(1)     O(log n)    O(n)       O(n log n)    O(n²)
n = 10         1        3           10         30            100
n = 100        1        7           100        700           10000
n = 10000      1        13          10000      130000        10⁸（爆炸）
```

### 1.2 空间复杂度（Space Complexity）

**定义**：算法执行过程中占用的额外内存空间（不包括输入数据本身）。

```python
def sum_list(nums):
    # 只用了 1 个变量 total
    # 空间复杂度 O(1)
    total = 0
    for n in nums:
        total += n
    return total

def copy_list(nums):
    # 创建了新数组
    # 空间复杂度 O(n)
    return [n * 2 for n in nums]
```

### 1.3 常见复杂度等级

从优到劣排列：

| 复杂度 | 名称 | 典型场景 |
|--------|------|----------|
| O(1) | 常数 | 哈希表查找、数组按下标访问 |
| O(log n) | 对数 | 二分查找、平衡二叉树 |
| O(n) | 线性 | 遍历数组 |
| O(n log n) | 线性对数 | 归并排序、快速排序 |
| O(n²) | 平方 | 双重循环、冒泡排序 |
| O(2ⁿ) | 指数 | 暴力递归斐波那契 |

### 1.4 如何分析复杂度？

**三原则**：
1. **只看最高阶项**：O(n² + n) ≈ O(n²)
2. **忽略常数系数**：O(2n) ≈ O(n)
3. **嵌套循环相乘**：`for i in n: for j in n` → O(n²)

## 2. 代码示例

### 2.1 同一问题，不同复杂度

```python
# 文件：complexity_demo.py
# 问题：找出数组中是否存在重复元素

from typing import List

# ❌ O(n²) 时间复杂度 - 双重循环
def has_duplicate_v1(nums: List[int]) -> bool:
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] == nums[j]:
                return True
    return False

# ✅ O(n) 时间复杂度 - 哈希表
def has_duplicate_v2(nums: List[int]) -> bool:
    seen = set()  # O(n) 空间换 O(n) 时间
    for n in nums:
        if n in seen:      # O(1) 查找
            return True
        seen.add(n)
    return False

# 数据规模 10000 时
# v1 需要 ~5000万次比较
# v2 只需要 ~10000 次哈希查找
```

**说明**：用 O(n) 的空间换 O(n²) → O(n) 的时间，这是经典的**时空权衡**。

### 2.2 分析递归的复杂度

```python
# 斐波那契：fib(n) = fib(n-1) + fib(n-2)

def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

# 时间复杂度：O(2ⁿ)
# 原因：fib(5) = fib(4) + fib(3) = fib(3)+fib(2) + fib(2)+fib(1) ...
# 每个 fib(k) 都会展开为两个 fib(k-1)，呈指数增长

# 优化：记忆化搜索
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_fast(n):
    if n <= 1:
        return n
    return fib_fast(n - 1) + fib_fast(n - 2)

# 时间复杂度：O(n)
# 空间复杂度：O(n)
```

## 3. dify 仓库源码解读

### 3.1 用 set 做去重（O(n²) → O(n)）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/embedding/embedding_cache.py`
**核心代码**（行 1-40）：

```python
import hashlib
from typing import Any

class EmbeddingCache:
    """Embedding 结果缓存，避免重复计算。"""

    def __init__(self):
        self.cache: dict[str, list[float]] = {}

    def get_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get_batch(
        self,
        texts: list[str],
        embedding_func: callable,
    ) -> list[list[float]]:
        """批量获取 embedding，自动处理缓存命中。"""
        hashes = [self.get_hash(t) for t in texts]
        results = []

        # 找出未缓存的索引
        missing_indices = [
            i for i, h in enumerate(hashes)
            if h not in self.cache   # O(1) 字典查找
        ]

        # 只对未缓存的文本计算 embedding
        if missing_indices:
            missing_texts = [texts[i] for i in missing_indices]
            new_embeddings = embedding_func(missing_texts)

            # 写回缓存
            for idx, emb in zip(missing_indices, new_embeddings):
                self.cache[hashes[idx]] = emb

        # 按原始顺序返回
        return [self.cache[h] for h in hashes]
```

**解读**：
- 第 28 行：`if h not in self.cache` —— 字典查找是 **O(1)**
- 如果用 `list` 存储缓存，这里会变成 O(n)，整体退化为 O(n²)
- **整体复杂度**：命中缓存时 **O(n)**（n 次哈希计算 + n 次字典查找）
- **设计意图**：embedding 计算非常昂贵（调用 LLM API），缓存能避免重复计算

## 4. 关键要点总结

- 时间复杂度衡量**执行步骤数**随 n 的增长趋势
- 空间复杂度衡量**额外内存**随 n 的增长趋势
- 常见等级：O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2ⁿ)
- 用**哈希表**（O(1) 查找）替代**列表**（O(n) 查找）是经典的优化手段
- 递归算法的时间复杂度要看**调用树的总节点数**

## 5. 练习题

### 练习 1：基础（必做）

分析下列代码的时间复杂度：

```python
def example1(nums):
    return nums[0] + nums[-1]

def example2(nums):
    total = 0
    for n in nums:
        total += n
    return total

def example3(matrix):
    for row in matrix:
        for cell in row:
            print(cell)

def example4(n):
    i = 1
    while i < n:
        print(i)
        i *= 2
```

### 练习 2：进阶

阅读 `api/core/rag/embedding/embedding_cache.py`，分析 `get_batch` 方法在**全部命中缓存**和**全部未命中**两种情况下的时间复杂度。

### 练习 3：挑战（选做）

给定一个列表，找出出现次数超过 `n/2` 的元素（"多数元素"）。要求时间复杂度 O(n)，空间复杂度 O(1)（Boyer-Moore 投票算法）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/embedding/embedding_cache.py`
- 算法导论（第 3 章）
- 大 O 速查表：https://www.bigocheatsheet.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13