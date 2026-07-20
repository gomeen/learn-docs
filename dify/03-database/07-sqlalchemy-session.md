# 3.3.5 SQLAlchemy 会话管理：Session 与 with 上下文

> 把 Session 当作工作单元和身份映射，明确事务、提交、回滚以及对象失效的生命周期。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Session 的身份映射与工作单元职责
- 使用 with 与 session.begin 管理事务
- 理解 flush、commit、rollback 和 expire_on_commit
- 分析 dify 仓储中的 Session 生命周期（仓储模式详见 [仓储模式](../../_common/22-architecture/03-repository-pattern.md)）

## 📚 前置知识

- [3.1.4 事务与隔离级别](../../_common/21-sql/04-sql-transaction.md)
- 上下文管理器：[`../01-fundamentals/12-context-manager.md`](../01-fundamentals/12-context-manager.md)

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

## 3. 关键要点总结

- Session 是身份映射和工作单元，不是线程安全全局对象
- flush 发送 SQL，commit 提交事务
- 上下文管理器保证关闭与异常回滚
- 跨 Session 使用对象要理解 expire 和 detached 状态

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
