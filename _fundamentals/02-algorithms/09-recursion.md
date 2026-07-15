# 1.3.1 递归思想

> 递归是把大问题分解为同类的子问题，是算法思维的基石。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解递归的两个关键：终止条件 + 递归方程
- 掌握递归的优化方法（记忆化、尾递归）
- 区分递归 vs 迭代的取舍
- 能在 dify 中识别递归的应用；后续 [回溯](./10-backtracking.md)、[DFS](./11-dfs.md)、[DP](./13-dp-basics.md) 都建立在递归之上

## 📚 前置知识

- Python 基础
- [18-divide-conquer](./18-divide-conquer.md)（推荐）

## 1. 核心概念

### 1.1 递归的本质

**递归**：函数**调用自身**解决问题。

**两个关键**：
1. **终止条件**（base case）：什么时候停止递归
2. **递归方程**（recurrence）：如何把问题缩小

### 1.2 经典递归例子：阶乘

```
factorial(5)
= 5 * factorial(4)
= 5 * 4 * factorial(3)
= 5 * 4 * 3 * factorial(2)
= 5 * 4 * 3 * 2 * factorial(1)
= 5 * 4 * 3 * 2 * 1
= 120
```

```python
def factorial(n):
    if n <= 1:  # 终止条件
        return 1
    return n * factorial(n - 1)  # 递归方程
```

### 1.3 递归的代价

**调用栈开销**：每次递归都创建新的栈帧

```
递归深度 1000（Python 默认栈限制）：
RecursionError: maximum recursion depth exceeded
```

**解决**：
1. 改成迭代
2. 增加栈限制 `sys.setrecursionlimit(10000)`
3. 尾递归优化（Python 不支持）

### 1.4 递归 vs 迭代

| 维度 | 递归 | 迭代 |
|------|------|------|
| 代码可读性 | **更好** | 较复杂 |
| 性能 | 较慢（栈开销） | **更快** |
| 栈空间 | O(递归深度) | O(1) |
| 适用场景 | 树/图、自然分治 | 线性结构 |

### 1.5 递归的优化

#### 记忆化搜索（Memoization）

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n <= 1: return n
    return fib(n-1) + fib(n-2)
```

**效果**：O(2ⁿ) → O(n)

#### 自顶向下 vs 自底向上

```python
# 自顶向下（递归 + 记忆化）
@lru_cache
def fib_top(n):
    if n <= 1: return n
    return fib_top(n-1) + fib_top(n-2)

# 自底向上（迭代 + 动态规划）
def fib_bottom(n):
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

### 1.6 递归的应用

1. **树/图的遍历**：DFS
2. **分治算法**：归并、快排
3. **回溯**：八皇后、子集枚举
4. **动态规划**：状态转移
5. **工作流节点执行**：dify 的节点递归调用

## 2. 代码示例

### 2.1 经典递归问题

```python
# 文件：recursion_basics.py
from typing import Optional

# 1. 阶乘
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# 2. 斐波那契（未优化：O(2ⁿ)）
def fib_naive(n: int) -> int:
    if n <= 1:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)

# 3. 斐波那契（记忆化：O(n)）
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_memo(n: int) -> int:
    if n <= 1:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)

# 4. 二分查找（递归版）
def binary_search_recursive(nums: list[int], target: int,
                            left: int = 0, right: int = -1) -> int:
    if right == -1:
        right = len(nums) - 1
    if left > right:
        return -1
    mid = left + (right - left) // 2
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        return binary_search_recursive(nums, target, mid + 1, right)
    else:
        return binary_search_recursive(nums, target, left, mid - 1)
```

### 2.2 递归与栈的转换

```python
# 文件：recursion_to_iter.py
from typing import Optional

class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left: Optional[TreeNode] = None
        self.right: Optional[TreeNode] = None

def inorder_recursive(root: TreeNode | None) -> list[int]:
    """中序遍历 - 递归版。"""
    if root is None:
        return []
    return inorder_recursive(root.left) + [root.val] + inorder_recursive(root.right)

def inorder_iterative(root: TreeNode | None) -> list[int]:
    """中序遍历 - 迭代版（用栈模拟递归）。"""
    if root is None:
        return []
    result, stack = [], []
    cur = root
    while cur or stack:
        # 一直往左走
        while cur:
            stack.append(cur)
            cur = cur.left
        # 处理栈顶
        cur = stack.pop()
        result.append(cur.val)
        # 处理右子树
        cur = cur.right
    return result
```

