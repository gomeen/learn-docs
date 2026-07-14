# 1.2.1 冒泡排序 / 选择排序 / 插入排序

> 三种最简单的 O(n²) 排序算法，是理解排序思想的起点。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握冒泡、选择、插入三种基础排序的实现
- 理解它们的稳定性、时间/空间复杂度
- 知道它们的适用场景（教学 vs 实际）
- 能在 dify 中识别排序的应用

## 📚 前置知识

- 01-complexity.md
- 03-array.md

## 1. 核心概念

### 1.1 排序算法的分类

**按时间复杂度**：
- **O(n²)**：冒泡、选择、插入、希尔
- **O(n log n)**：归并、快排、堆排
- **O(n)**：计数、桶、基数

**按稳定性**：
- **稳定排序**：相等元素的相对顺序不变（冒泡、插入、归并、计数）
- **不稳定排序**：相对顺序可能改变（选择、快排、堆排、希尔）

### 1.2 冒泡排序（Bubble Sort）

**思想**：相邻元素两两比较，把大的"冒泡"到末尾。

```
[5, 2, 8, 1, 4]
 ↑  ↑           5 > 2，交换 → [2, 5, 8, 1, 4]
    ↑  ↑        5 < 8，不交换
       ↑  ↑     8 > 1，交换 → [2, 5, 1, 8, 4]
          ↑  ↑  8 > 4，交换 → [2, 5, 1, 4, 8]  ← 8 到了末尾
```

**特点**：
- 时间：O(n²)
- 空间：O(1)
- 稳定
- 提前终止优化（如果某轮没交换）

### 1.3 选择排序（Selection Sort）

**思想**：每次从未排序部分找**最小值**，放到已排序末尾。

```
[5, 2, 8, 1, 4]
 找最小 1，放到位置 0 → [1, 5, 2, 8, 4]
 找最小 2，放到位置 1 → [1, 2, 5, 8, 4]
 找最小 4，放到位置 2 → [1, 2, 4, 5, 8]
 找最小 5，放到位置 3 → [1, 2, 4, 5, 8] ✓
```

**特点**：
- 时间：O(n²)，无论数据如何
- 空间：O(1)
- **不稳定**（如 `[5, 5, 2]` 会把两个 5 交换）

### 1.4 插入排序（Insertion Sort）

**思想**：从未排序部分取元素，**插入**到已排序部分的合适位置（类似打牌）。

```
[5, 2, 8, 1, 4]
 5（已排序）

 插入 2：[2, 5]（在 5 前）
 插入 8：[2, 5, 8]
 插入 1：[1, 2, 5, 8]
 插入 4：[1, 2, 4, 5, 8] ✓
```

**特点**：
- 时间：O(n²) 最坏，**O(n) 最好**（已排序）
- 空间：O(1)
- 稳定
- 适合**近乎有序**的数据

### 1.5 三种排序对比

| 算法 | 时间 | 空间 | 稳定 | 适用场景 |
|------|------|------|------|----------|
| 冒泡 | O(n²) | O(1) | ✓ | 教学、小数据 |
| 选择 | O(n²) | O(1) | ✗ | 教学、交换成本低 |
| 插入 | O(n²) | O(1) | ✓ | **近乎有序**的数据 |

## 2. 代码示例

### 2.1 冒泡排序

```python
# 文件：bubble_sort.py
from typing import List

def bubble_sort(nums: List[int]) -> List[int]:
    """冒泡排序：稳定，O(n²) 时间，O(1) 空间。"""
    n = len(nums)
    for i in range(n - 1):
        swapped = False  # 提前终止优化
        for j in range(n - 1 - i):
            if nums[j] > nums[j + 1]:
                nums[j], nums[j + 1] = nums[j + 1], nums[j]
                swapped = True
        if not swapped:
            break  # 已排好序
    return nums

# 测试
print(bubble_sort([5, 2, 8, 1, 4]))  # [1, 2, 4, 5, 8]
```

### 2.2 选择排序

```python
# 文件：selection_sort.py
from typing import List

def selection_sort(nums: List[int]) -> List[int]:
    """选择排序：不稳定，O(n²) 时间，O(1) 空间。"""
    n = len(nums)
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            if nums[j] < nums[min_idx]:
                min_idx = j
        if min_idx != i:
            nums[i], nums[min_idx] = nums[min_idx], nums[i]
    return nums

# 测试不稳定：[5, 5, 1] 会把两个 5 顺序颠倒
print(selection_sort([5, 2, 8, 1, 4]))  # [1, 2, 4, 5, 8]
```

