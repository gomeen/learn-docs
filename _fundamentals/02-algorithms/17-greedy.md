# 1.5.1 贪心算法

> 贪心算法在每一步选当前最优解，期望全局最优。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解贪心的"局部最优 → 全局最优"思想
- 掌握区间调度、跳跃游戏等经典问题
- 区分贪心与 DP 的取舍
- 能在 dify 中识别贪心的应用

## 📚 前置知识

- 13-dp-basics.md
- 18-divide-conquer.md

## 1. 核心概念

### 1.1 贪心的本质

**贪心**：在每一步选择当前看来**最好的选择**，**不回头**。

```
DP：考虑所有情况，记录子问题解
贪心：只看眼前，选最大的（或最小的）
```

### 1.2 贪心适用条件

1. **贪心选择性质**：局部最优能推出全局最优
2. **最优子结构**：问题的最优解包含子问题的最优解
3. **无后效性**：选择不会影响后续选择

### 1.3 贪心 vs DP

| 维度 | 贪心 | DP |
|------|------|----|
| 选择 | 当前最优 | 全局最优 |
| 时间复杂度 | 通常 O(n log n) | O(n²) ~ O(n³) |
| 适用范围 | 较窄（需证明） | 较广 |
| 证明 | 必须证明正确性 | 状态转移保证正确 |

### 1.4 经典问题

1. **区间调度**：选最多不重叠区间
2. **跳跃游戏**：能否到达终点
3. **任务分配**：最小化等待时间
4. **Huffman 编码**：最优前缀码
5. **Dijkstra 算法**：最短路径

## 2. 代码示例

### 2.1 区间调度（最多不重叠区间）

```python
# 文件：interval_scheduling.py
from typing import List, Tuple

def interval_scheduling(intervals: List[Tuple[int, int]]) -> int:
    """区间调度：选最多互不重叠的区间（LeetCode 435 变种）。

    贪心策略：按结束时间排序，每次选结束最早的。
    """
    if not intervals:
        return 0
    # 按结束时间排序
    intervals.sort(key=lambda x: x[1])

    count = 1
    end = intervals[0][1]
    for i in range(1, len(intervals)):
        if intervals[i][0] >= end:
            count += 1
            end = intervals[i][1]
    return count

# 测试
intervals = [(1, 3), (2, 4), (3, 5), (5, 7)]
print(interval_scheduling(intervals))  # 3：选 (1,3), (3,5), (5,7)
```

### 2.2 跳跃游戏

```python
# 文件：jump_game.py
from typing import List

def can_jump(nums: List[int]) -> bool:
    """跳跃游戏（LeetCode 55）：能否到达最后位置。

    贪心：维护当前能到达的最远距离。
    """
    max_reach = 0
    for i in range(len(nums)):
        if i > max_reach:
            return False  # 当前点不可达
        max_reach = max(max_reach, i + nums[i])
        if max_reach >= len(nums) - 1:
            return True
    return True

def jump(nums: List[int]) -> int:
    """跳跃游戏 II：最少跳跃次数到终点。"""
    jumps = 0
    current_end = 0
    farthest = 0
    for i in range(len(nums) - 1):
        farthest = max(farthest, i + nums[i])
        if i == current_end:
            jumps += 1
            current_end = farthest
    return jumps

# 测试
print(can_jump([2, 3, 1, 1, 4]))  # True
print(can_jump([3, 2, 1, 0, 4]))  # False
print(jump([2, 3, 1, 1, 4]))      # 2
```

### 2.3 任务分配（最小化总等待时间）

```python
# 文件：task_assignment.py
from typing import List, Tuple

def minimize_waiting_time(tasks: List[int]) -> int:
    """任务分配：执行时间短的先做，最小化总等待时间。

    贪心策略：按执行时间升序。
    """
    tasks.sort()
    total_wait = 0
    cur = 0
    for t in tasks:
        total_wait += cur  # 等待前面所有任务
        cur += t
    return total_wait

# 测试
print(minimize_waiting_time([3, 1, 4, 1, 5]))  # 0+1+2+6+10 = 19
```

