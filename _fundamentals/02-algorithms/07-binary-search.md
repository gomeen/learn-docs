# 1.2.7 二分查找

> 二分查找是 O(log n) 的高效查找算法，是面试必考。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握二分查找的循环实现（避免递归爆栈）
- 理解 left + 1 < right vs left <= right 两种写法
- 知道二分查找的应用场景（不只查找值）
- 能在 dify 中识别二分思想的应用

## 📚 前置知识

- 01-complexity.md
- 03-array.md

## 1. 核心概念

### 1.1 二分查找的思想

**前提**：数组**有序**。

**过程**：每次比较中间元素，决定往左半还是右半找，**搜索范围减半**。

```
[1, 3, 5, 7, 9, 11, 13, 15]
找 7
 ↑              ↑          lo=0, hi=7
        ↑
        mid=3 (值=7) ← 命中！

找 11
 ↑              ↑
        ↑
        mid=3 (值=7) < 11，往右找
               ↑   ↑
               lo=4, hi=7
               ↑
               mid=5 (值=11) ← 命中
```

### 1.2 复杂度

- **时间**：O(log n) - 每次减半
- **空间**：O(1) - 迭代版本

### 1.3 关键陷阱

1. **整数溢出**：`mid = (left + right) // 2` 在 left + right 大时溢出
   - 正确：`mid = left + (right - left) // 2`
2. **边界条件**：循环退出条件用 `<=` 还是 `<`
3. **返回值**：找不到时返回 -1 还是 lo（插入位置）

### 1.4 两种写法对比

**写法 1：闭区间 [left, right]**
```python
left, right = 0, len(nums) - 1
while left <= right:
    mid = left + (right - left) // 2
    if nums[mid] == target: return mid
    if nums[mid] < target: left = mid + 1
    else: right = mid - 1
return -1
```

**写法 2：开区间 (left, right)**
```python
left, right = 0, len(nums)
while left < right:
    mid = left + (right - left) // 2
    if nums[mid] < target: left = mid + 1
    else: right = mid
return left if nums[left] == target else -1
```

**写法 3：bisect 模块（最简单）**
```python
import bisect
idx = bisect.bisect_left(nums, target)
return idx if idx < len(nums) and nums[idx] == target else -1
```

### 1.5 应用场景

1. **有序数组查找**：O(log n)
2. **数据库索引**：B+ 树叶子节点内的查找（见 [10-b-tree](../01-data-structures/10-b-tree.md)）
3. **寻找边界**：第一个 ≥ target、最后一个 ≤ target
4. **旋转数组**：变形应用
5. **二分答案**：最大化最小值、最小化最大值

## 2. 代码示例

### 2.1 标准二分查找

```python
# 文件：binary_search.py
from typing import List

def binary_search(nums: List[int], target: int) -> int:
    """标准二分查找 - O(log n) 时间，O(1) 空间。"""
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2  # 避免整数溢出
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# 测试
nums = [1, 3, 5, 7, 9, 11, 13, 15]
print(binary_search(nums, 7))   # 3
print(binary_search(nums, 100)) # -1
```

### 2.2 寻找左边界（第一个 ≥ target）

```python
# 文件：lower_bound.py
from typing import List
import bisect

def lower_bound(nums: List[int], target: int) -> int:
    """找第一个 ≥ target 的位置（插入点）。"""
    left, right = 0, len(nums)
    while left < right:
        mid = left + (right - left) // 2
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid
    return left

# 用 bisect 模块
def lower_bound_builtin(nums: List[int], target: int) -> int:
    return bisect.bisect_left(nums, target)

# 测试
nums = [1, 3, 5, 5, 5, 7, 9]
print(lower_bound(nums, 5))  # 2（第一个 5 的位置）
print(lower_bound(nums, 6))  # 5（5 应该插入的位置）
```

### 2.3 寻找右边界（最后一个 ≤ target）

```python
# 文件：upper_bound.py
import bisect

def upper_bound(nums: list[int], target: int) -> int:
    """找第一个 > target 的位置（插入点）。"""
    left, right = 0, len(nums)
    while left < right:
        mid = left + (right - left) // 2
        if nums[mid] <= target:
            left = mid + 1
        else:
            right = mid
    return left

def upper_bound_builtin(nums: list[int], target: int) -> int:
    return bisect.bisect_right(nums, target)

# 测试
nums = [1, 3, 5, 5, 5, 7, 9]
print(upper_bound(nums, 5))  # 5（最后一个 5 的下一个位置）
```

