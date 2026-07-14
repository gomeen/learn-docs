# 5.2 SQL 优化技巧

> 写出高性能 SQL 是后端工程师的核心技能。本文档总结 12 个最实用的 SQL 优化技巧。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 12 个核心 SQL 优化技巧
- 识别常见的反模式（SELECT *、函数包裹列等）
- 在 dify/ruoyi 中应用优化技巧
- 量化优化的效果

## 📚 前置知识

- 22-explain.md
- 索引相关（10-15）

## 1. 核心概念

### 1.1 12 个核心优化技巧

1. **避免 SELECT ***
2. **WHERE 子句避免函数包裹列**
3. **小表驱动大表（JOIN 顺序）**
4. **用 UNION 替代 OR**
5. **批量插入替代循环单条**
6. **LIMIT 配合索引**
7. **覆盖索引避免回表**
8. **避免不必要的排序**
9. **合理使用 EXISTS 替代 IN**
10. **避免 % 前缀的 LIKE**
11. **分页优化（延迟关联 / 游标）**
12. **定期 ANALYZE / VACUUM**

### 1.2 反模式速查

| 反模式 | 优化 |
|--------|------|
| `SELECT *` | 只 SELECT 需要的列 |
| `WHERE YEAR(created_at)=2024` | `WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01'` |
| `WHERE LIKE '%x%'` | 全文索引 |
| 大 OFFSET 分页 | 游标分页 / 延迟关联 |
| `WHERE id IN (子查询)` | 改用 JOIN |
| 循环单条 INSERT | 批量 INSERT |
| 索引列上做运算 | 避免函数包裹 |

## 2. 代码示例

### 2.1 反例 vs 正例

```sql
-- ❌ 反例 1：SELECT *
SELECT * FROM users WHERE id = 1;
-- 问题：读不需要的列，浪费 IO

-- ✅ 正例：只 SELECT 需要的列
SELECT id, name FROM users WHERE id = 1;


-- ❌ 反例 2：函数包裹索引列
SELECT * FROM orders WHERE YEAR(created_at) = 2024;
-- 问题：YEAR() 让 created_at 上的索引失效

-- ✅ 正例：范围查询
SELECT * FROM orders
WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';


-- ❌ 反例 3：% 前缀 LIKE
SELECT * FROM articles WHERE content LIKE '%dify%';
-- 问题：全表扫描

-- ✅ 正例：全文索引
SELECT * FROM articles
WHERE to_tsvector('english', content) @@ to_tsquery('dify');
```

### 2.2 分页优化

```sql
-- ❌ 反例：大 OFFSET 分页（OFFSET 100000 时扫 10 万行）
SELECT * FROM messages WHERE conversation_id='x'
ORDER BY created_at DESC LIMIT 20 OFFSET 100000;

-- ✅ 正例 1：游标分页（Keyset Pagination）
SELECT * FROM messages WHERE conversation_id='x'
  AND created_at < :last_created_at
ORDER BY created_at DESC LIMIT 20;

-- ✅ 正例 2：延迟关联（先拿主键，再 JOIN）
SELECT m.* FROM messages m
INNER JOIN (
  SELECT id FROM messages WHERE conversation_id='x'
  ORDER BY created_at DESC LIMIT 20 OFFSET 100000
) AS t ON m.id = t.id;
```

### 2.3 批量插入 vs 循环

```python
# ❌ 反例：循环单条 INSERT（慢，1000 条需要 1000 次往返）
for user in users:
    session.execute(text("INSERT INTO users (name) VALUES (:n)"), {"n": user.name})

# ✅ 正例：批量 INSERT（1 次往返）
values = ",".join([f"('{u.name}')" for u in users])
session.execute(text(f"INSERT INTO users (name) VALUES {values}"))

# ✅✅ 最佳：使用 SQLAlchemy bulk_insert_mappings
session.bulk_insert_mappings(User, [{"name": u.name} for u in users])
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的批量操作

**文件位置**：`/Users/xu/code/github/dify/api/services/dataset_service.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy import insert
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.dataset import DocumentSegment

def batch_create_segments(segments: list[dict]) -> None:
    """批量创建文档段落——使用 bulk_insert_mappings"""
    with Session(db.engine) as session:
        with session.begin():
            # 批量插入，单次 SQL
            session.bulk_insert_mappings(DocumentSegment, segments)
            # 自动 commit
```

**解读**：
- `bulk_insert_mappings` 比逐条 `add()` 快 10x+
- 减少数据库往返次数
- **整体设计**：批量操作 + 事务，保证性能和数据一致性

### 3.2 ruoyi 的批量更新

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
**核心代码**：

```java
@Override
@Transactional
public void updateUserStatus(List<Long> ids, Integer status) {
    // 批量更新：单条 SQL 替代 N 条
    AdminUserDO update = new AdminUserDO();
    update.setStatus(status);
    userMapper.update(null, Wrappers.<AdminUserDO>lambdaUpdate()
        .set(AdminUserDO::getStatus, status)
        .in(AdminUserDO::getId, ids));
}
```

**解读**：
- MyBatis Plus 的 `lambdaUpdate().in()` 批量更新
- 生成 `UPDATE system_users SET status=? WHERE id IN (?, ?, ...)`
- 比循环 updateById 快 N 倍

## 4. 关键要点总结

- 避免 SELECT *、函数包裹列、% 前缀 LIKE
- 批量操作替代循环单条
- 分页用游标/延迟关联
- 覆盖索引避免回表
- dify 用 `bulk_insert_mappings`，ruoyi 用 `updateBatchById`

## 5. 练习题

### 练习 1：基础
把以下 SQL 优化：`SELECT * FROM users WHERE YEAR(created_at)=2024`

### 练习 2：进阶
阅读 ruoyi 的 `AdminUserServiceImpl.java`，找出所有批量操作的方法。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/dataset_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《高性能 MySQL》第 6 章：查询性能优化

---

**文档版本**：v1.0
**最后更新**：2026-07-13