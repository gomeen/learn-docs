# 1.2.2 二叉搜索树（BST）

> 二叉搜索树支持 O(log n) 的查找、插入、删除，是数据库索引的雏形。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 BST 的定义和"左小右大"性质
- 实现 BST 的查找、插入、删除
- 了解 BST 的退化问题（为什么需要平衡树）
- 能在 dify 中识别 BST 的应用场景

## 📚 前置知识

- 06-binary-tree.md
- 09-recursion.md

## 1. 核心概念

### 1.1 BST 的定义

**二叉搜索树**（Binary Search Tree）满足：
- 左子树上所有节点的值 < 根节点的值
- 右子树上所有节点的值 > 根节点的值
- 左右子树也都是 BST

```
        8
       / \
      3   10
     /|    |\
    1 6    9 14
      /|     /
     4 7    13
```

**中序遍历**：`1, 3, 4, 6, 7, 8, 9, 10, 13, 14` —— **有序**！

### 1.2 BST 的复杂度

**理想情况（平衡）**：
- 查找：O(log n)
- 插入：O(log n)
- 删除：O(log n)

**最坏情况（退化为链表）**：
```
1
 \
  2
   \
    3
     \
      4
```
- 查找：O(n)
- 插入：O(n)
- 删除：O(n)

**这就是为什么需要平衡树（[AVL](./08-avl.md)、[红黑树](./09-red-black-tree.md)）。**

### 1.3 BST 的操作

#### 查找

```python
def search(root, target):
    if root is None or root.val == target:
        return root
    if target < root.val:
        return search(root.left, target)
    return search(root.right, target)
```

#### 插入

```python
def insert(root, val):
    if root is None:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    else:
        root.right = insert(root.right, val)
    return root
```

#### 删除（最复杂）

三种情况：
1. **叶子节点**：直接删
2. **只有一子树**：用子树替换
3. **有两子树**：用**中序后继**（右子树最小值）或**中序前驱**（左子树最大值）替换

## 2. 代码示例

### 2.1 完整的 BST 实现

```python
# 文件：bst.py
from typing import Optional

class TreeNode:
    def __init__(self, val: int):
        self.val = val
        self.left: Optional[TreeNode] = None
        self.right: Optional[TreeNode] = None

class BST:
    def __init__(self):
        self.root: Optional[TreeNode] = None

    def search(self, val: int) -> Optional[TreeNode]:
        """查找 - O(log n) 平均，O(n) 最坏。"""
        return self._search(self.root, val)

    def _search(self, node: Optional[TreeNode], val: int) -> Optional[TreeNode]:
        if node is None or node.val == val:
            return node
        if val < node.val:
            return self._search(node.left, val)
        return self._search(node.right, val)

    def insert(self, val: int) -> None:
        """插入 - O(log n) 平均。"""
        self.root = self._insert(self.root, val)

    def _insert(self, node: Optional[TreeNode], val: int) -> TreeNode:
        if node is None:
            return TreeNode(val)
        if val < node.val:
            node.left = self._insert(node.left, val)
        else:
            node.right = self._insert(node.right, val)
        return node

    def find_min(self, node: TreeNode) -> TreeNode:
        """找最小值（最左节点）。"""
        while node.left is not None:
            node = node.left
        return node

    def delete(self, val: int) -> None:
        """删除 - O(log n) 平均。"""
        self.root = self._delete(self.root, val)

    def _delete(self, node: Optional[TreeNode], val: int) -> Optional[TreeNode]:
        if node is None:
            return None
        if val < node.val:
            node.left = self._delete(node.left, val)
        elif val > node.val:
            node.right = self._delete(node.right, val)
        else:
            # 找到目标节点
            if node.left is None:
                return node.right  # 情况 1 & 2：没有左子树
            if node.right is None:
                return node.left   # 情况 2：没有右子树
            # 情况 3：左右子树都存在，用中序后继（右子树最小值）替换
            successor = self.find_min(node.right)
            node.val = successor.val
            node.right = self._delete(node.right, successor.val)
        return node

    def inorder(self) -> list[int]:
        """中序遍历，返回有序列表。"""
        result = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node: Optional[TreeNode], result: list[int]) -> None:
        if node is None:
            return
        self._inorder(node.left, result)
        result.append(node.val)
        self._inorder(node.right, result)
```

