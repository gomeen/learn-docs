# 3.3 聚簇索引 vs 非聚簇索引

> 聚簇索引决定了数据的物理存储顺序。InnoDB 和 PostgreSQL 的聚簇索引实现有显著差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解聚簇索引 vs 非聚簇索引的本质区别
- 知道 InnoDB 和 PostgreSQL 的聚簇索引实现差异
- 理解"回表"（Bookmark Lookup）的概念
- 在 dify 中识别聚簇/非聚簇索引设计

## 📚 前置知识

- 11-b-plus-tree.md
- 10-index-basics.md

## 1. 核心概念

### 1.1 聚簇索引（Clustered Index）

**数据行的物理存储顺序与索引顺序一致**。

```
聚簇索引（InnoDB）：
叶子的"数据指针" = 整行数据

[1 → 完整行]  [2 → 完整行]  [3 → 完整行]  ...
   ↑            ↑            ↑
 物理相邻    物理相邻     物理相邻
```

### 1.2 非聚簇索引（Secondary Index）

**索引叶子存的是"主键"，不是数据**。

```
非聚簇索引（InnoDB）：
叶子的"数据指针" = 主键值

[name=Bob → id=2]  [name=Alice → id=1]  ...
                          ↓
                     聚簇索引查 id=1
                     （回表）
```

### 1.3 InnoDB vs PostgreSQL 对比

| 数据库 | 聚簇索引数量 | 默认聚簇键 |
|--------|------------|----------|
| InnoDB | 1 个 | 主键（无主键则用隐藏 ROWID） |
| PostgreSQL | 0 个（堆表） | 无聚簇（数据按堆存储） |

**InnoDB**：表本身就是聚簇索引（B+ 树），数据即索引。
**PostgreSQL**：数据按堆（Heap）存储，索引都是非聚簇。

### 1.4 回表（Bookmark Lookup）

当查询用非聚簇索引，但需要非索引列时：
1. 在非聚簇索引中找到主键
2. 用主键去聚簇索引中查完整行
3. **这个二次查询叫"回表"**

**优化**：覆盖索引（Covering Index）——索引包含所有查询列，避免回表。

## 2. 代码示例

### 2.1 模拟聚簇 vs 非聚簇

```python
class InnoDBTable:
    """模拟 InnoDB：表本身就是聚簇索引"""

    def __init__(self):
        # 主键索引 = 聚簇（B+ 树），叶子存完整行
        self.primary_index: dict[int, dict] = {}  # id → 完整行

    def insert(self, row: dict) -> None:
        self.primary_index[row["id"]] = row

    def find_by_id(self, id_) -> dict:
        """聚簇索引查找：O(log N)"""
        return self.primary_index.get(id_)

    def find_by_name(self, name) -> dict:
        """二级索引需要先建辅助索引"""
        # 1. 在非聚簇索引 (name → id) 找到 id
        id_ = self.name_index.get(name)
        if id_ is None:
            return None
        # 2. 用 id 在聚簇索引找完整行（回表）
        return self.primary_index[id_]

    def add_secondary_index(self, column: str) -> None:
        self.name_index: dict = {
            row[column]: id_ for id_, row in self.primary_index.items()
        }


class PostgreSQLTable:
    """模拟 PostgreSQL：堆表 + 独立索引"""

    def __init__(self):
        # 数据按插入顺序存储（堆）
        self.heap: list[dict] = []

    def find_by_id(self, id_) -> dict:
        for row in self.heap:
            if row["id"] == id_:
                return row
        return None
```

### 2.2 覆盖索引优化

```sql
-- ❌ 需要回表
SELECT name, age FROM users WHERE email = 'alice@x.com';
-- 1. email 索引找到 id
-- 2. 回表取 name, age

-- ✅ 覆盖索引（索引包含所有查询列）
CREATE INDEX idx_users_email_name_age ON users(email, name, age);
SELECT name, age FROM users WHERE email = 'alice@x.com';
-- 直接在索引中拿到所有列，无需回表
```

## 3. dify 仓库源码解读

### 3.1 PostgreSQL 的"非聚簇"索引

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**（行 1-30）：

```python
class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    app_id: Mapped[str] = mapped_column(String(36), index=True)
    query: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index("idx_conversation_created", "conversation_id", "created_at"),
    )
```

**解读**：
- PostgreSQL 中**所有索引都是非聚簇**（数据按堆存储）
- 第 10 行：联合索引 `idx_conversation_created` 加速"按会话查历史消息并按时间排序"
- **设计意图**：因为 PG 数据和索引分离，更新非索引列时不用重建索引

## 4. 关键要点总结

- 聚簇索引：数据行的物理顺序与索引一致（InnoDB 表即索引）
- 非聚簇索引：叶子存主键（InnoDB）或行指针（PG）
- PostgreSQL 是堆表，所有索引都是非聚簇
- 回表：非聚簇索引找到主键后，再去聚簇索引/堆取数据
- 覆盖索引：避免回表的优化手段

## 5. 练习题

### 练习 1：基础
在 PostgreSQL 中，`SELECT * FROM messages WHERE conversation_id='x'` 是否会回表？

### 练习 2：进阶
为 `SELECT conversation_id, created_at FROM messages WHERE conversation_id='x'` 设计覆盖索引。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- MySQL InnoDB 聚簇索引：https://dev.mysql.com/doc/refman/8.0/en/innodb-index-types.html
- 《高性能 MySQL》第 5 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13