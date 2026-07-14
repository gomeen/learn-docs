# 4.5 死锁检测与解决

> 死锁是并发系统的常见问题。理解死锁的产生条件和解决方法，能帮你快速定位线上故障。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解死锁的 4 个必要条件
- 知道数据库如何检测死锁
- 掌握常见的死锁解决策略
- 在 dify/ruoyi 中识别死锁风险

## 📚 前置知识

- 19-locks.md
- 17-isolation-levels.md

## 1. 核心概念

### 1.1 死锁的 4 个必要条件（缺一不可）

1. **互斥**：资源一次只能被一个事务占用
2. **占有并等待**：事务持有资源的同时等待其他资源
3. **不可剥夺**：事务已获得的资源不能被强行夺走
4. **循环等待**：事务之间形成环路等待

**任意一个条件不成立，死锁就不会发生**。

### 1.2 数据库的检测机制

**InnoDB**：
- 自动检测死锁（维护锁等待图）
- 发现环路时，**回滚代价最小的事务**（undo log 量最少）
- 把被回滚的事务返回错误：`ERROR 1213 (40001): Deadlock found`

**PostgreSQL**：
- 同样自动检测死锁
- 返回错误：`ERROR 40P01: deadlock detected`

### 1.3 死锁的 4 种解决策略

| 策略 | 方法 |
|------|------|
| 预防 | 破坏 4 个条件之一（通常按固定顺序加锁） |
| 避免 | 用事务调度算法避免进入不安全状态 |
| 检测 | 检测到死锁后回滚一个事务 |
| 恢复 | 回滚 + 重试 |

### 1.4 应用层处理死锁

```python
# 1. 捕获死锁异常
# 2. 等待随机时间
# 3. 重试整个事务
# 4. 限制重试次数
```

## 2. 代码示例

### 2.1 经典死锁场景

```python
# 两个事务互相等待对方的锁

# 事务 A                    # 事务 B
# BEGIN                     # BEGIN
# UPDATE t SET ...          # UPDATE t SET ...
#   WHERE id=1 (锁住 id=1)  #   WHERE id=2 (锁住 id=2)
# UPDATE t SET ...          # UPDATE t SET ...
#   WHERE id=2 (等待 B) ───→ #   WHERE id=1 (等待 A)
# 死锁！                     # 死锁！
```

### 2.2 应用层处理死锁

```python
import time
import random
from sqlalchemy.exc import OperationalError

def transfer_with_retry(from_id: int, to_id: int, amount: int, max_retries: int = 3) -> bool:
    """转账：捕获死锁异常，自动重试"""
    for attempt in range(max_retries):
        try:
            with Session(db.engine) as session:
                with session.begin():
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
            return True
        except OperationalError as e:
            # PostgreSQL 死锁错误码：40P01
            # MySQL 死锁错误码：1213
            if "deadlock" in str(e).lower():
                # 退避重试：随机等待避免活锁
                wait_ms = random.randint(10, 100) * (attempt + 1)
                time.sleep(wait_ms / 1000)
                continue
            raise
    return False
```

### 2.3 预防死锁：固定加锁顺序

```python
# ❌ 不同顺序加锁会导致死锁
def transfer_v1(from_id, to_id, amount):
    with db.transaction():
        lock(from_id)         # A 先锁 1 再锁 2
        lock(to_id)

# ✅ 固定顺序：按 ID 大小加锁
def transfer_v2(from_id, to_id, amount):
    with db.transaction():
        first, second = sorted([from_id, to_id])
        lock(first)          # 总是先锁小的 ID
        lock(second)
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的死锁处理

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from extensions.ext_database import db

def safe_update_account(account_id: str, updates: dict) -> bool:
    """安全的账户更新——捕获死锁并重试"""
    for retry in range(3):
        try:
            with Session(db.engine) as session:
                with session.begin():
                    account = session.query(Account).filter_by(id=account_id).with_for_update().first()
                    if not account:
                        return False
                    for key, value in updates.items():
                        setattr(account, key, value)
                    # 自动 commit
            return True
        except OperationalError as e:
            if "deadlock" in str(e).lower():
                continue  # 重试
            raise
    return False
```

**解读**：
- 第 11 行：`.with_for_update()` 显式加行锁
- 第 16-19 行：捕获死锁并重试
- **整体设计**：预防 + 检测 + 重试，三重保障

### 3.2 ruoyi 的死锁处理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**：

```java
@Aspect
@Component
public class RetryAspect {
    // Spring Retry 自动处理乐观锁冲突和死锁
    @Retryable(
        value = {DeadlockLoserDataAccessException.class, OptimisticLockException.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 100, multiplier = 2)
    )
    public Object retry(ProceedingJoinPoint pjp) throws Throwable {
        return pjp.proceed();
    }
}
```

**解读**：
- `@Retryable` 自动重试死锁和乐观锁冲突
- `backoff` 指数退避：100ms, 200ms, 400ms
- **整体设计**：用 Spring AOP + Spring Retry 自动处理

## 4. 关键要点总结

- 死锁 4 条件：互斥、占有并等待、不可剥夺、循环等待
- 数据库自动检测死锁并回滚一个事务
- 应用层策略：固定加锁顺序、降低事务粒度、捕获异常重试
- dify 用 `with_for_update()` + 手动重试
- ruoyi 用 Spring Retry + `@Retryable`

## 5. 练习题

### 练习 1：基础
构造一个死锁场景，并观察 PostgreSQL 的错误日志。

### 练习 2：进阶
阅读 ruoyi 的 `yudao-spring-boot-starter-protection` 模块，找出死锁重试的配置。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- 《数据库系统概念》第 18 章：并发控制

---

**文档版本**：v1.0
**最后更新**：2026-07-13