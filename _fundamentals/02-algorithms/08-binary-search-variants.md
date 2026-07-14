# 1.2.8 变种二分查找

> 二分查找有很多变种，理解"循环不变量"是关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握寻找左边界、右边界的统一写法
- 理解"循环不变量"的思维方式
- 能在复杂问题中灵活运用二分（如旋转数组、矩阵查找）
- 能在 dify 中识别二分变种的应用

## 📚 前置知识

- 07-binary-search.md

## 1. 核心概念

### 1.1 循环不变量

**核心思想**：在循环中维护一个**不变的性质**，用这个性质判断何时停止。

```
left  |  right
  ↓        ↓
[  < x  | ? x | > x  ]
left      答案范围    right
```

### 1.2 寻找左边界（lower_bound）

找**第一个 ≥ target** 的位置：

```python
def lower_bound(nums, target):
    left, right = 0, len(nums)  # [left, right)
    while left < right:
        mid = left + (right - left) // 2
        if nums[mid] < target:
            left = mid + 1  # mid 不可能是答案
        else:
            right = mid  # mid 可能是答案，保留
    return left  # left == right
```

### 1.3 寻找右边界（upper_bound）

找**第一个 > target** 的位置：

```python
def upper_bound(nums, target):
    left, right = 0, len(nums)
    while left < right:
        mid = left + (right - left) // 2
        if nums[mid] <= target:
            left = mid + 1
        else:
            right = mid
    return left
```

### 1.4 实战问题分类

| 问题 | 二分写法 |
|------|----------|
| 找 target 出现位置 | 标准 |
| 找 target 第一次出现 | lower_bound |
| 找 target 最后一次出现 | upper_bound - 1 |
| 找第一个 ≥ target | lower_bound |
| 找第一个 > target | upper_bound |
| 找最后一个 ≤ target | upper_bound - 1 |
| 旋转数组查找 | 分类讨论 |

## 2. 代码示例

### 2.1 完整的二分查找库

```python
# 文件：binary_search_lib.py
from typing import List, Optional
import bisect

class BinarySearch:
    """二分查找工具集。"""

    @staticmethod
    def lower_bound(nums: List[int], target: int) -> int:
        """第一个 >= target 的位置。"""
        left, right = 0, len(nums)
        while left < right:
            mid = left + (right - left) // 2
            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid
        return left

    @staticmethod
    def upper_bound(nums: List[int], target: int) -> int:
        """第一个 > target 的位置。"""
        left, right = 0, len(nums)
        while left < right:
            mid = left + (right - left) // 2
            if nums[mid] <= target:
                left = mid + 1
            else:
                right = mid
        return left

    @staticmethod
    def first_occurrence(nums: List[int], target: int) -> int:
        """target 第一次出现的位置。"""
        idx = BinarySearch.lower_bound(nums, target)
        return idx if idx < len(nums) and nums[idx] == target else -1

    @staticmethod
    def last_occurrence(nums: List[int], target: int) -> int:
        """target 最后一次出现的位置。"""
        idx = BinarySearch.upper_bound(nums, target) - 1
        return idx if idx >= 0 and nums[idx] == target else -1

    @staticmethod
    def count_occurrences(nums: List[int], target: int) -> int:
        """target 出现的次数。"""
        return BinarySearch.upper_bound(nums, target) - BinarySearch.lower_bound(nums, target)

    @staticmethod
    def search_in_rotated(nums: List[int], target: int) -> int:
        """在旋转数组中查找 - O(log n)。"""
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = left + (right - left) // 2
            if nums[mid] == target:
                return mid
            # 判断哪一半是有序的
            if nums[left] <= nums[mid]:  # 左半有序
                if nums[left] <= target < nums[mid]:
                    right = mid - 1
                else:
                    left = mid + 1
            else:  # 右半有序
                if nums[mid] < target <= nums[right]:
                    left = mid + 1
                else:
                    right = mid - 1
        return -1

    @staticmethod
    def find_min_rotated(nums: List[int]) -> int:
        """找旋转数组的最小值。"""
        left, right = 0, len(nums) - 1
        while left < right:
            mid = left + (right - left) // 2
            if nums[mid] < nums[right]:
                right = mid  # 最小值在左半（含 mid）
            else:
                left = mid + 1  # 最小值在右半（不含 mid）
        return nums[left]
```

### 2.2 二维矩阵查找

```python
# 文件：search_2d_matrix.py
from typing import List

def search_matrix(matrix: List[List[int]], target: int) -> bool:
    """搜索二维矩阵（每行有序、每列有序）- O(m + n)。"""
    if not matrix or not matrix[0]:
        return False
    rows, cols = len(matrix), len(matrix[0])
    # 从右上角开始
    r, c = 0, cols - 1
    while r < rows and c >= 0:
        val = matrix[r][c]
        if val == target:
            return True
        elif val > target:
            c -= 1  # 这一列都大于 target
        else:
            r += 1  # 这一行都小于 target
    return False

def search_matrix_sorted(matrix: List[List[int]], target: int) -> bool:
    """搜索二维矩阵（每行首元素 > 上一行末元素）- O(log(m*n))。"""
    if not matrix or not matrix[0]:
        return False
    rows, cols = len(matrix), len(matrix[0])
    left, right = 0, rows * cols - 1
    while left <= right:
        mid = left + (right - left) // 2
        val = matrix[mid // cols][mid % cols]
        if val == target:
            return True
        elif val < target:
            left = mid + 1
        else:
            right = mid - 1
    return False
```

