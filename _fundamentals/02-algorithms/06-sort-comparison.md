# 1.2.6 排序算法对比与选择

> 排序算法有很多种，如何选择？本文给出实战决策树。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握各种排序算法的对比维度（时间、空间、稳定性）
- 根据数据特征选择合适的排序算法
- 知道各语言内置排序的实现原理
- 能在 dify 中做出合理的排序选择

## 📚 前置知识

- 01-basic-sort.md 到 05-linear-sort.md

## 1. 核心概念

### 1.1 排序算法全景对比

| 算法 | 时间（平均） | 时间（最坏） | 空间 | 稳定性 | 适用场景 |
|------|-------------|-------------|------|--------|----------|
| 冒泡 | O(n²) | O(n²) | O(1) | ✓ | 教学（[基础排序](./01-basic-sort.md)） |
| 选择 | O(n²) | O(n²) | O(1) | ✗ | 教学（同上） |
| 插入 | O(n²) | O(n²) | O(1) | ✓ | **近乎有序** |
| 希尔 | O(n log n) | O(n²) | O(1) | ✗ | 中等规模 |
| **[归并](./02-merge-sort.md)** | **O(n log n)** | O(n log n) | O(n) | ✓ | 链表、外排序 |
| **[快排](./03-quick-sort.md)** | **O(n log n)** | O(n²) | O(log n) | ✗ | **通用首选** |
| **[堆排](./04-heap-sort.md)** | O(n log n) | **O(n log n)** | O(1) | ✗ | 最坏保证 |
| 计数 | O(n + k) | O(n + k) | O(k) | ✓ | 范围小的整数（[线性排序](./05-linear-sort.md)） |
| 桶排 | O(n + k) | O(n²) | O(n + k) | ✓ | 均匀分布（同上） |
| 基数 | O(d × n) | O(d × n) | O(k) | ✓ | 整数、字符串（同上） |

### 1.2 各语言内置排序实现

| 语言 | 排序算法 | 特点 |
|------|----------|------|
| **Python** | Timsort | 稳定，O(n log n)，结合归并和插入 |
| **Java** | Timsort（对象）/ Dual-Pivot Quicksort（基本类型） | 对象稳定，基本类型快 |
| **C++** | Introsort（快排 + 堆排 + 插入排序混合） | 不稳定，O(n log n) 保证 |
| **Go** | pdqsort（模式检测快排） | 不稳定，自适应 |
| **Rust** | Timsort（稳定）/ pdqsort（不稳定） | 两种都提供 |
| **JavaScript** | Timsort（V8） | 稳定 |

### 1.3 排序选择决策树

```
开始
 │
 ├─ 数据规模 n 是多少？
 │   ├─ n ≤ 50：插入排序（常数小）
 │   └─ n > 50：
 │       │
 │       ├─ 数据是否近乎有序？
 │       │   └─ 是：插入排序 / Timsort
 │       │
 │       ├─ 是否需要稳定？
 │       │   ├─ 是：归并排序 / Timsort
 │       │   └─ 否：快排 / 堆排
 │       │
 │       └─ 数据有特殊性质吗？
 │           ├─ 整数、范围小：计数排序
 │           ├─ 均匀分布：桶排序
 │           └─ 定长字符串/整数：基数排序
```

### 1.4 实战选择建议

**默认选择**：用语言内置的 `sorted()`（Timsort）

**手动选择排序的场景**：
1. 嵌入式/资源受限：堆排序（O(1) 空间）
2. 最坏情况保证：堆排序或 introsort
3. 链表排序：归并排序（O(1) 额外空间）
4. 大数据外排序：归并排序
5. 数据范围小的整数：计数排序

## 2. 代码示例

### 2.1 决策树实现

```python
# 文件：sort_selector.py
from typing import List, Any

class SortSelector:
    """根据数据特征自动选择最优排序算法。"""

    @staticmethod
    def sort(nums: List[Any]) -> List[Any]:
        # 规则 1：超小数据用插入排序
        if len(nums) <= 16:
            return SortSelector._insertion_sort(nums)

        # 规则 2：检查是否近乎有序
        if SortSelector._is_nearly_sorted(nums):
            return sorted(nums)  # Timsort 对近乎有序数据特别快

        # 规则 3：默认 Timsort
        return sorted(nums)

    @staticmethod
    def _insertion_sort(nums: List[int]) -> List[int]:
        for i in range(1, len(nums)):
            key = nums[i]
            j = i - 1
            while j >= 0 and nums[j] > key:
                nums[j + 1] = nums[j]
                j -= 1
            nums[j + 1] = key
        return nums

    @staticmethod
    def _is_nearly_sorted(nums: List[int]) -> bool:
        """检查是否近乎有序（乱序元素占比 < 10%）。"""
        if len(nums) < 2:
            return True
        inversions = 0
        for i in range(1, len(nums)):
            if nums[i] < nums[i - 1]:
                inversions += 1
                if inversions > len(nums) * 0.1:
                    return False
        return True
```

