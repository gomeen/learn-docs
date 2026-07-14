# 3.4 联合索引与最左前缀

> 联合索引（Composite Index）是多列组合的索引。最左前缀原则是设计联合索引的核心准则。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解联合索引的内部结构（按列顺序排序）
- 掌握最左前缀原则
- 知道索引列顺序对性能的影响
- 在 dify 中设计合理的联合索引

## 📚 前置知识

- 11-b-plus-tree.md
- 12-clustered-index.md

## 1. 核心概念

### 1.1 联合索引的结构

```
索引：idx_a_b_c(a, b, c)

B+ 树按 (a, b, c) 元组排序：

[(1, 1, 1) → row]  [(1, 1, 2) → row]  [(1, 2, 1) → row]  [(2, 1, 1) → row]  ...

先按 a 排序，a 相同再按 b，b 相同再按 c
```

### 1.2 最左前缀原则

**联合索引 `idx(a, b, c)` 可用于以下查询**：
- `WHERE a = ?` ✅
- `WHERE a = ? AND b = ?` ✅
- `WHERE a = ? AND b = ? AND c = ?` ✅
- `WHERE a = ? AND c = ?` ⚠️（只用 a 部分）
- `WHERE b = ?` ❌（不命中）
- `WHERE c = ?` ❌（不命中）

### 1.3 列顺序的选择

**高区分度列放前面**（如 user_id），**常用查询列放前面**。

**举例**：订单查询通常按 `user_id` 过滤，再按 `created_at` 排序：
- 索引 `idx(user_id, created_at)` → 高效
- 索引 `idx(created_at, user_id)` → 低效（无法走索引）

### 1.4 索引下推（Index Condition Pushdown, ICP）

MySQL 5.6+ / PostgreSQL 都支持：
- 在存储引擎层就用 WHERE 过滤，减少回表次数。

```sql
SELECT * FROM users WHERE a=1 AND b LIKE '%x%';
-- ICP：直接在索引层过滤 b LIKE '%x%'，不满足的不回表
```

## 2. 代码示例

### 2.1 模拟联合索引

```python
from bisect import bisect_left

class CompositeIndex:
    """联合索引：按元组排序"""

    def __init__(self, columns: list[str]):
        self.columns = columns
        self.entries: list[tuple] = []  # [(key_tuple, row_id), ...]

    def insert(self, row: dict, row_id: int) -> None:
        key = tuple(row[col] for col in self.columns)
        entry = (key, row_id)
        i = bisect_left([e[0] for e in self.entries], key)
        self.entries.insert(i, entry)

    def find(self, **conditions) -> list[int]:
        """按最左前缀匹配"""
        # 构造前缀 key
        prefix = []
        for col in self.columns:
            if col in conditions:
                prefix.append(conditions[col])
            else:
                break  # 中断——最左前缀
        if not prefix:
            return [e[1] for e in self.entries]  # 全表扫描
        prefix = tuple(prefix)
        results = []
        for key, row_id in self.entries:
            if key[:len(prefix)] == prefix:
                results.append(row_id)
            elif key > prefix:
                break
        return results


idx = CompositeIndex(["a", "b", "c"])
idx.insert({"a": 1, "b": 1, "c": 1}, row_id=10)
idx.insert({"a": 1, "b": 1, "c": 2}, row_id=11)
idx.insert({"a": 1, "b": 2, "c": 1}, row_id=12)
idx.insert({"a": 2, "b": 1, "c": 1}, row_id=13)

print(idx.find(a=1))           # [10, 11, 12]——只用 a
print(idx.find(a=1, b=1))      # [10, 11]——用 (a, b)
print(idx.find(b=1))           # []——不命中最左前缀
```

### 2.2 列顺序的反例

```sql
-- 表：orders(id, user_id, created_at, status, amount)

-- ✅ 推荐：常用过滤列在前
CREATE INDEX idx_user_created ON orders(user_id, created_at);
-- 优化：WHERE user_id=? AND created_at BETWEEN ? AND ?
-- 优化：WHERE user_id=? ORDER BY created_at DESC

-- ❌ 不推荐：低区分度列在前
CREATE INDEX idx_status_user ON orders(status, user_id);
-- 问题：status 只有 3-5 个值，几乎全表扫描
```

## 3. dify 仓库源码解读

### 3.1 dify 的联合索引设计

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

class DocumentSegment(Base):
    __tablename__ = "document_segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(36))
    document_id: Mapped[str] = mapped_column(String(36))
    position: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index(
            "idx_dataset_document_position",
            "dataset_id", "document_id", "position",
        ),
    )
```

**解读**：
- 联合索引顺序：`dataset_id` → `document_id` → `position`
- **最左前缀适用**：
  - `WHERE dataset_id=?` ✅
  - `WHERE dataset_id=? AND document_id=?` ✅
  - `WHERE dataset_id=? AND document_id=? AND position=?` ✅
- **设计意图**：RAG 检索时按"知识库 → 文档 → 段落顺序"读取，是常见访问模式

### 3.2 dify 的多列排序索引

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**：

```python
class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[int] = mapped_column(BigInteger)

    __table_args__ = (
        Index("idx_conversation_created", "conversation_id", "created_at"),
    )
```

**解读**：
- `(conversation_id, created_at)` 联合索引
- **优化查询**：`SELECT * FROM messages WHERE conversation_id='x' ORDER BY created_at`
- 索引天然有序，ORDER BY 不需额外排序（避免 filesort）

## 4. 关键要点总结

- 联合索引按列顺序排序，必须满足最左前缀
- 高区分度列、常用查询列放在前面
- 索引列顺序错了，可能完全用不上
- 索引下推（ICP）进一步优化回表次数
- dify 的消息、段落表都设计了合理的联合索引

## 5. 练习题

### 练习 1：基础
联合索引 `idx(a, b, c)`，以下查询哪些能用？
- `WHERE a=1`
- `WHERE b=1`
- `WHERE a=1 AND c=1`
- `WHERE a=1 AND b=1 AND c=1`

### 练习 2：进阶
阅读 `dify/api/models/dataset.py`，找出所有联合索引，分析列顺序是否合理。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/dataset.py`
- MySQL ICP：https://dev.mysql.com/doc/refman/8.0/en/index-condition-pushdown-optimization.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13