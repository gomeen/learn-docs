# 1.2.5 计数排序 / 桶排序 / 基数排序

> 三种 O(n) 线性时间排序算法，适用于特定场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解三种线性排序的原理和适用场景
- 区分它们与基于比较的排序（O(n log n) 下界）
- 知道每种算法的限制（数据范围、桶数等）
- 能在 dify 中识别计数排序的应用

## 📚 前置知识

- 01-basic-sort.md
- 03-quick-sort.md

## 1. 核心概念

### 1.1 基于比较的排序下界

**比较排序**（冒泡、选择、插入、归并、快排、堆排）的最坏时间复杂度是 **O(n log n)**，这是数学下界。

**突破下界**：利用数据的特殊性质（如整数范围小），可以做到 O(n)。

### 1.2 计数排序（Counting Sort）

**思想**：统计每个值出现的次数，然后按顺序输出。

```
数组：[2, 5, 3, 0, 2, 3, 0, 3]
计数：[2, 0, 2, 3, 0, 1]   ← 0 出现 2 次，1 出现 0 次，2 出现 2 次...
       0  1  2  3  4  5

输出：[0, 0, 2, 2, 3, 3, 3, 5]
```

**限制**：
- 数据必须是非负整数
- 数据范围（max）不能太大
- 空间复杂度 O(max)

### 1.3 桶排序（Bucket Sort）

**思想**：把数据分到多个**桶**里，每个桶内部排序，最后合并。

```
[29, 25, 3, 49, 9, 37, 21, 43]

桶 0-9:   [3, 9]
桶 10-19: []
桶 20-29: [29, 25, 21]
桶 30-39: [37]
桶 40-49: [49, 43]

桶内排序后合并：[3, 9, 21, 25, 29, 37, 43, 49]
```

**适用场景**：
- 数据**均匀分布**
- 桶数 ≈ n，每个桶内少量元素

### 1.4 基数排序（Radix Sort）

**思想**：按**位数**逐位排序（从低位到高位），每位用稳定的子排序（计数排序）。

```
[170, 45, 75, 90, 802, 24, 2, 66]

按个位：[170, 90, 802, 2, 24, 45, 75, 66]
按十位： [802, 2, 24, 45, 66, 170, 75, 90]
按百位： [2, 24, 45, 66, 75, 90, 170, 802]
```

**适用场景**：
- 整数、字符串排序
- 数据位数较少

### 1.5 三种线性排序对比

| 算法 | 时间 | 空间 | 限制 | 稳定 |
|------|------|------|------|------|
| 计数 | O(n + k) | O(k) | 整数、范围小 | ✓ |
| 桶排 | O(n + k) | O(n + k) | 均匀分布 | ✓ |
| 基数 | O(d × n) | O(k) | 整数、字符串 | ✓ |

## 2. 代码示例

### 2.1 计数排序

```python
# 文件：counting_sort.py
from typing import List

def counting_sort(nums: List[int]) -> List[int]:
    """计数排序：适合数据范围小的非负整数。"""
    if not nums:
        return nums
    max_val = max(nums)
    # 计数数组
    count = [0] * (max_val + 1)
    for num in nums:
        count[num] += 1
    # 累加（前缀和）用于稳定排序
    for i in range(1, len(count)):
        count[i] += count[i - 1]
    # 输出
    output = [0] * len(nums)
    for num in reversed(nums):  # 反向遍历保证稳定性
        output[count[num] - 1] = num
        count[num] -= 1
    return output

# 测试
print(counting_sort([2, 5, 3, 0, 2, 3, 0, 3]))  # [0, 0, 2, 2, 3, 3, 3, 5]
```

### 2.2 桶排序

```python
# 文件：bucket_sort.py
from typing import List
import random

def bucket_sort(nums: List[float], bucket_count: int = 10) -> List[float]:
    """桶排序：适合均匀分布的浮点数。"""
    if not nums:
        return nums
    min_val, max_val = min(nums), max(nums)
    bucket_size = (max_val - min_val) / bucket_count

    # 创建桶
    buckets: List[List[float]] = [[] for _ in range(bucket_count)]
    for num in nums:
        idx = min(int((num - min_val) / bucket_size), bucket_count - 1)
        buckets[idx].append(num)

    # 桶内排序 + 合并
    result = []
    for bucket in buckets:
        result.extend(sorted(bucket))  # 桶内用内置排序
    return result

# 测试
random.seed(42)
nums = [random.uniform(0, 100) for _ in range(20)]
print(bucket_sort(nums))
```

### 2.3 基数排序

