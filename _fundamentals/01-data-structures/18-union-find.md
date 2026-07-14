# 1.4.2 并查集（Union-Find）

> 并查集是处理"连通分量"问题的利器，几乎所有图算法都会用到。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解并查集的"找根 + 合并"操作
- 掌握路径压缩和按秩合并两个优化
- 能用并查集解决连通性问题
- 能在 dify 中识别需要并查集的场景（如权限分组、好友关系）

## 📚 前置知识

- 17-graph.md
- 11-heap.md

## 1. 核心概念

### 1.1 什么是并查集？

**并查集**（Union-Find / Disjoint Set Union, DSU）是处理**不相交集合**合并与查询的数据结构。

**核心操作**：
- `find(x)`：找 x 所在集合的**根节点**
- `union(x, y)`：合并 x 和 y 所在的集合

### 1.2 直观理解

```
初始：每个人是自己的集合
[A] [B] [C] [D] [E]

union(A, B)：A 和 B 是朋友
{A, B} [C] [D] [E]

union(C, D)：
{A, B} {C, D} [E]

union(B, C)：
{A, B, C, D} [E]

find(A) = find(D) = 同一个根 → A 和 D 是朋友
```

### 1.3 数据结构

**用数组实现**：`parent[i] = j` 表示 i 的父节点是 j。

```
parent 数组：[0, 0, 1, 2, 4]

含义：
- 0 是根
- 1 的父是 0，2 的父是 1（→ 根是 0）
- 3 的父是 2（→ 根是 0）
- 4 是根
```

### 1.4 关键优化

#### 路径压缩（Path Compression）

`find` 时把路径上的节点直接挂到根：

```
之前：3 → 2 → 1 → 0
之后：3 → 0, 2 → 0, 1 → 0

下次 find(3) 直接到 0！
```

#### 按秩合并（Union by Rank）

合并时把**矮树挂到高树下**，避免树变深：

```
union(树 A 高度 3, 树 B 高度 1)：
- 把 B 挂到 A 下 → 总高度仍是 3
- 而不是反过来 → 总高度变成 4
```

### 1.5 复杂度

**优化后**：单次操作的均摊时间复杂度是 **α(n)**（反阿克曼函数），几乎等同于 O(1)。

| 操作 | 复杂度 |
|------|--------|
| find | O(α(n)) ≈ O(1) |
| union | O(α(n)) ≈ O(1) |

### 1.6 应用场景

1. **连通性问题**：岛屿数量、网络连通
2. **Kruskal 算法**：最小生成树
3. **社交网络**：好友关系、间接关系
4. **权限系统**：用户分组、资源访问
5. **编译器**：变量等价类分析

## 2. 代码示例

### 2.1 完整实现

```python
# 文件：union_find.py
from typing import Any

class UnionFind:
    """并查集：路径压缩 + 按秩合并。"""

    def __init__(self, n: int):
        self._parent = list(range(n))
        self._rank = [0] * n  # 树高
        self._count = n  # 连通分量数

    def find(self, x: int) -> int:
        """找 x 的根节点 - 路径压缩。"""
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: int, y: int) -> bool:
        """合并 x 和 y 的集合 - 按秩合并。

        Returns:
            True 表示发生了合并，False 表示已经在同一集合。
        """
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False  # 已经在同一集合

        # 按秩合并：矮树挂到高树下
        if self._rank[root_x] < self._rank[root_y]:
            root_x, root_y = root_y, root_x
        self._parent[root_y] = root_x

        if self._rank[root_x] == self._rank[root_y]:
            self._rank[root_x] += 1

        self._count -= 1
        return True

    def connected(self, x: int, y: int) -> bool:
        """判断 x 和 y 是否在同一集合。"""
        return self.find(x) == self.find(y)

    def count(self) -> int:
        """返回连通分量数。"""
        return self._count
```

### 2.2 岛屿数量（LeetCode 200）

```python
# 文件：number_of_islands.py
from typing import List

def num_islands(grid: List[List[str]]) -> int:
    """计算岛屿数量：用并查集。"""
    if not grid:
        return 0

    rows, cols = len(grid), len(grid[0])
    uf = UnionFind(rows * cols)
    water = 0

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "0":
                water += 1
                continue
            # 检查右、下两个方向
            idx = r * cols + c
            if c + 1 < cols and grid[r][c + 1] == "1":
                uf.union(idx, idx + 1)
            if r + 1 < rows and grid[r + 1][c] == "1":
                uf.union(idx, idx + cols)

    return uf.count() - water

# 测试
grid = [
    ["1","1","0","0","0"],
    ["1","1","0","0","0"],
    ["0","0","1","0","0"],
    ["0","0","0","1","1"],
]
print(num_islands(grid))  # 3
```

