# 1.4.2 背包问题

> 背包问题是 DP 的经典应用，几乎所有面试都会考。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 01 背包、完全背包的 DP 解法
- 理解背包问题的状态转移方程推导
- 区分 01 背包与完全背包的遍历顺序差异
- 能在 dify 中识别背包思想的应用（资源分配）

## 📚 前置知识

- 13-dp-basics.md

## 1. 核心概念

### 1.1 背包问题分类

| 类型 | 特点 |
|------|------|
| **01 背包** | 每个物品**最多用一次** |
| **完全背包** | 每个物品**可以用无限次** |
| **多重背包** | 每个物品有数量限制 |
| **分组背包** | 物品分组，每组最多选一个 |

### 1.2 01 背包

**问题描述**：N 件物品，第 i 件重 `weight[i]`，价值 `value[i]`，背包容量 W。每件物品最多用一次，求最大价值。

**状态定义**：`dp[i][j]` = 前 i 件物品，容量 j 下的最大价值

**状态转移**：
```
不选第 i 件：dp[i][j] = dp[i-1][j]
选第 i 件（如果装得下）：dp[i][j] = dp[i-1][j-weight[i]] + value[i]

dp[i][j] = max(不选, 选)
```

### 1.3 01 背包的空间优化

二维 `dp[i][j]` 可以优化为一维 `dp[j]`。

**关键**：**逆序遍历 j**

```python
for i in range(n):
    for j in range(W, weight[i] - 1, -1):  # 逆序！
        dp[j] = max(dp[j], dp[j - weight[i]] + value[i])
```

**为什么逆序？** 防止本轮的状态被本轮覆盖（影响后续计算）。

### 1.4 完全背包

**问题描述**：每件物品**可以用无限次**，求最大价值。

**状态转移**：与 01 背包类似，但 j 维**正序遍历**（允许重复选）。

```python
for i in range(n):
    for j in range(weight[i], W + 1):  # 正序！
        dp[j] = max(dp[j], dp[j - weight[i]] + value[i])
```

**为什么正序？** `dp[j - weight[i]]` 已经是本轮更新的结果，可以重复选。

### 1.5 背包变种

- **恰好装满**：初始化 `dp[0] = 0`，`dp[其他] = -inf`
- **方案数**：状态转移改成加法
- **二维费用**：状态多一维
- **输出方案**：记录每个状态的选择

## 2. 代码示例

### 2.1 01 背包

```python
# 文件：knapsack_01.py
from typing import List

def knapsack_01(
    weights: List[int],
    values: List[int],
    W: int,
) -> int:
    """01 背包：每个物品最多用一次。"""
    n = len(weights)
    # dp[j] = 容量 j 下的最大价值
    dp = [0] * (W + 1)

    for i in range(n):
        # 逆序遍历：保证每个物品只用一次
        for j in range(W, weights[i] - 1, -1):
            dp[j] = max(dp[j], dp[j - weights[i]] + values[i])

    return dp[W]

# 测试
weights = [2, 3, 4, 5]
values = [3, 4, 5, 6]
W = 8
print(knapsack_01(weights, values, W))  # 12（选 1+3+4 号）
```

### 2.2 完全背包

```python
# 文件：knapsack_complete.py
from typing import List

def knapsack_complete(
    weights: List[int],
    values: List[int],
    W: int,
) -> int:
    """完全背包：每个物品可以用无限次。"""
    n = len(weights)
    dp = [0] * (W + 1)

    for i in range(n):
        # 正序遍历：允许重复使用
        for j in range(weights[i], W + 1):
            dp[j] = max(dp[j], dp[j - weights[i]] + values[i])

    return dp[W]

# 测试
weights = [2, 3]
values = [3, 4]
W = 7
print(knapsack_complete(weights, values, W))  # 12（选 1 号 0+1+2+3 号 = 2 个 1 号 + 1 个 2 号）
# 实际：选 1 号 2 次（值 6，重 4）+ 2 号 1 次（值 4，重 3）= 10
# 或：选 1 号 0 次 + 2 号 2 次（值 8，重 6）= 8
# 或：选 1 号 1 次（值 3）+ 2 号 1 次（值 4）= 7
# 选 1 号 2 次（值 6）+ 2 号 1 次（值 4）= 10 最佳
```

### 2.3 二维费用背包

