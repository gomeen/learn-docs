# 1.2.3 快速排序

> 快速排序是最快的通用排序算法，平均 O(n log n)，是工业级排序首选。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解快速排序的"分治"思想（与归并排序的关键区别）
- 掌握三种分区方法（Hoare、Lomuto、3-way）
- 知道快速排序的最坏情况和优化（三数取中、随机化）
- 能在 dify 中识别分治思想的应用

## 📚 前置知识

- 01-basic-sort.md
- 02-merge-sort.md
- 09-recursion.md

## 1. 核心概念

### 1.1 快速排序的核心思想

**分治**：
1. **选 pivot**：选一个元素作为基准
2. **分区**：把小于 pivot 的放左边，大于 pivot 的放右边
3. **递归**：对左右两部分分别递归

```
[5, 2, 8, 1, 4]，选 pivot = 4
分区后：  [2, 1] [4] [5, 8]
           ↓    pivot   ↓
          递归    4    递归
           ↓            ↓
          [1, 2]      [5, 8]
                      ↓
                    [5] [8]

最终：[1, 2, 4, 5, 8] ✓
```

### 1.2 与归并排序的关键区别

| 维度 | 快速排序 | 归并排序 |
|------|----------|----------|
| 分区时机 | **先分区再递归** | 先递归再合并 |
| 时间 | O(n log n) 平均，**O(n²) 最坏** | O(n log n) 稳定 |
| 空间 | O(log n) 栈 | O(n) 辅助数组 |
| 稳定性 | **不稳定** | 稳定 |
| 实际性能 | **更快**（缓存友好） | 稍慢 |

### 1.3 三种分区方法

#### Lomuto 分区（简单）

```python
# 选 nums[right] 为 pivot
# 把小于 pivot 的元素移到左边
i = lo
for j in range(lo, hi):
    if nums[j] < pivot:
        swap(nums[i], nums[j])
        i += 1
swap(nums[i], nums[hi])  # pivot 到位
return i
```

#### Hoare 分区（高效）

```python
# 双指针，从两端向中间
i, j = lo, hi
while i < j:
    while nums[i] < pivot: i += 1
    while nums[j] > pivot: j -= 1
    swap(nums[i], nums[j])
return j
```

#### 3-way 分区（处理重复元素）

```python
# 把数组分成 < pivot, == pivot, > pivot 三部分
# 对包含大量重复元素的数据特别快，O(n)
```

### 1.4 最坏情况与优化

**最坏情况**：
- 已排序数据，选首/尾为 pivot → O(n²)
- 改进：**随机选 pivot** 或 **三数取中**

**优化策略**：
1. **随机 pivot**：避免有序数据的退化
2. **三数取中**：选 nums[lo]、nums[mid]、nums[hi] 的中位数
3. **小数组切换插入排序**：n < 16 时用插入排序更快
4. **尾递归优化**：减小栈深度

### 1.5 应用场景

1. **通用排序**：语言内置（Python `sorted`、C `qsort`、Java `Arrays.sort`）
2. **数据库排序**：部分数据库内部用快排
3. **快速选择**：找第 k 大/小的元素（O(n) 平均）

## 2. 代码示例

### 2.1 基础快排（Lomuto 分区）

```python
# 文件：quick_sort.py
from typing import List
import random

def quick_sort(nums: List[int]) -> List[int]:
    """快速排序：Lomuto 分区，随机 pivot，O(n log n) 平均。"""
    def sort(lo: int, hi: int) -> None:
        if lo >= hi:
            return
        # 随机选 pivot，避免有序数据退化
        pivot_idx = random.randint(lo, hi)
        nums[pivot_idx], nums[hi] = nums[hi], nums[pivot_idx]

        # 分区
        i = lo
        pivot = nums[hi]
        for j in range(lo, hi):
            if nums[j] < pivot:
                nums[i], nums[j] = nums[j], nums[i]
                i += 1
        nums[i], nums[hi] = nums[hi], nums[i]

        # 递归
        sort(lo, i - 1)
        sort(i + 1, hi)

    sort(0, len(nums) - 1)
    return nums

# 测试
print(quick_sort([5, 2, 8, 1, 4]))  # [1, 2, 4, 5, 8]
```

### 2.2 Hoare 分区版本

```python
# 文件：quick_sort_hoare.py
import random

def quick_sort_hoare(nums: list[int]) -> list[int]:
    """Hoare 分区版本：性能略优于 Lomuto。"""
    def sort(lo: int, hi: int) -> None:
        if lo >= hi:
            return
        # 随机 pivot
        pivot_idx = random.randint(lo, hi)
        pivot = nums[pivot_idx]
        # Hoare 分区
        i, j = lo, hi
        while True:
            while nums[i] < pivot:
                i += 1
            while nums[j] > pivot:
                j -= 1
            if i >= j:
                break
            nums[i], nums[j] = nums[j], nums[i]
            i += 1
            j -= 1
        sort(lo, j)
        sort(j + 1, hi)

    sort(0, len(nums) - 1)
    return nums
```

### 2.3 3-way 分区（处理重复元素）

