# 1.2.6 堆（Heap）与优先队列

> 堆是优先队列的底层实现，支持 O(log n) 的插入和 O(1) 取出最值。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解最小堆和最大堆的内部结构（完全二叉树）
- 用数组实现堆的插入和删除
- 掌握 Python `heapq` 的常用操作
- 能在 dify 中识别优先级调度的实现

## 📚 前置知识

- 06-binary-tree.md
- 03-array.md

## 1. 核心概念

### 1.1 堆的定义

**堆**是满足以下性质的**完全二叉树**：
- **最大堆**：父节点 ≥ 子节点（根最大）
- **最小堆**：父节点 ≤ 子节点（根最小）

```
最大堆：                最小堆：
       10                    1
      /  \                  / \
     8    9                2   3
    /|   /|               /|  /|
   7 5  6 4              4 5 6 7
```

### 1.2 数组存储

完全二叉树可以用数组紧凑存储：

```
数组：[10, 8, 9, 7, 5, 6, 4]
下标： 0  1  2  3  4  5  6

父子关系（下标从 0 开始）：
- 父 i → 左子 2i+1，右子 2i+2
- 子 i → 父 (i-1) // 2
```

### 1.3 核心操作

| 操作 | 时间复杂度 |
|------|------------|
| 插入 `push` | O(log n) |
| 弹出堆顶 `pop` | O(log n) |
| 查看堆顶 `top` | O(1) |
| 建堆 `heapify` | O(n) |

### 1.4 堆 vs 排序

**堆排序**：每次 O(log n) 取堆顶，总共 O(n log n)。

```
[3, 1, 4, 1, 5, 9, 2, 6]
 ↓
[1, 1, 2, 3, 4, 5, 6, 9]  ← 升序
```

### 1.5 堆的应用场景

1. **优先队列**：任务调度（高优先级先执行）
2. **Top K 问题**：找前 K 大/小的元素
3. **堆排序**：O(n log n) 排序
4. **Dijkstra 算法**：图的最短路径
5. **流式数据中位数**：维护两个堆

## 2. 代码示例

### 2.1 Python `heapq` 模块

```python
# 文件：heap_demo.py
import heapq

# heapq 默认是最小堆
nums = [3, 1, 4, 1, 5, 9, 2, 6]
heapq.heapify(nums)  # O(n) 建堆
print(nums)  # [1, 1, 2, 6, 5, 9, 4, 3]

# 弹出最小
print(heapq.heappop(nums))  # 1
print(heapq.heappop(nums))  # 1

# 推入新元素
heapq.heappush(nums, 0)
print(heapq.heappop(nums))  # 0
```

### 2.2 实现最大堆（用负数技巧）

```python
# 文件：max_heap.py
import heapq

class MaxHeap:
    """用 heapq 实现最大堆（负数技巧）。"""

    def __init__(self):
        self._heap: list[int] = []

    def push(self, val: int) -> None:
        heapq.heappush(self._heap, -val)

    def pop(self) -> int:
        return -heapq.heappop(self._heap)

    def top(self) -> int:
        return -self._heap[0]

    def __len__(self) -> int:
        return len(self._heap)

# 测试
mh = MaxHeap()
for x in [3, 1, 4, 1, 5, 9, 2, 6]:
    mh.push(x)

print(mh.pop())  # 9
print(mh.pop())  # 6
print(mh.pop())  # 5
```

### 2.3 Top K 问题

```python
# 文件：topk.py
import heapq
from typing import List

def topk_smallest(nums: List[int], k: int) -> List[int]:
    """前 K 小的元素 - O(n log k)。"""
    if k <= 0:
        return []
    # 最大堆：堆顶是当前第 K 小的最大值
    heap = []
    for num in nums:
        if len(heap) < k:
            heapq.heappush(heap, -num)
        elif -heap[0] > num:
            heapq.heapreplace(heap, -num)
    return [-x for x in heap]

def topk_largest(nums: List[int], k: int) -> List[int]:
    """前 K 大的元素 - O(n log k)。"""
    if k <= 0:
        return []
    heap = []
    for num in nums:
        if len(heap) < k:
            heapq.heappush(heap, num)
        elif heap[0] < num:
            heapq.heapreplace(heap, num)
    return heap

# 测试
print(topk_smallest([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5], 3))  # [1, 1, 2]
print(topk_largest([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5], 3))   # [6, 9, 5]
```

