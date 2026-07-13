# 3.3.6 SQLAlchemy 原生 SQL 与混合查询

> 在表达式 API 不足或数据库特性更适合 SQL 时，安全嵌入参数化原生 SQL并保留会话边界。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 text() 与命名参数执行原生 SQL
- 读取 Row 与 `_mapping` 结果
- 判断何时应使用原生 SQL
- 理解方言 SQL、动态结构与注入边界

## 📚 前置知识

- [3.3.2 select() 表达式风格](./13-sqlalchemy-query.md)
- [3.1.6 PostgreSQL 特有功能](./06-postgresql-features.md)

## 1. 核心概念

### 1.1 为什么仍需要原生 SQL

复杂报表、窗口函数、数据库专有语法或大批量迁移有时用 SQL 更清楚。原生 SQL 仍应复用 Session、连接和事务。

### 1.2 值参数与结构参数

`text("... WHERE id=:id")` 可绑定值。表名、列名和排序方向不能当普通值参数；动态结构只能从固定白名单映射。

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

## 3. dify 仓库源码解读

### 3.1 模型属性中的参数化原生查询

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`  
**核心代码**（行 584-602）：

```python

        with sessionmaker(db.engine).begin() as session:
            if api_provider_ids:
                existing_api_providers = [
                    str(api_provider.id)
                    for api_provider in session.execute(
                        text("SELECT id FROM tool_api_providers WHERE id IN :provider_ids"),
                        {"provider_ids": tuple(api_provider_ids)},
                    ).fetchall()
                ]
            else:
                existing_api_providers = []

        if builtin_provider_ids:
            # get the non-hardcoded builtin providers
            non_hardcoded_builtin_providers = [
                provider_id for provider_id in builtin_provider_ids if not provider_id.is_hardcoded
            ]
            if non_hardcoded_builtin_providers:
```

**解读**：
- 原生 SQL 用于 provider ID 集合查询。
- `:provider_ids` 是命名绑定参数。
- 后续插件检查仍由服务完成，体现混合查询。

### 3.2 报表查询保留命名参数

**文件位置**：`/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`  
**核心代码**（行 1360-1383）：

```python
        arg_dict: dict[str, Any] = {
            "tz": timezone,
            "tenant_id": tenant_id,
            "app_id": app_id,
            "triggered_from": triggered_from,
        }

        if start_date:
            sql_query += " AND created_at >= :start_date"
            arg_dict["start_date"] = start_date

        if end_date:
            sql_query += " AND created_at < :end_date"
            arg_dict["end_date"] = end_date

        sql_query += " GROUP BY date ORDER BY date"

        response_data = []
        with self._session_maker() as session:
            rs = session.execute(sa.text(sql_query), arg_dict)
            for row in rs:
                response_data.append({"date": str(row.date), "runs": row.runs})

        return cast(list[DailyRunsStats], response_data)
```

**解读**：
- SQL 结构按受控条件追加，实际值进入 `arg_dict`。
- `session.execute(sa.text(...), arg_dict)` 复用 Session。
- 具名列被转换成 DTO。

## 4. 关键要点总结

- 原生 SQL 适合专有能力和复杂报表，但不是默认选择
- 所有值必须参数绑定
- 动态表名和列名只能来自白名单
- 原生 SQL 仍服从 Session 和事务边界

## 5. 练习题

### 练习 1：基础（必做）

用 `text()` 写按状态分组的参数化 COUNT。

### 练习 2：进阶

说明表名不能用 `:table` 值参数，并用白名单选择。

### 练习 3：挑战（选做）

把 dify 原生日报 SQL 改写成表达式。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`
- SQLAlchemy text：https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
