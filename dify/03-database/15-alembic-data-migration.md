# 3.4.3 数据迁移与回滚策略

> 把结构变化与数据回填按可重试、可观察和可回滚的步骤组织，避免大表迁移阻塞线上服务。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 schema migration 与 data migration
- 设计 expand/backfill/contract 发布流程
- 使用 op.execute 进行受控回填
- 判断 downgrade 可逆、补偿或禁止的边界

## 📚 前置知识

- [3.4.2 Alembic 自动生成](./14-alembic-autogenerate.md)
- [3.1.4 事务与隔离级别](../../_common/21-sql/04-sql-transaction.md)

## 1. 核心概念

### 1.1 Expand / Migrate / Contract

先扩展兼容结构，再部署可双读/双写代码，然后分批回填，验证完成后收缩旧结构。这个流程让应用版本和数据库版本短期兼容，避免一次迁移承担所有风险。

### 1.2 大数据回填

迁移脚本中的单条全表 UPDATE 可能产生长事务、锁和大量 WAL。大表应使用独立、可重试的后台命令按主键批量回填（后台任务可参考 [Celery 架构](../04-cache-and-queue/05-celery-architecture.md)）；Alembic 只负责新增结构和最终约束。

### 1.3 回滚不是总能恢复数据

删除列后，downgrade 再创建列也找不回原值。不可逆操作应在迁移中明确失败、依赖备份恢复，或设计补偿迁移。生产发生问题时常用“向前修复”比回滚已执行的数据变换更安全。

## 2. 代码示例

### 2.1 可回填的新列迁移

```python
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("maintainer", sa.String(36), nullable=True))
    op.create_index(
        "project_tenant_maintainer_idx",
        "projects",
        ["tenant_id", "maintainer"],
    )
    op.execute(
        sa.text("UPDATE projects SET maintainer = created_by WHERE maintainer IS NULL")
    )


def downgrade() -> None:
    op.drop_index("project_tenant_maintainer_idx", table_name="projects")
    op.drop_column("projects", "maintainer")
```

**说明**：示例与 dify 的维护者字段迁移同型；若 projects 很大，应把 UPDATE 改为可重试批处理，并推迟非空约束。

## 3. 关键要点总结

- 数据迁移要与应用兼容窗口一起设计
- 大表回填应分批、幂等、可观察
- downgrade 应逆序撤销依赖对象
- 不可逆数据变化依赖备份或向前修复

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
