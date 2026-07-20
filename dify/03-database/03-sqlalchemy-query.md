# 3.3.2 SQLAlchemy 2.x 查询 API：select() 表达式风格

> 用统一的 select()、where() 和 Session 执行 API 构建可组合、可类型检查的 ORM 查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 构造 select、where、order_by、limit 查询
- 区分 scalar、scalars、execute 的返回形状
- 组合动态过滤与聚合子查询
- 读懂 dify 的 SQLAlchemy 2.x 查询链

## 📚 前置知识

- [3.3.1 声明式映射](./02-sqlalchemy-mapping.md)
- [3.1.2 多表查询](../../_common/21-sql/02-sql-join.md)
- Session 生命周期（详见 [Session 与 with](./07-sqlalchemy-session.md)）

## 1. 核心概念

### 1.1 Statement 与执行分离

`select(User)` 只创建语句对象，不访问数据库；`session.execute(stmt)` 才执行。语句对象可组合：每次 `.where()`、`.order_by()` 返回新语句，适合按请求参数逐步追加条件。

### 1.2 选择正确的结果 API

| API | 结果 |
|---|---|
| `execute(stmt)` | Row 序列，适合多列/多实体 |
| `scalars(stmt)` | 每行第一列，适合单实体列表 |
| `scalar(stmt)` | 首行首列，适合单对象/聚合 |
| `scalar_one()` | 必须恰好一行，否则异常 |
| `scalar_one_or_none()` | 零或一行，多行异常 |

### 1.3 动态查询

不要拼接 SQL 值。先创建基础 `stmt`，再依据可选参数追加表达式；空 `IN` 列表可提前返回，减少无用查询并明确语义。

## 2. 代码示例

### 2.1 组合可选过滤和稳定分页

```python
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

class Base(DeclarativeBase):
    pass

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(100))

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
with Session(engine) as session:
    session.add_all([
        Task(status="open", title="A"),
        Task(status="done", title="B"),
    ])
    session.commit()

    status: str | None = "open"
    stmt = select(Task)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.order_by(Task.id.asc()).limit(20)
    tasks = session.scalars(stmt).all()
    print([task.title for task in tasks])
```

**说明**：语句构建和执行分离；因为只选择一个 ORM 实体，使用 `session.scalars` 得到 `Task` 对象序列。

## 3. 关键要点总结

- `select()` 构建语句，Session 负责执行
- 单实体列表用 `scalars`，多列结果用 `execute`
- 查询对象可按条件逐步组合
- 结果 API 应与预期基数匹配

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
