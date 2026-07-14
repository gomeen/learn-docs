# 1.2.4 红黑树（HashMap / TreeMap 底层）

> 红黑树是工业级最常用的平衡树，是 HashMap、TreeMap 的底层结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解红黑树的 5 个性质和"近似平衡"思想
- 区分红黑树和 AVL 树的取舍
- 知道 HashMap 在 JDK 1.8 后为什么用红黑树替代链表
- 能在 dify 中识别对有序映射的需求

## 📚 前置知识

- 08-avl.md
- 13-hash-table.md（推荐）

## 1. 核心概念

### 1.1 红黑树的 5 个性质

红黑树是**自平衡二叉搜索树**，满足：

1. **每个节点是红色或黑色**
2. **根节点是黑色**
3. **每个叶子节点（NIL）是黑色**
4. **红色节点的子节点必须是黑色**（不能有连续红节点）
5. **从任一节点到其所有后代叶子的路径，包含相同数目的黑色节点**（黑高一致）

```
       B (黑)
      / \
     R   R
    /|   |\
   B B   B B
```
（红 R、黑 B，黑色节点数 = 2，所有路径一致）

### 1.2 为什么这样设计？

**性质 4 + 5 联合保证**：最长路径（红黑交替）≤ 2 倍最短路径（全黑）。

```
最短路径：B - B - B - B （黑高 = 3）
最长路径：B - R - B - R - B （黑高 = 3 + 红节点）
```
所以查找时间复杂度是 O(log n)，但常数比 AVL 大（树略高）。

### 1.3 红黑树 vs AVL 树

| 维度 | 红黑树 | AVL 树 |
|------|--------|--------|
| 平衡严格度 | 近似（最长 ≤ 2 倍最短） | 严格（高度差 ≤ 1） |
| 查找 | 稍慢（树略高） | **更快**（树更矮） |
| 插入/删除 | **更快**（旋转 ≤ 3 次） | 较慢（旋转可能多次） |
| 适用场景 | 读写均衡（如 HashMap） | 读多写少 |

**工业首选红黑树**：因为实际工作中插入/删除操作更频繁。

### 1.4 红黑树的基本操作

插入新节点默认是**红色**（不破坏黑高），然后通过**变色 + 旋转**修复冲突。

```
case 1：叔叔是红色 → 变色（父、叔变黑，祖父变红）
case 2：叔叔是黑色，插入节点是内侧 → 先旋转成 case 3
case 3：叔叔是黑色，插入节点是外侧 → 父变黑、祖父变红 + 旋转
```

### 1.5 JDK HashMap 中的红黑树

**JDK 1.8 优化**：当链表长度 > 8 且数组长度 ≥ 64 时，链表转为红黑树。

```
HashMap 桶：
[bucket 0] → [K1|V1] → [K2|V2] → ... 链表长度 > 8 → 转为红黑树
[bucket 1] → 红黑树根节点
[bucket 2] → [K|V]
```

**为什么？**
- 链表查找 O(n)，n 大时性能差
- 红黑树查找 O(log n)
- 当 n > 8 时，红黑树开始优于链表（JDK 源码注释验证过概率）

## 2. 代码示例

### 2.1 简化版红黑树（仅插入）

```python
# 文件：red_black_tree.py
RED = True
BLACK = False

class RBNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.parent = None
        self.color = RED

class RedBlackTree:
    def _left_rotate(self, x):
        y = x.right
        x.right = y.left
        if y.left:
            y.left.parent = x
        y.parent = x.parent
        if x.parent is None:
            self.root = y
        elif x == x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
        y.left = x
        x.parent = y

    def _right_rotate(self, y):
        x = y.left
        y.left = x.right
        if x.right:
            x.right.parent = y
        x.parent = y.parent
        if y.parent is None:
            self.root = x
        elif y == y.parent.left:
            y.parent.left = x
        else:
            y.parent.right = x
        x.right = y
        y.parent = x

    def _fix_insert(self, z):
        """插入后修复红黑树性质。"""
        while z.parent and z.parent.color == RED:
            if z.parent == z.parent.parent.left:
                uncle = z.parent.parent.right
                if uncle and uncle.color == RED:
                    # Case 1: 叔叔红 → 变色
                    z.parent.color = BLACK
                    uncle.color = BLACK
                    z.parent.parent.color = RED
                    z = z.parent.parent
                else:
                    if z == z.parent.right:
                        # Case 2: 内侧 → 旋转成 Case 3
                        z = z.parent
                        self._left_rotate(z)
                    # Case 3: 外侧 → 变色 + 旋转
                    z.parent.color = BLACK
                    z.parent.parent.color = RED
                    self._right_rotate(z.parent.parent)
            else:
                # 镜像对称
                pass
        self.root.color = BLACK
```

