# 3.2 B+ 树索引原理

> B+ 树是数据库最常用的索引结构（MySQL InnoDB、PostgreSQL）。理解 B+ 树能让你理解"为什么范围查询快"。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 B+ 树的结构（多路平衡查找树）
- 理解 B+ 树 vs B 树的区别（数据只在叶子）
- 知道为什么 B+ 树适合范围查询
- 在 dify/ruoyi 中识别 B+ 树索引

## 📚 前置知识

- 二叉树、平衡二叉树（AVL）
- 10-index-basics.md

## 1. 核心概念

### 1.1 B+ 树的结构

```
                [50 | 100]                  ← 内部节点（只存索引键）
              /      |      \
       [10|30]   [60|80]   [120|150]        ← 内部节点
       /  |  \    /  |  \    /  |  \
      ◇ ◇ [→10|→30|→50] ◇ ◇ [→60|→80|→100]  ◇ ◇ ...   ← 叶子节点（数据指针）
                                                  ↑
                                          叶子之间用链表连接
```

### 1.2 B+ 树 vs B 树

| 维度 | B 树 | B+ 树 |
|------|------|--------|
| 数据存储位置 | 所有节点都存 | **只存在叶子** |
| 叶子节点 | 无序 | **有序链表** |
| 范围查询 | 需多次树遍历 | **叶子链表一次扫描** |
| 单值查询 | 较快 | 略慢（要多走一层） |
| 空间利用率 | 低 | 高（叶子连续存储） |

### 1.3 B+ 树为什么适合数据库

1. **矮胖**：每个节点存 N 个键 → 树高 3-4 层就能存百万行
2. **磁盘友好**：每次 IO 读一个节点（页），充分利用预读
3. **范围查询**：叶子链表 + 有序 → `WHERE id BETWEEN 1 AND 100` 极快
4. **排序友好**：索引天然有序，`ORDER BY` 不需额外排序

### 1.4 B+ 树的关键参数（InnoDB）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 页大小 | 16 KB | 每次 IO 读取 |
| 阶（fanout） | ~1200 | 每个节点最多指针数 |
| 树高 | 3-4 | 千万级数据 |

## 2. 代码示例

### 2.1 B+ 树简化实现

```python
from bisect import bisect_left
from typing import Optional

class BPlusTreeNode:
    def __init__(self, order: int = 4, is_leaf: bool = False):
        self.order = order
        self.is_leaf = is_leaf
        self.keys: list = []
        self.children: list = []    # 内部节点：子节点；叶子节点：数据指针
        self.next_leaf: Optional["BPlusTreeNode"] = None  # 叶子链表指针

    def __repr__(self):
        return f"Leaf={self.is_leaf} Keys={self.keys}"


class BPlusTree:
    """简化版 B+ 树（仅演示结构）"""

    def __init__(self, order: int = 4):
        self.root = BPlusTreeNode(order, is_leaf=True)
        self.order = order

    def search(self, key) -> Optional[any]:
        """O(log N) 查找"""
        node = self.root
        while not node.is_leaf:
            i = bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                i += 1
            node = node.children[i]
        i = bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            return node.children[i]  # 返回数据指针
        return None

    def range_query(self, low, high) -> list:
        """范围查询：找到 low，叶子链表向后扫"""
        node = self.root
        while not node.is_leaf:
            i = bisect_left(node.keys, low)
            node = node.children[i]
        results = []
        i = bisect_left(node.keys, low)
        while node:
            while i < len(node.keys):
                if node.keys[i] > high:
                    return results
                results.append(node.children[i])
                i += 1
            node = node.next_leaf
            i = 0
        return results
```

### 2.2 为什么 B+ 树适合范围查询

```python
# 假设有 100 万行，B+ 树高 3
# 范围查询 WHERE id BETWEEN 100 AND 200
# 1. 树查找定位到 id=100 的叶子 → 3 次 IO
# 2. 沿叶子链表向后扫到 id=200 → 顺序读，极快
# 总耗时：~5 ms（vs 全表扫描 ~500 ms）
```

## 3. dify 仓库源码解读

### 3.1 PostgreSQL 的 B+ 树索引

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**：

```python
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 主键 → B+ 树
    email: Mapped[str] = mapped_column(String(255), unique=True)   # 唯一索引 → B+ 树

    __table_args__ = (
        Index("idx_account_email_lower", text("lower(email)")),    # 函数索引（B+ 树）
    )
```

**解读**：
- PostgreSQL 所有索引默认都是 B+ 树
- `primary_key` 自动创建 B+ 树索引（聚簇）
- `unique=True` 也是 B+ 树（但非聚簇）
- 第 9 行：函数索引（`lower(email)`）也是 B+ 树——加速不区分大小写的邮箱查询

## 4. 关键要点总结

- B+ 树 = 多路平衡树 + 叶子链表
- 数据只在叶子节点，内部节点只存键和指针
- 范围查询极快（叶子链表顺序扫描）
- 树高 3-4 层，磁盘 IO 少
- PostgreSQL / MySQL InnoDB 默认使用 B+ 树

## 5. 练习题

### 练习 1：基础
在 PostgreSQL 中：`CREATE INDEX idx_users_email ON users(email)`，查看索引大小：`\\d users`。

### 练习 2：进阶
执行 `EXPLAIN ANALYZE SELECT * FROM messages WHERE conversation_id = 'xxx'`，确认使用 B+ 树索引（Bitmap Heap Scan / Index Scan）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/account.py`
- CMU 15-721 课程：https://15445.courses.cs.cmu.edu
- 《数据库系统概念》第 14 章：索引结构

---

**文档版本**：v1.0
**最后更新**：2026-07-13