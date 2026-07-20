# 3.1.4 事务与隔离级别：ACID / MVCC

> 用事务保证一组变更的原子性，并理解 MVCC 如何在并发读写之间提供一致视图。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ACID 四个属性
- 理解 PostgreSQL MVCC 快照与行版本
- 区分 Read Committed、Repeatable Read、Serializable
- 识别并处理并发写冲突与回滚

## 📚 前置知识

- [3.1.1 SQL 基础语法](01-sql-basics.md)
- 进程并发与竞态条件基础

## 1. 核心概念

### 1.1 ACID

- **Atomicity**：事务内操作全成或全败。
- **Consistency**：约束在提交前后保持成立。
- **Isolation**：并发事务的中间状态互不泄漏到不允许的程度。
- **Durability**：提交后结果能在故障恢复后保留。

### 1.2 MVCC

PostgreSQL 更新时创建新行版本，而不是原地覆盖所有读者可见的数据。读事务依据快照判断哪个版本可见，因此普通读通常不阻塞普通写。旧版本最终由 VACUUM 回收。

### 1.3 隔离级别

| 级别 | 同一事务两次查询 | 典型处理 |
|---|---|---|
| Read Committed | 每条语句新快照 | 默认，短事务 |
| Repeatable Read | 事务级快照 | 一致报表，提交时可能冲突 |
| Serializable | 模拟串行执行 | 捕获序列化失败并重试 |

事务应尽量短；把网络调用放在持锁事务中会放大阻塞和死锁概率（行锁/版本号策略详见 [乐观锁与悲观锁](09-lock-strategy.md)）。

## 2. 代码示例

### 2.1 原子转账与失败回滚

```python
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE account (id INTEGER PRIMARY KEY, balance INTEGER)")
conn.executemany("INSERT INTO account VALUES (?, ?)", [(1, 100), (2, 50)])
conn.commit()


def transfer(source: int, target: int, amount: int) -> None:
    try:
        with conn:
            row = conn.execute(
                "SELECT balance FROM account WHERE id = ?", (source,)
            ).fetchone()
            if row is None or row[0] < amount:
                raise ValueError("insufficient balance")
            conn.execute("UPDATE account SET balance = balance - ? WHERE id = ?", (amount, source))
            conn.execute("UPDATE account SET balance = balance + ? WHERE id = ?", (amount, target))
    except Exception:
        # with conn 会自动 rollback；这里保留异常给调用方处理
        raise


transfer(1, 2, 30)
print(conn.execute("SELECT * FROM account ORDER BY id").fetchall())
```

**说明**：上下文退出时成功提交、异常回滚，两条余额更新不会只完成一半。生产系统还应校验目标账户和受影响行数。

## 3. dify 仓库源码解读

### 3.1 悲观锁保护令牌轮换

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
- 第 406-408 行注释明确指出要消除 TOCTOU 竞态。
- 第 419 行 `with_for_update()` 生成 `FOR UPDATE`，让同一业务键的并发更新串行化。
- 读取旧行和撤销旧令牌必须处在同一事务生命周期中。

### 3.2 连接归还池前的安全回滚

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`  
**核心代码**（行 35-50）：

```python
    @event.listens_for(Pool, "reset")
    def _safe_reset(dbapi_connection, connection_record, reset_state):
        if reset_state.terminate_only:
            return

        # Safe rollback for connection
        try:
            hub = gevent.get_hub()
            if hasattr(hub, "loop") and getattr(hub.loop, "in_callback", False):
                gevent.spawn_later(0, lambda: _safe_rollback(dbapi_connection))
            else:
                _safe_rollback(dbapi_connection)
        except (AttributeError, ImportError):
            _safe_rollback(dbapi_connection)

    _gevent_compatibility_setup = True
```

**解读**：
- 连接池 `reset` 事件用于清理连接上残留的事务状态。
- 在 gevent 回调上下文中延迟 rollback，避免不兼容的同步调用。
- 连接复用要求上一位使用者的事务必须被提交或回滚。

## 4. 关键要点总结

- 事务以提交/回滚为边界保证原子性
- MVCC 让读者基于快照读取合适的行版本
- 隔离越强并不等于免费，Serializable 通常需要重试
- 事务要短，并发热点可用条件更新或行锁保护

## 5. 练习题

### 练习 1：基础（必做）

为“创建订单 + 扣减库存”写出事务伪代码和失败路径。

### 练习 2：进阶

描述 Read Committed 下不可重复读，并说明 Repeatable Read 的差异。

### 练习 3：挑战（选做）

阅读 dify 的 `_upsert`，画出两个并发登录请求在有无 `FOR UPDATE` 时的时序。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/oauth_device_flow.py`
- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- PostgreSQL 事务隔离：https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL MVCC：https://www.postgresql.org/docs/current/mvcc.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
