# 3.3.3 SQLAlchemy 关系映射：One-to-One / One-to-Many / Many-to-Many

> 让数据库外键与 ORM 对象导航各司其职，正确表达关系基数、级联和生命周期。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置一对一、一对多和多对多关系
- 理解 ForeignKey 与 relationship 的不同职责
- 使用 back_populates 和 cascade
- 分析 dify 评论模型的父子与提及关系

## 📚 前置知识

- [3.2.2 主键、外键、唯一约束](./08-database-keys.md)
- [3.3.1 声明式映射](./12-sqlalchemy-mapping.md)

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

## 3. dify 仓库源码解读

### 3.1 评论的一对多关系

**文件位置**：`/Users/xu/code/github/dify/api/models/comment.py`  
**核心代码**（行 64-85）：

```python
    )
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime, default=None)
    resolved_by: Mapped[str | None] = mapped_column(StringUUID, default=None)

    resolved: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"), default=False)
    # Relationships
    replies: Mapped[list[WorkflowCommentReply]] = relationship(
        lambda: WorkflowCommentReply, back_populates="comment", cascade="all, delete-orphan", init=False
    )
    mentions: Mapped[list[WorkflowCommentMention]] = relationship(
        lambda: WorkflowCommentMention, back_populates="comment", cascade="all, delete-orphan", init=False
    )

    @property
    def created_by_account(self):
        """Get creator account."""
        if hasattr(self, "_created_by_account_cache"):
            return self._created_by_account_cache
        return db.session.get(Account, self.created_by)

    def cache_created_by_account(self, account: Account | None) -> None:
        """Cache creator account to avoid extra queries."""
```

**解读**：
- `replies` 与 `mentions` 都是父评论到子对象的集合关系。
- `back_populates` 明确双向配对，`delete-orphan` 表示脱离父评论的子对象应删除。
- 账户属性使用显式查询/缓存，不是声明式关系。

### 3.2 子对象返回父关系

**文件位置**：`/Users/xu/code/github/dify/api/models/comment.py`  
**核心代码**（行 160-178）：

```python

    id: Mapped[str] = mapped_column(StringUUID, default_factory=gen_uuidv7_string, init=False)
    comment_id: Mapped[str] = mapped_column(
        StringUUID, sa.ForeignKey("workflow_comments.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_by: Mapped[str] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=func.current_timestamp(), init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )
    # Relationships
    comment: Mapped[WorkflowComment] = relationship(lambda: WorkflowComment, back_populates="replies", init=False)
```

**解读**：
- `comment_id` 提供真实外键和数据库级级联。
- `comment` relationship 与父类的 `replies` 配对。
- 外键列用于过滤，relationship 用于对象导航。

## 4. 关键要点总结

- ForeignKey 保证数据库完整性，relationship 管理对象导航
- 一对一需要数据库唯一性支撑
- 多对多关联有属性时应映射为独立对象
- ORM 与数据库级联配置要一致

## 5. 练习题

### 练习 1：基础（必做）

把示例扩展成作者一对一资料表。

### 练习 2：进阶

设计文章与标签的多对多关联，并给关联增加 `created_at`。

### 练习 3：挑战（选做）

画出 dify 评论、回复、提及三类模型的基数图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/comment.py`
- SQLAlchemy 2.0 ORM 快速入门：https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- SQLAlchemy 基本关系模式：https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
