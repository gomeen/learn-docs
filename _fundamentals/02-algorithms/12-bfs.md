# 1.3.4 广度优先搜索（BFS）

> BFS 是"层层推进"的图遍历算法，适合求最短路径。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 BFS 的队列实现和层级遍历
- 理解 BFS 在最短路径、连通分量中的应用
- 区分 BFS vs DFS 的应用场景
- 能在 dify 中识别 BFS 的应用

## 📚 前置知识

- 17-graph.md
- 11-dfs.md

## 1. 核心概念

### 1.1 BFS 的思想

**广度优先**：从一个节点出发，**逐层**向外扩展，先访问近的节点。

```
图：
    A --- B
    |     |
    C --- D --- E

从 A 出发 BFS：
第 0 层：A
第 1 层：B, C
第 2 层：D（通过 B 或 C）
第 3 层：E
```

### 1.2 BFS 的实现

用**队列**实现：

```python
def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        v = queue.popleft()
        for u in graph[v]:
            if u not in visited:
                visited.add(u)
                queue.append(u)
```

### 1.3 BFS 的关键特性

**层级概念**：每个节点都有"层号"（距离起点的最短距离）。

```
A (层 0)
B (层 1), C (层 1)
D (层 2)
E (层 3)
```

**最短路径**（无权图）：第一次到达节点就是最短路径。

### 1.4 BFS vs DFS 完整对比

| 维度 | BFS | DFS |
|------|-----|-----|
| 数据结构 | 队列 | 栈 |
| 顺序 | 逐层 | 一路到底 |
| 最短路径 | **保证**（无权图） | 不保证 |
| 空间 | O(宽度) | O(深度) |
| 找最近 | **快** | 慢 |
| 找是否存在 | 一样 | 一样 |

### 1.5 BFS 的应用

1. **最短路径**：迷宫、棋盘
2. **层级遍历**：二叉树层序、社交网络度数
3. **连通分量**：Flood Fill
4. **拓扑排序**：BFS + 入度表（Kahn 算法）
5. **双向 BFS**：单词接龙、最少编辑次数

## 2. 代码示例

### 2.1 图的 BFS

```python
# 文件：graph_bfs.py
from collections import defaultdict, deque
from typing import Any

class GraphBFS:
    """图的 BFS 遍历。"""

    def __init__(self):
        self._adj: dict[Any, list[Any]] = defaultdict(list)

    def add_edge(self, u: Any, v: Any) -> None:
        self._adj[u].append(v)
        self._adj[v].append(u)

    def bfs(self, start: Any) -> list[Any]:
        """BFS 遍历。"""
        visited = {start}
        result = []
        queue = deque([start])
        while queue:
            v = queue.popleft()
            result.append(v)
            for u in self._adj[v]:
                if u not in visited:
                    visited.add(u)
                    queue.append(u)
        return result

    def shortest_path(self, start: Any, end: Any) -> list[Any] | None:
        """BFS 求最短路径（无权图）。"""
        if start == end:
            return [start]
        visited = {start}
        parent = {start: None}
        queue = deque([start])
        while queue:
            v = queue.popleft()
            for u in self._adj[v]:
                if u not in visited:
                    visited.add(u)
                    parent[u] = v
                    if u == end:
                        # 回溯路径
                        path = []
                        cur = u
                        while cur is not None:
                            path.append(cur)
                            cur = parent[cur]
                        return path[::-1]
                    queue.append(u)
        return None

    def bfs_by_level(self, start: Any) -> list[list[Any]]:
        """按层返回 BFS 结果。"""
        visited = {start}
        result = []
        queue = deque([start])
        while queue:
            level = []
            for _ in range(len(queue)):  # 处理当前层所有节点
                v = queue.popleft()
                level.append(v)
                for u in self._adj[v]:
                    if u not in visited:
                        visited.add(u)
                        queue.append(u)
            result.append(level)
        return result
```

### 2.2 二叉树层序遍历

```python
# 文件：level_order.py
from collections import deque
from typing import Optional

class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left: Optional[TreeNode] = None
        self.right: Optional[TreeNode] = None

def level_order(root: TreeNode | None) -> list[list[int]]:
    """二叉树层序遍历。"""
    if root is None:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result

# 测试
#       3
#      / \
#     9   20
#        /  \
#       15    7
root = TreeNode(3)
root.left = TreeNode(9)
root.right = TreeNode(20)
root.right.left = TreeNode(15)
root.right.right = TreeNode(7)
print(level_order(root))  # [[3], [9, 20], [15, 7]]
```

### 2.3 最短路径：迷宫问题

