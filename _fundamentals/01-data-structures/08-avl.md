# 1.2.3 平衡二叉树：AVL 树

> AVL 树通过自平衡保证 O(log n) 的查找，是平衡树的最早实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 AVL 树的自平衡机制（旋转操作）
- 掌握四种旋转：LL、RR、LR、RL
- 了解 AVL vs 红黑树的取舍
- 能在 dify 代码中识别对平衡数据结构的需求

## 📚 前置知识

- 07-bst.md
- 06-binary-tree.md

## 1. 核心概念

### 1.1 为什么需要 AVL？

BST 在**有序数据插入**时会退化为链表：

```
插入 1, 2, 3, 4, 5（有序）：
1
 \
  2
   \
    3
     \
      4
       \
        5
```
查找变成 O(n)，与链表无异。

### 1.2 AVL 树的定义

**AVL 树**：任何节点的**左右子树高度差 ≤ 1**（称为**平衡因子**）。

```
       4                平衡因子（BF）=|左高 - 右高|
      / \               4: BF=1
     2   6              2: BF=0
    /|   |              6: BF=0
   1 3   7              1, 3, 7: BF=0
```
**每个节点的 |BF| ≤ 1**。

### 1.3 失衡的四种情况

```
LL（Left-Left）：插入在左子树的左子树
    y                x
   / \             /   \
  x   T3   →     z     y
 / \            / \   / \
z   T2         T1 T2 T3 T4
/ \
T1 T2

RR（Right-Right）：插入在右子树的右子树
   y                 x
  / \              /   \
 T1  x    →       y     z
    / \         / \   / \
   T2  z       T1 T2 T3 T4
      / \
     T3 T4

LR（Left-Right）：插入在左子树的右子树
先对 x 做 RR 旋转变成 LL，再对 y 做 LL 旋转

RL（Right-Left）：插入在右子树的左子树
先对 x 做 LL 旋转变成 RR，再对 y 做 RR 旋转
```

### 1.4 旋转操作

#### LL 旋转（右旋）

```python
def right_rotate(y):
    x = y.left
    T2 = x.right
    x.right = y
    y.left = T2
    # 更新高度
    return x  # 新的根
```

#### RR 旋转（左旋）

```python
def left_rotate(x):
    y = x.right
    T2 = y.left
    y.left = x
    x.right = T2
    return y
```

### 1.5 AVL vs 红黑树

| 特性 | AVL | 红黑树 |
|------|-----|--------|
| 严格平衡 | 严格（高度差 ≤ 1） | 近似（最长路径 ≤ 2 倍最短） |
| 查找 | **更快**（树更矮） | 稍慢 |
| 插入/删除 | 较慢（旋转多） | **更快**（旋转少） |
| 适用场景 | 读多写少 | **读写均衡**（如 HashMap 内部） |

**结论**：Java `TreeMap`、C++ `std::map` 都用红黑树。

## 2. 代码示例

### 2.1 简化版 AVL 树

```python
# 文件：avl_tree.py
from typing import Optional

class AVLNode:
    def __init__(self, val: int):
        self.val = val
        self.left: Optional[AVLNode] = None
        self.right: Optional[AVLNode] = None
        self.height: int = 1

class AVLTree:
    def _height(self, node: Optional[AVLNode]) -> int:
        return node.height if node else 0

    def _balance_factor(self, node: Optional[AVLNode]) -> int:
        if node is None:
            return 0
        return self._height(node.left) - self._height(node.right)

    def _update_height(self, node: AVLNode) -> None:
        node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _right_rotate(self, y: AVLNode) -> AVLNode:
        """LL 失衡 → 右旋。"""
        x = y.left
        T2 = x.right
        x.right = y
        y.left = T2
        self._update_height(y)
        self._update_height(x)
        return x

    def _left_rotate(self, x: AVLNode) -> AVLNode:
        """RR 失衡 → 左旋。"""
        y = x.right
        T2 = y.left
        y.left = x
        x.right = T2
        self._update_height(x)
        self._update_height(y)
        return y

    def insert(self, root: Optional[AVLNode], val: int) -> AVLNode:
        """插入节点并保持平衡。"""
        # 1. 普通 BST 插入
        if root is None:
            return AVLNode(val)
        if val < root.val:
            root.left = self.insert(root.left, val)
        else:
            root.right = self.insert(root.right, val)

        # 2. 更新高度
        self._update_height(root)

        # 3. 检查失衡并旋转
        bf = self._balance_factor(root)

        # LL
        if bf > 1 and val < root.left.val:
            return self._right_rotate(root)
        # RR
        if bf < -1 and val > root.right.val:
            return self._left_rotate(root)
        # LR
        if bf > 1 and val > root.left.val:
            root.left = self._left_rotate(root.left)
            return self._right_rotate(root)
        # RL
        if bf < -1 and val < root.right.val:
            root.right = self._right_rotate(root.right)
            return self._left_rotate(root)

        return root

    def inorder(self, root: Optional[AVLNode]) -> list[int]:
        if root is None:
            return []
        return self.inorder(root.left) + [root.val] + self.inorder(root.right)
```

