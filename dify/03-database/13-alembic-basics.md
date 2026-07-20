# 3.4.1 Alembic 基础：初始化与环境配置

> 理解 Alembic 如何连接应用、加载 metadata，并沿版本图执行可审计的结构迁移。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 alembic.ini、env.py、versions 的职责
- 理解 revision、down_revision 版本图
- 配置 target_metadata 与在线/离线迁移
- 读懂 dify 的 Flask-Migrate 环境接入

## 📚 前置知识

- [3.3.1 SQLAlchemy 声明式映射](./02-sqlalchemy-mapping.md)
- [3.1.4 事务与隔离级别](../../_common/21-sql/04-sql-transaction.md)

## 1. 核心概念

### 1.1 Alembic 管理的是版本图

每个迁移文件都有唯一 `revision`，并通过 `down_revision` 指向父版本。数据库在 `alembic_version` 表记录当前位置。升级就是沿图调用 `upgrade()`，降级则反向调用 `downgrade()`。

### 1.2 三个核心位置

- `alembic.ini`：脚本位置、文件名模板和日志；
- `env.py`：创建连接、提供 metadata、配置迁移上下文；
- `versions/`：不可变更历史，每个文件包含正向与反向操作。

### 1.3 在线与离线

在线模式使用真实 Engine/Connection 执行迁移；离线模式只依赖 URL 生成 SQL，适合审计和受控发布。生产迁移前要备份、在同版本数据副本演练，并估算锁时间（锁与并发详见 [乐观锁与悲观锁](../../_common/21-sql/09-lock-strategy.md)）。

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

## 3. 关键要点总结

- Alembic 用 revision/down_revision 构成版本图
- env.py 连接应用配置与模型 metadata
- 在线执行 SQL，离线可生成 SQL
- 迁移历史需审查、演练并保持可追踪

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