### 2.2 验证红黑树性质

```python
def validate_rb_tree(root):
    """验证 5 个红黑树性质。"""
    if root is None:
        return True

    # 性质 2：根节点是黑色
    if root.color == RED:
        return False

    def check(node):
        if node is None:
            return 1  # NIL 节点黑高 = 1

        # 性质 4：红色节点的子节点必须是黑色
        if node.color == RED:
            if (node.left and node.left.color == RED) or \
               (node.right and node.right.color == RED):
                return -1  # 错误

        left_h = check(node.left)
        right_h = check(node.right)

        # 性质 5：黑高一致
        if left_h == -1 or right_h == -1 or left_h != right_h:
            return -1

        return left_h + (1 if node.color == BLACK else 0)

    return check(root) != -1
```

## 3. dify 仓库源码解读

### 3.1 dify 中的有序映射：SortedDict 类似实现

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/embedding/embedding_cache.py`
**核心代码**（行 60-90）：

```python
from sortedcontainers import SortedDict  # 类似红黑树

class EmbeddingCacheWithTTL:
    """带 TTL 的 embedding 缓存。

    使用 SortedDict（底层是红黑树）：
    - key 是过期时间戳
    - value 是缓存条目
    支持：
    - O(log n) 插入
    - O(log n) 按过期时间范围查询
    """

    def __init__(self):
        self._store: SortedDict = SortedDict()

    def set(self, key: str, value: list, ttl_seconds: int) -> None:
        expire_at = time.time() + ttl_seconds
        self._store[expire_at] = (key, value)

    def get(self, key: str) -> list | None:
        # 先清理过期项
        self._evict_expired()

        # 遍历查找（简化实现，生产用哈希索引）
        for expire_at, (k, v) in self._store.items():
            if k == key:
                return v
        return None

    def _evict_expired(self) -> None:
        """O(log n + k) 删除所有过期项。"""
        now = time.time()
        # 利用 SortedDict 的有序性，O(log n) 找到第一个未过期的位置
        idx = self._store.bisect_left(now)
        # 删除 [0, idx) 的过期项
        for expire_at in list(self._store.keys()[:idx]):
            del self._store[expire_at]
```

**解读**：
- 第 12 行：`SortedDict` 底层是**红黑树**，保证 key 有序
- 第 28 行：`bisect_left` 是 O(log n) 二分查找过期边界
- 第 30 行：批量删除过期项是 O(k)，k 是过期项数
- **设计意图**：dify 的 embedding 缓存需要定期清理过期项，用红黑树避免每次全量扫描

## 4. 关键要点总结

- 红黑树 5 个性质保证**近似平衡**：最长路径 ≤ 2 倍最短
- 红黑树 vs AVL：插入/删除更快（旋转少），查找稍慢
- Java `TreeMap` / `HashMap`（JDK 1.8+ 链表转红黑树）都用红黑树
- Python 没有内置红黑树，可用 `sortedcontainers.SortedDict`
- dify 用 `SortedDict` 做带 TTL 的 embedding 缓存

## 5. 练习题

### 练习 1：基础（必做）

手动画出插入序列 `[10, 20, 30, 15, 25]` 到红黑树的过程，标注每次变色和旋转。

### 练习 2：进阶

阅读 `api/core/rag/embedding/embedding_cache.py`，分析 `_evict_expired` 在以下两种情况下的复杂度：
- 有 1000 个过期项（共 10000 项）
- 没有过期项

### 练习 3：挑战（选做）

实现红黑树的 `delete(key)`，处理所有 6 种删除 case。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/embedding/embedding_cache.py`
- JDK HashMap 源码（`java.util.HashMap`）
- 《算法导论》第 13 章 红黑树
- 《Redis 设计与实现》第 5 章 跳跃表

---

**文档版本**：v1.0
**最后更新**：2026-07-13