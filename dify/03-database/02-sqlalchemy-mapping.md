# 3.3.1 SQLAlchemy 2.x 声明式映射与模型定义

> 用类型标注把 Python 类、表、列和约束组织成可检查的 SQLAlchemy 2.x 模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 DeclarativeBase、Mapped 与 mapped_column 定义模型
- 理解 `__tablename__`、`__table_args__` 和列选项
- 区分 Python 默认值与数据库 server_default
- 能看懂 dify 新旧两种模型基类与映射风格

## 📚 前置知识

- [3.2.2 主键、外键、唯一约束](../../_common/21-sql/07-database-keys.md)
- Python 类型标注：[`../01-fundamentals/08-python-typing-basics.md`](../01-fundamentals/08-python-typing-basics.md)

## 1. 核心概念

### 1.1 声明式映射

声明式映射把类定义同时作为 ORM 映射和表结构描述。`Mapped[str]` 表示 ORM 管理的字符串属性；`mapped_column(String(255))` 补充数据库类型、可空性、默认值和约束。

### 1.2 默认值的三个层次

- `default` / `default_factory`：构造 Python 对象时产生值；
- `insert_default`：SQLAlchemy 发出 INSERT 时使用；
- `server_default`：数据库在 INSERT 未提供值时生成。

多进程或绕过 ORM 的写入也需要默认值时，应配置 `server_default`。时间默认优先使用数据库函数或项目统一 UTC 工具。

### 1.3 表级配置

`__table_args__` 可集中声明主键、唯一约束、检查约束和索引。显式命名让 Alembic 迁移、报错和跨环境对比更稳定（Alembic 详见 [Alembic 基础](./13-alembic-basics.md)）。

## 2. 代码示例

### 2.1 定义带类型和约束的模型

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)


engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
with Session(engine) as session:
    session.add(User(email="owner@example.com"))
    session.commit()
```

**说明**：示例展示了类型化列、外键、索引、唯一约束和数据库端时间默认值；生产项目用 Alembic 管理表结构，不直接 `create_all`。`with Session(...)` 是会话上下文写法（详见 [Session 与 with](./07-sqlalchemy-session.md)）。

## 3. 关键要点总结

- `Mapped[T]` 同时服务 ORM 映射和静态类型检查
- `mapped_column` 描述数据库类型、约束和默认值
- Python 默认与 server_default 的生效位置不同
- 生产结构变更应交给 Alembic

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