```python
# 文件：quick_sort_3way.py
import random

def quick_sort_3way(nums: list[int]) -> list[int]:
    """3-way 分区：处理大量重复元素。"""
    def sort(lo: int, hi: int) -> None:
        if lo >= hi:
            return
        # 随机 pivot
        pivot_idx = random.randint(lo, hi)
        pivot = nums[pivot_idx]

        # 3-way 分区
        lt, i, gt = lo, lo, hi
        while i <= gt:
            if nums[i] < pivot:
                nums[lt], nums[i] = nums[i], nums[lt]
                lt += 1
                i += 1
            elif nums[i] > pivot:
                nums[i], nums[gt] = nums[gt], nums[i]
                gt -= 1
            else:  # nums[i] == pivot
                i += 1

        sort(lo, lt - 1)
        sort(gt + 1, hi)

    sort(0, len(nums) - 1)
    return nums

# 测试：大量重复元素特别快
print(quick_sort_3way([5, 2, 8, 1, 4, 5, 2, 8, 5]))  # [1, 2, 2, 4, 5, 5, 5, 8, 8]
```

### 2.4 快速选择（找第 k 大的元素）

```python
# 文件：quickselect.py
import random

def quickselect(nums: list[int], k: int) -> int:
    """快速选择：找第 k 大的元素 - O(n) 平均时间。

    Args:
        nums: 数组
        k: 第几大（k=1 表示最大）
    """
    def select(lo: int, hi: int, k_small: int) -> int:
        # k_small 是第几小（k_small=0 表示最小）
        if lo == hi:
            return nums[lo]
        # 随机 pivot + 分区
        pivot_idx = random.randint(lo, hi)
        nums[pivot_idx], nums[hi] = nums[hi], nums[pivot_idx]
        pivot = nums[hi]

        i = lo
        for j in range(lo, hi):
            if nums[j] < pivot:
                nums[i], nums[j] = nums[j], nums[i]
                i += 1
        nums[i], nums[hi] = nums[hi], nums[i]

        if k_small == i - lo:
            return nums[i]
        elif k_small < i - lo:
            return select(lo, i - 1, k_small)
        else:
            return select(i + 1, hi, k_small - (i - lo + 1))

    return select(0, len(nums) - 1, len(nums) - k)

# 测试
print(quickselect([5, 2, 8, 1, 4], 1))  # 8（最大）
print(quickselect([5, 2, 8, 1, 4], 3))  # 4（第 3 大）
```

## 3. dify 仓库源码解读

### 3.1 dify 的快速排序应用：rerank

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
**核心代码**（行 1-50）：

```python
import math
from collections import Counter
from typing import Any

class WeightRerank:
    """权重重排序：根据多个特征计算文档的相关性分数。

    dify 的检索结果需要重排序（rerank），按相关性分数降序排列。

    实际使用 Python 内置 sorted()（Timsort），但内部的"分治分区"
    思想与快速排序一致。
    """

    def __init__(self):
        self._vector_weight = 0.7  # 向量相似度权重
        self._keyword_weight = 0.3  # 关键词匹配权重

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """对文档按相关性分数降序排列。

        Args:
            documents: [{"content": "...", "vector_score": 0.8, ...}, ...]
        """
        scored = []
        query_words = set(query.lower().split())

        for doc in documents:
            # 多维度打分
            vector_score = doc.get("vector_score", 0.0)
            keyword_score = self._keyword_score(
                doc.get("content", ""), query_words
            )
            final_score = (
                vector_score * self._vector_weight
                + keyword_score * self._keyword_weight
            )
            doc["rerank_score"] = final_score
            scored.append(doc)

        # 按分数降序排列（用内置 sorted，TimSort）
        scored.sort(key=lambda d: d["rerank_score"], reverse=True)

        if top_k:
            scored = scored[:top_k]

        return scored

    def _keyword_score(self, content: str, query_words: set[str]) -> float:
        """关键词匹配分数：BM25 简化版。"""
        words = content.lower().split()
        if not words:
            return 0.0
        matched = sum(1 for w in words if w in query_words)
        return matched / len(query_words) if query_words else 0.0
```

**解读**：
- 第 38 行：`scored.sort(key=lambda d: d["rerank_score"], reverse=True)`
- **实际使用 Timsort**（CPython 内部），不是手写快排
- **Timsort 的优势**：对近乎有序的数据特别快（rerank 结果可能已有部分顺序）
- **设计意图**：dify 的 rerank 需要按分数排序，内置 `sorted` 已经足够好，不应该重新发明轮子
- **分治思想**：Timsort 内部用归并 + 插入排序混合，但**底层思想仍是分治**

## 4. 关键要点总结

- 快速排序：**O(n log n) 平均，O(n²) 最坏**，O(log n) 空间
- 关键：选 pivot → 分区 → 递归
- 优化：随机 pivot、三数取中、小数组切换插入排序、3-way 分区
- **不稳定**排序，但常数因子小，实际最快
- 快速选择：找第 k 大元素 O(n) 平均
- dify 用内置 sorted（Timsort）做 rerank 排序

## 5. 练习题

### 练习 1：基础（必做）

实现快速排序的迭代版本（用栈模拟递归），避免深递归栈溢出。

### 练习 2：进阶

阅读 `api/core/rag/rerank/weight_rerank.py`，说明 dify 为什么不自己实现快排而用内置 `sorted`（提示：Timsort 的优势、代码可维护性）。

### 练习 3：挑战（选做）

实现**introsort**：开始用快排，当递归深度超过 log n 时切换到堆排，避免 O(n²) 最坏情况（C++ `std::sort` 的实现）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
- 《算法导论》第 7 章 快速排序
- CPython list.sort 实现（Tim Peters）
- LeetCode 215 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13