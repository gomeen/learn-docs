# 1.4.1 图基础：邻接表 / 邻接矩阵

> 图是描述实体间关系的数据结构，社交网络、地图、依赖分析都离不开图。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解图的定义（顶点、边、度）和分类（有向/无向、加权/无权）
- 区分邻接表和邻接矩阵的存储方式
- 实现 BFS 和 DFS 遍历
- 能在 dify 中识别图结构的应用（如工作流依赖、调用链）

## 📚 前置知识

- 06-binary-tree.md
- 12-bfs.md（推荐）

## 1. 核心概念

### 1.1 图的定义

**图**（Graph）由**顶点（Vertex）** 和 **边（Edge）** 组成：

```
顶点：A, B, C, D, E
边：{A-B, A-C, B-C, C-D, D-E}

图示：
    A --- B
    |   /
    C --- D --- E
```

### 1.2 图的分类

| 分类 | 描述 | 例子 |
|------|------|------|
| 有向图 | 边有方向 | 微博关注、网页链接 |
| 无向图 | 边无方向 | 好友关系、道路网络 |
| 加权图 | 边有权重 | 地图距离、网络带宽 |
| 无权图 | 边无权重 | 社交关系 |
| 简单图 | 无自环、无重边 | 大多数应用 |
| 多重图 | 允许多重边 | 交通运输 |

### 1.3 邻接矩阵（Adjacency Matrix）

用 `n × n` 的二维数组表示，矩阵 `[i][j] = 1` 表示 i 到 j 有边。

```
顶点：A, B, C, D

  A B C D
A[0 1 1 0]
B[1 0 1 0]
C[1 1 0 1]
D[0 0 1 0]
```

**特点**：
- 空间复杂度 **O(V²)**
- 查询两点是否有边 **O(1)**
- 适合**稠密图**（边多）
- 不适合大图（1 万顶点就要 100M 空间）

### 1.4 邻接表（Adjacency List）

每个顶点维护一个邻居列表：

```
A: [B, C]
B: [A, C]
C: [A, B, D]
D: [C]
```

**特点**：
- 空间复杂度 **O(V + E)**
- 查询两点是否有边 **O(度)**
- 适合**稀疏图**（边少）
- 大图首选（实际工业级）

### 1.5 邻接矩阵 vs 邻接表

| 维度 | 邻接矩阵 | 邻接表 |
|------|----------|--------|
| 空间 | O(V²) | O(V + E) |
| 查询边 | O(1) | O(度) |
| 遍历邻居 | O(V) | O(度) |
| 适合 | 稠密图 | **稀疏图** |
| 大图（V=1万） | 100 MB | 几十 KB |

### 1.6 图的常见算法

> 📌 **Sighting**：连通分量合并还可看 [并查集](./18-union-find.md)；DFS/BFS 算法详解见 [02-algorithms](../02-algorithms/)。

| 算法 | 用途 |
|------|------|
| BFS | 最短路径（无权图）、连通分量 |
| DFS | 拓扑排序、环检测、强连通分量 |
| Dijkstra | 最短路径（正权图） |
| Bellman-Ford | 最短路径（可负权） |
| Floyd-Warshall | 全对最短路径 |
| Prim/Kruskal | 最小生成树 |
| Tarjan | 强连通分量 |

## 2. 代码示例

### 2.1 邻接表实现

```python
# 文件：graph_adjlist.py
from collections import defaultdict, deque
from typing import Any

class Graph:
    """无向图（邻接表实现）。"""

    def __init__(self):
        self._adj: dict[Any, list[Any]] = defaultdict(list)

    def add_edge(self, u: Any, v: Any) -> None:
        """添加无向边。"""
        self._adj[u].append(v)
        self._adj[v].append(u)

    def neighbors(self, v: Any) -> list[Any]:
        return self._adj[v]

    def bfs(self, start: Any) -> list[Any]:
        """广度优先遍历。"""
        visited = {start}
        result = []
        q = deque([start])
        while q:
            v = q.popleft()
            result.append(v)
            for u in self._adj[v]:
                if u not in visited:
                    visited.add(u)
                    q.append(u)
        return result

    def dfs(self, start: Any) -> list[Any]:
        """深度优先遍历。"""
        visited = set()
        result = []
        self._dfs_recursive(start, visited, result)
        return result

    def _dfs_recursive(self, v: Any, visited: set, result: list) -> None:
        visited.add(v)
        result.append(v)
        for u in self._adj[v]:
            if u not in visited:
                self._dfs_recursive(u, visited, result)

    def shortest_path(self, start: Any, end: Any) -> list[Any] | None:
        """BFS 求最短路径（无权图）。"""
        if start == end:
            return [start]
        visited = {start}
        parent = {start: None}
        q = deque([start])
        while q:
            v = q.popleft()
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
                    q.append(u)
        return None
```

### 2.2 邻接矩阵实现

```python
# 文件：graph_adjmatrix.py
from typing import Any

class GraphMatrix:
    """无向图（邻接矩阵实现）。"""

    def __init__(self, vertices: list[Any]):
        self._vertices = list(vertices)
        self._index = {v: i for i, v in enumerate(vertices)}
        n = len(vertices)
        self._matrix = [[0] * n for _ in range(n)]

    def add_edge(self, u: Any, v: Any) -> None:
        i, j = self._index[u], self._index[v]
        self._matrix[i][j] = 1
        self._matrix[j][i] = 1

    def has_edge(self, u: Any, v: Any) -> bool:
        """O(1) 查询两点是否有边。"""
        i, j = self._index[u], self._index[v]
        return self._matrix[i][j] == 1

    def neighbors(self, v: Any) -> list[Any]:
        """O(V) 遍历邻居。"""
        i = self._index[v]
        return [self._vertices[j] for j, val in enumerate(self._matrix[i]) if val == 1]
```