### 2.3 Kruskal 最小生成树

```python
# 文件：kruskal.py
def kruskal(n: int, edges: list[tuple[int, int, int]]) -> tuple[int, list]:
    """Kruskal 算法：求最小生成树。

    Args:
        n: 顶点数
        edges: [(u, v, weight), ...]
    """
    uf = UnionFind(n)
    edges.sort(key=lambda e: e[2])  # 按权重排序

    mst_weight = 0
    mst_edges = []

    for u, v, w in edges:
        if uf.union(u, v):  # 不在同一个集合 → 加入 MST
            mst_weight += w
            mst_edges.append((u, v, w))

    return mst_weight, mst_edges

# 测试：4 个顶点 5 条边
edges = [
    (0, 1, 10), (0, 2, 6), (0, 3, 5),
    (1, 3, 15), (2, 3, 4),
]
print(kruskal(4, edges))  # (19, [(2, 3, 4), (0, 3, 5), (0, 1, 10)])
```

## 3. dify 仓库源码解读

### 3.1 dify 的角色权限分组

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 100-140）：

```python
from typing import Any

class TenantAccessControl:
    """租户访问控制：管理用户在不同租户的角色。

    dify 支持多租户架构，每个用户在不同租户下有不同角色：
    - owner：所有者
    - admin：管理员
    - editor：编辑者
    - normal：普通用户

    并查集思想：把同一租户下的用户合并到同一集合。
    """

    def __init__(self):
        # 模拟并查集：tenant_id -> user_ids
        self._tenant_users: dict[str, set[str]] = {}

    def add_user_to_tenant(self, tenant_id: str, user_id: str) -> None:
        """添加用户到租户。"""
        if tenant_id not in self._tenant_users:
            self._tenant_users[tenant_id] = set()
        self._tenant_users[tenant_id].add(user_id)

    def is_in_same_tenant(
        self,
        user_a: str,
        user_b: str,
        tenant_id: str,
    ) -> bool:
        """判断两个用户是否在同一租户（find 操作）。"""
        users = self._tenant_users.get(tenant_id, set())
        return user_a in users and user_b in users

    def can_access_resource(
        self,
        user_id: str,
        resource_owner_id: str,
        tenant_id: str,
    ) -> bool:
        """判断用户是否能访问资源（同租户即可访问）。"""
        # 简化：同租户即有访问权限
        return self.is_in_same_tenant(user_id, resource_owner_id, tenant_id)


# dify 的真实实现更复杂：
# - 用 PostgreSQL 的 account_joins 表记录用户-租户关系
# - 查询通过 JOIN 实现（类似并查集的 find）
# - 角色变更通过 UPDATE（类似 union）
```

**解读**：
- 第 20 行：`_tenant_users` 字典模拟并查集，key 是租户 ID，value 是用户集合
- 第 28 行：`is_in_same_tenant` 类似 `find`：判断两个用户是否在同一集合
- **dify 中无直接 UnionFind 类调用**，但**多租户权限模型本质上是并查集思想**
- **类似场景**：dify 的应用共享、API Key 授权、数据集权限都依赖这种"集合归属"判断

## 4. 关键要点总结

- 并查集处理**集合合并**和**根查询**两类问题
- 两种核心优化：**路径压缩** + **按秩合并**
- 优化后均摊复杂度 **O(α(n)) ≈ O(1)**
- 应用：连通性、岛屿、Kruskal、权限分组
- dify 多租户权限系统类似并查集思想

## 5. 练习题

### 练习 1：基础（必做）

实现并查集，解决以下问题：
- 初始有 10 个元素
- 合并 (1,2), (3,4), (5,6), (1,3)
- 判断 1 和 4 是否在同一集合

### 练习 2：进阶

阅读 `api/services/account_service.py`，说明 dify 的多租户权限如何用并查集思想优化查询性能。

### 练习 3：挑战（选做）

实现**带权并查集**：每个元素除了根还有一个到根的距离（如好友关系中"A 到 B 的距离是 2 度"），支持路径压缩 + 距离更新。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- 《算法导论》第 21 章 不相交集合的数据结构
- LeetCode 200/547/990 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13