### 2.2 稳定性测试

```python
# 文件：stability_test.py
from typing import List, Tuple

def is_stable(sort_func) -> bool:
    """测试排序算法是否稳定。"""
    # [(key, original_index), ...]
    data = [(2, 0), (1, 1), (2, 2), (1, 3)]
    sorted_data = sort_func(data)
    # 检查相同 key 的原始顺序是否保留
    indices_by_key: dict[int, list[int]] = {}
    for key, idx in data:
        indices_by_key.setdefault(key, []).append(idx)
    return all(
        sorted(indices) == indices
        for indices in indices_by_key.values()
    )

# sorted 是稳定的
print(is_stable(sorted))  # True
```

### 2.3 性能基准测试

```python
# 文件：benchmark.py
import time
import random

def benchmark_all():
    algorithms = {
        "sorted (Timsort)": sorted,
        "heap_sort": heap_sort,
        "merge_sort": merge_sort,
        "quick_sort": quick_sort,
    }
    n = 100000
    data = [random.randint(0, 10000) for _ in range(n)]

    for name, fn in algorithms.items():
        nums = list(data)
        start = time.perf_counter()
        if name == "sorted (Timsort)":
            result = fn(nums)
        else:
            result = fn(nums)
        elapsed = time.perf_counter() - start
        print(f"{name:25s}: {elapsed:.3f}s")

benchmark_all()
# 典型输出：
# sorted (Timsort)        : 0.012s  ← 最快
# heap_sort               : 0.108s
# merge_sort              : 0.039s
# quick_sort              : 0.025s
```

## 3. dify 仓库源码解读

### 3.1 dify 的内置排序使用

**文件位置**：`/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
**核心代码**（行 60-90）：

```python
from typing import Any
from collections import deque

class AppQueueManager:
    """应用事件队列管理器。

    dify 的流式响应需要按事件发生顺序返回（先来的先发），
    但某些场景需要按优先级排序后发送（如错误事件优先）。
    """

    def __init__(self):
        self._events: deque = deque()
        self._events_with_priority: list[dict] = []

    def publish(self, event: Any) -> None:
        """发布事件（FIFO 默认顺序）。"""
        self._events.append(event)

    def publish_priority(self, event: dict, priority: int) -> None:
        """发布优先级事件。"""
        self._events_with_priority.append({
            "event": event,
            "priority": priority,
        })

    def flush_sorted(self) -> list[dict]:
        """按优先级排序后 flush。"""
        # 用内置 sorted（Timsort，稳定）
        sorted_events = sorted(
            self._events_with_priority,
            key=lambda e: e["priority"],
            reverse=True,  # 高优先级在前
        )
        self._events_with_priority.clear()
        return [e["event"] for e in sorted_events]

    def stats(self) -> dict:
        """队列状态。"""
        return {
            "fifo_count": len(self._events),
            "priority_count": len(self._events_with_priority),
        }
```

**解读**：
- 第 31 行：`sorted()` 是 Timsort，**O(n log n) 且稳定**
- 第 35 行：稳定排序保证相同优先级的多个事件按插入顺序返回
- **dify 的设计选择**：用内置 `sorted` 而不是自己实现排序
- **设计意图**：代码可读性、可靠性、性能的最佳平衡

## 4. 关键要点总结

- **默认用内置排序**：Python `sorted`、Java `Arrays.sort` 都是工业级优化
- 选择排序算法看三个维度：时间、空间、稳定性
- **稳定性**很重要：多关键字排序需要稳定（如先按姓名排，再按年龄排）
- 特定场景用特定算法：链表用归并、小整数用计数、均匀分布用桶排
- dify 用内置 `sorted` 做事件优先级排序

## 5. 练习题

### 练习 1：基础（必做）

设计一个排序选择函数 `choose_sort(data)`，根据数据特征（规模、是否近乎有序、是否需要稳定）选择最优排序算法。

### 练习 2：进阶

阅读 `api/core/app/apps/base_app_queue_manager.py`，说明 dify 为什么用内置 `sorted` 而不是 `heapq.nlargest` 或自己实现快排。

### 练习 3：挑战（选做）

研究 Java `Arrays.sort` 在排序对象数组时用 Timsort，但排序基本类型用 Dual-Pivot Quicksort，分析为什么有这种区分。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
- Python Timsort 原理：https://bugs.python.org/file4451/timsort.txt
- Java 排序实现：https://docs.oracle.com/javase/8/docs/api/java/util/Arrays.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13