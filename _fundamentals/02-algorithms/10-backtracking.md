# 1.3.2 回溯算法：八皇后 / 子集

> 回溯是递归的"暴力搜索"形式，DFS 的应用典范。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解回溯算法的"选择 - 递归 - 撤销"模板
- 掌握八皇后、子集、排列等经典问题
- 区分回溯与动态规划的取舍
- 能在 dify 中识别回溯的应用

## 📚 前置知识

- 09-recursion.md
- 11-dfs.md

## 1. 核心概念

### 1.1 回溯的模板

```python
def backtrack(路径, 选择列表):
    if 满足结束条件:
        result.append(路径.copy())
        return
    for 选择 in 选择列表:
        # 做选择
        路径.append(选择)
        # 递归
        backtrack(路径, 新的选择列表)
        # 撤销选择（关键！）
        路径.pop()
```

**三要素**：
1. **路径**：已经做的选择
2. **选择列表**：当前可以做的选择
3. **结束条件**：到达决策树的叶子节点

### 1.2 回溯 vs DFS

- **DFS** 是遍历图/树的算法
- **回溯** 是 DFS 在决策树上的应用，带"撤销选择"

### 1.3 回溯 vs 动态规划

| 维度 | 回溯 | 动态规划 |
|------|------|----------|
| 思路 | 枚举所有可能 | 记录子问题解 |
| 时间 | O(2ⁿ) ~ O(n!) | O(n²) ~ O(n³) |
| 空间 | O(路径长度) | O(状态数) |
| 适用 | 决策问题 | 最优化问题 |

### 1.4 回溯的剪枝

回溯常配合**剪枝**优化：提前排除不可能的分支。

```python
def backtrack_with_pruning(状态):
    if 满足结束条件:
        result.append(状态.copy())
        return
    for 选择 in 候选:
        if 不满足约束:
            continue  # 剪枝
        做选择(状态, 选择)
        backtrack_with_pruning(状态)
        撤销选择(状态, 选择)
```

### 1.5 经典问题

1. **全排列**：N 个数的所有排列
2. **子集**：N 个数的所有子集
3. **组合**：从 N 个数选 K 个
4. **八皇后**：8 个皇后互不攻击
5. **数独**：填充 9×9 数独

## 2. 代码示例

### 2.1 子集问题

```python
# 文件：subsets.py
from typing import List

def subsets(nums: List[int]) -> List[List[int]]:
    """求所有子集（无重复元素）。

    [1,2,3] → [[],[1],[2],[3],[1,2],[1,3],[2,3],[1,2,3]]
    """
    result = []

    def backtrack(start: int, path: List[int]) -> None:
        # 每个 path 都是一个子集
        result.append(path.copy())
        # 从 start 开始选，避免重复
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()

    backtrack(0, [])
    return result

# 测试
print(subsets([1, 2, 3]))
```

### 2.2 全排列

```python
# 文件：permutations.py
from typing import List

def permute(nums: List[int]) -> List[List[int]]:
    """求所有全排列。"""
    result = []
    used = [False] * len(nums)

    def backtrack(path: List[int]) -> None:
        if len(path) == len(nums):
            result.append(path.copy())
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path)
            path.pop()
            used[i] = False

    backtrack([])
    return result

# 测试
print(permute([1, 2, 3]))
```

### 2.3 八皇后问题

```python
# 文件：n_queens.py
from typing import List

def solve_n_queens(n: int) -> List[List[str]]:
    """N 皇后问题：求所有解法。"""
    result = []
    # 记录每行皇后在哪个列
    queens: List[int] = [-1] * n

    def is_valid(row: int, col: int) -> bool:
        """检查 (row, col) 位置是否安全。"""
        for i in range(row):
            # 同列检查
            if queens[i] == col:
                return False
            # 对角线检查（|row_diff| == |col_diff|）
            if abs(queens[i] - col) == abs(i - row):
                return False
        return True

    def backtrack(row: int) -> None:
        if row == n:
            # 找到一个解
            solution = []
            for r in range(n):
                line = ["."] * n
                line[queens[r]] = "Q"
                solution.append("".join(line))
            result.append(solution)
            return

        for col in range(n):
            if is_valid(row, col):
                queens[row] = col
                backtrack(row + 1)
                queens[row] = -1

    backtrack(0)
    return result

# 测试
solutions = solve_n_queens(4)
print(f"4 皇后有 {len(solutions)} 个解")
for sol in solutions[:2]:
    print("\n".join(sol))
    print()
```