```python
# 文件：maze_bfs.py
from collections import deque
from typing import List

def shortest_maze_path(maze: List[List[int]]) -> int:
    """最短迷宫路径：从 (0,0) 到 (m-1, n-1)，0 是通路，1 是墙。"""
    if not maze or maze[0][0] == 1:
        return -1
    rows, cols = len(maze), len(maze[0])
    queue = deque([(0, 0, 1)])  # (row, col, distance)
    visited = {(0, 0)}
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    while queue:
        r, c, dist = queue.popleft()
        if r == rows - 1 and c == cols - 1:
            return dist
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows and 0 <= nc < cols
                    and maze[nr][nc] == 0
                    and (nr, nc) not in visited):
                visited.add((nr, nc))
                queue.append((nr, nc, dist + 1))
    return -1  # 不可达

# 测试
maze = [
    [0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0],
    [1, 1, 0, 1, 0],
    [0, 0, 0, 0, 0],
]
print(shortest_maze_path(maze))  # 9
```

### 2.4 拓扑排序（BFS + 入度表，Kahn 算法）

```python
# 文件：topological_sort_bfs.py
from collections import defaultdict, deque
from typing import Any

def topological_sort_kahn(n: int, edges: list[tuple[Any, Any]]) -> list[Any] | None:
    """BFS 实现拓扑排序（Kahn 算法）。

    入度为 0 的节点先入队，处理后减少邻居的入度。
    """
    adj: dict[Any, list[Any]] = defaultdict(list)
    indegree = [0] * n
    for u, v in edges:
        adj[u].append(v)
        indegree[v] += 1

    queue = deque([i for i in range(n) if indegree[i] == 0])
    result = []

    while queue:
        v = queue.popleft()
        result.append(v)
        for u in adj[v]:
            indegree[u] -= 1
            if indegree[u] == 0:
                queue.append(u)

    if len(result) != n:
        return None  # 有环
    return result

# 测试
print(topological_sort_kahn(4, [(0, 1), (0, 2), (1, 3), (2, 3)]))
# [0, 1, 2, 3]
```

## 3. dify 仓库源码解读

### 3.1 dify 文档的层级遍历

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/summary_index/summary_index.py`
**核心代码**（行 40-80）：

```python
from collections import deque
from typing import Any

class SummaryIndex:
    """摘要索引：树形文档结构。

    dify 的摘要索引把文档组织成树形：
    - 根节点：全文摘要
    - 中间节点：段落摘要
    - 叶子节点：原文

    BFS 用于按层级遍历，保留文档的层级关系。
    """

    def traverse_bfs(self, root: 'SummaryNode') -> list[list['SummaryNode']]:
        """BFS 按层遍历，返回每层的节点列表。

        类似工作流的"分层执行"：先处理上层（粗粒度），
        再处理下层（细粒度）。
        """
        if root is None:
            return []
        result = []
        current_layer = [root]
        while current_layer:
            result.append(current_layer)
            next_layer = []
            for node in current_layer:
                next_layer.extend(node.children)
            current_layer = next_layer
        return result

    def find_k_hop_neighbors(
        self,
        start: str,
        k: int,
    ) -> list[str]:
        """BFS 找 K 跳邻居（社交网络分析）。"""
        visited = {start}
        current_layer = {start}
        for _ in range(k):
            next_layer = set()
            for node in current_layer:
                for neighbor in self._adj.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_layer.add(neighbor)
            current_layer = next_layer
        return list(current_layer)
```

**解读**：
- 第 25 行：`current_layer` 维护当前层所有节点
- 第 28 行：`next_layer` 收集下一层
- 第 30 行：用 list/set 替代 deque，简化代码（不需要严格 FIFO）
- **设计意图**：dify 的摘要索引按层遍历，先看粗粒度（摘要），再看细粒度（原文）

## 4. 关键要点总结

- BFS：**逐层推进**，用队列实现
- 时间 O(V + E)，空间 O(V)
- **保证无权图最短路径**
- 应用：最短路径、层级遍历、连通分量、拓扑排序
- BFS + 入度表 = Kahn 拓扑排序
- dify 用 BFS 遍历文档摘要层级

## 5. 练习题

### 练习 1：基础（必做）

用 BFS 实现二叉树的**右视图**：返回从右侧看每层最右边的节点。

### 练习 2：进阶

阅读 `api/core/rag/summary_index/summary_index.py`，分析 dify 为什么用 BFS 而非 DFS 遍历文档摘要层级（提示：考虑分层处理的需求）。

### 练习 3：挑战（选做）

实现**双向 BFS**：从起点和终点同时 BFS，在中间相遇，时间 O(b^(d/2))（b 是分支因子，d 是深度）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/summary_index/summary_index.py`
- 《算法导论》第 22 章 基本的图算法
- LeetCode 102/107/199/1091 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13