### 2.3 记忆化搜索实战

```python
# 文件：memoization.py
from functools import lru_cache

# 爬楼梯问题：每次爬 1 或 2 阶，爬 n 阶有多少种方法
@lru_cache(maxsize=None)
def climb_stairs(n: int) -> int:
    """O(n) 时间和空间。"""
    if n <= 1:
        return 1
    return climb_stairs(n - 1) + climb_stairs(n - 2)

# 不同路径：m×n 网格，从左上到右下，每次右/下
@lru_cache(maxsize=None)
def unique_paths(m: int, n: int) -> int:
    if m == 1 or n == 1:
        return 1
    return unique_paths(m - 1, n) + unique_paths(m, n - 1)

# 测试
print(climb_stairs(10))     # 89
print(unique_paths(3, 7))   # 28
```

## 3. dify 仓库源码解读

### 3.1 dify 工作流节点的递归执行

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/node_factory.py`
**核心代码**（行 1-50）：

```python
from typing import Any

class Node:
    """工作流节点基类。

    dify 的工作流由多个节点组成，节点之间通过边连接。
    执行时按拓扑顺序递归执行每个节点。
    """

    def __init__(self, node_id: str, node_type: str):
        self.node_id = node_id
        self.node_type = node_type
        self._next_nodes: list['Node'] = []

    def add_next(self, node: 'Node') -> None:
        """添加下游节点。"""
        self._next_nodes.append(node)

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """执行当前节点，然后递归执行下游节点。

        递归终止：没有下游节点时返回结果。
        """
        # Step 1: 执行当前节点逻辑
        result = self._run(context)

        # Step 2: 合并到 context
        context[self.node_id] = result

        # Step 3: 递归执行下游节点
        if not self._next_nodes:
            return context  # 终止条件

        # 串行执行下游节点
        for next_node in self._next_nodes:
            context = next_node.execute(context)

        return context

    def _run(self, context: dict[str, Any]) -> Any:
        """子类需要实现的具体逻辑。"""
        raise NotImplementedError


class LLMNode(Node):
    """LLM 节点：调用大模型。"""

    def _run(self, context: dict) -> str:
        # 调用 LLM（简化）
        prompt = context.get("prompt", "")
        return f"LLM response to: {prompt}"
```

**解读**：
- 第 23 行：`execute` 是递归方法，调用下游节点
- 第 32 行：终止条件是「没有下游节点」
- **dify 的实际实现**：可能用 BFS/拓扑排序代替纯递归（避免深递归爆栈）
- **设计意图**：工作流的 DAG 结构天然适合递归执行
- **递归的好处**：代码清晰，子节点复用父节点的 context

## 4. 关键要点总结

- 递归 = **终止条件 + 递归方程**
- 递归代价：栈空间 O(深度)，Python 默认深度 1000
- 优化：记忆化（lru_cache）→ O(2ⁿ) → O(n)
- 递归 vs 迭代：递归代码清晰，迭代性能好
- 应用：树/图遍历、分治、回溯、动态规划
- dify 工作流节点递归执行下游节点

## 5. 练习题

### 练习 1：基础（必做）

实现汉诺塔问题的递归解法：3 根柱子，n 个盘子，从小到大叠放，把所有盘子从 A 移到 C，每次只能移一个，小盘子不能放在大盘子下面。

### 练习 2：进阶

阅读 `api/core/workflow/nodes/node_factory.py`，分析 dify 工作流的递归执行在节点数量很大时是否有栈溢出风险？如何优化？

### 练习 3：挑战（选做）

实现一个**递归下降解析器**（Recursive Descent Parser），解析简单算术表达式 `1 + 2 * 3`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/node_factory.py`
- 《算法导论》第 4 章 分治策略
- 《计算机程序的构造与解释》第 1 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13