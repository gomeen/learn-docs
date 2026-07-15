# 3.1.2 多表查询：JOIN / 子查询 / UNION

> 把规范化后的多张表重新组合成业务视图，并根据问题选择连接、子查询或集合运算。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 INNER JOIN 与 LEFT JOIN 的结果差异
- 编写相关与非相关子查询
- 使用 UNION / UNION ALL 合并同构结果集
- 能看懂 dify 统计、导出和分页查询中的多表组合

## 📚 前置知识

- [3.1.1 SQL 基础语法](./01-sql-basics.md)
- 主键与外键的基本概念（约束设计详见 [主键、外键、唯一约束](./08-database-keys.md)）

## 1. 核心概念

### 1.1 JOIN：按关系横向扩展列

`INNER JOIN` 只保留两侧都匹配的行；`LEFT JOIN` 保留左表全部行，右侧没有匹配时填 `NULL`。连接条件应写在 `ON` 中，结果过滤写在 `WHERE` 中；对 LEFT JOIN 的右表条件放错位置，可能意外退化成 INNER JOIN。

### 1.2 子查询：把查询当作临时数据源

子查询可出现在 `FROM`、`WHERE` 或标量表达式中。`EXISTS` 适合判断“是否存在”，聚合后的子查询适合先缩小数据，再参与外层连接。需要注意相关子查询可能对外层每一行重复执行。

### 1.3 UNION：纵向合并同构行

`UNION` 去重，`UNION ALL` 保留重复且通常更快。两侧列数必须相同，对应列类型要兼容。

| 目标 | 首选 |
|---|---|
| 获取关联对象的字段 | JOIN |
| 判断是否存在关联记录 | EXISTS |
| 合并两个来源的同构记录 | UNION ALL |

## 2. 代码示例

### 2.1 组合用户、订单与归档订单

```sql
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount NUMERIC NOT NULL
);
CREATE TABLE archived_orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount NUMERIC NOT NULL
);

SELECT u.name, COALESCE(SUM(o.amount), 0) AS total
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
WHERE EXISTS (
    SELECT 1 FROM orders x WHERE x.user_id = u.id
)
GROUP BY u.id, u.name;

SELECT id, user_id, amount, 'active' AS source FROM orders
UNION ALL
SELECT id, user_id, amount, 'archive' AS source FROM archived_orders;
```

**说明**：第一个查询展示 LEFT JOIN、EXISTS 和聚合；第二个查询用 UNION ALL 合并结构一致的活动与归档订单。

## 3. dify 仓库源码解读

### 3.1 反馈导出的多表连接

**文件位置**：`/Users/xu/code/github/dify/api/services/feedback_service.py`  
**核心代码**（行 46-56）：

```python
        # Build base query
        stmt = (
            select(MessageFeedback, Message, Conversation, App, Account)
            .join(Message, MessageFeedback.message_id == Message.id)
            .join(Conversation, MessageFeedback.conversation_id == Conversation.id)
            .join(App, MessageFeedback.app_id == App.id)
            .outerjoin(Account, MessageFeedback.from_account_id == Account.id)
            .where(MessageFeedback.app_id == app_id)
        )

        # Apply filters
```

**解读**：
- 第 47 行一次选择五个 ORM 实体。
- 第 48-50 行使用内连接要求消息、会话和应用都存在。
- 第 51 行使用 `outerjoin`，即使反馈没有账户也保留该行。

### 3.2 用子查询统计剩余分页记录

**文件位置**：`/Users/xu/code/github/dify/api/services/conversation_service.py`  
**核心代码**（行 85-101）：

```python
        query_stmt = stmt.order_by(sort_direction(getattr(Conversation, sort_field))).limit(limit)
        conversations = session.scalars(query_stmt).all()

        has_more = False
        if len(conversations) == limit:
            current_page_last_conversation = conversations[-1]
            rest_filter_condition = cls._build_filter_condition(
                sort_field=sort_field,
                sort_direction=sort_direction,
                reference_conversation=current_page_last_conversation,
            )
            count_stmt = select(func.count()).select_from(stmt.where(rest_filter_condition).subquery())
            rest_count = session.scalar(count_stmt) or 0
            if rest_count > 0:
                has_more = True

        return InfiniteScrollPagination(data=conversations, limit=limit, has_more=has_more)
```

**解读**：
- 第 85 行先完成排序和限制，形成当前页查询。
- 第 96 行把追加游标条件的语句转成子查询，再从它执行 `COUNT(*)`。
- 这避免加载剩余实体，只回答是否还有下一页。

## 4. 关键要点总结

- JOIN 横向组合关联表，连接类型决定未匹配行是否保留
- EXISTS 常用于存在性判断，子查询可先过滤或聚合
- UNION 会去重，UNION ALL 更直接、更高效
- 多表查询应关注基数膨胀和 NULL 语义

## 5. 练习题

### 练习 1：基础（必做）

写一个 LEFT JOIN，列出所有用户及其订单数量，包括零订单用户。

### 练习 2：进阶

把“至少有一条已完成订单”的 JOIN 查询改写为 EXISTS。

### 练习 3：挑战（选做）

设计活动表与归档表的 UNION ALL 查询，并说明何时需要额外去重。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/feedback_service.py`
- `/Users/xu/code/github/dify/api/services/conversation_service.py`
- PostgreSQL 表表达式：https://www.postgresql.org/docs/current/queries-table-expressions.html
- PostgreSQL UNION：https://www.postgresql.org/docs/current/queries-union.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
