# 3.3.4 SQLAlchemy 加载策略：lazy / joined / selectinload / subquery

> 按结果基数和访问路径选择关系加载策略，避免 N+1、笛卡尔膨胀和隐式数据库访问。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 lazy、joinedload、selectinload、subqueryload
- 识别 N+1 查询
- 根据关系基数选择加载策略
- 读懂 dify 的 lazy="raise" 与 selectinload

## 📚 前置知识

- [3.3.3 关系映射](./04-sqlalchemy-relations.md)
- [3.1.5 SQL 性能优化](../../_common/21-sql/05-sql-performance.md)

## 1. 核心概念

### 1.1 四种策略

`lazy="select"` 首次访问关系时发 SQL，方便但容易 N+1。`joinedload` 在主查询 JOIN，适合多对一/一对一或小集合。`selectinload` 先查父行，再用 `WHERE child.fk IN (...)` 批量查子行，通常是一对多首选。`subqueryload` 使用父查询子查询加载，现代代码通常优先 selectinload。

### 1.2 行数膨胀

对两个大集合同时 joinedload，父行会按集合大小相乘。ORM 虽可去重对象，网络和数据库仍处理膨胀行。

### 1.3 禁止意外懒加载

`lazy="raise"` 在未预加载关系时直接报错，强迫调用方显式声明 I/O，适合大对象、异步代码和序列化路径（`async` 机制详见 [async/await](../01-fundamentals/14-async-asyncio.md)，此处不展开）。

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

## 3. 关键要点总结

- lazy 方便但容易 N+1，joinedload 可能造成行膨胀
- selectinload 通常适合一对多批量加载
- subqueryload 是另一种分离加载策略
- `lazy="raise"` 可把隐藏 I/O 变成显式错误

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
