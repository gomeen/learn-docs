# 3.2.3 软删除与硬删除策略

> 根据恢复、审计、隐私与存储成本选择删除语义，并让所有查询和唯一性规则与之匹配。

## 🎯 学习目标

完成本文档后，你将能够：
- 比较软删除和硬删除的优缺点
- 设计软删除字段、过滤和部分索引
- 理解级联清理与异步清理的风险
- 识别 dify 中会话可见性与物理删除的组合

## 📚 前置知识

- [3.2.2 主键、外键、唯一约束](./08-database-keys.md)
- [3.1.3 索引原理](./03-sql-index.md)

## 1. 核心概念

### 1.1 两种删除语义

硬删除使用 `DELETE` 物理移除行，简单且释放空间，但恢复困难。软删除通过 `is_deleted` 或 `deleted_at` 隐藏行，支持恢复和审计，却要求每条读取路径都正确过滤。

### 1.2 软删除的完整设计

只增加布尔列不够，还要处理：默认查询作用域、唯一键是否允许复用、关联数据是否仍可见、归档保留期、后台物理清理。`deleted_at` 比布尔值多出删除时间信息。

### 1.3 混合策略

常见策略是先从用户视图隐藏，经过保留期再硬删除；或先删主记录，再异步清理大体量从属数据。异步清理必须幂等，并监控失败重试，否则会留下孤儿数据。

## 2. 代码示例

### 2.1 实现可恢复的软删除

```sql
CREATE TABLE articles (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    deleted_at TIMESTAMP NULL
);

CREATE UNIQUE INDEX article_live_slug_key
ON articles (slug)
WHERE deleted_at IS NULL;

INSERT INTO articles (slug, title) VALUES ('sql-basics', 'SQL Basics');

UPDATE articles
SET deleted_at = CURRENT_TIMESTAMP
WHERE slug = 'sql-basics' AND deleted_at IS NULL;

SELECT id, slug, title
FROM articles
WHERE deleted_at IS NULL
ORDER BY id;

DELETE FROM articles
WHERE deleted_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
```

**说明**：部分唯一索引只约束活跃文章，因此软删后 slug 可被新文章复用；最后一条语句代表保留期后的物理清理。

## 3. dify 仓库源码解读

### 3.1 软删除字段与活跃行索引

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
- 会话表的两个列表索引都只覆盖 `is_deleted IS false`。
- 活跃集合通常远小于历史集合，部分索引可减少存储和扫描。
- 任何希望使用这些索引的查询都应显式包含同等软删除条件。

### 3.2 服务层统一过滤不可见会话

**文件位置**：`/Users/xu/code/github/dify/api/services/conversation_service.py`  
**核心代码**（行 51-68）：

```python
        stmt = select(Conversation).where(
            Conversation.is_deleted == False,
            Conversation.app_id == app_model.id,
            Conversation.from_source == ("api" if isinstance(user, EndUser) else "console"),
            Conversation.from_end_user_id == (user.id if isinstance(user, EndUser) else None),
            Conversation.from_account_id == (user.id if isinstance(user, Account) else None),
            or_(Conversation.invoke_from.is_(None), Conversation.invoke_from == invoke_from.value),
        )
        # Check if include_ids is not None to apply filter
        if include_ids is not None:
            if len(include_ids) == 0:
                # If include_ids is empty, return empty result
                return InfiniteScrollPagination(data=[], limit=limit, has_more=False)
            stmt = stmt.where(Conversation.id.in_(include_ids))
        # Check if exclude_ids is not None to apply filter
        if exclude_ids is not None:
            if len(exclude_ids) > 0:
                stmt = stmt.where(~Conversation.id.in_(exclude_ids))
```

**解读**：
- 第 52 行首先排除软删除会话。
- 查询同时按应用、来源和用户归属限定可见性。
- 这说明软删除是读取语义的一部分，而不只是模型上的一个字段。

## 4. 关键要点总结

- 软删除支持恢复，但会把过滤责任扩散到所有读取路径
- 部分索引可只覆盖活跃行
- 硬删除适合隐私、容量和生命周期明确的场景
- 混合删除中的异步清理必须幂等且可观测

## 5. 练习题

### 练习 1：基础（必做）

为用户表设计 `deleted_at`，并让邮箱只在活跃用户中唯一。

### 练习 2：进阶

列出一个软删除方案需要修改的查询、统计和关联路径。

### 练习 3：挑战（选做）

追踪 dify 会话删除流程，区分可见性字段、主行删除和异步关联清理。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/services/conversation_service.py`
- PostgreSQL 部分索引：https://www.postgresql.org/docs/current/indexes-partial.html
- PostgreSQL DELETE：https://www.postgresql.org/docs/current/sql-delete.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
