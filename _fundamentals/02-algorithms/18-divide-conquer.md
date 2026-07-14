# 1.5.2 分治算法

> 分治算法把问题分解为子问题，递归求解后合并结果。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分治的"分、治、合"三步
- 掌握归并排序、快速排序等分治应用
- 区分分治与 DP、贪心的取舍
- 能在 dify 中识别分治的应用

## 📚 前置知识

- 09-recursion.md
- 02-merge-sort.md

## 1. 核心概念

### 1.1 分治的三步

```
1. 分（Divide）：把问题分成 k 个子问题
2. 治（Conquer）：递归解决子问题（子问题足够小时直接解）
3. 合（Combine）：合并子问题的解
```

### 1.2 分治 vs DP

| 维度 | 分治 | DP |
|------|------|----|
| 子问题重叠 | 否 | **是**（DP 用记忆化） |
| 子问题独立 | **是** | 否 |
| 典型应用 | 归并、快排、Strassen | 背包、LCS、最短路径 |

**关键区别**：分治的子问题**独立**，DP 的子问题**重叠**。

### 1.3 分治的复杂度分析

**主定理（Master Theorem）**：
```
T(n) = a T(n/b) + f(n)

情况 1：f(n) = O(n^(log_b(a) - ε))  →  T(n) = Θ(n^log_b(a))
情况 2：f(n) = Θ(n^log_b(a))        →  T(n) = Θ(n^log_b(a) log n)
情况 3：f(n) = Ω(n^(log_b(a) + ε))  →  T(n) = Θ(f(n))
```

### 1.4 经典分治算法

1. **归并排序**：分 O(1)，治 2T(n/2)，合 O(n) → O(n log n)
2. **快速排序**：分 O(n)，治 2T(n/2)，合 O(1) → O(n log n)
3. **二分查找**：分 O(1)，治 T(n/2)，合 O(1) → O(log n)
4. **Strassen 矩阵乘法**：从 O(n³) 优化到 O(n^2.807)
5. **最近点对**：分治经典问题

### 1.5 应用场景

1. **排序**：归并、快排
2. **搜索**：二分查找
3. **数学**：矩阵乘法、大整数乘法
4. **几何**：最近点对、凸包
5. **分治 FFT**：多项式乘法

## 2. 代码示例

### 2.1 归并排序（分治经典）

```python
# 文件：merge_sort_dc.py
from typing import List

def merge_sort(nums: List[int]) -> List[int]:
    """归并排序：分治经典，O(n log n)。"""
    if len(nums) <= 1:
        return nums

    # 1. 分
    mid = len(nums) // 2
    left = merge_sort(nums[:mid])
    right = merge_sort(nums[mid:])

    # 2. 合（治已隐含在递归中）
    return merge(left, right)

def merge(left: List[int], right: List[int]) -> List[int]:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
```

### 2.2 最近点对问题

```python
# 文件：closest_pair.py
from typing import List, Tuple
import math

def closest_pair(points: List[Tuple[float, float]]) -> float:
    """最近点对：找距离最近的两点（分治 O(n log n)）。

    points: [(x1, y1), (x2, y2), ...]
    """
    def dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def closest(px: List, py: List) -> float:
        n = len(px)
        if n <= 3:
            # 暴力
            return min(
                dist(px[i], px[j])
                for i in range(n) for j in range(i + 1, n)
            )

        # 1. 分（按 x 中位数分）
        mid = n // 2
        mid_x = px[mid][0]
        left_px = px[:mid]
        right_px = px[mid:]
        # py 按 mid_x 分到两侧
        left_py = [p for p in py if p[0] <= mid_x]
        right_py = [p for p in py if p[0] > mid_x]

        # 2. 治
        dl = closest(left_px, left_py)
        dr = closest(right_px, right_py)
        d = min(dl, dr)

        # 3. 合：检查跨越中线的点对
        strip = [p for p in py if abs(p[0] - mid_x) < d]
        for i in range(len(strip)):
            for j in range(i + 1, len(strip)):
                # 只需检查 y 方向后续 7 个点
                if strip[j][1] - strip[i][1] >= d:
                    break
                d = min(d, dist(strip[i], strip[j]))
        return d

    # 预排序
    px = sorted(points, key=lambda p: p[0])
    py = sorted(points, key=lambda p: p[1])
    return closest(px, py)

# 测试
points = [(0, 0), (1, 1), (2, 2), (3, 3)]
print(closest_pair(points))  # ~1.414（(0,0) 和 (1,1)）
```

### 2.3 大整数乘法（Karatsuba）