### 2.4 手写堆（完整版）

```python
# 文件：my_heap.py
from typing import Any, List

class MinHeap:
    """手写最小堆，加深理解。"""

    def __init__(self):
        self._heap: List[Any] = []

    def _parent(self, i: int) -> int:
        return (i - 1) // 2

    def _left(self, i: int) -> int:
        return 2 * i + 1

    def _right(self, i: int) -> int:
        return 2 * i + 2

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _sift_up(self, i: int) -> None:
        """上浮：新元素比父节点小则交换。"""
        while i > 0 and self._heap[i] < self._heap[self._parent(i)]:
            self._swap(i, self._parent(i))
            i = self._parent(i)

    def _sift_down(self, i: int) -> None:
        """下沉：父节点比子节点大则交换。"""
        n = len(self._heap)
        while True:
            smallest = i
            l, r = self._left(i), self._right(i)
            if l < n and self._heap[l] < self._heap[smallest]:
                smallest = l
            if r < n and self._heap[r] < self._heap[smallest]:
                smallest = r
            if smallest == i:
                break
            self._swap(i, smallest)
            i = smallest

    def push(self, val: Any) -> None:
        self._heap.append(val)
        self._sift_up(len(self._heap) - 1)

    def pop(self) -> Any:
        if not self._heap:
            raise IndexError("pop from empty heap")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

    def top(self) -> Any:
        return self._heap[0]
```

## 3. dify 仓库源码解读

### 3.1 dify 的任务优先级队列

**文件位置**：`/Users/xu/code/github/dify/api/tasks/rag_pipeline/priority_rag_pipeline_run_task.py`
**核心代码**（行 1-40）：

```python
import heapq
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class PrioritizedTask:
    """带优先级的 RAG 任务。

    @dataclass(order=True) 自动生成 __lt__ 方法，
    这样 heapq 可以按 priority 排序。
    """
    priority: int
    created_at: float = field(compare=False)  # 不参与排序
    payload: dict[str, Any] = field(compare=False)

class PriorityTaskQueue:
    """RAG pipeline 任务优先级队列。

    dify 的 RAG 任务分优先级（付费用户优先），
    用最小堆实现，最高 priority 先出队。
    """

    def __init__(self):
        self._heap: list[PrioritizedTask] = []

    def push(self, task: PrioritizedTask) -> None:
        heapq.heappush(self._heap, task)  # O(log n)

    def pop(self) -> PrioritizedTask | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap)  # O(log n)

    def peek(self) -> PrioritizedTask | None:
        return self._heap[0] if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)
```

**解读**：
- 第 9 行：`@dataclass(order=True)` 自动生成 `__lt__`，按 priority 排序
- 第 16 行：`compare=False` 让 `created_at` 和 `payload` 不参与排序（避免 tie-breaker 问题）
- 第 29 行：`heapq.heappush` 是 O(log n)
- **设计意图**：dify 需要按优先级调度 RAG 任务（付费用户 > 普通用户），用堆保证高优先级任务优先执行
- **实际生产**：dify 用 Celery 的优先级队列，但内存队列用同样的堆思想

## 4. 关键要点总结

- 堆是完全二叉树，**数组存储**，父子关系通过下标计算
- 最大堆父 ≥ 子，最小堆父 ≤ 子
- Python `heapq` 是**最小堆**，实现最大堆用**负数技巧**
- 插入/删除都是 **O(log n)**，建堆 **O(n)**
- Top K 问题用大小为 K 的堆，时间 O(n log k)
- dify 用堆实现任务优先级调度

## 5. 练习题

### 练习 1：基础（必做）

用 `heapq` 实现一个**数据流中位数**维护器：每次插入数据后，返回当前所有数据的中位数。

### 练习 2：进阶

阅读 `api/tasks/rag_pipeline/priority_rag_pipeline_run_task.py`，说明 dify 为什么用堆而不是 sorted list 做优先级队列（提示：`sorted` 的 `pop(0)` 复杂度是多少？）。

### 练习 3：挑战（选做）

实现一个**斐波那契堆**（Fibonacci Heap）的简化版，了解它在 Dijkstra 算法中的优势。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/rag_pipeline/priority_rag_pipeline_run_task.py`
- Python heapq 文档：https://docs.python.org/3/library/heapq.html
- 《算法导论》第 6 章 堆排序

---

**文档版本**：v1.0
**最后更新**：2026-07-13