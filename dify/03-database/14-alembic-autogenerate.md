# 3.4.2 自动生成迁移脚本：alembic revision --autogenerate

> 让 Alembic 比较 metadata 与数据库结构生成候选迁移，再由开发者审查、补全与验证。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 autogenerate 的比较输入和输出
- 配置 target_metadata
- 识别自动生成能与不能可靠判断的变更
- 建立生成、审查、测试迁移的流程

## 📚 前置知识

- [3.4.1 Alembic 基础](./13-alembic-basics.md)
- [3.3.1 声明式映射](./02-sqlalchemy-mapping.md)

## 1. 核心概念

### 1.1 自动生成不是自动正确

`alembic revision --autogenerate -m "..."` 读取当前数据库 schema 和 `target_metadata`，生成二者差异。它擅长表、列、索引和部分约束；重命名通常会被识别成“删除 + 新增”，数据迁移、业务默认、方言对象也需人工处理。

### 1.2 审查清单

1. 有没有误删表或列；2. nullable 改动对旧行是否安全；3. server_default 是否只是回填过渡；4. 索引是否会长时间锁表（锁代价详见 [乐观锁与悲观锁](../../_common/21-sql/09-lock-strategy.md)）；5. downgrade 是否真实可逆；6. 多数据库方言是否兼容。数据回填策略见 [数据迁移](./15-alembic-data-migration.md)。

### 1.3 Dify 的空迁移抑制

env.py 的 `process_revision_directives` 在 upgrade_ops 为空时删除生成指令，避免提交没有实际变更的版本文件。它只减少噪声，不替代人工审查。

## 2. 代码示例

### 2.1 生成后应人工调整的迁移

```python
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 第一步允许 NULL，避免旧行立即违反约束
    op.add_column("users", sa.Column("display_name", sa.String(100), nullable=True))
    # 自动生成不会知道如何回填业务数据
    op.execute(
        sa.text("UPDATE users SET display_name = email WHERE display_name IS NULL")
    )
    op.alter_column("users", "display_name", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "display_name")
```

**说明**：新增非空列采用“可空新增 → 回填 → 改非空”三步；中间的数据语义必须由开发者提供。

## 3. 关键要点总结

- autogenerate 生成候选差异，不理解业务数据
- 重命名、回填和数据库专有对象必须人工处理
- 每个 upgrade/downgrade 都要审查和实测
- 空迁移抑制只能减少噪声

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
