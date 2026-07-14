# 4.4 锁机制：行锁 / 表锁 / 间隙锁

> 锁是数据库实现并发控制的核心机制。理解锁的类型和粒度，能帮助你排查死锁和性能问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分悲观锁和乐观锁
- 掌握行锁、表锁、间隙锁的应用场景
- 知道 SELECT ... FOR UPDATE 的用法
- 在 dify/ruoyi 中识别锁的应用

## 📚 前置知识

- 16-acid.md
- 17-isolation-levels.md

## 1. 核心概念

### 1.1 悲观锁 vs 乐观锁

| 类型 | 思想 | 实现 | 适用 |
|------|------|------|------|
| 悲观锁 | 先锁再操作 | SELECT ... FOR UPDATE | 写多读少、冲突频繁 |
| 乐观锁 | 不锁，更新时检查版本 | version 字段 + CAS | 读多写少、冲突少 |

### 1.2 锁的粒度

| 锁类型 | 范围 | 开销 | 并发 |
|--------|------|------|------|
| 表锁 | 整张表 | 小 | 低 |
| 行锁 | 单行 | 大 | 高 |
| 页锁 | 介于两者之间 | 中 | 中 |

### 1.3 行锁的细分

**InnoDB 行锁**：
- **记录锁（Record Lock）**：锁定单行
- **间隙锁（Gap Lock）**：锁定区间（不存在的行），防止幻读
- **Next-Key Lock**：记录锁 + 间隙锁（左开右闭）
- **插入意向锁（Insert Intention Lock）**：插入前等待

### 1.4 MySQL InnoDB 锁矩阵

| SQL | 锁类型 |
|-----|--------|
| `SELECT ... LOCK IN SHARE MODE` | 共享锁（S 锁） |
| `SELECT ... FOR UPDATE` | 排他锁（X 锁） |
| `INSERT / UPDATE / DELETE` | 排他锁（X 锁） |

## 2. 代码示例

### 2.1 悲观锁：SELECT FOR UPDATE

```python
from sqlalchemy import text

def transfer_with_lock(from_id: int, to_id: int, amount: int) -> None:
    """悲观锁转账——防止超卖"""
    with Session(db.engine) as session:
        with session.begin():
            # 锁定账户行
            from_acc = session.execute(
                text("SELECT * FROM accounts WHERE id=:id FOR UPDATE"),
                {"id": from_id},
            ).first()
            if from_acc.balance < amount:
                raise ValueError("余额不足")

            session.execute(
                text("UPDATE accounts SET balance=balance-:a WHERE id=:id"),
                {"a": amount, "id": from_id},
            )
            session.execute(
                text("UPDATE accounts SET balance=balance+:a WHERE id=:id"),
                {"a": amount, "id": to_id},
            )
```

### 2.2 乐观锁：version 字段

```python
from sqlalchemy.orm import Session

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[float]
    version: Mapped[int] = mapped_column(default=0)  # 乐观锁版本号


def transfer_with_version(from_id: int, to_id: int, amount: int) -> bool:
    """乐观锁转账——CAS 更新"""
    with Session(db.engine) as session:
        with session.begin():
            from_acc = session.get(Account, from_id)
            current_version = from_acc.version

            # CAS 更新：version 必须等于 current_version
            result = session.execute(
                text("""
                    UPDATE accounts
                    SET balance = balance - :a, version = version + 1
                    WHERE id = :id AND version = :v
                """),
                {"a": amount, "id": from_id, "v": current_version},
            )
            if result.rowcount == 0:
                raise ValueError("乐观锁冲突")
            return True
```

### 2.3 死锁演示

```python
# 经典死锁：A 锁了行 1，等待行 2；B 锁了行 2，等待行 1

# 事务 1                    # 事务 2
# BEGIN                     # BEGIN
# UPDATE t SET ... WHERE id=1  # UPDATE t SET ... WHERE id=2
# UPDATE t SET ... WHERE id=2  # UPDATE t SET ... WHERE id=1
#   ↑ 等待 B 释放             #   ↑ 等待 A 释放
# 死锁！数据库自动检测并 rollback 一个事务
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的并发控制

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 40-70）：

```python
def update_account_quota(account_id: str, delta: int) -> None:
    """更新账户配额——依赖数据库行锁保证一致性"""
    with Session(db.engine) as session:
        with session.begin():
            account = session.query(Account).filter_by(id=account_id).first()
            if account.quota + delta < 0:
                raise ValueError("配额不足")
            account.quota += delta
            # 提交时 PostgreSQL 自动加行锁
```

**解读**：
- 通过 `with session.begin()` 让数据库自动加行锁
- PostgreSQL 默认 RC 隔离级别 + MVCC——读不阻塞写
- 写并发时通过行锁串行化

### 3.2 ruoyi 的乐观锁

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/user/AdminUserDO.java`
**核心代码**：

```java
@Data
@TableName("system_users")
public class AdminUserDO extends TenantBaseDO {
    @TableField(value = "version", fill = FieldFill.INSERT)
    private Integer version;  // MyBatis Plus 乐观锁
}
```

**Mapper 用法**（MyBatis Plus 自动加 WHERE version=?）：

```java
@Override
public void updateUser(AdminUserDO user) {
    // MyBatis Plus 自动在 UPDATE 语句加 WHERE version=?
    // UPDATE system_users SET ..., version=version+1 WHERE id=? AND version=?
    userMapper.updateById(user);
}
```

**解读**：
- `@TableField` + MyBatis Plus 插件自动实现乐观锁
- UPDATE 时自动加 `WHERE version=?`，更新后 `version+1`
- 影响行数 = 0 表示冲突，需要重试

## 4. 关键要点总结

- 悲观锁：先锁再操作（`SELECT ... FOR UPDATE`）
- 乐观锁：version 字段 + CAS（MyBatis Plus `@TableField` 自动实现）
- InnoDB 行锁：记录锁 + 间隙锁 + Next-Key Lock
- 死锁：循环等待，数据库自动检测并回滚一个事务
- dify 用 PostgreSQL 行锁，ruoyi 用 MyBatis Plus 乐观锁

## 5. 练习题

### 练习 1：基础
解释为什么"库存扣减"必须用锁（不能靠应用层判断）。

### 练习 2：进阶
阅读 ruoyi 的 `AdminUserDO.java`，找到 version 字段对应的乐观锁配置。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- MySQL 锁文档：https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13