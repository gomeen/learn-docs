# 3.3.2 SQLAlchemy 2.x 查询 API：select() 表达式风格

> 用统一的 select()、where() 和 Session 执行 API 构建可组合、可类型检查的 ORM 查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 构造 select、where、order_by、limit 查询
- 区分 scalar、scalars、execute 的返回形状
- 组合动态过滤与聚合子查询
- 读懂 dify 的 SQLAlchemy 2.x 查询链

## 📚 前置知识

- [3.3.1 声明式映射](./12-sqlalchemy-mapping.md)
- [3.1.2 多表查询](./02-sql-join.md)

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

## 3. dify 仓库源码解读

### 3.1 基础作用域与动态 ID 过滤

**文件位置**：`/Users/xu/code/github/dify/api/services/conversation_service.py`  
**核心代码**（行 50-68）：

```python

        stmt = select(Conversation).where(
            Conversation.is_deleted == False,
            Conversation.app_id == app_model.id,
            Conversation.from_source == ("api" if isinstance(user, EndUser) else "console"),
            Conversation.from_end_user_id == (user.id if isinstance(user, EndUser) else None),
            Conversation.from_account_id == (user.id if isinstance(user, Account) else None),
            or_(Conversation.invoke_from.is_(None), Conversation.invoke_from == invoke_from.value),
        )
        # Check if include_ids is not None to apply filter
        if include_ids is not None:
            if len(include_ids) == 0:
                # If include_ids is empty, return empty result
                return InfiniteScrollPagination(data=[], limit=limit, has_more=False)
            stmt = stmt.where(Conversation.id.in_(include_ids))
        # Check if exclude_ids is not None to apply filter
        if exclude_ids is not None:
            if len(exclude_ids) > 0:
                stmt = stmt.where(~Conversation.id.in_(exclude_ids))
```

**解读**：
- 基础语句一次写出软删除、应用和用户作用域。
- `include_ids` 与 `exclude_ids` 按请求参数动态追加。
- 对空 include 列表提前返回，避免不必要的 SQL。

### 3.2 归档批查询的表达式组合

**文件位置**：`/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`  
**核心代码**（行 454-482）：

```python
            stmt = (
                select(WorkflowRun)
                .where(
                    WorkflowRun.created_at < end_before,
                    WorkflowRun.status.in_(WorkflowExecutionStatus.ended_values()),
                )
                .order_by(WorkflowRun.created_at.asc(), WorkflowRun.id.asc())
                .limit(batch_size)
            )
            if run_types is not None:
                if not run_types:
                    return []
                stmt = stmt.where(WorkflowRun.type.in_(run_types))

            if start_from:
                stmt = stmt.where(WorkflowRun.created_at >= start_from)

            if tenant_ids:
                stmt = stmt.where(WorkflowRun.tenant_id.in_(tenant_ids))

            if tenant_prefixes:
                stmt = stmt.where(_tenant_prefix_condition(tenant_prefixes))

            if workflow_ids:
                stmt = stmt.where(WorkflowRun.workflow_id.in_(workflow_ids))

            if run_shard_index is not None and run_shard_total is not None:
                stmt = stmt.where((_workflow_run_id_shard_expr() % run_shard_total) == run_shard_index)

```

**解读**：
- `select(WorkflowRun)` 创建单实体查询，最终可用 `session.scalars`。
- 状态、时间、租户、工作流和分片条件逐步追加。
- 表达式避免手工拼值，也便于测试每个可选条件。

## 4. 关键要点总结

- `select()` 构建语句，Session 负责执行
- 单实体列表用 `scalars`，多列结果用 `execute`
- 查询对象可按条件逐步组合
- 结果 API 应与预期基数匹配

## 5. 练习题

### 练习 1：基础（必做）

用 `select()` 查询最近 10 个未完成任务。

### 练习 2：进阶

分别用 `execute` 和 `scalars` 选择 `(Task.id, Task.title)`，观察差异。

### 练习 3：挑战（选做）

为 dify 会话分页查询写一个可选名称过滤表达式。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/conversation_service.py`
- `/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`
- SQLAlchemy 2.0 ORM 快速入门：https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- SQLAlchemy ORM 查询指南：https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
