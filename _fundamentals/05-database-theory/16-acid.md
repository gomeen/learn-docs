# 4.1 ACID 四大特性

> ACID 是数据库事务的四大特性：原子性、一致性、隔离性、持久性。任何事务型数据库都必须满足。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ACID 四特性的含义
- 知道每个特性由哪些机制保证
- 在 dify/ruoyi 中识别事务应用
- 识别常见的事务错误用法

## 📚 前置知识

- SQL 基础（INSERT/UPDATE/DELETE）
- 关系模型（01-relational-model.md）

## 1. 核心概念

### 1.1 ACID 定义

| 特性 | 英文 | 含义 | 保证机制 |
|------|------|------|---------|
| 原子性 | Atomicity | 事务中的操作要么全成功，要么全失败 | undo log / 回滚 |
| 一致性 | Consistency | 事务前后数据满足完整性约束 | 应用层 + 数据库约束 |
| 隔离性 | Isolation | 并发事务互不干扰 | 锁 + MVCC |
| 持久性 | Durability | 事务提交后数据不丢失 | redo log + WAL |

### 1.2 原子性（Atomicity）

```sql
START TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- A 减 100
UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- B 加 100
COMMIT;
-- 要么两步都成功，要么都失败
```

### 1.3 一致性（Consistency）

- 数据完整性约束（主键、外键、CHECK）
- 事务前后都必须满足所有约束
- 一致性 = 原子性 + 隔离性 + 完整性约束

### 1.4 隔离性（Isolation）

通过锁（Lock）或 MVCC 实现：
- 锁：悲观并发控制
- MVCC：乐观并发控制

### 1.5 持久性（Durability）

事务一旦 COMMIT，数据就永久保存（即使断电也不丢）：
- WAL（Write-Ahead Log）
- redo log 刷盘

## 2. 代码示例

### 2.1 模拟事务的 ACID

```python
class MiniTransaction:
    """迷你事务系统"""

    def __init__(self):
        self.in_transaction = False
        self.saved_state: dict | None = None

    def begin(self) -> None:
        self.in_transaction = True
        self.saved_state = {}  # 保存旧状态用于回滚

    def commit(self) -> None:
        if not self.in_transaction:
            raise RuntimeError("no active transaction")
        self.in_transaction = False
        self.saved_state = None

    def rollback(self) -> None:
        """原子性：回滚到事务开始前的状态"""
        if self.saved_state:
            # 恢复旧值（简化）
            print("Rollback to:", self.saved_state)
        self.in_transaction = False
        self.saved_state = None
```

### 2.2 经典案例：转账

```python
def transfer(from_id: int, to_id: int, amount: int) -> bool:
    """转账必须保证 ACID"""
    try:
        with db.session.begin():    # BEGIN
            account_a = db.session.query(Account).filter_by(id=from_id).one()
            if account_a.balance < amount:
                raise ValueError("余额不足")
            account_a.balance -= amount   # A 减
            account_b = db.session.query(Account).filter_by(id=to_id).one()
            account_b.balance += amount   # B 加
        return True
    except Exception:
        return False   # 自动 ROLLBACK
```

## 3. dify 仓库源码解读

### 3.1 dify 用 SQLAlchemy Session 管理事务

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1-40）：

```python
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.account import Account

def create_account(email: str, name: str, password: str) -> Account:
    """创建账户——自动事务管理（ACID 保证）"""
    with Session(db.engine, expire_on_commit=False) as session:
        with session.begin():    # 开启事务
            account = Account(
                email=email,
                name=name,
                password=password,
                status="uninitialized",
            )
            session.add(account)
            # 退出 with 时自动 commit（或 rollback）
        return account
```

**解读**：
- 第 11 行：`session.begin()` 开启事务
- 第 19 行：退出 `with` 时**自动 commit**——ACID 中的**原子性**保证
- 如果中间抛异常，自动 **rollback**——ACID 中的**一致性**保证
- **整体设计**：用 Python 上下文管理器显式声明事务边界

## 3.2 ruoyi 用 Spring @Transactional

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
**核心代码**（行 1-40）：

```java
@Service
@Validated
public class AdminUserServiceImpl implements AdminUserService {

    @Override
    @Transactional(rollbackFor = Exception.class)  // 关键：声明事务
    public Long createUser(UserSaveReqVO reqVO) {
        // 1. 插入用户
        AdminUserDO user = BeanUtils.toBean(reqVO, AdminUserDO.class);
        userMapper.insert(user);
        // 2. 插入用户角色
        userRoleMapper.insertBatch(user.getId(), reqVO.getRoleIds());
        return user.getId();
    }
}
```

**解读**：
- `@Transactional(rollbackFor = Exception.class)`：Spring AOP 实现事务管理
- 任何异常都触发 rollback——保证**原子性**
- **持久性**由 MySQL redo log + WAL 保证
- **整体设计**：用注解声明事务，Spring 框架自动处理 commit/rollback

## 4. 关键要点总结

- ACID = 原子性 + 一致性 + 隔离性 + 持久性
- 原子性靠 undo log / 回滚
- 持久性靠 redo log + WAL
- 隔离性靠锁或 MVCC
- dify 用 SQLAlchemy `session.begin()`，ruoyi 用 Spring `@Transactional`

## 5. 练习题

### 练习 1：基础
解释为什么"转账"业务必须用事务。

### 练习 2：进阶
在 dify 中找一个用 `session.begin()` 的方法，画出 ACID 的保证机制。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《数据库系统概念》第 14 章：事务

---

**文档版本**：v1.0
**最后更新**：2026-07-13