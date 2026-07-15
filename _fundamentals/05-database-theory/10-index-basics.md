# 3.1 索引的本质：数据结构的封装

> 索引是数据库性能的核心。理解索引的本质，能让你设计出高效的查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解索引的本质是有序数据结构 + 指针
- 区分主键索引、二级索引、唯一索引
- 知道索引的代价（写入变慢、占用空间）
- 在 dify 中识别索引设计

## 📚 前置知识

- 数据结构（[B 树 / B+ 树](./11-b-plus-tree.md)，亦见 [01-data-structures/10-b-tree](../01-data-structures/10-b-tree.md)）
- SQL WHERE、JOIN

## 1. 核心概念

### 1.1 索引的本质

```
表（无序）         索引（有序）        指针
[id=3]      ──>   [1 → 2 → 3]   ──>  [磁盘地址]
[id=1]           ...
[id=2]
```

**索引 = 有序数据结构 + 指向原数据的指针**（InnoDB 主键索引见 [B+ 树](./11-b-plus-tree.md)、[聚簇索引](./12-clustered-index.md)）

### 1.2 索引的核心作用

1. **加速查询**：从 O(N) 全表扫描 → O(log N) 树查找
2. **保证唯一**：唯一索引
3. **加速排序**：索引本身有序，无需额外排序
4. **加速 JOIN**：被 JOIN 列建索引

### 1.3 索引的代价

| 维度 | 影响 |
|------|------|
| 写入性能 | 下降（INSERT/UPDATE 需维护索引） |
| 存储空间 | 占用（通常是数据的 30-50%） |
| 查询优化器 | 更多索引 → 优化器选择困难 |

### 1.4 何时不该建索引

- 频繁更新的列
- 区分度低的列（性别、状态）
- 小表（<1000 行）
- 大字段（TEXT）

## 2. 代码示例

### 2.1 简单索引模拟

```python
from bisect import bisect_left
from typing import Optional

class SimpleIndex:
    """索引 = (key → row_id) 的有序映射"""

    def __init__(self):
        self.keys: list = []            # 有序键
        self.row_ids: list = []         # 对应行 ID

    def insert(self, key, row_id) -> None:
        pos = bisect_left(self.keys, key)
        self.keys.insert(pos, key)
        self.row_ids.insert(pos, row_id)

    def find(self, key) -> Optional[int]:
        """O(log N) 查找"""
        pos = bisect_left(self.keys, key)
        if pos < len(self.keys) and self.keys[pos] == key:
            return self.row_ids[pos]
        return None


class TableWithoutIndex:
    """无索引表：必须全表扫描"""

    def __init__(self):
        self.rows: list[dict] = []

    def find_by_name(self, name) -> Optional[dict]:
        for row in self.rows:                # O(N)
            if row["name"] == name:
                return row
        return None


class TableWithIndex:
    """有索引表：O(log N) 查找"""

    def __init__(self):
        self.rows: list[dict] = []
        self.name_index = SimpleIndex()       # 索引

    def insert(self, row) -> None:
        self.rows.append(row)
        self.name_index.insert(row["name"], len(self.rows) - 1)

    def find_by_name(self, name) -> Optional[dict]:
        row_id = self.name_index.find(name)   # O(log N)
        return self.rows[row_id] if row_id is not None else None
```

### 2.2 索引代价演示

```python
import time

# 假设有 100 万行
# 无索引：find_by_id = O(N) → ~1ms
# 有索引：find_by_id = O(log N) → ~0.001ms

# 但插入时：
# 无索引：O(1)
# 有索引：O(log N) + 维护成本
```

## 3. dify 仓库源码解读

### 3.1 dify 的索引设计

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**（行 1-40）：

```python
class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)   # 主键索引（自动）
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)  # 二级索引
    app_id: Mapped[str] = mapped_column(String(36), index=True)     # 二级索引
    created_at: Mapped[int] = mapped_column(BigInteger, index=True) # 二级索引
```

**解读**：
- 第 4 行：`primary_key=True` 自动创建主键索引（聚簇索引）
- 第 5-7 行：`index=True` 显式创建二级索引——加速按 conversation_id / app_id 查询
- **设计意图**：消息表的查询模式是"按会话查历史消息"，所以 `conversation_id` 必须索引

### 3.2 联合索引示例

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy import Index

class DocumentSegment(Base):
    __tablename__ = "document_segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(36))
    document_id: Mapped[str] = mapped_column(String(36))
    position: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        Index("idx_dataset_document_position", "dataset_id", "document_id", "position"),
    )
```

**解读**：
- 第 9 行：`__table_args__` 定义**联合索引**
- 索引顺序：dataset_id → document_id → position
- **最左前缀**：可加速 `WHERE dataset_id=?`、`WHERE dataset_id=? AND document_id=?`、`WHERE dataset_id=? AND document_id=? AND position=?`

## 4. 关键要点总结

- 索引 = 有序数据结构 + 指针，加速读但减慢写
- 主键自动有索引，二级索引需显式声明
- 低区分度列、小表、大字段不适合建索引
- dify 在高频查询字段（conversation_id、app_id）上建索引

## 5. 练习题

### 练习 1：基础
列出你的数据库中所有表的索引：`SELECT * FROM pg_indexes WHERE schemaname='public'`

### 练习 2：进阶
阅读 `dify/api/models/dataset.py`，找出 Document 表的所有索引字段。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/models/dataset.py`
- 《高性能 MySQL》第 5 章：创建高性能索引

---

**文档版本**：v1.0
**最后更新**：2026-07-13