### 2.4 分糖果（区间贪心）

```python
# 文件：candy.py
from typing import List

def candy(ratings: List[int]) -> int:
    """分糖果（LeetCode 135）：评分高的孩子比邻居糖果多，最少糖果数。

    两次贪心扫描：
    1. 从左到右：如果 ratings[i] > ratings[i-1]，糖果更多
    2. 从右到左：如果 ratings[i] > ratings[i+1]，糖果更多
    """
    n = len(ratings)
    candies = [1] * n

    # 左到右
    for i in range(1, n):
        if ratings[i] > ratings[i - 1]:
            candies[i] = candies[i - 1] + 1

    # 右到左
    for i in range(n - 2, -1, -1):
        if ratings[i] > ratings[i + 1]:
            candies[i] = max(candies[i], candies[i + 1] + 1)

    return sum(candies)

# 测试
print(candy([1, 0, 2]))  # 5（2, 1, 2）
print(candy([1, 2, 2]))  # 4（1, 2, 1）
```

## 3. dify 仓库源码解读

### 3.1 dify 的工作流任务调度（贪心）

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
**核心代码**（行 80-110）：

```python
import heapq
from typing import Any

class WorkflowScheduler:
    """工作流任务调度器。

    dify 的工作流任务调度使用贪心 + 优先级：
    - 按优先级排序（贪心：高优先级先做）
    - 同优先级按时间戳排序（先进先出）
    """

    def __init__(self):
        self._queue: list = []  # 最小堆：(priority, timestamp, task)

    def add_task(self, task: dict, priority: int = 0) -> None:
        """添加任务到队列。"""
        # 用负数实现"最大优先级先出"
        import time
        heapq.heappush(
            self._queue,
            (-priority, time.time(), task),
        )

    def get_next(self) -> dict | None:
        """获取下一个任务（贪心选优先级最高的）。"""
        if not self._queue:
            return None
        neg_priority, ts, task = heapq.heappop(self._queue)
        return task

    def batch_schedule(
        self,
        tasks: list[dict],
        max_concurrent: int,
    ) -> list[dict]:
        """批量调度：贪心选优先级最高的 N 个任务并行执行。"""
        # 按优先级排序（贪心）
        sorted_tasks = sorted(
            tasks,
            key=lambda t: t.get("priority", 0),
            reverse=True,
        )
        # 取 top N 并行执行
        return sorted_tasks[:max_concurrent]

    def estimate_completion_order(
        self,
        tasks: list[dict],
    ) -> list[dict]:
        """估算任务完成顺序（SJF - 短作业优先）。

    贪心策略：执行时间短的先做，平均等待时间最少。
    """
        return sorted(tasks, key=lambda t: t.get("estimated_duration", 0))
```

**解读**：
- 第 21 行：用堆实现优先级队列（贪心：取最高优先级）
- 第 35 行：批量调度时按优先级排序选 top N
- 第 43 行：SJF（短作业优先）贪心策略
- **设计意图**：任务调度需要在公平（先来先服务）和效率（优先级）之间平衡
- **贪心证明**：SJF 能最小化平均等待时间（这是经典的贪心证明）

## 4. 关键要点总结

- 贪心：**局部最优 → 全局最优**（需要证明）
- 时间复杂度通常 O(n log n)（排序 + 一次扫描）
- 与 DP 区别：贪心不回溯，DP 记录所有可能
- 应用：区间调度、跳跃游戏、任务分配、Huffman
- **必须证明正确性**（否则可能错）
- dify 用贪心做任务优先级调度

## 5. 练习题

### 练习 1：基础（必做）

实现**买卖股票的最佳时机**（LeetCode 121）：最多一次交易，求最大利润。用贪心解决。

### 练习 2：进阶

阅读 `api/services/workflow/queue_dispatcher.py`，说明 dify 的任务调度为什么用贪心（SJF）而不是 DP。

### 练习 3：挑战（选做）

实现**Huffman 编码**：用最小堆构建 Huffman 树，验证编码的最优性。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- 《算法导论》第 16 章 贪心算法
- LeetCode 55/45/435/135 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13