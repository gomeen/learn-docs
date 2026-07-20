# 3.3.6 SQLAlchemy 原生 SQL 与混合查询

> 在表达式 API 不足或数据库特性更适合 SQL 时，安全嵌入参数化原生 SQL并保留会话边界。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 text() 与命名参数执行原生 SQL
- 读取 Row 与 `_mapping` 结果
- 判断何时应使用原生 SQL
- 理解方言 SQL、动态结构与注入边界

## 📚 前置知识

- [3.3.2 select() 表达式风格](./03-sqlalchemy-query.md)
- [3.1.6 PostgreSQL 特有功能](./01-postgresql-features.md)

## 1. 核心概念

### 1.1 为什么仍需要原生 SQL

复杂报表、窗口函数、数据库专有语法或大批量迁移有时用 SQL 更清楚。原生 SQL 仍应复用 Session、连接和事务（Session 边界详见 [Session 与 with](./07-sqlalchemy-session.md)；事务详见 [事务与隔离级别](../../_common/21-sql/04-sql-transaction.md)）。

### 1.2 值参数与结构参数

`text("... WHERE id=:id")` 可绑定值。表名、列名和排序方向不能当普通值参数；动态结构只能从固定白名单映射（禁止拼接用户输入，详见 [SQL 注入](../../_common/05-web-security/03-sql-injection.md)）。

### 1.3 混合查询

可用表达式 API 处理大部分条件，只在局部用 `func`、方言运算符或 `text`。原生结果是 Row，可用 `row._mapping` 或具名列访问。

## 2. 代码示例

### 2.1 参数化执行聚合 SQL

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

engine = create_engine("sqlite://")
with engine.begin() as connection:
    connection.execute(text("CREATE TABLE events (tenant_id TEXT, kind TEXT)"))
    connection.execute(
        text("INSERT INTO events VALUES (:tenant, :kind)"),
        [
            {"tenant": "t1", "kind": "run"},
            {"tenant": "t1", "kind": "run"},
            {"tenant": "t1", "kind": "error"},
        ],
    )

sql = text("""
    SELECT kind, COUNT(*) AS total
    FROM events
    WHERE tenant_id = :tenant_id
    GROUP BY kind
    ORDER BY total DESC
""")
with Session(engine) as session:
    rows = session.execute(sql, {"tenant_id": "t1"}).all()
    result = [dict(row._mapping) for row in rows]
    print(result)
```

**说明**：值通过命名参数绑定，原生 SQL 仍在 Session 中执行，结果通过 RowMapping 转成字典。

## 3. 关键要点总结

- 原生 SQL 适合专有能力和复杂报表，但不是默认选择
- 所有值必须参数绑定
- 动态表名和列名只能来自白名单
- 原生 SQL 仍服从 Session 和事务边界

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