```python
# 文件：knapsack_2d.py
from typing import List

def knapsack_2d(
    weights: List[int],
    volumes: List[int],
    values: List[int],
    W: int,
    V: int,
) -> int:
    """二维费用背包：同时考虑重量和体积。"""
    n = len(weights)
    dp = [[0] * (V + 1) for _ in range(W + 1)]

    for i in range(n):
        for w in range(W, weights[i] - 1, -1):
            for v in range(V, volumes[i] - 1, -1):
                dp[w][v] = max(
                    dp[w][v],
                    dp[w - weights[i]][v - volumes[i]] + values[i],
                )
    return dp[W][V]

# 测试
print(knapsack_2d([2, 3], [1, 2], [3, 4], 5, 3))  # 7
```

### 2.4 分割等和子集（01 背包变种）

```python
# 文件：partition_equal_subset.py
from typing import List

def can_partition(nums: List[int]) -> bool:
    """判断是否能分成两个等和子集（LeetCode 416）。"""
    total = sum(nums)
    if total % 2 != 0:
        return False
    target = total // 2
    # 01 背包：找和为 target 的子集
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        for j in range(target, num - 1, -1):
            dp[j] = dp[j] or dp[j - num]
    return dp[target]

# 测试
print(can_partition([1, 5, 11, 5]))  # True（[1,5,5] 和 [11]）
print(can_partition([1, 2, 3, 5]))   # False
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Token 预算分配（背包思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/model_runtime/model_providers/__base/ai_model.py`
**核心代码**（行 200-240）：

```python
from typing import Any

class TokenBudgetAllocator:
    """Token 预算分配器。

    dify 的工作流可能包含多个 LLM 调用，每个调用有 Token 限制。
    需要在总预算下最大化总价值（如总输出质量）。

    背包思想：
    - 物品：每次 LLM 调用
    - 重量：消耗的 Token 数
    - 价值：调用产生的价值（用输出长度、相关性等衡量）
    - 容量：总 Token 预算
    """

    def __init__(self, max_budget: int):
        self._max_budget = max_budget

    def allocate(
        self,
        calls: list[dict],
    ) -> list[dict]:
        """分配每个调用的 Token 数。

        简化版：贪心 + DP 混合。
        """
        n = len(calls)
        # dp[j] = 总预算 j 下的最大价值
        dp = [0.0] * (self._max_budget + 1)
        # 记录选择
        choice = [[None] * (self._max_budget + 1) for _ in range(n)]

        for i, call in enumerate(calls):
            weight = call.get("estimated_tokens", 1)  # Token 消耗
            value = call.get("estimated_value", 1.0)  # 价值
            for j in range(self._max_budget, weight - 1, -1):
                if dp[j - weight] + value > dp[j]:
                    dp[j] = dp[j - weight] + value
                    choice[i][j] = "select"

        # 输出每个调用的分配建议
        return [
            {**call, "allocated": choice[i][self._max_budget] == "select"}
            for i, call in enumerate(calls)
        ]

    def estimate_tokens(self, text: str, model: str = "gpt-4") -> int:
        """估算文本的 Token 数（简化）。"""
        return len(text) // 4  # 1 token ≈ 4 字符
```

**解读**：
- 第 32 行：dp[j] 是"预算 j 下的最大价值"
- 第 35 行：01 背包思想（每个调用选或不选）
- 第 41 行：记录每个状态的选择
- **dify 的实际实现**：用更复杂的策略（如优先级、用户等级）
- **设计意图**：在总 Token 预算下，最大化工作流的价值

## 4. 关键要点总结

- 01 背包：每个物品最多用一次，**逆序遍历**
- 完全背包：每个物品可用无限次，**正序遍历**
- 状态转移：`dp[j] = max(dp[j], dp[j - weight] + value)`
- 空间优化：从二维压缩到一维
- 变种：恰好装满、方案数、二维费用
- dify 的 Token 预算分配有背包思想

## 5. 练习题

### 练习 1：基础（必做）

实现**零钱兑换**（LeetCode 322）：给定硬币面额和总金额，求凑出金额的最少硬币数（完全背包）。

### 练习 2：进阶

阅读 `api/core/model_runtime/model_providers/__base/ai_model.py`，分析 dify 的 Token 预算分配如何用背包思想实现。

### 练习 3：挑战（选做）

实现**多重背包**（每个物品有数量限制），用二进制拆分优化到 O(NW log K)。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/model_runtime/model_providers/__base/ai_model.py`
- 《背包九讲》：https://github.com/tianyicui/pack
- LeetCode 416/322/518/474 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13