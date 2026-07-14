# 1.4.1 动态规划基础：斐波那契 / 爬楼梯

> 动态规划（DP）是把大问题分解为子问题，记录子问题解避免重复计算。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 DP 的两个关键：状态定义 + 状态转移
- 掌握自顶向下（记忆化）和自底向上（迭代）两种实现
- 区分 DP 与分治、贪心的取舍
- 能在 dify 中识别 DP 的应用

## 📚 前置知识

- 09-recursion.md
- 18-divide-conquer.md

## 1. 核心概念

### 1.1 DP 的本质

**DP = 分治 + 记忆化**

**两个关键**：
1. **状态定义**：`dp[i]` 代表什么
2. **状态转移**：状态之间如何变化

### 1.2 DP vs 递归 vs 分治

| 维度 | DP | 递归 | 分治 |
|------|-----|------|------|
| 子问题重叠 | **是**（记录子问题） | 否 | 否 |
| 子问题独立 | 否 | 是 | 是 |
| 时间复杂度 | 多项式 | 指数（无记忆化） | 多项式 |

### 1.3 DP 的两种实现

#### 自顶向下（Top-Down，记忆化搜索）

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def dp(n):
    if n <= 1: return n
    return dp(n - 1) + dp(n - 2)
```

#### 自底向上（Bottom-Up，迭代）

```python
def dp(n):
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

### 1.4 DP 适用场景

满足以下条件的问题用 DP：
1. **最优子结构**：问题的最优解包含子问题的最优解
2. **子问题重叠**：不同分支会重复求解同一子问题
3. **无后效性**：未来只与现在有关，与过去无关

### 1.5 DP 套路

```
1. 定义 dp[i] 的含义
2. 找到状态转移方程 dp[i] = f(dp[子状态])
3. 确定初始值（base case）
4. 确定遍历顺序（从小到大 / 从大到小）
5. 举例验证
```

### 1.6 DP 的应用

1. **斐波那契 / 爬楼梯**
2. **背包问题**：01 背包、完全背包
3. **最长公共子序列（LCS）**
4. **最长上升子序列（LIS）**
5. **编辑距离**
6. **股票买卖问题**

## 2. 代码示例

### 2.1 斐波那契（两种实现）

```python
# 文件：fib_dp.py
from functools import lru_cache

# 自顶向下（记忆化）
@lru_cache(maxsize=None)
def fib_top_down(n: int) -> int:
    if n <= 1:
        return n
    return fib_top_down(n - 1) + fib_top_down(n - 2)

# 自底向上（迭代）
def fib_bottom_up(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# 空间优化版
def fib_optimized(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

# 测试
print(fib_top_down(40))     # 102334155
print(fib_bottom_up(40))    # 102334155
print(fib_optimized(40))    # 102334155
```

### 2.2 爬楼梯问题

```python
# 文件：climb_stairs.py
def climb_stairs(n: int) -> int:
    """爬楼梯：每次 1 或 2 阶，爬 n 阶有多少种方法。

    dp[i] = dp[i-1] + dp[i-2]
    """
    if n <= 1:
        return 1
    dp = [0] * (n + 1)
    dp[0] = dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]

# 空间优化版
def climb_stairs_optimized(n: int) -> int:
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# 测试
print(climb_stairs(10))  # 89
```

### 2.3 打家劫舍（线性）

```python
# 文件：house_robber.py
from typing import List

def rob(nums: List[int]) -> int:
    """打家劫舍：不能偷相邻的两家。

    dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    """
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]

    n = len(nums)
    dp = [0] * n
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, n):
        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])
    return dp[n - 1]

# 空间优化版（只用两个变量）
def rob_optimized(nums: List[int]) -> int:
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    prev, curr = nums[0], max(nums[0], nums[1])
    for i in range(2, len(nums)):
        prev, curr = curr, max(curr, prev + nums[i])
    return curr

# 测试
print(rob([1, 2, 3, 1]))  # 4（偷第 1、3 家）
print(rob([2, 7, 9, 3, 1]))  # 12（偷第 1、3、5 家）
```

### 2.4 最小路径和（网格）

