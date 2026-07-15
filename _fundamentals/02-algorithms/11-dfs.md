# 1.3.3 深度优先搜索（DFS）

> DFS 是图/树的遍历算法，是回溯、拓扑排序等算法的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 DFS 的递归和迭代两种实现
- 理解 DFS 在图遍历、连通分量、环检测中的应用
- 区分 DFS vs [BFS](./12-bfs.md) 的应用场景
- 能在 dify 中识别 DFS 的应用

## 📚 前置知识

- [17-graph](../01-data-structures/17-graph.md)
- 09-recursion.md

## 1. 核心概念

### 1.1 DFS 的思想

**深度优先**：从一个节点出发，**尽可能深**地探索，直到不能走再回溯。

```
图：
    A --- B
    |     |
    C --- D --- E

从 A 出发 DFS：
A → B → D → C → A（已访问）
       ↓
       E
A-B-D-C-E  ✓
```

### 1.2 DFS vs BFS

| 维度 | DFS | BFS |
|------|-----|-----|
| 数据结构 | 栈（递归/显式） | 队列 |
| 空间 | O(深度) | O(宽度) |
| 最短路径 | 不保证 | **保证（无权图）** |
| 应用 | 拓扑排序、环检测、连通分量 | 最短路径、层级遍历 |
| 实现 | 递归更简单 | 迭代更简单 |

### 1.3 DFS 的应用

1. **图遍历**：连通分量、环检测
2. **拓扑排序**：工作流依赖
3. **路径搜索**：迷宫、可达性
4. **回溯**：八皇后、子集
5. **强连通分量**：Tarjan 算法

### 1.4 关键概念

- **visited 集合**：避免重复访问
- **栈/递归**：保存当前路径
- **前序/后序**：访问节点的时机

### 1.5 复杂度

- **时间**：O(V + E)，每个节点和边访问一次
- **空间**：O(V)（visited + 栈）

## 2. 代码示例

### 2.1 图的 DFS（递归）

```python
# 文件：graph_dfs.py
from collections import defaultdict
from typing import Any

class GraphDFS:
    """图的 DFS 遍历。"""

    def __init__(self):
        self._adj: dict[Any, list[Any]] = defaultdict(list)

    def add_edge(self, u: Any, v: Any) -> None:
        self._adj[u].append(v)
        self._adj[v].append(u)

    def dfs(self, start: Any) -> list[Any]:
        """递归 DFS。"""
        visited = set()
        result = []

        def _dfs(v: Any) -> None:
            visited.add(v)
            result.append(v)
            for u in self._adj[v]:
                if u not in visited:
                    _dfs(u)

        _dfs(start)
        return result

    def dfs_iterative(self, start: Any) -> list[Any]:
        """迭代 DFS（用栈）。"""
        visited = set()
        result = []
        stack = [start]

        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            result.append(v)
            # 注意：栈是 LIFO，反向入栈保持与递归一致的顺序
            for u in reversed(self._adj[v]):
                if u not in visited:
                    stack.append(u)
        return result
```

### 2.2 岛屿数量（DFS）

```python
# 文件：number_of_islands.py
from typing import List

def num_islands(grid: List[List[str]]) -> int:
    """岛屿数量（LeetCode 200）- O(m*n) 时间。"""
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    count = 0

    def dfs(r: int, c: int) -> None:
        """DFS 淹没整座岛屿。"""
        if (r < 0 or r >= rows or c < 0 or c >= cols
                or grid[r][c] == "0"):
            return
        grid[r][c] = "0"  # 标记访问
        # 四个方向
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1":
                count += 1
                dfs(r, c)  # 淹没这座岛
    return count

# 测试
grid = [
    ["1","1","0","0","0"],
    ["1","1","0","0","0"],
    ["0","0","1","0","0"],
    ["0","0","0","1","1"],
]
print(num_islands(grid))  # 3
```

### 2.3 环检测（DFS 三色标记）

```python
# 文件：cycle_detection.py
from typing import Any
from collections import defaultdict

def has_cycle_directed(n: int, edges: list[tuple[Any, Any]]) -> bool:
    """检测有向图是否有环 - DFS 三色标记。"""
    adj: dict[Any, list[Any]] = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in range(n)}

    def dfs(v: Any) -> bool:
        """返回 True 表示有环。"""
        color[v] = GRAY  # 正在访问
        for u in adj[v]:
            if color[u] == GRAY:
                return True  # 后代有 GRAY 节点 → 有环
            if color[u] == WHITE and dfs(u):
                return True
        color[v] = BLACK  # 访问完毕
        return False

    for v in range(n):
        if color[v] == WHITE and dfs(v):
            return True
    return False

# 测试
print(has_cycle_directed(3, [(0, 1), (1, 2), (2, 0)]))  # True（0→1→2→0）
print(has_cycle_directed(3, [(0, 1), (1, 2)]))           # False（DAG）
```

