# 3.5 Hash 索引

> Hash 索引是另一种索引结构，适合**精确等值查询**，但不支持范围查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Hash 索引的原理（哈希表）
- 知道 Hash 索引 vs B+ 树的适用场景
- 识别 PostgreSQL Hash 索引的限制
- 理解自适应哈希索引（InnoDB）

## 📚 前置知识

- 11-b-plus-tree.md
- 哈希表数据结构

## 1. 核心概念

### 1.1 Hash 索引的原理

```
键 → 哈希函数 → 桶号 → 定位行

key="alice"  → hash() → 3  → bucket[3] → [row_id=1, row_id=42, ...]
key="bob"    → hash() → 7  → bucket[7] → [row_id=2]
```

### 1.2 Hash 索引 vs B+ 树

| 维度 | Hash 索引 | B+ 树 |
|------|----------|-------|
| 等值查询 | O(1) | O(log N) |
| 范围查询 | ❌ 不支持 | ✅ 极快 |
| 排序 | ❌ 不支持 | ✅ 天然有序 |
| 前缀匹配 | ❌ | ✅ |
| 空间 | 通常更小 | 较大 |
| 哈希冲突 | 链表 / 开放寻址 | 不存在 |

### 1.3 PostgreSQL Hash 索引

**曾经**：PostgreSQL Hash 索引**不写 WAL**，崩溃后不可恢复，官方不推荐。
**PG 10+**：Hash 索引已写 WAL，但**仍有限制**：
- 不支持多列 hash 索引（只能用单列）
- 范围查询、ORDER BY 不能用
- 实际场景几乎不用

**结论**：PostgreSQL **默认用 B+ 树**，Hash 索引只在内存数据库（如 Memcached）有用。

### 1.4 InnoDB 自适应哈希索引

InnoDB 自动为**热点 B+ 树页**建立内存哈希索引：
- 自动开启（`innodb_adaptive_hash_index`）
- 不可手动控制
- 等值查询特别多时自动启用

## 2. 代码示例

### 2.1 哈希索引简化实现

```python
class HashIndex:
    """简单的哈希索引"""

    def __init__(self, bucket_size: int = 16):
        self.buckets: list[list[tuple]] = [[] for _ in range(bucket_size)]
        self.bucket_size = bucket_size

    def _hash(self, key) -> int:
        return hash(key) % self.bucket_size

    def insert(self, key, row_id: int) -> None:
        bucket = self.buckets[self._hash(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, row_id)
                return
        bucket.append((key, row_id))

    def find(self, key) -> list[int]:
        """O(1) 等值查找"""
        return [row_id for k, row_id in self.buckets[self._hash(key)] if k == key]

    def range_query(self, low, high):
        """❌ Hash 索引不支持范围查询——必须全表扫描"""
        return None


idx = HashIndex()
idx.insert("alice", 1)
idx.insert("alice", 42)
idx.insert("bob", 2)
print(idx.find("alice"))  # [1, 42]
```

### 2.2 对比性能

```python
import time

# 假设 100 万行数据

# B+ 树：等值查询
#   树高 3-4 → ~3-4 次磁盘 IO → ~3 ms

# Hash 索引：等值查询
#   1 次磁盘 IO（如果有缓冲则内存命中）→ ~0.1 ms

# B+ 树：范围查询
#   定位起点 + 叶子链表顺序扫描 → ~5 ms

# Hash 索引：范围查询
#   全表扫描 → ~500 ms（不可用！）
```

## 3. dify 仓库源码解读

### 3.1 PostgreSQL 默认 B+ 树（无 Hash 索引）

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**：

```python
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # B+ 树
    email: Mapped[str] = mapped_column(String(255), unique=True)   # B+ 树

    # 注意：SQLAlchemy 的 Index 默认就是 B+ 树
    __table_args__ = (
        Index("idx_account_created_at", "created_at"),            # B+ 树
    )
```

**解读**：
- dify 的所有 PostgreSQL 索引都是 B+ 树（默认）
- **不显式使用 Hash 索引**——Hash 索引在 PG 中应用场景有限
- dify/ruoyi 中无直接 Hash 索引示例

## 4. 关键要点总结

- Hash 索引只适合精确等值查询（O(1)）
- 不支持范围查询、排序、前缀匹配
- PostgreSQL Hash 索引 PG 10+ 已写 WAL，但限制多
- 实际生产环境几乎只用 B+ 树
- InnoDB 自适应哈希索引是自动的，等值查询热点数据时启用

## 5. 练习题

### 练习 1：基础
为什么 PostgreSQL 官方推荐 B+ 树而不是 Hash 索引？

### 练习 2：进阶
调研：Memcached、Redis 是否使用 Hash 索引？它们与数据库的 Hash 索引有什么区别？

## 6. 参考资料

- PostgreSQL Hash 索引：https://www.postgresql.org/docs/current/indexes-types.html
- dify/ruoyi 中无直接 Hash 索引示例
- 《数据库系统概念》第 14 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13