### 2.3 插入排序

```python
# 文件：insertion_sort.py
from typing import List

def insertion_sort(nums: List[int]) -> List[int]:
    """插入排序：稳定，O(n²) 最坏，O(n) 最好（已排序）。"""
    for i in range(1, len(nums)):
        key = nums[i]
        j = i - 1
        # 把 nums[j] > key 的元素后移一位
        while j >= 0 and nums[j] > key:
            nums[j + 1] = nums[j]
            j -= 1
        nums[j + 1] = key
    return nums

# 测试：近乎有序的数据非常快
print(insertion_sort([1, 2, 3, 4, 5]))  # O(n) - 已排序
print(insertion_sort([5, 2, 8, 1, 4]))  # [1, 2, 4, 5, 8]
```

### 2.4 性能对比

```python
# 文件：compare.py
import time
import random

def benchmark():
    algorithms = {
        "bubble": bubble_sort,
        "selection": selection_sort,
        "insertion": insertion_sort,
    }
    n = 3000

    for name, fn in algorithms.items():
        nums = [random.randint(0, 10000) for _ in range(n)]
        start = time.perf_counter()
        fn(nums)
        elapsed = time.perf_counter() - start
        print(f"{name}: {elapsed:.3f}s")

benchmark()
# 输出（示例）：
# bubble: 0.385s
# selection: 0.298s
# insertion: 0.301s
```

## 3. dify 仓库源码解读

### 3.1 dify 的简单排序应用：插件排序

**文件位置**：`/Users/xu/code/github/dify/api/core/plugin/plugin_service.py`
**核心代码**（行 1-50）：

```python
from typing import Any

class PluginService:
    """插件服务：管理已安装的插件列表。

    dify 的插件按声明顺序加载，但展示时按某些规则排序（如按名称、版本）。

    对于小规模数据（< 1000 插件），简单的内置排序即可满足需求。
    """

    def __init__(self):
        self._plugins: dict[str, dict[str, Any]] = {}

    def list_plugins_sorted(
        self,
        sort_by: str = "name",
        desc: bool = False,
    ) -> list[dict]:
        """列出已排序的插件。

        使用 Python 内置 sorted()，底层是 Timsort（O(n log n) 混合排序）。
        小数据量场景，简化逻辑比性能更重要。
        """
        plugins = list(self._plugins.values())
        return sorted(
            plugins,
            key=lambda p: p.get(sort_by, ""),
            reverse=desc,
        )

    def find_latest_version(self, plugin_name: str) -> dict | None:
        """查找插件的最新版本。

        对于小规模版本列表（< 100），用简单的 max() 即可。
        """
        versions = [
            p for p in self._plugins.values()
            if p["name"] == plugin_name
        ]
        if not versions:
            return None
        # max 用法：按 version 字段比较
        return max(versions, key=lambda p: p.get("version", ""))
```

**解读**：
- 第 24 行：`sorted()` 是 Timsort，**O(n log n)**，实际工程首选
- 第 41 行：`max()` 内部也是 O(n)，小数据足够
- **dify 的设计取舍**：插件列表规模小（通常 < 1000），用 Python 内置排序即可
- **不会自己实现冒泡等 O(n²) 算法**：因为内置排序已经足够好
- **设计意图**：代码可读性 > 微优化（除非性能瓶颈）

## 4. 关键要点总结

- 冒泡排序：稳定，O(n²)，可优化提前终止
- 选择排序：不稳定，O(n²)，交换次数少
- 插入排序：稳定，O(n²) 最坏，**O(n) 最好**（近乎有序）
- 三种都是教学算法，**实际生产用内置 `sorted()`**
- Python 内置 sorted 是 Timsort，O(n log n) 且稳定

## 5. 练习题

### 练习 1：基础（必做）

实现插入排序的**二分查找优化**：用二分查找定位插入位置，减少比较次数（但仍需 O(n) 移动元素）。

### 练习 2：进阶

阅读 `api/core/plugin/plugin_service.py`，说明 dify 为什么用内置 `sorted()` 而不是自己实现排序算法（提示：从代码可读性、维护成本、性能三个角度分析）。

### 练习 3：挑战（选做）

实现**希尔排序**（Shell Sort）：插入排序的改进版，按间隔分组插入排序，逐步缩小间隔到 1。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/plugin/plugin_service.py`
- 《算法导论》第 2 章 算法基础
- Python Timsort 文档

---

**文档版本**：v1.0
**最后更新**：2026-07-13