# 4.2 事务隔离级别：RU / RC / RR / Serializable

> SQL 标准定义了 4 种隔离级别，解决不同的并发问题。隔离级别越高，并发性能越低。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 4 种隔离级别（RU、RC、RR、Serializable）
- 知道每种级别能解决哪些并发问题
- 在 dify/ruoyi 中配置隔离级别
- 做出合理的隔离级别选择

## 📚 前置知识

- 16-acid.md
- 18-mvcc.md

## 1. 核心概念

### 1.1 三种并发问题

| 问题 | 英文 | 说明 |
|------|------|------|
| 脏读 | Dirty Read | 读到其他事务未提交的数据 |
| 不可重复读 | Non-repeatable Read | 同一事务内，两次读同一行，结果不同 |
| 幻读 | Phantom Read | 同一事务内，两次范围查询，结果集不同 |

### 1.2 四种隔离级别

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | 性能 |
|---------|------|----------|------|------|
| 读未提交（RU） | ❌ 可能 | ❌ 可能 | ❌ 可能 | 最高 |
| 读已提交（RC） | ✅ 解决 | ❌ 可能 | ❌ 可能 | 高 |
| 可重复读（RR） | ✅ 解决 | ✅ 解决 | ⚠️ 部分解决* | 中 |
| 串行化（Serializable） | ✅ 解决 | ✅ 解决 | ✅ 解决 | 最低 |

*InnoDB 在 RR 级别通过 **Next-Key Lock** 大部分解决幻读（锁机制详见 [19-locks](./19-locks.md)；多版本实现见 [18-mvcc](./18-mvcc.md)）。

### 1.3 各数据库默认隔离级别

| 数据库 | 默认 | 说明 |
|--------|------|------|
| PostgreSQL | **读已提交（RC）** | 多数生产环境的折衷 |
| MySQL InnoDB | **可重复读（RR）** | 比 PG 更保守 |
| Oracle | 读已提交（RC） | 一直如此 |
| SQL Server | 读已提交（RC） | 默认 |

## 2. 代码示例

### 2.1 演示三种并发问题

```python
# 时间线演示：脏读（RU 级别）

# T1                          T2
# BEGIN
# SELECT balance
#   FROM accounts WHERE id=1   → 看到 100
#                             BEGIN
#                             UPDATE accounts
#                               SET balance=200 WHERE id=1
#                             （未提交）
# SELECT balance
#   FROM accounts WHERE id=1   → 看到 200（脏读！）
#                             ROLLBACK
```

### 2.2 各隔离级别的 SQL 设置

```sql
-- PostgreSQL
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;  -- 默认
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- MySQL
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;  -- 默认
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

## 3. dify 仓库源码解读

### 3.1 dify 使用 PostgreSQL 默认隔离级别（RC）

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow_service.py`
**核心代码**（行 1-40）：

```python
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.workflow import Workflow

def get_workflow(workflow_id: str, tenant_id: str) -> Workflow | None:
    """读工作流——默认 RC 隔离级别"""
    with Session(db.engine, expire_on_commit=False) as session:
        return session.query(Workflow).filter_by(
            tenant_id=tenant_id,
            id=workflow_id,
        ).first()
```

**解读**：
- PostgreSQL 默认 RC 隔离级别——多数业务足够
- 配合 PostgreSQL MVCC，可重复读在同一事务内也能保证
- **整体设计**：dify 信任 PG 的默认隔离级别，没有显式覆盖

### 3.2 ruoyi 的事务隔离级别配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
**核心代码**：

```properties
# application.yml 关键配置（默认）
spring.datasource.druid.default-transaction-isolation: 2
# 2 = READ_COMMITTED (MySQL)
# 4 = REPEATABLE_READ (MySQL 默认)
```

**解读**：
- ruoyi 默认使用 **READ_COMMITTED**——避免 RR 级别的间隙锁性能问题
- **设计意图**：互联网业务读写并发高，RC 比 RR 性能更好

## 4. 关键要点总结

- 4 种隔离级别：RU < RC < RR < Serializable
- PostgreSQL / Oracle / SQL Server 默认 RC
- MySQL InnoDB 默认 RR（特殊）
- 隔离级别越高，并发性能越差
- 大多数业务用 RC 即可，金融/票务系统才需要 Serializable

## 5. 练习题

### 练习 1：基础
在 PostgreSQL 中分别设置 4 种隔离级别，观察脏读/不可重复读/幻读现象。

### 练习 2：进阶
调研：dify 是否对某些关键业务（如扣费）使用 Serializable？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- PostgreSQL 事务隔离：https://www.postgresql.org/docs/current/transaction-iso.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13