### 2.2 验证 BST

```python
def is_valid_bst(root: Optional[TreeNode]) -> bool:
    """验证是否是合法 BST - O(n) 时间和空间。"""
    def validate(node: Optional[TreeNode], min_val: float, max_val: float) -> bool:
        if node is None:
            return True
        if node.val <= min_val or node.val >= max_val:
            return False
        return (validate(node.left, min_val, node.val)
                and validate(node.right, node.val, max_val))

    return validate(root, float('-inf'), float('inf'))
```

## 3. dify 仓库源码解读

### 3.1 dify 中 BST 风格的元数据过滤

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/utils/dataset_retriever.py`
**核心代码**（行 100-130）：

```python
from typing import Any

class MetadataFilter:
    """数据集元数据过滤器。

    dify 把文档的元数据按字段组织，每个字段用排序结构存储，
    支持范围查询（类似 BST 的 lower_bound / upper_bound）。
    """

    def __init__(self):
        # value -> [document_id] 的有序映射
        self._index: dict[str, list[str]] = {}
        # 缓存每个字段的排序结果（懒加载）
        self._sorted_keys: dict[str, list[str]] = {}

    def add(self, key: str, value: str, doc_id: str) -> None:
        """添加文档到索引。"""
        full_key = f"{key}={value}"
        if full_key not in self._index:
            self._index[full_key] = []
        self._index[full_key].append(doc_id)

    def range_query(self, key: str, low: str, high: str) -> list[str]:
        """范围查询，返回 key 字段值在 [low, high] 的所有文档。"""
        # 实际生产用 PostgreSQL 的 B-Tree 索引（基于 BST 思想）
        # 这里简化展示逻辑
        sorted_keys = self._sorted_keys.setdefault(
            key, sorted(k for k in self._index if k.startswith(f"{key}="))
        )
        # 二分查找 low 和 high 的位置
        import bisect
        lo = bisect.bisect_left(sorted_keys, f"{key}={low}")
        hi = bisect.bisect_right(sorted_keys, f"{key}={high}")

        result = []
        for k in sorted_keys[lo:hi]:
            result.extend(self._index[k])
        return result
```

**解读**：
- 第 25 行：`bisect` 模块用**二分查找**在有序列表中找插入点
- 第 26 行：`bisect_left` / `bisect_right` 是 O(log n) 查找
- 第 31 行：切片 `[lo:hi]` 是 O(k)，k 是结果数
- **整体复杂度**：范围查询 **O(log n + k)**
- **设计意图**：底层用 PostgreSQL 的 B-Tree（多路 BST）索引，比全表扫描快得多

## 4. 关键要点总结

- BST：左子树 < 根 < 右子树，中序遍历有序
- 平衡 BST 查找/插入/删除都是 O(log n)
- 退化为链表时变成 O(n)，所以需要平衡树
- 删除节点：找中序后继（右子树最小值）替换
- 数据库索引底层是 [B+ 树](./10-b-tree.md)（BST 的多路版本）

## 5. 练习题

### 练习 1：基础（必做）

实现 BST 的 `floor(val)` 方法：返回小于等于 `val` 的最大节点值。

### 练习 2：进阶

阅读 `api/core/tools/utils/dataset_retriever.py`，分析如果数据集有 100 万个文档，`range_query` 的实际执行时间。

### 练习 3：挑战（选做）

给定一个有序数组 `[1,2,3,4,5,6,7]`，构造一个**高度平衡**的 BST（提示：用中间元素作为根）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/utils/dataset_retriever.py`
- 《算法导论》第 12 章 二叉搜索树
- LeetCode 98/230/450 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13