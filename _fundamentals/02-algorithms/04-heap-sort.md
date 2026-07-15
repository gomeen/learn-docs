# 1.2.4 堆排序

> 堆排序利用堆结构实现 O(n log n) 的原地排序。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解堆排序的两阶段：建堆 + 排序（堆结构见 [11-heap](../01-data-structures/11-heap.md)）
- 掌握 sift_down 和 sift_up 操作
- 区分堆排序 vs [快排](./03-quick-sort.md) vs [归并](./02-merge-sort.md) 的取舍
- 能在 dify 中识别堆排序的应用

## 📚 前置知识

- 11-heap.md
- 03-quick-sort.md

## 1. 核心概念

### 1.1 堆排序的两阶段

1. **建堆**：把无序数组建成最大堆（O(n)）
2. **排序**：反复取堆顶（最大元素）放到末尾（O(n log n)）

```
初始：[5, 2, 8, 1, 4, 7, 6, 3]

建堆（最大堆）：
         8
       /   \
      7     6
     / \   / \
    5   3 4   2
   / \
  1   2

排序过程：
取堆顶 8 → [_, 7, 6, 5, 3, 4, 2, 1, 8]（8 已到位）
取堆顶 7 → [_, 6, 5, 4, 3, 1, 2, 7, 8]
...
```

### 1.2 复杂度分析

**时间复杂度**：O(n log n)
- 建堆：O(n)
- 排序：n 次 sift_down，每次 O(log n) → O(n log n)

**空间复杂度**：O(1) **原地排序**

**稳定性**：**不稳定**

### 1.3 堆排序 vs 快速排序

| 维度 | 堆排序 | 快速排序 |
|------|--------|----------|
| 时间 | O(n log n) 稳定 | O(n log n) 平均，O(n²) 最坏 |
| 空间 | O(1) 原地 | O(log n) 栈 |
| 稳定性 | 不稳定 | 不稳定 |
| 缓存友好 | ✗（跳着访问） | **✓**（顺序访问） |
| 实际性能 | 稍慢 | **更快** |

**结论**：实际工程首选快排，堆排的优势是**最坏情况保证**和**原地排序**。

### 1.4 应用场景

1. **需要保证 O(n log n) 最坏**：操作系统任务调度
2. **Top K 问题**：维护大小为 K 的堆
3. **优先级队列**：堆是天然优先级队列
4. **流式数据中位数**：两个堆

## 2. 代码示例

### 2.1 完整堆排序实现

```python
# 文件：heap_sort.py
from typing import List

def heap_sort(nums: List[int]) -> List[int]:
    """堆排序：原地排序，O(n log n) 时间，O(1) 空间。"""
    n = len(nums)

    # 阶段 1：建堆（从最后一个非叶子节点开始 sift_down）
    for i in range(n // 2 - 1, -1, -1):
        _sift_down(nums, i, n)

    # 阶段 2：排序（每次把堆顶交换到末尾）
    for end in range(n - 1, 0, -1):
        nums[0], nums[end] = nums[end], nums[0]  # 堆顶（最大）放到末尾
        _sift_down(nums, 0, end)  # 重新堆化

    return nums

def _sift_down(nums: List[int], start: int, end: int) -> None:
    """从 start 开始向下调整到 end。"""
    root = start
    while True:
        child = 2 * root + 1
        if child >= end:
            break
        # 找更大的子节点
        if child + 1 < end and nums[child] < nums[child + 1]:
            child += 1
        # 如果根已经比子节点大，停止
        if nums[root] >= nums[child]:
            break
        # 否则交换
        nums[root], nums[child] = nums[child], nums[root]
        root = child

# 测试
print(heap_sort([5, 2, 8, 1, 4]))  # [1, 2, 4, 5, 8]
```

### 2.2 性能对比