## 3. dify 仓库源码解读

### 3.1 dify 的文档索引（类 AVL 思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/index_processor/processor/parent_child_index_processor.py`
**核心代码**（行 1-50）：

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class ChunkNode:
    """文档片段节点：父子结构。

    dify 的 Parent-Child Index 把文档切成父子两层：
    - Parent：粗粒度段落（用于上下文）
    - Child：细粒度句子（用于精确匹配）

    类似 AVL 的分层思想：粗粒度在上层，细粒度在下层。
    """
    chunk_id: str
    content: str
    parent_id: Optional[str] = None
    children: list[str] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

class ParentChildIndex:
    def __init__(self):
        self._parents: dict[str, ChunkNode] = {}
        self._children: dict[str, ChunkNode] = {}

    def add_chunk(self, chunk: ChunkNode) -> None:
        """添加文档片段，维护父子关系。"""
        if chunk.parent_id is None:
            # 父节点
            self._parents[chunk.chunk_id] = chunk
        else:
            # 子节点
            self._children[chunk.chunk_id] = chunk
            parent = self._parents.get(chunk.parent_id)
            if parent:
                parent.children.append(chunk.chunk_id)

    def retrieve_balanced(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[ChunkNode]:
        """分层检索：先匹配子节点，再返回对应父节点。

        类似 AVL 的思路：先在细粒度层命中，再回到粗粒度层取上下文。
        """
        # Step 1: 在子节点层向量检索
        child_hits = self._vector_search_children(query, top_k * 2)

        # Step 2: 找每个 hit 对应的父节点
        parent_ids = list({
            self._children[h].parent_id for h in child_hits
            if self._children[h].parent_id
        })

        # Step 3: 返回父节点（去重后按 top_k 截断）
        return [self._parents[pid] for pid in parent_ids[:top_k]]
```

**解读**：
- 第 45 行：先去子节点（细粒度）匹配，再回到父节点（粗粒度）取上下文
- **分层思想**：类似 AVL 的"上层稀疏、下层密集"结构
- **设计意图**：精确匹配句子但返回段落，避免断章取义
- **与 AVL 的区别**：这里是**业务分层**而非**平衡约束**，但思想相通——分层组织提高检索效率

## 4. 关键要点总结

- AVL 树保证 |平衡因子| ≤ 1，最坏查找 O(log n)
- 失衡时通过旋转恢复平衡：LL→右旋，RR→左旋，LR/RL→双旋
- AVL 查找快但插入删除旋转多，红黑树读写更均衡
- Java `TreeMap` 用红黑树，**实际生产首选红黑树**
- dify 的文档索引用"父子分层"思想，类似 AVL 的分层平衡

## 5. 练习题

### 练习 1：基础（必做）

手动画出对序列 `[1, 2, 3, 4, 5, 6]` 插入 AVL 树的过程，标注每次旋转。

### 练习 2：进阶

阅读 `api/core/rag/index_processor/processor/parent_child_index_processor.py`，说明为什么 dify 检索时先匹配子节点再返回父节点，而不是直接在父节点检索。

### 练习 3：挑战（选做）

实现 AVL 树的 `delete(val)` 方法，处理删除节点后的四种失衡情况。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/index_processor/processor/parent_child_index_processor.py`
- AVL 树发明者论文：Adelson-Velsky and Landis (1962)
- 《算法导论》第 13 章 平衡二叉树

---

**文档版本**：v1.0
**最后更新**：2026-07-13