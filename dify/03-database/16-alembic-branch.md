# 3.4.4 Alembic 迁移的分支与合并

> 把并行开发产生的多个 migration head 合并成有共同后继的有向无环版本图。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 head、base、branch point 和 merge point
- 识别多个 head 的产生原因
- 使用 alembic heads、history、merge
- 读懂 dify 的真实 merge revision

## 📚 前置知识

- [3.4.1 Alembic 基础](./13-alembic-basics.md)
- Git 分支基础：[`../../_common/15-git/01-git-advanced.md`](../../_common/15-git/01-git-advanced.md)

## 1. 核心概念

### 1.1 为什么会有多个 head

两个开发分支都从 revision A 创建新迁移 B、C，合并代码后版本图出现两个 head（Git 分支与协作详见前置 [Git 进阶](../../_common/15-git/01-git-advanced.md)）。不要偷偷把其中一个 `down_revision` 改成另一个：那会重写已发布历史，并可能让已升级环境无法对齐。

### 1.2 合并版本

`alembic merge -m "merge heads" B C` 创建 revision D，令 `down_revision=(B, C)`。D 的 upgrade 往往为空，因为它只表示两条历史都已完成。若两分支修改同一对象，还需在 merge 迁移中解决结构冲突。

```text
A ── B ──┐
         ├── D
A ── C ──┘
```

### 1.3 协作流程

提交前运行 `alembic heads`；出现多 head 时先判断迁移是否冲突，再创建 merge revision。CI 应校验只有预期 head，并从空库与旧版本分别升级测试。

## 2. 代码示例

### 2.1 一个标准 merge revision

```python
"""merge account and dataset branches"""

revision = "merge_004_005"
down_revision = ("004_add_account", "005_add_dataset")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 两个父迁移已分别完成结构修改；这里只汇合版本图
    pass


def downgrade() -> None:
    # 降级到 merge point 的父级会重新出现两个 heads
    pass


if __name__ == "__main__":
    parents = down_revision
    assert len(parents) == 2
    print(f"merge {parents[0]} and {parents[1]}")
```

**说明**：合并点通过元数据表达多个父版本；空 upgrade 并不代表无意义，它把版本图重新汇成一个 head。

## 3. 关键要点总结

- 并行分支会自然产生多个 head
- 不要重写已共享迁移历史来伪造线性链
- merge revision 用多个 down_revision 汇合版本图
- CI 应检查 heads 并测试完整升级路径

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
