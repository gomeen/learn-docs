# 3.2.4 乐观锁与悲观锁

> 根据冲突概率和临界区成本，在版本校验与数据库行锁之间选择并发控制策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释丢失更新与 TOCTOU 竞态
- 实现版本号/哈希乐观锁
- 使用 SELECT FOR UPDATE 悲观锁
- 分析 dify 工作流同步和令牌轮换的不同策略

## 📚 前置知识

- [3.1.4 事务与隔离级别](./04-sql-transaction.md)
- HTTP 冲突响应与重试基础

## 1. 核心概念

### 1.1 乐观锁

乐观锁假设冲突少：读取时带出 `version` 或内容哈希，更新时要求旧版本仍相等。若影响行数为 0，说明发生冲突，调用方重新读取并合并。它不长期持锁，适合用户编辑和跨请求流程。

### 1.2 悲观锁

悲观锁假设临界区会冲突：`SELECT ... FOR UPDATE` 锁定目标行直到事务结束。适合短小、必须串行的余额扣减、令牌轮换等路径，但会等待、死锁，并降低吞吐。

### 1.3 选择原则

| 场景 | 推荐 |
|---|---|
| 人工编辑，冲突少，跨 HTTP 请求 | 乐观锁 |
| 热点计数或唯一活动记录轮换 | 悲观锁/原子语句 |
| 可交换累加 | 数据库原子 UPDATE |

无论哪种策略，都应限制事务长度并定义冲突重试或错误反馈。

## 2. 代码示例

### 2.1 用版本号实现乐观锁

```python
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, body TEXT, version INTEGER)")
conn.execute("INSERT INTO docs VALUES (1, 'draft', 1)")
conn.commit()


def update_doc(doc_id: int, old_version: int, new_body: str) -> int:
    with conn:
        cursor = conn.execute(
            """UPDATE docs
               SET body = ?, version = version + 1
               WHERE id = ? AND version = ?""",
            (new_body, doc_id, old_version),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("concurrent modification")
        return old_version + 1


next_version = update_doc(1, 1, "first edit")
print(next_version)
try:
    update_doc(1, 1, "stale edit")
except RuntimeError as error:
    print(error)
```

**说明**：更新条件包含旧版本，过期客户端不会覆盖新内容。真实 API 可把冲突映射为 409，并返回最新版本。

## 3. dify 仓库源码解读

### 3.1 工作流内容哈希作为乐观锁令牌

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow_service.py`  
**核心代码**（行 313-333）：

```python
        self,
        *,
        app_model: App,
        graph: dict[str, Any],
        features: dict[str, Any],
        unique_hash: str | None,
        account: Account,
        environment_variables: Sequence[VariableBase],
        conversation_variables: Sequence[VariableBase],
        session: Session,
    ) -> Workflow:
        """
        Sync draft workflow
        :raises WorkflowHashNotEqualError
        """
        # fetch draft workflow by app_model
        workflow = self.get_draft_workflow(app_model=app_model, session=session)

        if workflow and workflow.unique_hash != unique_hash:
            raise WorkflowHashNotEqualError()

```

**解读**：
- 调用方提交此前读取到的 `unique_hash`。
- 第 332-333 行在写入前比较当前工作流哈希，不一致立即报冲突。
- 这种策略适合画布编辑：事务不需要覆盖用户思考时间。

### 3.2 FOR UPDATE 串行化令牌轮换

**文件位置**：`/Users/xu/code/github/dify/api/services/oauth_device_flow.py`  
**核心代码**（行 406-427）：

```python
    # (subject, client, device) serialize here rather than both reading
    # the same prior and producing two active tokens (TOCTOU race).
    prior = session.execute(
        select(OAuthAccessToken.id, OAuthAccessToken.token_hash)
        .where(
            OAuthAccessToken.subject_email == subject_email,
            OAuthAccessToken.subject_issuer == subject_issuer,
            OAuthAccessToken.client_id == client_id,
            OAuthAccessToken.device_label == device_label,
            OAuthAccessToken.revoked_at.is_(None),
        )
        .limit(1)
        .with_for_update()
    ).first()
    old_hash = prior.token_hash if prior else None

    # Revoke any existing active token for this (subject, client, device) combination.
    # PostgreSQL's ON CONFLICT doesn't support partial unique indexes (those with WHERE clauses),
    # so we use a manual revoke-then-insert pattern instead.
    if prior:
        session.execute(update(OAuthAccessToken).where(OAuthAccessToken.id == prior.id).values(revoked_at=func.now()))

```

**解读**：
- 查询锁定当前活动令牌行，直到事务结束。
- 并发请求不能同时读取同一个“旧活动令牌”并各自插入新令牌。
- 这是短临界区，悲观锁比让调用方合并冲突更符合业务。

## 4. 关键要点总结

- 乐观锁通过版本/哈希检测冲突，失败后由调用方重试或合并
- 悲观锁通过行锁让临界区串行执行
- 冲突少且跨请求用乐观锁，短热点事务可用悲观锁
- 必须定义超时、死锁和冲突处理

## 5. 练习题

### 练习 1：基础（必做）

给文章更新接口增加 `version` 条件，并检查 rowcount。

### 练习 2：进阶

写出两事务使用 `FOR UPDATE` 扣减同一库存的时序。

### 练习 3：挑战（选做）

比较 dify 两段源码中冲突发现时机和用户体验。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow_service.py`
- `/Users/xu/code/github/dify/api/services/oauth_device_flow.py`
- PostgreSQL 显式锁：https://www.postgresql.org/docs/current/explicit-locking.html
- PostgreSQL SELECT 锁子句：https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