### 2.3 加权有向图（Dijkstra 准备）

```python
# 文件：weighted_graph.py
import heapq
from collections import defaultdict
from typing import Any

class WeightedDirectedGraph:
    """加权有向图（邻接表）。"""

    def __init__(self):
        self._adj: dict[Any, list[tuple[Any, float]]] = defaultdict(list)

    def add_edge(self, u: Any, v: Any, weight: float) -> None:
        self._adj[u].append((v, weight))

    def shortest_path(self, start: Any, end: Any) -> tuple[float, list[Any]]:
        """Dijkstra 求最短路径 - O((V + E) log V)。"""
        dist = {start: 0}
        prev: dict[Any, Any] = {}
        pq = [(0, start)]  # (距离, 顶点)
        visited = set()

        while pq:
            d, v = heapq.heappop(pq)
            if v in visited:
                continue
            visited.add(v)
            if v == end:
                break
            for u, w in self._adj[v]:
                if u not in visited:
                    new_d = d + w
                    if new_d < dist.get(u, float('inf')):
                        dist[u] = new_d
                        prev[u] = v
                        heapq.heappush(pq, (new_d, u))

        # 回溯路径
        path = []
        cur = end
        while cur in prev:
            path.append(cur)
            cur = prev[cur]
        path.append(start)
        path.reverse()

        return dist.get(end, float('inf')), path
```

## 3. dify 仓库源码解读

### 3.1 dify 的工作流依赖图（DFS 遍历）

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/graph_traversal.py`
**核心代码**（行 1-50）：

```python
from collections import defaultdict, deque
from typing import Any

class WorkflowGraph:
    """工作流依赖图。

    dify 的工作流由多个节点组成（如 LLM、知识库、条件判断），
    节点之间存在依赖关系（如 B 依赖 A 的输出）。
    执行前需要拓扑排序确定执行顺序。

    这里用邻接表存储图，DFS 检测循环依赖。
    """

    def __init__(self):
        self._adj: dict[str, list[str]] = defaultdict(list)
        self._in_degree: dict[str, int] = defaultdict(int)

    def add_node(self, node_id: str, depends_on: list[str] | None = None) -> None:
        """添加节点和它的依赖。"""
        if depends_on:
            for dep in depends_on:
                self._adj[dep].append(node_id)  # dep → node
                self._in_degree[node_id] += 1
        self._in_degree.setdefault(node_id, 0)

    def topological_sort(self) -> list[str] | None:
        """拓扑排序：BFS + 入度表。

        Returns:
            排序后的节点列表，如果存在环则返回 None。
        """
        result = []
        q = deque([
            node for node, deg in self._in_degree.items() if deg == 0
        ])
        in_deg = dict(self._in_degree)

        while q:
            v = q.popleft()
            result.append(v)
            for u in self._adj[v]:
                in_deg[u] -= 1
                if in_deg[u] == 0:
                    q.append(u)

        if len(result) != len(self._in_degree):
            return None  # 有环

        return result

    def has_cycle(self) -> bool:
        """DFS 检测环。"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self._in_degree}

        def dfs(v: str) -> bool:
            color[v] = GRAY
            for u in self._adj[v]:
                if color[u] == GRAY:  # 后代有 GRAY 节点 → 有环
                    return True
                if color[u] == WHITE and dfs(u):
                    return True
            color[v] = BLACK
            return False

        for node in color:
            if color[node] == WHITE and dfs(node):
                return True
        return False
```

**解读**：
- 第 21 行：邻接表存储，`self._adj[A] = [B, C]` 表示 A → B, A → C
- 第 22 行：`in_degree` 记录每个节点的入度（被依赖次数）
- 第 33 行：拓扑排序用 BFS + 入度表，入度为 0 的先入队
- 第 49 行：DFS 三色标记检测环（GRAY 节点被再次访问 = 有环）
- **设计意图**：dify 工作流执行前必须拓扑排序，保证依赖在前；如果有循环依赖则报错

## 4. 关键要点总结

- 图由顶点和边组成，可分为有向/无向、加权/无权
- **邻接表**：O(V + E) 空间，适合稀疏图，**工业首选**
- **邻接矩阵**：O(V²) 空间，O(1) 查询边，适合稠密图
- BFS 求最短路径（无权），Dijkstra 求最短路径（正权）
- 拓扑排序：检测环、确定依赖顺序
- dify 用邻接表做工作流依赖图

## 5. 练习题

### 练习 1：基础（必做）

用邻接表实现一个图，并验证以下拓扑排序是否合理：
```
依赖：build → test → deploy
依赖：lint → test
依赖：test → release
```

### 练习 2：进阶

阅读 `api/core/workflow/graph_engine/graph_traversal.py`，说明 dify 为什么用 DFS 检测环而不是并查集（提示：考虑环的方向性）。

### 练习 3：挑战（选做）

实现 Dijkstra 算法（用堆优化），计算 5 个城市的航班最短路径。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/graph_engine/graph_traversal.py`
- 《算法导论》第 22 章 图的基本算法
- LeetCode 200/547/797 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13