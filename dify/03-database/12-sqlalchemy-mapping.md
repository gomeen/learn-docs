# 3.3.1 SQLAlchemy 2.x 声明式映射与模型定义

> 用类型标注把 Python 类、表、列和约束组织成可检查的 SQLAlchemy 2.x 模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 DeclarativeBase、Mapped 与 mapped_column 定义模型
- 理解 `__tablename__`、`__table_args__` 和列选项
- 区分 Python 默认值与数据库 server_default
- 能看懂 dify 新旧两种模型基类与映射风格

## 📚 前置知识

- [3.2.2 主键、外键、唯一约束](./08-database-keys.md)
- Python 类型标注：[`../01-fundamentals/07-python-typing-basics.md`](../01-fundamentals/07-python-typing-basics.md)

## 1. 核心概念

### 1.1 声明式映射

声明式映射把类定义同时作为 ORM 映射和表结构描述。`Mapped[str]` 表示 ORM 管理的字符串属性；`mapped_column(String(255))` 补充数据库类型、可空性、默认值和约束。

### 1.2 默认值的三个层次

- `default` / `default_factory`：构造 Python 对象时产生值；
- `insert_default`：SQLAlchemy 发出 INSERT 时使用；
- `server_default`：数据库在 INSERT 未提供值时生成。

多进程或绕过 ORM 的写入也需要默认值时，应配置 `server_default`。时间默认优先使用数据库函数或项目统一 UTC 工具。

### 1.3 表级配置

`__table_args__` 可集中声明主键、唯一约束、检查约束和索引。显式命名让 Alembic 迁移、报错和跨环境对比更稳定（Alembic 详见 [Alembic 基础](./20-alembic-basics.md)）。

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

**说明**：示例展示了类型化列、外键、索引、唯一约束和数据库端时间默认值；生产项目用 Alembic 管理表结构，不直接 `create_all`。`with Session(...)` 是会话上下文写法（详见 [Session 与 with](./16-sqlalchemy-session.md)）。

## 3. dify 仓库源码解读

### 3.1 Dify 的声明式基类

**文件位置**：`/Users/xu/code/github/dify/api/models/base.py`  
**核心代码**（行 14-24）：

```python

class Base(DeclarativeBase):
    metadata = metadata


class TypeBase(MappedAsDataclass, DeclarativeBase):
    """
    This is for adding type, after all finished, rename to Base.
    """

    metadata = metadata
```

**解读**：
- `Base` 与 `TypeBase` 都绑定项目统一 metadata。
- `TypeBase` 组合 `MappedAsDataclass`，让映射对象获得 dataclass 风格构造（dataclass 语言机制详见 [dataclass](../01-fundamentals/36-dataclasses.md)；dify 规范详见 [TypeBase](./18-typebase-model.md)）。
- 注释说明 TypeBase 是迁移期间的过渡基类，阅读模型时需注意两个 registry。

### 3.2 类型化账户模型

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`  
**核心代码**（行 88-117）：

```python

class Account(UserMixin, TypeBase):
    __tablename__ = "accounts"
    __table_args__ = (sa.PrimaryKeyConstraint("id", name="account_pkey"), sa.Index("account_email_idx", "email"))

    id: Mapped[str] = mapped_column(
        StringUUID, insert_default=lambda: str(uuid4()), default_factory=lambda: str(uuid4()), init=False
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255), default=None)
    password_salt: Mapped[str | None] = mapped_column(String(255), default=None)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    interface_language: Mapped[str | None] = mapped_column(String(255), default=None)
    interface_theme: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    timezone: Mapped[str | None] = mapped_column(String(255), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    last_login_ip: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        EnumText(AccountStatus, length=16), server_default=sa.text("'active'"), default=AccountStatus.ACTIVE
    )
    initialized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False, onupdate=func.current_timestamp()
```

**解读**：
- 类名、表名和表级主键/索引集中声明。
- `Mapped[str | None]` 与 `nullable=True/default=None` 清楚表达可空属性。
- 创建/更新时间使用数据库默认，更新时间还配置 `onupdate`。

## 4. 关键要点总结

- `Mapped[T]` 同时服务 ORM 映射和静态类型检查
- `mapped_column` 描述数据库类型、约束和默认值
- Python 默认与 server_default 的生效位置不同
- 生产结构变更应交给 Alembic

## 5. 练习题

### 练习 1：基础（必做）

定义 `Article` 模型，包含 UUID 主键、标题、状态和创建时间。

### 练习 2：进阶

分别演示 `default_factory` 与 `server_default` 在对象构造前后的差异。

### 练习 3：挑战（选做）

比较 dify 的 `Base` 与 `TypeBase`，列出适用的模型示例。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/base.py`
- `/Users/xu/code/github/dify/api/models/account.py`
- SQLAlchemy 2.0 ORM 快速入门：https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- SQLAlchemy 声明式映射：https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
