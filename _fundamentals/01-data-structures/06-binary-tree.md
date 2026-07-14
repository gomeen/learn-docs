# 1.2.1 二叉树基础

> 二叉树是树结构的基础，递归思维的核心训练场。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解二叉树的定义、术语和存储方式
- 实现前序/中序/后序/层序遍历
- 用递归思维解决树的问题
- 能在 dify 中识别树结构的实际应用（如 RAG 文档树）

## 📚 前置知识

- 04-linked-list.md
- 09-recursion.md（推荐）

## 1. 核心概念

### 1.1 什么是二叉树？

每个节点最多有**两个**子节点（左子、右子）的树结构。

```
        A           ← 根节点（root）
       / \
      B   C         ← 子树（subtree）
     / \   \
    D   E   F       ← 叶子节点（leaf）
```

### 1.2 重要术语

| 术语 | 定义 |
|------|------|
| 根节点 | 没有父节点的节点 |
| 叶子 | 没有子节点的节点 |
| 高度 | 从根到叶子的最长路径的边数 |
| 深度 | 从根到该节点的边数 |
| 层 | 根在第 0 层，子节点在第 n+1 层 |
| 度 | 子节点的数量（二叉树 ≤ 2） |

### 1.3 满二叉树 vs 完全二叉树

**满二叉树**：所有叶子都在最后一层，且节点全满。

```
       A
      / \
     B   C
    /|  |\
   D E  F G
```

**完全二叉树**：除了最后一层，其他层都满；最后一层节点**靠左**。

```
       A
      / \
     B   C
    /|  /
   D E F
```

完全二叉树可以用**数组**紧凑存储（第 i 个节点的左子是 `2i+1`，右子是 `2i+2`）。

### 1.4 存储方式

**链式存储**（最常用）：
```python
class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left: TreeNode | None = None
        self.right: TreeNode | None = None
```

**数组存储**（仅限完全二叉树）：
```
       A       → [A, B, C, D, E, _, F]
      / \
     B   C
    /|  /
   D E F
```

### 1.5 四种遍历方式

| 遍历 | 顺序 | 应用 |
|------|------|------|
| 前序 | 根→左→右 | 序列化、复制树 |
| 中序 | 左→根→右 | BST 升序输出 |
| 后序 | 左→右→根 | 释放内存、计算子树 |
| 层序 | 按层从左到右 | BFS、序列化 |

## 2. 代码示例

### 2.1 实现四种遍历

```python
# 文件：binary_tree.py
from collections import deque
from typing import Optional

class TreeNode:
    def __init__(self, val: int):
        self.val = val
        self.left: Optional[TreeNode] = None
        self.right: Optional[TreeNode] = None

# 构建示例树
#       1
#      / \
#     2   3
#    /|   |\
#   4 5   6 7
root = TreeNode(1)
root.left = TreeNode(2)
root.right = TreeNode(3)
root.left.left = TreeNode(4)
root.left.right = TreeNode(5)
root.right.left = TreeNode(6)
root.right.right = TreeNode(7)

# 前序遍历：根→左→右
def preorder(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    return [node.val] + preorder(node.left) + preorder(node.right)

# 中序遍历：左→根→右
def inorder(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    return inorder(node.left) + [node.val] + inorder(node.right)

# 后序遍历：左→右→根
def postorder(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    return postorder(node.left) + postorder(node.right) + [node.val]

# 层序遍历：BFS
def level_order(node: TreeNode | None) -> list[int]:
    if node is None:
        return []
    result = []
    q = deque([node])
    while q:
        n = q.popleft()
        result.append(n.val)
        if n.left:
            q.append(n.left)
        if n.right:
            q.append(n.right)
    return result

print(preorder(root))    # [1, 2, 4, 5, 3, 6, 7]
print(inorder(root))     # [4, 2, 5, 1, 6, 3, 7]
print(postorder(root))   # [4, 5, 2, 6, 7, 3, 1]
print(level_order(root)) # [1, 2, 3, 4, 5, 6, 7]
```

### 2.2 计算树的高度

```python
def max_depth(node: TreeNode | None) -> int:
    """递归：树的高度 = max(左子树高度, 右子树高度) + 1"""
    if node is None:
        return 0
    return 1 + max(max_depth(node.left), max_depth(node.right))

# 迭代版本（避免递归爆栈）
def max_depth_iter(root: TreeNode | None) -> int:
    if root is None:
        return 0
    depth = 0
    q = deque([root])
    while q:
        depth += 1
        for _ in range(len(q)):  # 处理当前层所有节点
            node = q.popleft()
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
    return depth
```

## 3. dify 仓库源码解读

### 3.1 树形结构索引（Hierarchical Index）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/summary_index/summary_index.py`
**核心代码**（行 1-50）：

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class SummaryNode:
    """摘要索引节点：树形结构的节点。

    dify 的 SummaryIndex 把文档组织成树状结构，
    每个节点代表一段文本的摘要，子节点是更细粒度的子段落。
    """
    node_id: str
    content: str
    summary: str
    children: list['SummaryNode']
    embedding: list[float] | None = None

    def traverse_dfs(self) -> list['SummaryNode']:
        """深度优先遍历，返回所有节点。"""
        result = [self]
        for child in self.children:
            result.extend(child.traverse_dfs())
        return result

    def traverse_bfs(self) -> list['SummaryNode']:
        """广度优先遍历，按层返回节点。"""
        result = []
        current_layer = [self]
        while current_layer:
            result.extend(current_layer)
            next_layer = []
            for node in current_layer:
                next_layer.extend(node.children)
            current_layer = next_layer
        return result

    def find_leaf(self) -> list['SummaryNode']:
        """找出所有叶子节点（无子节点的节点）。"""
        if not self.children:
            return [self]
        leaves = []
        for child in self.children:
            leaves.extend(child.find_leaf())
        return leaves
```

**解读**：
- 第 16 行：`children` 是 `list`，支持任意子节点（不只是二叉）
- 第 22 行：`traverse_dfs` 是递归 DFS
- 第 32 行：`traverse_bfs` 用**双 buffer 思想**实现 BFS，避免多次 `deque` 操作
- **设计意图**：dify 的文档摘要索引用树形组织，根节点是全文摘要，叶子是段落原文，查询时从根往下匹配

## 4. 关键要点总结

- 二叉树每个节点最多 2 个子节点（左、右）
- 完全二叉树可以用数组紧凑存储（堆就是完全二叉树）
- 四种遍历：前序（根左右）、中序（左根右）、后序（左右根）、层序（BFS）
- 树的问题**优先考虑递归**（子树是天然递归结构）
- dify 用树形结构组织文档摘要索引

## 5. 练习题

### 练习 1：基础（必做）

给定二叉树的根节点，判断它是否**镜像对称**（如 `[1,2,2,3,4,4,3]` 是对称的）。

### 练习 2：进阶

阅读 `api/core/rag/summary_index/summary_index.py`，分析 `traverse_dfs` 和 `traverse_bfs` 的时间和空间复杂度。

### 练习 3：挑战（选做）

给定一棵二叉树，**原地**展开为链表（LeetCode 114）。要求：
- 展开顺序：前序
- 使用右指针作为链表 next
- 空间 O(1)

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/summary_index/summary_index.py`
- 《算法导论》第 12 章 二叉搜索树
- LeetCode 94/102/104 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13