# 3.2.2 主键、外键、唯一约束

> 用数据库约束表达身份、引用完整性和业务唯一性，把不变量落实到并发安全的最后防线。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分主键、外键与唯一约束
- 理解自然键、代理键和复合键的取舍
- 使用 ON DELETE 与可空外键设计生命周期
- 读懂 dify 模型中的命名约束与级联关系

## 📚 前置知识

- [3.2.1 三大范式与反范式](./07-database-normalization.md)
- [3.1.4 事务与隔离级别](./04-sql-transaction.md)

## 1. 核心概念

### 1.1 三类约束

主键唯一标识一行且不可为 NULL；外键保证引用目标存在；唯一约束表达候选键或业务不变量。应用层“先查再插”无法抵抗并发，最终仍需数据库唯一约束裁决。

### 1.2 键的选择

自然键有业务意义但可能变化；代理键稳定、窄且便于引用。Dify 大量使用 UUID 代理键，并对真正的业务键额外加唯一约束，例如 `(tenant_id, account_id)`。

### 1.3 删除策略

`ON DELETE CASCADE` 适合生命周期严格依附父对象的子记录；`RESTRICT` 适合需要显式清理的核心数据；`SET NULL` 适合允许保留历史但解除关联的记录。选择必须匹配领域生命周期，而非图省事。

## 2. 代码示例

### 2.1 用约束表达团队成员关系

```sql
CREATE TABLE teams (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE team_members (
    id UUID PRIMARY KEY,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    CONSTRAINT team_member_unique UNIQUE (team_id, user_id)
);

INSERT INTO teams VALUES
    ('00000000-0000-0000-0000-000000000001', 'docs');
INSERT INTO users VALUES
    ('00000000-0000-0000-0000-000000000002', 'a@example.com');
```

**说明**：代理主键用于引用，名称/邮箱是候选键，关联表用复合唯一约束禁止同一用户重复加入团队。

## 3. dify 仓库源码解读

### 3.1 租户账户关联的组合唯一性

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`  
**核心代码**（行 291-308）：

```python
class TenantAccountJoin(TypeBase):
    __tablename__ = "tenant_account_joins"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="tenant_account_join_pkey"),
        sa.Index("tenant_account_join_account_id_idx", "account_id"),
        sa.Index("tenant_account_join_tenant_id_idx", "tenant_id"),
        sa.UniqueConstraint("tenant_id", "account_id", name="unique_tenant_account_join"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID, insert_default=lambda: str(uuid4()), default_factory=lambda: str(uuid4()), init=False
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    account_id: Mapped[str] = mapped_column(StringUUID)
    current: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"), default=False)
    role: Mapped[TenantAccountRole] = mapped_column(
        EnumText(TenantAccountRole, length=16), server_default="normal", default=TenantAccountRole.NORMAL
    )
```

**解读**：
- 每条关联有独立 UUID 主键，便于其他记录引用。
- `UniqueConstraint("tenant_id", "account_id")` 把“同一账户在租户中只能出现一次”交给数据库保证。
- 两个单列索引支持分别按账户或租户查成员关系。

### 3.2 评论回复的外键与 ORM 关系

**文件位置**：`/Users/xu/code/github/dify/api/models/comment.py`  
**核心代码**（行 154-178）：

```python
    __tablename__ = "workflow_comment_replies"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="workflow_comment_replies_pkey"),
        Index("comment_replies_comment_idx", "comment_id"),
        Index("comment_replies_created_at_idx", "created_at"),
    )

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
- `comment_id` 外键指向父评论，并配置 `ON DELETE CASCADE`。
- 回复自身有独立主键与时间字段。
- `relationship(... back_populates="replies")` 是对象导航；真正的引用完整性来自外键。

## 4. 关键要点总结

- 主键标识行，外键保证引用，唯一约束保证业务候选键
- 应用检查不能替代数据库唯一约束
- 代理键与业务唯一键可以同时存在
- 级联删除必须与对象生命周期一致

## 5. 练习题

### 练习 1：基础（必做）

设计文章与评论表，明确每个键和删除策略。

### 练习 2：进阶

演示两个并发“先查后插”为什么仍可能重复，并用唯一约束修复。

### 练习 3：挑战（选做）

检查 dify 一个 Join 模型，列出其主键、候选键和索引。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/account.py`
- `/Users/xu/code/github/dify/api/models/comment.py`
- PostgreSQL 约束：https://www.postgresql.org/docs/current/ddl-constraints.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
