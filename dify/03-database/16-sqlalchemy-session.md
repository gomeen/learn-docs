# 3.3.5 SQLAlchemy 会话管理：Session 与 with 上下文

> 把 Session 当作工作单元和身份映射，明确事务、提交、回滚以及对象失效的生命周期。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Session 的身份映射与工作单元职责
- 使用 with 与 session.begin 管理事务
- 理解 flush、commit、rollback 和 expire_on_commit
- 分析 dify 仓储中的 Session 生命周期

## 📚 前置知识

- [3.1.4 事务与隔离级别](./04-sql-transaction.md)
- 上下文管理器：[`../01-fundamentals/11-context-manager.md`](../01-fundamentals/11-context-manager.md)

## 1. 核心概念

### 1.1 Session 不是连接

Session 管理 ORM 对象、待写变更和事务，按需从连接池取得连接。它不是全局缓存，也不是线程安全对象。一个请求或任务通常拥有明确 Session 生命周期。

### 1.2 flush 与 commit

`flush` 把待写变化发送到数据库，但事务尚未提交，可用于取得数据库生成值和提前发现约束错误。`commit` 先 flush 再提交；异常后必须 rollback。

### 1.3 上下文模式

`with Session(engine) as session` 保证关闭；`with session.begin()` 正常退出提交、异常回滚。`expire_on_commit=False` 让提交后属性保持可用，但对象可能不是最新状态。

## 2. 代码示例

### 2.1 用事务上下文管理工作单元

```python
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

class Base(DeclarativeBase):
    pass

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)

with Session(engine, expire_on_commit=False) as session:
    with session.begin():
        item = Item(name="vector-index")
        session.add(item)
        session.flush()
        print(item.id)
    print(item.name)

with Session(engine) as session:
    loaded = session.scalar(select(Item).where(Item.name == "vector-index"))
    print(loaded)
```

**说明**：内层 `begin` 负责提交/回滚，外层负责关闭；flush 后可访问主键，真正持久化要到提交。

## 3. dify 仓库源码解读

### 3.1 事务上下文与预加载

**文件位置**：`/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`  
**核心代码**（行 1179-1199）：

```python
        with self._session_maker() as session, session.begin():
            # Get the workflow run with pause
            stmt = select(WorkflowRun).options(selectinload(WorkflowRun.pause)).where(WorkflowRun.id == workflow_run_id)
            workflow_run = session.scalar(stmt)

            if workflow_run is None:
                raise ValueError(f"WorkflowRun not found: {workflow_run_id}")

            if workflow_run.status != WorkflowExecutionStatus.PAUSED:
                raise _WorkflowRunError(
                    f"WorkflowRun is not in PAUSED status, workflow_run_id={workflow_run_id}, "
                    f"current_status={workflow_run.status}"
                )
            pause_model = workflow_run.pause
            if pause_model is None:
                raise _WorkflowRunError(f"No pause state found for workflow run: {workflow_run_id}")

            if pause_model.id != pause_entity.id:
                raise _WorkflowRunError(
                    "different id in WorkflowPause and WorkflowPauseEntity, "
                    f"WorkflowPause.id={pause_model.id}, "
```

**解读**：
- `with session, session.begin()` 组合资源关闭与事务提交/回滚。
- 关系在同一 Session 内预加载。
- 状态校验和修改处在明确事务边界中。

### 3.2 跨 Session 生命周期保留属性

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`  
**核心代码**（行 132-150）：

```python
    def current_tenant(self, tenant: "Tenant"):
        with Session(db.engine, expire_on_commit=False) as session:
            tenant_join_query = select(TenantAccountJoin).where(
                TenantAccountJoin.tenant_id == tenant.id, TenantAccountJoin.account_id == self.id
            )
            tenant_join = session.scalar(tenant_join_query)
            tenant_query = select(Tenant).where(Tenant.id == tenant.id)
            # TODO: A workaround to reload the tenant with `expire_on_commit=False`, allowing
            # access to it after the session has been closed.
            # This prevents `DetachedInstanceError` when accessing the tenant outside
            # the session's lifecycle.
            # (The `tenant` argument is typically loaded by `db.session` without the
            # `expire_on_commit=False` flag, meaning its lifetime is tied to the web
            # request's lifecycle.)
            tenant_reloaded = session.scalars(tenant_query).one()

        if tenant_join:
            self.role = TenantAccountRole(tenant_join.role)
            self._current_tenant = tenant_reloaded
```

**解读**：
- 临时 Session 配置 `expire_on_commit=False`，关闭后属性仍可访问。
- 注释明确这是避免 DetachedInstanceError 的权衡。
- 属性可用不代表数据仍是最新。

## 4. 关键要点总结

- Session 是身份映射和工作单元，不是线程安全全局对象
- flush 发送 SQL，commit 提交事务
- 上下文管理器保证关闭与异常回滚
- 跨 Session 使用对象要理解 expire 和 detached 状态

## 5. 练习题

### 练习 1：基础（必做）

用 `session.begin()` 插入两行并故意违反唯一约束。

### 练习 2：进阶

比较 `expire_on_commit=True` 与 False。

### 练习 3：挑战（选做）

把手工 try/commit/rollback/finally 改写为双层 with。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`
- `/Users/xu/code/github/dify/api/models/account.py`
- SQLAlchemy Session：https://docs.sqlalchemy.org/en/20/orm/session_basics.html
- SQLAlchemy 事务：https://docs.sqlalchemy.org/en/20/orm/session_transaction.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