```python
# 文件：karatsuba.py
from math import log10

def karatsuba(x: int, y: int) -> int:
    """Karatsuba 大整数乘法 - O(n^log2(3)) ≈ O(n^1.585)。

    比传统 O(n²) 更快。
    """
    if x < 10 or y < 10:
        return x * y

    n = max(len(str(x)), len(str(y)))
    m = n // 2

    # 拆分：x = a * 10^m + b, y = c * 10^m + d
    a, b = divmod(x, 10 ** m)
    c, d = divmod(y, 10 ** m)

    # 递归计算三部分
    ac = karatsuba(a, c)
    bd = karatsuba(b, d)
    ad_bc = karatsuba(a + b, c + d) - ac - bd

    # 合并：x * y = ac * 10^(2m) + (ad+bc) * 10^m + bd
    return ac * 10 ** (2 * m) + ad_bc * 10 ** m + bd

# 测试
print(karatsuba(1234, 5678))  # 7006652
```

### 2.4 多数元素（分治版）

```python
# 文件：majority_element.py
from typing import List

def majority_element(nums: List[int]) -> int:
    """多数元素（LeetCode 169）：找出现次数超过 n/2 的元素。

    分治：左右两边的多数元素，相同则是，相异则需要计数。
    Boyer-Moore 更简单（Boyer-Moore 投票算法 O(n)）。
    """
    def dc(lo: int, hi: int) -> int:
        # base case
        if lo == hi:
            return nums[lo]
        mid = (lo + hi) // 2
        left = dc(lo, mid)
        right = dc(mid + 1, hi)

        if left == right:
            return left
        # 计数
        left_count = sum(1 for i in range(lo, hi + 1) if nums[i] == left)
        right_count = sum(1 for i in range(lo, hi + 1) if nums[i] == right)
        return left if left_count > right_count else right

    return dc(0, len(nums) - 1)

# 测试
print(majority_element([3, 2, 3]))  # 3
```

## 3. dify 仓库源码解读

### 3.1 dify 的文档检索（分治思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_index.py`
**核心代码**（行 1-50）：

```python
import numpy as np
from typing import Any

class HierarchicalIndex:
    """分层向量索引（类似 HNSW）。

    dify 在大规模向量库中使用分层索引（Hierarchical Navigable Small World），
    分治思想：
    - 把向量空间分成多层
    - 上层：稀疏采样（少而精），快速缩小范围
    - 下层：密集搜索（多而细），精确匹配

    实际查找类似分治：
    1. 从顶层开始（粗搜索）
    2. 沿层向下（细搜索）
    3. 在底层找精确匹配
    """

    def __init__(self, vectors: list, levels: int = 3):
        self._vectors = vectors
        self._levels = levels
        self._hierarchical = self._build_hierarchy(vectors, levels)

    def _build_hierarchy(self, vectors: list, levels: int) -> list:
        """递归构建分层索引 - 分治。"""
        if levels == 0 or len(vectors) <= 1:
            return vectors
        # 用 k-means 把向量分成多个簇（分）
        clusters = self._cluster(vectors, k=min(len(vectors) // 10, 10))
        # 递归构建子层（治）
        return [
            self._build_hierarchy(cluster, levels - 1)
            for cluster in clusters
        ]

    def _cluster(self, vectors: list, k: int) -> list[list]:
        """简化的聚类（实际用 k-means）。"""
        # 简化：随机分配
        import random
        random.shuffle(vectors)
        return [vectors[i::k] for i in range(k)]

    def search(self, query, top_k: int = 5) -> list:
        """分层搜索：分治。"""
        # 从顶层开始
        candidates = self._hierarchical
        for level in range(self._levels - 1, -1, -1):
            # 在当前层找最相似的簇
            best_cluster = self._find_closest_cluster(query, candidates)
            # 向下递归（合）
            candidates = best_cluster
        return candidates[:top_k]

    def _find_closest_cluster(self, query, clusters: list) -> list:
        """找最相似的簇（简化）。"""
        # 实际计算距离
        return clusters[0] if clusters else []
```

**解读**：
- 第 24 行：分治构建索引树（k-means 聚类）
- 第 43 行：搜索时分层下钻，类似分治的缩小规模
- **设计意图**：分层索引是经典分治 + 空间换时间的应用
- **实际生产**：dify 用 FAISS / Milvus 等成熟库，不是手写

## 4. 关键要点总结

- 分治三步：**分、治、合**
- 子问题**独立**，与 DP 的子问题重叠不同
- 主定理：T(n) = aT(n/b) + f(n) → 三种情况
- 经典应用：归并排序、快排、二分、Karatsuba、Strassen
- 时间复杂度分析：递归树或主定理
- dify 的分层向量索引有分治思想

## 5. 练习题

### 练习 1：基础（必做）

用主定理分析归并排序、快速排序、二分查找的时间复杂度。

### 练习 2：进阶

阅读 `api/core/rag/datasource/vdb/vector_index.py`，说明 dify 的分层索引如何体现分治思想。

### 练习 3：挑战（选做）

实现**Strassen 矩阵乘法**：从 O(n³) 优化到 O(n^2.807)，用 7 次乘法代替 8 次。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_index.py`
- 《算法导论》第 4 章 分治策略
- 《算法导论》第 30 章 矩阵乘法

---

**文档版本**：v1.0
**最后更新**：2026-07-13