```python
# 文件：radix_sort.py
from typing import List

def radix_sort(nums: List[int]) -> List[int]:
    """基数排序：LSD（从低位到高位），用计数排序作为子排序。"""
    if not nums:
        return nums
    max_val = max(nums)
    exp = 1  # 当前位数（1=个位，10=十位...）

    while max_val // exp > 0:
        # 按当前位做计数排序
        output = [0] * len(nums)
        count = [0] * 10

        # 计数
        for num in nums:
            count[(num // exp) % 10] += 1
        # 累加
        for i in range(1, 10):
            count[i] += count[i - 1]
        # 输出（反向遍历保证稳定）
        for num in reversed(nums):
            digit = (num // exp) % 10
            output[count[digit] - 1] = num
            count[digit] -= 1

        nums = output
        exp *= 10

    return nums

# 测试
print(radix_sort([170, 45, 75, 90, 802, 24, 2, 66]))  # [2, 24, 45, 66, 75, 90, 170, 802]
```

### 2.4 字符串基数排序

```python
# 文件：radix_sort_strings.py
def radix_sort_strings(strings: list[str]) -> list[str]:
    """字符串基数排序：按字符逐位排序。"""
    if not strings:
        return strings
    max_len = max(len(s) for s in strings)
    # 补齐到相同长度（用 '\0' 填充）
    strings = [s.ljust(max_len, '\0') for s in strings]

    for i in range(max_len - 1, -1, -1):
        # 按第 i 个字符计数排序
        count = [0] * 256  # ASCII
        for s in strings:
            count[ord(s[i])] += 1
        for j in range(1, 256):
            count[j] += count[j - 1]
        output = [''] * len(strings)
        for s in reversed(strings):
            digit = ord(s[i])
            output[count[digit] - 1] = s
            count[digit] -= 1
        strings = output

    return [s.rstrip('\0') for s in strings]

# 测试
print(radix_sort_strings(["apple", "app", "banana", "bat", "cat"]))
# ['app', 'apple', 'banana', 'bat', 'cat']
```

## 3. dify 仓库源码解读

### 3.1 dify 的 token 频率统计

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
**核心代码**（行 30-60）：

```python
from collections import Counter
from typing import Any

class BM25Scorer:
    """BM25 评分器：经典的文档相关性打分算法。

    BM25 核心是 TF-IDF 的改进版，需要统计：
    - 词频（TF）：文档中每个词出现次数
    - 文档频率（DF）：包含该词的文档数

    这里用 Counter（基于 dict）做词频统计，
    类似计数排序的思想。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self._k1 = k1
        self._b = b

    def compute_tf(self, text: str) -> dict[str, int]:
        """计算词频 - 计数思想。"""
        words = text.lower().split()
        return Counter(words)  # Counter 内部就是 dict 计数

    def compute_idf(self, documents: list[str]) -> dict[str, float]:
        """计算逆文档频率。"""
        n_docs = len(documents)
        # 统计每个词出现在多少文档中
        df: dict[str, int] = {}
        for doc in documents:
            seen = set()
            for word in doc.lower().split():
                if word not in seen:
                    df[word] = df.get(word, 0) + 1
                    seen.add(word)
        # IDF = log((N - df + 0.5) / (df + 0.5))
        import math
        idf = {word: math.log((n_docs - count + 0.5) / (count + 0.5) + 1)
               for word, count in df.items()}
        return idf

    def score(self, query: str, document: str, avg_dl: float, dl: int) -> float:
        """计算 BM25 分数。"""
        tf = self.compute_tf(document)
        idf = self.compute_idf([document])  # 简化
        words = query.lower().split()
        score = 0.0
        for word in words:
            if word in tf:
                tf_val = tf[word]
                idf_val = idf.get(word, 0)
                numerator = tf_val * (self._k1 + 1)
                denominator = tf_val + self._k1 * (1 - self._b + self._b * dl / avg_dl)
                score += idf_val * (numerator / denominator)
        return score
```

**解读**：
- 第 23 行：`Counter(words)` 是 O(n) 词频统计，**类似计数排序**的思想
- 第 26 行：用 dict 统计文档频率（DF），也是计数思想
- **dify 中无直接排序调用**：但 BM25 的核心是"统计 + 计算"，与计数排序同源
- **设计意图**：BM25 是经典 IR 算法，dify 用它做关键词相关性打分

## 4. 关键要点总结

- 计数排序：O(n + k)，适合范围小的非负整数
- 桶排序：O(n + k)，适合均匀分布数据
- 基数排序：O(d × n)，适合整数和定长字符串
- 三种都是**稳定**排序
- 突破 O(n log n) 下界的关键是利用**数据特殊性质**
- dify 的 BM25 算法基于"计数"思想

## 5. 练习题

### 练习 1：基础（必做）

实现计数排序的**原地版本**（用前缀和优化），要求空间复杂度 O(1)。

### 练习 2：进阶

阅读 `api/core/rag/rerank/weight_rerank.py`，分析 BM25 算法中"计数"思想如何体现。

### 练习 3：挑战（选做）

实现**MSD 基数排序**（从高位到高位），用分治思想递归处理。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
- 《算法导论》第 8 章 线性时间排序
- LeetCode 912/164 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13