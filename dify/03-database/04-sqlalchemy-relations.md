# 3.3.3 SQLAlchemy 关系映射：One-to-One / One-to-Many / Many-to-Many

> 让数据库外键与 ORM 对象导航各司其职，正确表达关系基数、级联和生命周期。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置一对一、一对多和多对多关系
- 理解 ForeignKey 与 relationship 的不同职责
- 使用 back_populates 和 cascade
- 分析 dify 评论模型的父子与提及关系

## 📚 前置知识

- [3.2.2 主键、外键、唯一约束](../../_common/21-sql/07-database-keys.md)
- [3.3.1 声明式映射](./02-sqlalchemy-mapping.md)
- 关系加载策略（N+1 等，详见 [加载策略](./06-sqlalchemy-loading.md)）

## 1. 核心概念

### 1.1 外键不是 relationship

`ForeignKey` 是数据库约束，保证引用存在；`relationship` 是 ORM 的对象导航和同步配置。只写 relationship 不会自动获得数据库完整性，二者通常要配合。

### 1.2 三种基数

- 一对多：父类属性为 `Mapped[list[Child]]`，子类保存外键；
- 一对一：本质是子表外键加唯一约束，ORM 侧用非集合类型；
- 多对多：通过关联表连接两边，关联本身有属性时建成 Association Object。

### 1.3 级联

`cascade="all, delete-orphan"` 表示子对象生命周期依附父对象；数据库 `ON DELETE CASCADE` 处理直接 SQL 删除。两层级联应保持一致。

## 2. 代码示例

### 2.1 映射作者与文章的一对多

```python
from sqlalchemy import ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    articles: Mapped[list["Article"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(120))
    author: Mapped[Author] = relationship(back_populates="articles")

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
with Session(engine) as session:
    session.add(Author(name="Ada", articles=[Article(title="ORM")]))
    session.commit()
```

**说明**：数据库外键保护引用，双向 relationship 提供对象导航，删除孤儿级联与生命周期一致。

## 3. 关键要点总结

- ForeignKey 保证数据库完整性，relationship 管理对象导航
- 一对一需要数据库唯一性支撑
- 多对多关联有属性时应映射为独立对象
- ORM 与数据库级联配置要一致

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
