# 3.4.1 Alembic 基础：初始化与环境配置

> 理解 Alembic 如何连接应用、加载 metadata，并沿版本图执行可审计的结构迁移。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 alembic.ini、env.py、versions 的职责
- 理解 revision、down_revision 版本图
- 配置 target_metadata 与在线/离线迁移
- 读懂 dify 的 Flask-Migrate 环境接入

## 📚 前置知识

- [3.3.1 SQLAlchemy 声明式映射](./12-sqlalchemy-mapping.md)
- [3.1.4 事务与隔离级别](./04-sql-transaction.md)

## 1. 核心概念

### 1.1 Alembic 管理的是版本图

每个迁移文件都有唯一 `revision`，并通过 `down_revision` 指向父版本。数据库在 `alembic_version` 表记录当前位置。升级就是沿图调用 `upgrade()`，降级则反向调用 `downgrade()`。

### 1.2 三个核心位置

- `alembic.ini`：脚本位置、文件名模板和日志；
- `env.py`：创建连接、提供 metadata、配置迁移上下文；
- `versions/`：不可变更历史，每个文件包含正向与反向操作。

### 1.3 在线与离线

在线模式使用真实 Engine/Connection 执行迁移；离线模式只依赖 URL 生成 SQL，适合审计和受控发布。生产迁移前要备份、在同版本数据副本演练，并估算锁时间。

## 2. 代码示例

### 2.1 最小 Alembic 迁移文件

```python
"""add task status

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.create_index("task_status_idx", "tasks", ["status"])


def downgrade() -> None:
    op.drop_index("task_status_idx", table_name="tasks")
    op.drop_column("tasks", "status")
```

**说明**：`upgrade` 与 `downgrade` 方向相反，版本标识形成链。真实项目应先生成 revision，再人工审查锁、默认值和回滚语义。

## 3. dify 仓库源码解读

### 3.1 Dify 的 metadata 与对象过滤

**文件位置**：`/Users/xu/code/github/dify/api/migrations/env.py`  
**核心代码**（行 39-49）：

```python

from models.base import TypeBase


def get_metadata():
    return TypeBase.metadata

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "foreign_key_constraint":
        return False
    else:
```

**解读**：
- `get_metadata()` 返回 TypeBase.metadata，供自动生成比较。
- `include_object` 明确排除外键约束自动生成。
- 这类过滤意味着 autogenerate 结果反映项目策略，不一定包含所有数据库对象。

### 3.2 在线迁移上下文

**文件位置**：`/Users/xu/code/github/dify/api/migrations/env.py`  
**核心代码**（行 82-105）：

```python

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            process_revision_directives=process_revision_directives,
            include_object=include_object,
            **current_app.extensions['migrate'].configure_args
        )

        with context.begin_transaction():
            context.run_migrations()
```

**解读**：
- 回调在无 schema 变化时取消空迁移。
- 连接来自 Flask-Migrate 已配置 Engine。
- `context.configure` 注入连接、metadata、过滤器和扩展参数。

## 4. 关键要点总结

- Alembic 用 revision/down_revision 构成版本图
- env.py 连接应用配置与模型 metadata
- 在线执行 SQL，离线可生成 SQL
- 迁移历史需审查、演练并保持可追踪

## 5. 练习题

### 练习 1：基础（必做）

画出三条线性迁移的版本图。

### 练习 2：进阶

在临时项目初始化 Alembic，配置 Base.metadata。

### 练习 3：挑战（选做）

解释 dify 为什么在 include_object 中排除外键约束。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/migrations/env.py`
- `/Users/xu/code/github/dify/api/migrations/alembic.ini`
- Alembic 教程：https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Alembic 运行环境：https://alembic.sqlalchemy.org/en/latest/api/runtime.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