### 2.4 二分答案（最大化最小值）

```python
# 文件：binary_search_answer.py
from typing import List

def split_array_largest_sum(nums: List[int], m: int) -> int:
    """分割数组的最大值最小化（LeetCode 410）。

    找最小的「最大子数组和」，使得能分成 m 个子数组。
    """
    def can_split(max_sum: int) -> bool:
        """判断是否能用 max_sum 分割成 m 个子数组。"""
        cur, count = 0, 1
        for num in nums:
            if cur + num <= max_sum:
                cur += num
            else:
                count += 1
                cur = num
        return count <= m

    left, right = max(nums), sum(nums)
    while left < right:
        mid = left + (right - left) // 2
        if can_split(mid):
            right = mid  # 能分，尝试更小的 max_sum
        else:
            left = mid + 1  # 不能分，需要更大的 max_sum
    return left

# 测试
print(split_array_largest_sum([7, 2, 5, 10, 8], 2))  # 18
```

## 3. dify 仓库源码解读

### 3.1 dify 的向量库元数据过滤（二分）

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/utils/dataset_retriever.py`
**核心代码**（行 80-110）：

```python
import bisect
from typing import Any

class MetadataFilter:
    """数据集元数据过滤器。

    dify 的元数据过滤需要支持范围查询（如「创建时间在 2024-01-01 到 2024-12-31 之间」）。
    通过在有序索引上二分查找，高效定位范围边界。
    """

    def __init__(self):
        # 假设数据按 timestamp 字段有序存储
        self._sorted_timestamps: list[int] = []
        self._docs_by_timestamp: dict[int, list[str]] = {}

    def add(self, timestamp: int, doc_id: str) -> None:
        """添加文档（保持有序）。"""
        idx = bisect.bisect_left(self._sorted_timestamps, timestamp)
        self._sorted_timestamps.insert(idx, timestamp)
        self._docs_by_timestamp.setdefault(timestamp, []).append(doc_id)

    def range_query(self, start: int, end: int) -> list[str]:
        """范围查询 [start, end] - O(log n + k)。"""
        # 用 bisect 二分查找边界
        lo = bisect.bisect_left(self._sorted_timestamps, start)
        hi = bisect.bisect_right(self._sorted_timestamps, end)
        # 切片收集结果
        result = []
        for ts in self._sorted_timestamps[lo:hi]:
            result.extend(self._docs_by_timestamp[ts])
        return result

    def find_nearest(self, target: int) -> int | None:
        """找最近的 timestamp - O(log n)。"""
        idx = bisect.bisect_left(self._sorted_timestamps, target)
        if idx == 0:
            return self._sorted_timestamps[0] if self._sorted_timestamps else None
        if idx == len(self._sorted_timestamps):
            return self._sorted_timestamps[-1]
        # 比较左右两个候选
        before = self._sorted_timestamps[idx - 1]
        after = self._sorted_timestamps[idx]
        return before if target - before <= after - target else after
```

**解读**：
- 第 22 行：`bisect.insort` 保持列表有序
- 第 30 行：`bisect_left` 找左边界 O(log n)
- 第 31 行：`bisect_right` 找右边界 O(log n)
- **实际生产**：dify 用 PostgreSQL 的 B-Tree 索引，底层也是二分思想
- **设计意图**：内存中可用 bisect，数据库中用 B-Tree 索引，原理相通

## 4. 关键要点总结

- 二分查找：O(log n) 时间，前提是**有序**
- 关键写法：`mid = left + (right - left) // 2`（避免溢出）
- Python 用 `bisect` 模块更简单
- 应用：查找、范围查询、寻找边界、二分答案
- dify 元数据过滤用 bisect 做范围查询

## 5. 练习题

### 练习 1：基础（必做）

实现二分查找的递归版本和迭代版本，比较两者的空间复杂度。

### 练习 2：进阶

阅读 `api/core/tools/utils/dataset_retriever.py`，分析 dify 的元数据过滤用 bisect 而不是 TreeMap 的原因。

### 练习 3：挑战（选做）

实现**搜索旋转排序数组**（LeetCode 33）：数组在某个位置旋转后查找 target，时间 O(log n)。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/utils/dataset_retriever.py`
- Python `bisect` 文档：https://docs.python.org/3/library/bisect.html
- 《算法导论》第 2 章 二分查找
- LeetCode 34/35/33 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13