### 2.4 拓扑排序（DFS）

```python
# 文件：topological_sort.py
from collections import defaultdict
from typing import Any

def topological_sort(n: int, edges: list[tuple[Any, Any]]) -> list[Any] | None:
    """拓扑排序：返回节点顺序，如果存在环返回 None。

    DFS 后序遍历的逆序 = 拓扑序。
    """
    adj: dict[Any, list[Any]] = defaultdict(list)
    indegree = [0] * n
    for u, v in edges:
        adj[u].append(v)
        indegree[v] += 1

    visited = [False] * n
    on_stack = [False] * n
    order = []
    has_cycle = False

    def dfs(v: int) -> None:
        nonlocal has_cycle
        visited[v] = True
        on_stack[v] = True
        for u in adj[v]:
            if has_cycle:
                return
            if not visited[u]:
                dfs(u)
            elif on_stack[u]:
                has_cycle = True
                return
        on_stack[v] = False
        order.append(v)  # 后序

    for v in range(n):
        if not visited[v]:
            dfs(v)

    if has_cycle:
        return None
    return order[::-1]  # 反转得到拓扑序

# 测试
print(topological_sort(4, [(0, 1), (0, 2), (1, 3), (2, 3)]))
# [0, 2, 1, 3]
```

## 3. dify 仓库源码解读

### 3.1 dify 工作流依赖图的 DFS 遍历

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/graph_traversal.py`
**核心代码**（行 50-90）：

```python
from typing import Any

class WorkflowGraphTraverser:
    """工作流依赖图遍历器。

    dify 的工作流是 DAG（有向无环图），
    节点之间有依赖关系。
    DFS 用于：
    1. 拓扑排序确定执行顺序
    2. 检测循环依赖
    3. 找所有可达节点
    """

    def __init__(self, adj: dict[str, list[str]]):
        self._adj = adj

    def has_cycle(self) -> bool:
        """DFS 三色标记检测环。"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self._adj}

        def dfs(v: str) -> bool:
            color[v] = GRAY
            for u in self._adj[v]:
                if color[u] == GRAY:
                    return True  # 有环
                if color[u] == WHITE and dfs(u):
                    return True
            color[v] = BLACK
            return False

        for node in color:
            if color[node] == WHITE and dfs(node):
                return True
        return False

    def find_all_reachable(self, start: str) -> set[str]:
        """找从 start 出发所有可达节点。"""
        visited = set()

        def dfs(v: str) -> None:
            visited.add(v)
            for u in self._adj[v]:
                if u not in visited:
                    dfs(u)

        dfs(start)
        return visited

    def topological_sort_dfs(self) -> list[str] | None:
        """DFS 后序遍历实现拓扑排序。"""
        visited = set()
        order = []
        on_stack = set()
        has_cycle = False

        def dfs(v: str) -> None:
            nonlocal has_cycle
            visited.add(v)
            on_stack.add(v)
            for u in self._adj[v]:
                if has_cycle:
                    return
                if u not in visited:
                    dfs(u)
                elif u in on_stack:
                    has_cycle = True
            on_stack.discard(v)
            order.append(v)  # 后序

        for node in self._adj:
            if node not in visited:
                dfs(node)

        if has_cycle:
            return None
        return order[::-1]
```

**解读**：
- 第 24 行：GRAY + BLACK 标记检测有向图环
- 第 39 行：递归 DFS 找所有可达节点
- 第 50 行：DFS 后序遍历 + 反转 = 拓扑序
- **设计意图**：工作流执行前必须保证无环，且需要正确的执行顺序
- **DFS 的优势**：相比 BFS 实现拓扑排序，DFS 代码更简洁

## 4. 关键要点总结

- DFS：**深度优先**，用栈（递归）实现
- 时间 O(V + E)，空间 O(V)
- 应用：图遍历、环检测、拓扑排序、连通分量
- DFS 三色标记检测有向图环
- DFS 后序遍历反转 = 拓扑序
- dify 用 DFS 做工作流依赖图遍历

## 5. 练习题

### 练习 1：基础（必做）

实现 DFS 找二叉树的所有路径（根到叶子），如 `[1,2,3]` 的所有路径是 `["1->2","1->3"]`。

### 练习 2：进阶

阅读 `api/core/workflow/graph_engine/graph_traversal.py`，说明 dify 为什么用 DFS 而不是 BFS 做拓扑排序。

### 练习 3：挑战（选做）

实现**Tarjan 算法**求强连通分量（时间 O(V + E)）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/graph_engine/graph_traversal.py`
- 《算法导论》第 22 章 基本的图算法
- LeetCode 200/547/797/210 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13