### 2.3 二分答案（实战）

```python
# 文件：binary_search_answer.py
from typing import List

def kth_smallest_in_matrix(matrix: List[List[int]], k: int) -> int:
    """二维矩阵中第 K 小的元素 - O(n log(max-min))。"""
    left, right = matrix[0][0], matrix[-1][-1]
    while left < right:
        mid = left + (right - left) // 2
        # 计算 ≤ mid 的元素个数
        count = 0
        for row in matrix:
            # row 也是有序的，可以二分
            import bisect
            count += bisect.bisect_right(row, mid)
        if count < k:
            left = mid + 1
        else:
            right = mid
    return left

# 测试
matrix = [
    [1, 5, 9],
    [10, 11, 13],
    [12, 13, 15],
]
print(kth_smallest_in_matrix(matrix, 8))  # 13
```

## 3. dify 仓库源码解读

### 3.1 dify 的文档检索（多种查询）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
**核心代码**（行 60-100）：

```python
import bisect
from typing import Any

class DatasetRetrieval:
    """数据集检索：支持多种查询模式。

    dify 的检索需要支持：
    - 精确查找（按 ID）
    - 范围查询（按时间、分数）
    - Top K（按相关性）
    - 阈值过滤（分数 < threshold 的不要）

    这些都可以用二分查找或其变种实现。
    """

    def __init__(self):
        self._sorted_doc_ids: list[str] = []  # 按 ID 排序
        self._docs: dict[str, dict] = {}

    def search_by_id_range(
        self,
        id_prefix: str,
        limit: int = 100,
    ) -> list[dict]:
        """按 ID 前缀范围查询。

        用二分找前缀起点，然后顺序扫描 limit 个。
        """
        left = bisect.bisect_left(self._sorted_doc_ids, id_prefix)
        result = []
        for i in range(left, min(left + limit, len(self._sorted_doc_ids))):
            doc_id = self._sorted_doc_ids[i]
            if not doc_id.startswith(id_prefix):
                break  # 已经跨过前缀
            result.append(self._docs[doc_id])
        return result

    def find_threshold_position(
        self,
        scores: list[float],
        threshold: float,
    ) -> int:
        """找分数 ≥ threshold 的第一个位置（左边界）。"""
        # scores 是降序排列的，用 upper_bound
        left, right = 0, len(scores)
        while left < right:
            mid = left + (right - left) // 2
            if scores[mid] >= threshold:  # 仍满足条件，可能不是第一个
                left = mid + 1
            else:
                right = mid
        return left

    def top_k_by_score(
        self,
        scores: list[float],
        k: int,
    ) -> list[int]:
        """Top K 元素的下标（用二分答案）。"""
        if not scores:
            return []
        # 找第 k 大的分数
        sorted_scores = sorted(scores, reverse=True)
        threshold = sorted_scores[k - 1] if k <= len(scores) else sorted_scores[-1]
        # 用阈值过滤
        threshold_pos = self.find_threshold_position(
            sorted(scores, reverse=True), threshold
        )
        return [i for i, s in enumerate(scores) if s >= threshold][:k]
```

**解读**：
- 第 28 行：`bisect_left` 找前缀起点 O(log n)
- 第 35 行：扫描到前缀结束，O(limit)
- 第 47 行：降序数组的 upper_bound 找阈值位置
- **设计意图**：dify 的检索需要高效的范围查询，二分查找是最适合的工具

## 4. 关键要点总结

- **循环不变量**：维护「[left, right)」区间是答案候选
- 左边界用 `lower_bound`，右边界用 `upper_bound`
- 旋转数组：先判断哪半有序，再决定搜索方向
- 二维矩阵：从右上角 / 左下角开始
- 二分答案：最大化最小、最小化最大
- dify 用 bisect 实现 ID 前缀范围查询

## 5. 练习题

### 练习 1：基础（必做）

实现 `first_occurrence` 和 `last_occurrence`，处理 target 不存在的边界情况。

### 练习 2：进阶

阅读 `api/core/rag/retrieval/dataset_retrieval.py`，分析 dify 为什么用 bisect 而不是 TreeMap。

### 练习 3：挑战（选做）

实现**寻找峰值**（LeetCode 162）：数组中 nums[i] ≠ nums[i+1]，找峰值元素（比邻居都大），要求 O(log n)。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
- LeetCode 34/33/74/153/162 题
- 《编程珠玑》第 4 章 二分查找

---

**文档版本**：v1.0
**最后更新**：2026-07-13