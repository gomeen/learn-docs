# 3.1.3 索引原理：B+Tree / Hash / 覆盖索引

> 理解索引如何缩小扫描范围，并根据查询谓词、排序与投影设计可用索引。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 B+Tree 与 Hash 索引的访问特征
- 识别联合索引的最左前缀与排序能力
- 理解覆盖索引、部分索引及其代价
- 能分析 dify 模型中的复合索引设计

## 📚 前置知识

- [3.1.1 SQL 基础语法](./01-sql-basics.md)
- 数据结构中的树与哈希表基础

## 1. 核心概念

### 1.1 为什么索引能加速

索引保存“键 → 行位置”的有序或散列结构。PostgreSQL 默认 B-tree，适合等值、范围和排序；Hash 主要服务等值比较。索引减少读页数量，但写入时也要维护，因此不是越多越好。

### 1.2 联合索引与最左前缀

索引 `(tenant_id, app_id, created_at DESC)` 先按租户组织，再按应用，最后按时间。查询跳过 `tenant_id` 时，通常难以充分利用该顺序。列顺序应由高频过滤、等值条件、范围条件与排序共同决定。

### 1.3 覆盖与部分索引

查询所需列都可从索引取得时，优化器可能使用 Index Only Scan；PostgreSQL 可用 `INCLUDE` 添加非排序列。部分索引只索引满足谓词的行，例如仅索引未删除会话，体积更小，但查询条件必须能推出该谓词。

```text
代价 = 更快的读取 + 更多磁盘占用 + 更慢的 INSERT/UPDATE/DELETE
```

## 2. 代码示例

### 2.1 为多租户时间线设计索引

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    app_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    payload TEXT NOT NULL
);

CREATE INDEX event_tenant_app_time_idx
ON events (tenant_id, app_id, created_at DESC)
INCLUDE (id)
WHERE is_deleted IS FALSE;

EXPLAIN
SELECT id, created_at
FROM events
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
  AND app_id = '00000000-0000-0000-0000-000000000002'
  AND is_deleted IS FALSE
ORDER BY created_at DESC
LIMIT 20;
```

**说明**：复合部分索引同时服务租户/应用过滤、时间倒序和小结果集投影；`INCLUDE (id)` 提高覆盖机会。

## 3. dify 仓库源码解读

### 3.1 会话列表的部分复合索引

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`  
**核心代码**（行 1097-1114）：

```python
    __tablename__ = "conversations"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="conversation_pkey"),
        sa.Index("conversation_app_from_user_idx", "app_id", "from_source", "from_end_user_id"),
        sa.Index(
            "conversation_app_created_at_idx",
            "app_id",
            sa.text("created_at DESC"),
            postgresql_where=sa.text("is_deleted IS false"),
        ),
        sa.Index(
            "conversation_app_updated_at_idx",
            "app_id",
            sa.text("updated_at DESC"),
            postgresql_where=sa.text("is_deleted IS false"),
        ),
    )

```

**解读**：
- 第 1102-1106 行索引 `app_id, created_at DESC`，匹配按应用读取最近会话。
- `postgresql_where` 只保存 `is_deleted IS false` 的活跃行。
- 第二个索引用同样策略服务按更新时间排序的列表。

### 3.2 工作流运行记录的访问路径

**文件位置**：`/Users/xu/code/github/dify/api/models/workflow.py`  
**核心代码**（行 789-818）：

```python
    __tablename__ = "workflow_runs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="workflow_run_pkey"),
        sa.Index("workflow_run_triggerd_from_idx", "tenant_id", "app_id", "triggered_from"),
        sa.Index("workflow_run_created_at_id_idx", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    app_id: Mapped[str] = mapped_column(StringUUID)

    workflow_id: Mapped[str] = mapped_column(StringUUID)
    type: Mapped[WorkflowType] = mapped_column(EnumText(WorkflowType, length=255))
    triggered_from: Mapped[WorkflowRunTriggeredFrom] = mapped_column(EnumText(WorkflowRunTriggeredFrom, length=255))
    version: Mapped[str] = mapped_column(String(255))
    graph: Mapped[str | None] = mapped_column(LongText)
    inputs: Mapped[str | None] = mapped_column(LongText)
    status: Mapped[WorkflowExecutionStatus] = mapped_column(
        EnumText(WorkflowExecutionStatus, length=255),
        nullable=False,
    )
    outputs: Mapped[str | None] = mapped_column(LongText, default="{}")
    error: Mapped[str | None] = mapped_column(LongText)
    elapsed_time: Mapped[float] = mapped_column(sa.Float, nullable=False, server_default=sa.text("0"))
    total_tokens: Mapped[int] = mapped_column(sa.BigInteger, server_default=sa.text("0"))
    total_steps: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"), nullable=True)
    created_by_role: Mapped[CreatorUserRole] = mapped_column(EnumText(CreatorUserRole, length=255))  # account, end_user
    created_by: Mapped[str] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
```

**解读**：
- 第 791-793 行声明主键和两个二级索引。
- `workflow_run_triggerd_from_idx` 把常见等值过滤列放在同一索引。
- `created_at, id` 与稳定游标分页的双列排序相呼应。

## 4. 关键要点总结

- B-tree 支持等值、范围和排序，Hash 主要支持等值
- 联合索引列顺序必须匹配真实查询形状
- 覆盖索引减少回表，部分索引缩小活跃数据集
- 索引会增加写放大，应以执行计划和负载验证

## 5. 练习题

### 练习 1：基础（必做）

为 `(tenant_id, status, created_at)` 查询设计索引并解释列顺序。

### 练习 2：进阶

比较只查 `app_id` 与同时查 `app_id + is_deleted` 时部分索引的可用性。

### 练习 3：挑战（选做）

选择 dify 一个复合索引，列出能高效支持和不能高效支持的各两种查询。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/models/workflow.py`
- PostgreSQL 索引：https://www.postgresql.org/docs/current/indexes.html
- PostgreSQL Index-Only Scan：https://www.postgresql.org/docs/current/indexes-index-only-scans.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
