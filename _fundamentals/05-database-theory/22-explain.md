# 5.1 EXPLAIN 执行计划

> EXPLAIN 是 SQL 性能调优的核心工具，能告诉你数据库"怎么执行"你的查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 读懂 PostgreSQL/MySQL 的 EXPLAIN 输出
- 识别常见的执行算子（Seq Scan、Index Scan、Hash Join）
- 判断查询是否走了索引
- 定位慢查询瓶颈

## 📚 前置知识

- 11-b-plus-tree.md
- 索引相关（10-15）

## 1. 核心概念

### 1.1 EXPLAIN 是什么？

EXPLAIN 返回数据库优化器选择的**执行计划**——不是实际执行，只是"计划"。

```sql
EXPLAIN SELECT * FROM users WHERE age > 25;
```

### 1.2 关键算子

| 算子 | 含义 | 性能 |
|------|------|------|
| Seq Scan | 全表扫描 | ⚠️ 大表时很慢 |
| Index Scan | 索引扫描（读索引+回表） | ✅ 快 |
| Index Only Scan | 仅索引扫描（覆盖索引） | ✅✅ 最快 |
| Bitmap Index Scan | 位图索引扫描 | ✅ 适合多条件 |
| Hash Join | 哈希联接 | ✅ 等值联接 |
| Nested Loop | 嵌套循环 | ✅ 小表/索引联接 |
| Sort | 排序 | ⚠️ 大数据量慢 |

### 1.3 EXPLAIN ANALYZE

不仅给计划，还**真实执行**并返回实际耗时：
```sql
EXPLAIN ANALYZE SELECT * FROM users WHERE age > 25;
```

### 1.4 关键指标

- **cost**：估算代价（越小越好）
- **rows**：估算行数
- **actual time**：实际耗时（ANALYZE 才有）
- **loops**：循环次数

## 2. 代码示例

### 2.1 PostgreSQL EXPLAIN 解读

```sql
EXPLAIN ANALYZE
SELECT m.id, m.query, m.answer
FROM messages m
WHERE m.conversation_id = 'abc-123'
ORDER BY m.created_at DESC
LIMIT 20;
```

**输出示例**：
```
Limit (cost=10.5..15.0 rows=20 width=100)
  -> Sort (cost=10.5..12.0 rows=100 width=100)
        Sort Key: created_at DESC
        -> Index Scan using idx_conversation_created on messages m
              Index Cond: (conversation_id = 'abc-123')
              (actual time=0.5..2.1 rows=20 loops=1)
```

**解读**：
- 最内层：Index Scan 用了 `idx_conversation_created` 索引 ✅
- 上面一层：Sort 按 created_at 排序
- 最外层：Limit 取前 20 条
- **整体评估**：走了索引，性能好

### 2.2 反例：全表扫描

```sql
EXPLAIN ANALYZE
SELECT * FROM messages WHERE content LIKE '%dify%';
```

**输出**：
```
Seq Scan on messages  (cost=0.00..15000.00 rows=100 width=200)
  Filter: (content ~~ '%dify%')
  Rows Removed by Filter: 999900
  (actual time=0.1..250 ms rows=100 loops=1)
```

**问题**：
- 全表扫描（Seq Scan）
- Filter 过滤掉 99.99% 行
- 耗时 250ms（慢！）

**优化**：用全文索引（GIN）替代 LIKE。

### 2.3 Python 模拟成本估算

```python
def estimate_cost(table_size: int, index_used: bool, rows_returned: int) -> float:
    """简化版的代价估算"""
    seq_scan_cost = table_size  # 全表扫描：O(N)
    if index_used:
        index_cost = 3 + rows_returned  # 索引扫描：O(log N + K)
        return index_cost
    return seq_scan_cost


print(estimate_cost(1000000, True, 100))    # 103
print(estimate_cost(1000000, False, 100))   # 1000000
```

## 3. dify 仓库源码解读

### 3.1 dify 的慢查询：消息表查询

**示例场景**：dify 消息表查询

```python
# dify 的典型慢查询（用于演示）
# api/services/conversation_service.py
def list_conversation_messages(conversation_id: str, page: int = 1) -> list[Message]:
    """列出会话消息——已优化"""
    with Session(db.engine) as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(20)
            .offset((page - 1) * 20)
        )
        return list(session.scalars(stmt).all())
```

**配套索引**（`models/model.py`）：

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
- 联合索引 `(conversation_id, created_at)` 同时加速 WHERE 和 ORDER BY
- **EXPLAIN 应该看到**：`Index Scan using idx_conversation_created`，无 Sort 算子

### 3.2 ruoyi 的 MySQL EXPLAIN

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/resources/mapper/system/AdminUserMapper.xml`
**核心代码**：

```xml
<select id="selectByUsername" resultType="AdminUserDO">
    SELECT * FROM system_users WHERE username = #{username} AND deleted = 0
</select>
```

**配套索引**：

```sql
CREATE INDEX idx_username ON system_users(username);
-- EXPLAIN SELECT * FROM system_users WHERE username = 'admin';
-- type: const（最高效）
```

**解读**：
- MySQL `EXPLAIN` 输出 type 字段：`const > eq_ref > ref > range > index > ALL`
- `const` 表示主键或唯一索引等值查询——最优

## 4. 关键要点总结

- EXPLAIN 看执行计划，EXPLAIN ANALYZE 真实执行
- Seq Scan 全表扫描 → 性能差，应走索引
- Index Scan / Index Only Scan → 性能好
- 关键算子：Sort、Nested Loop、Hash Join
- dify 的消息查询用联合索引优化

## 5. 练习题

### 练习 1：基础
执行 `EXPLAIN SELECT * FROM messages LIMIT 10`，判断是否走索引。

### 练习 2：进阶
为一个慢查询（`WHERE content LIKE '%x%'`）设计优化方案。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- PostgreSQL EXPLAIN：https://www.postgresql.org/docs/current/using-explain.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13