### 2.4 组合总和

```python
# 文件：combination_sum.py
from typing import List

def combination_sum(candidates: List[int], target: int) -> List[List[int]]:
    """组合总和：从 candidates 中选数字（可重复）凑出 target。

    [2,3,6,7], target=7 → [[2,2,3],[7]]
    """
    result = []
    candidates.sort()

    def backtrack(start: int, path: List[int], remaining: int) -> None:
        if remaining == 0:
            result.append(path.copy())
            return
        if remaining < 0:
            return  # 剪枝
        for i in range(start, len(candidates)):
            if candidates[i] > remaining:
                break  # 剪枝（已排序）
            path.append(candidates[i])
            # 注意：i 不变（可重复使用）
            backtrack(i, path, remaining - candidates[i])
            path.pop()

    backtrack(0, [], target)
    return result

# 测试
print(combination_sum([2, 3, 6, 7], 7))
```

## 3. dify 仓库源码解读

### 3.1 dify 的工作流条件分支（回溯思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/if_else/if_else_node.py`
**核心代码**（行 1-60）：

```python
from typing import Any

class IfElseNode:
    """条件分支节点：根据条件选择分支执行。

    dify 工作流的 IfElse 节点类似回溯的"选择 - 执行"，
    但只执行一条分支（不是回溯所有）。
    """

    def __init__(self, node_id: str, cases: list[dict]):
        self.node_id = node_id
        self.cases = cases  # [{"condition": "...", "next_node": ...}, ...]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """执行条件分支 - 类似回溯的选择 + 执行。"""
        for case in self.cases:
            condition = case["condition"]
            # Step 1: 评估条件（选择）
            if self._evaluate(condition, context):
                # Step 2: 执行对应分支
                next_node = case["next_node"]
                if next_node:
                    return next_node.execute(context)
                else:
                    return context

        # 默认分支（else）
        return context

    def _evaluate(self, condition: str, context: dict) -> bool:
        """评估条件表达式（简化示例）。"""
        # 实际 dify 用 Dify 表达式引擎
        try:
            # 用安全的 eval（限制内置函数）
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False


class WorkflowEngine:
    """工作流引擎：执行整个工作流。

    实际上 dify 用更复杂的执行器（事件驱动 + 队列），
    但思想类似回溯：选择分支 → 执行 → 收集结果。
    """

    def __init__(self, start_node):
        self._start = start_node

    def run(self, context: dict) -> dict:
        return self._start.execute(context)
```

**解读**：
- 第 19 行：`IfElseNode.execute` 类似回溯的"选择列表"
- 第 21 行：评估每个 case，类似回溯的"选择"
- 第 26 行：找到第一个满足条件的 case 就执行，类似回溯的"剪枝"
- **dify 的实际执行**：实际用事件队列（`AppQueueManager`），不是同步递归
- **设计意图**：IfElse 是回溯思想的简化版——只探索一条路径而不是所有路径

## 4. 关键要点总结

- 回溯三要素：**路径、选择列表、结束条件**
- 模板：`做选择 → 递归 → 撤销选择`
- 剪枝优化：提前排除不可能的分支
- 应用：子集、排列、八皇后、组合、图着色
- 时间复杂度通常是**指数级**（O(2ⁿ) ~ O(n!)）
- dify 的 IfElse 节点是回溯思想的简化版

## 5. 练习题

### 练习 1：基础（必做）

实现**括号生成**（LeetCode 22）：给定 n 对括号，生成所有合法的括号组合。

### 练习 2：进阶

阅读 `api/core/workflow/nodes/if_else/if_else_node.py`，分析 dify 的 IfElse 节点为什么只执行一条分支（不是回溯所有）。

### 练习 3：挑战（选做）

实现**数独求解器**：用回溯 + 剪枝填充 9×9 数独。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/if_else/if_else_node.py`
- 《算法导论》第 5 章 概率分析和随机算法
- LeetCode 46/78/51/22 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13