```python
# 文件：compare.py
import time
import random

def benchmark():
    n = 100000
    nums = [random.randint(0, 10000) for _ in range(n)]

    # heap_sort
    nums1 = list(nums)
    start = time.perf_counter()
    heap_sort(nums1)
    t_heap = time.perf_counter() - start

    # sorted (Timsort)
    start = time.perf_counter()
    sorted(nums)
    t_sorted = time.perf_counter() - start

    print(f"heap_sort: {t_heap:.3f}s")
    print(f"sorted:    {t_sorted:.3f}s")
    # 实际 sorted 更快（Tim Peters 优化过）

benchmark()
```

### 2.3 堆排序找前 K 大

```python
# 文件：topk_heap.py
import heapq
from typing import List

def topk_heap(nums: List[int], k: int) -> List[int]:
    """用堆找前 K 大的元素 - O(n log k)。"""
    if k <= 0 or not nums:
        return []
    # 最小堆：堆顶是当前第 K 大的最小值
    heap = []
    for num in nums:
        if len(heap) < k:
            heapq.heappush(heap, num)
        elif num > heap[0]:
            heapq.heapreplace(heap, num)
    return heap

# 测试
print(topk_heap([5, 2, 8, 1, 4, 9, 3, 7], 3))  # [7, 8, 9]
```

## 3. dify 仓库源码解读

### 3.1 dify 的优先级队列（基于堆）

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
**核心代码**（行 40-70）：

```python
import heapq
from dataclasses import dataclass
from typing import Any

@dataclass(order=True)
class PrioritizedTask:
    """带优先级的任务。"""
    priority: int
    task_id: str = field(compare=False)
    payload: dict = field(compare=False)

class WorkflowQueue:
    """工作流任务优先级队列。

    dify 的工作流任务按优先级调度（付费用户 > 普通用户），
    用 heapq 实现最小堆，最高优先级先出队。
    """

    def __init__(self):
        self._heap: list[PrioritizedTask] = []

    def push(self, task: PrioritizedTask) -> None:
        """O(log n)。"""
        heapq.heappush(self._heap, task)

    def pop(self) -> PrioritizedTask | None:
        """O(log n)。"""
        return heapq.heappop(self._heap) if self._heap else None

    def peek(self) -> PrioritizedTask | None:
        """O(1)。"""
        return self._heap[0] if self._heap else None

    def batch_pop(self, k: int) -> list[PrioritizedTask]:
        """批量取出前 k 个最高优先级任务。"""
        return [heapq.heappop(self._heap) for _ in range(min(k, len(self._heap)))]

    def stats(self) -> dict:
        """堆状态统计。"""
        return {
            "size": len(self._heap),
            "top_priority": self._heap[0].priority if self._heap else None,
        }
```

**解读**：
- 第 27 行：`heapq.heappush` 是 O(log n)，底层 sift_up
- 第 31 行：`heapq.heappop` 是 O(log n)，底层 sift_down
- 第 39 行：批量取出前 k 个任务，O(k log n)
- **堆排序思想**：每次取最大（最优先），剩下元素重新堆化
- **设计意图**：dify 需要按优先级调度任务，堆是天然优先级队列
- **生产实现**：实际 dify 用 Celery 的优先级队列，但内存队列用同样的堆思想

## 4. 关键要点总结

- 堆排序：建堆 O(n) + 排序 O(n log n) = **O(n log n)**
- **原地排序**，空间 O(1)
- 不稳定，但最坏情况保证 O(n log n)
- 实际工程首选快排，堆排用于需要保证最坏情况
- dify 用 `heapq` 实现任务优先级调度

## 5. 练习题

### 练习 1：基础（必做）

实现堆排序的迭代版本（用 while 循环代替递归的 sift_down）。

### 练习 2：进阶

阅读 `api/services/workflow/queue_dispatcher.py`，说明 dify 用 `heapq` 而不是 `sorted list` 的原因（提示：`sorted list` 的 pop 复杂度）。

### 练习 3：挑战（选做）

实现**原地堆排序的优化版**：建堆时跳过已经是子堆的节点，进一步优化建堆常数。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- 《算法导论》第 6 章 堆排序
- Python `heapq` 文档

---

**文档版本**：v1.0
**最后更新**：2026-07-13