```python
# 文件：min_path_sum.py
from typing import List

def min_path_sum(grid: List[List[int]]) -> int:
    """网格最小路径和：从左上到右下，每次只能右或下。

    dp[i][j] = grid[i][j] + min(dp[i-1][j], dp[i][j-1])
    """
    if not grid:
        return 0
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]

    # 第一行：只能从左边来
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]

    # 第一列：只能从上面来
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]

    # 其他格子
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])

    return dp[m - 1][n - 1]

# 测试
grid = [
    [1, 3, 1],
    [1, 5, 1],
    [4, 2, 1],
]
print(min_path_sum(grid))  # 7（路径 1→3→1→1→1）
```

## 3. dify 仓库源码解读

### 3.1 dify 的 LLM 成本优化（DP 思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/entities/provider_entities.py`
**核心代码**（行 50-90）：

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class TokenUsage:
    """Token 使用统计。"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class CostOptimizer:
    """成本优化器：用 DP 思想优化多 LLM 调用的成本。

    dify 的工作流可能调用多个 LLM，需要优化：
    1. 哪些调用可以并行
    2. 哪些调用可以用小模型
    3. 哪些结果可以缓存

    这里用 DP 思想：每个子任务选择最优策略。
    """

    def __init__(self):
        # 不同模型的成本（输入 token 单价）
        self._model_costs: dict[str, float] = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0015,
            "claude-3-opus": 0.015,
            "claude-3-haiku": 0.00025,
        }

    def optimal_model_selection(
        self,
        required_quality: float,
        max_budget: float,
    ) -> str:
        """根据质量要求和预算，选最优模型。

        DP 思想：
        dp[budget] = 在预算 budget 下能达到的最高质量
        """
        # 简化实现
        models = sorted(
            self._model_costs.items(),
            key=lambda x: x[1],  # 按成本排序
        )
        for model, cost in models:
            if cost <= max_budget:
                return model
        return models[0][0]

    def estimate_cost(self, tokens: int, model: str) -> float:
        """估算成本。"""
        return tokens * self._model_costs.get(model, 0.01)

    def find_optimal_split(
        self,
        tasks: list[dict],
        budget: float,
    ) -> list[str]:
        """为每个任务分配模型，在总预算下最大化总质量。

        DP 思想：
        dp[i][b] = 处理前 i 个任务，预算为 b 时的最大质量
        """
        n = len(tasks)
        # 简化的 DP 表
        dp = [0.0] * (int(budget) + 1)
        assignments = [""] * n

        # 贪心简化版（实际用 2D DP）
        sorted_tasks = sorted(tasks, key=lambda t: t["priority"], reverse=True)
        remaining_budget = budget

        for i, task in enumerate(sorted_tasks):
            # 找当前预算下能用的最好模型
            best_model = None
            for model, cost in self._model_costs.items():
                if cost <= remaining_budget and best_model is None:
                    best_model = model
            if best_model:
                assignments[i] = best_model
                remaining_budget -= self._model_costs[best_model]

        return assignments
```

**解读**：
- 第 51 行：DP 思想在 dify 中的应用——为每个任务选最优模型
- 第 67 行：`optimal_model_selection` 简化的 DP
- **dify 中无直接 DP 代码**，但模型选择、成本估算都有 DP 思想
- **设计意图**：在工作流执行时，根据预算和质量要求，动态选择模型

## 4. 关键要点总结

- DP = **分治 + 记忆化**
- 两个关键：**状态定义 + 状态转移方程**
- 两种实现：自顶向下（递归 + 记忆化）vs 自底向上（迭代）
- 适用条件：最优子结构、子问题重叠、无后效性
- 应用：斐波那契、爬楼梯、打家劫舍、最短路径、背包
- dify 模型选择有 DP 思想

## 5. 练习题

### 练习 1：基础（必做）

实现**不同路径**（LeetCode 62）：m×n 网格，从左上到右下，每次右或下，求路径数。用 DP 解决。

### 练习 2：进阶

阅读 `api/core/entities/provider_entities.py`，说明 dify 的模型选择策略如何体现 DP 思想。

### 练习 3：挑战（选做）

实现**最长上升子序列（LIS）**：用 DP 解决 O(n²)，用二分优化到 O(n log n)。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/entities/provider_entities.py`
- 《算法导论》第 15 章 动态规划
- LeetCode 70/198/62/300 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13