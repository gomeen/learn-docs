# 3.3.4 SQLAlchemy 加载策略：lazy / joined / selectinload / subquery

> 按结果基数和访问路径选择关系加载策略，避免 N+1、笛卡尔膨胀和隐式数据库访问。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 lazy、joinedload、selectinload、subqueryload
- 识别 N+1 查询
- 根据关系基数选择加载策略
- 读懂 dify 的 lazy="raise" 与 selectinload

## 📚 前置知识

- [3.3.3 关系映射](./14-sqlalchemy-relations.md)
- [3.1.5 SQL 性能优化](./05-sql-performance.md)

## 1. 核心概念

### 1.1 四种策略

`lazy="select"` 首次访问关系时发 SQL，方便但容易 N+1。`joinedload` 在主查询 JOIN，适合多对一/一对一或小集合。`selectinload` 先查父行，再用 `WHERE child.fk IN (...)` 批量查子行，通常是一对多首选。`subqueryload` 使用父查询子查询加载，现代代码通常优先 selectinload。

### 1.2 行数膨胀

对两个大集合同时 joinedload，父行会按集合大小相乘。ORM 虽可去重对象，网络和数据库仍处理膨胀行。

### 1.3 禁止意外懒加载

`lazy="raise"` 在未预加载关系时直接报错，强迫调用方显式声明 I/O，适合大对象、异步代码和序列化路径。

## 2. 代码示例

### 2.1 用 selectinload 消除 N+1

```python
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, Session, mapped_column,
    relationship, selectinload,
)

class Base(DeclarativeBase):
    pass

class Parent(Base):
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    children: Mapped[list["Child"]] = relationship(lazy="raise")

class Child(Base):
    __tablename__ = "children"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    name: Mapped[str] = mapped_column(String(40))

engine = create_engine("sqlite://", echo=True)
Base.metadata.create_all(engine)
with Session(engine) as session:
    stmt = select(Parent).options(selectinload(Parent.children))
    parents = session.scalars(stmt).all()
    for parent in parents:
        print(parent.name, [child.name for child in parent.children])
```

**说明**：`lazy="raise"` 防止遗漏加载选项；`selectinload` 通常只需父查询与一条批量子查询。

## 3. dify 仓库源码解读

### 3.1 关系默认禁止隐式加载

**文件位置**：`/Users/xu/code/github/dify/api/models/workflow.py`  
**核心代码**（行 818-827）：

```python
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    exceptions_count: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"), nullable=True)

    pause: Mapped[Optional["WorkflowPause"]] = orm.relationship(
        lambda: WorkflowPause,
        primaryjoin=lambda: WorkflowRun.id == orm.foreign(WorkflowPause.workflow_run_id),
        uselist=False,
        # require explicit preloading.
        lazy="raise",
        back_populates="workflow_run",
```

**解读**：
- `pause` 是一对一关系，`uselist=False` 表明只期望一个对象。
- `lazy="raise"` 要求读取时显式预加载。
- 这样可避免 Session 关闭后触发隐式 SQL。

### 3.2 仓储显式使用 selectinload

**文件位置**：`/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`  
**核心代码**（行 1135-1153）：

```python
        with self._session_maker() as session:
            # Query workflow run with pause and state file
            stmt = select(WorkflowRun).options(selectinload(WorkflowRun.pause)).where(WorkflowRun.id == workflow_run_id)
            workflow_run = session.scalar(stmt)

            if workflow_run is None:
                raise ValueError(f"WorkflowRun not found: {workflow_run_id}")

            pause_model = workflow_run.pause
            if pause_model is None:
                return None
            pause_reason_models = self._get_reasons_by_pause_id(session, pause_model.id)
            pause_reasons = self._hydrate_pause_reasons(session, pause_reason_models)

        return _PrivateWorkflowPauseEntity(
            pause_model=pause_model,
            reason_models=pause_reason_models,
            pause_reasons=pause_reasons,
        )
```

**解读**：
- 查询通过 `.options(selectinload(...))` 声明关系 I/O。
- 主记录与暂停记录批量加载，不逐个访问触发 N+1。
- 离开 Session 后所需关系已准备好。

## 4. 关键要点总结

- lazy 方便但容易 N+1，joinedload 可能造成行膨胀
- selectinload 通常适合一对多批量加载
- subqueryload 是另一种分离加载策略
- `lazy="raise"` 可把隐藏 I/O 变成显式错误

## 5. 练习题

### 练习 1：基础（必做）

开启 SQL 日志构造 N+1，再用 selectinload 修复。

### 练习 2：进阶

比较 100 个父对象、每个 20 个子对象时 joinedload 与 selectinload。

### 练习 3：挑战（选做）

找到 dify 一个 `lazy="raise"` 关系，列出预加载入口。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/workflow.py`
- `/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`
- SQLAlchemy 关系加载：https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
