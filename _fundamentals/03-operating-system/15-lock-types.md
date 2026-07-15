# 3.4.2 乐观锁 vs 悲观锁

> 乐观锁和悲观锁是并发控制的两种哲学。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分乐观锁和悲观锁的适用场景
- 理解版本号机制和 [CAS](./16-cas.md)
- 知道数据库的锁机制
- 能在 dify 中识别锁的应用（死锁见 [14-deadlock](./14-deadlock.md)）

## 📚 前置知识

- 14-deadlock.md
- 16-cas.md

## 1. 核心概念

### 1.1 悲观锁（Pessimistic Lock）

**哲学**：假设**冲突一定会发生**，先加锁再操作。

```sql
BEGIN;
SELECT * FROM accounts WHERE id = 1 FOR UPDATE;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;
```

**特点**：
- 阻塞其他事务
- 适合**写多**的场景
- 实现：行锁、表锁、读写锁

### 1.2 乐观锁（Optimistic Lock）

**哲学**：假设**冲突很少发生**，不加锁，更新时检查冲突。

```sql
-- 不加锁读
SELECT version, balance FROM accounts WHERE id = 1;
-- version = 1, balance = 1000

-- 更新时检查 version
UPDATE accounts
SET balance = 900, version = 2
WHERE id = 1 AND version = 1;
-- 如果 affected_rows = 0，说明 version 已被其他事务修改 → 重试
```

**特点**：
- 不阻塞读
- 适合**读多写少**
- 实现：版本号、CAS

### 1.3 两种锁的对比

| 维度 | 悲观锁 | 乐观锁 |
|------|--------|--------|
| 哲学 | 假设冲突必发生 | 假设冲突少发生 |
| 实现 | 行锁、表锁 | 版本号、CAS |
| 阻塞 | 阻塞其他事务 | 不阻塞 |
| 性能 | 写多快，读慢 | 读多快，写可能重试 |
| 死锁 | 可能 | **不会** |
| 适用 | 写多 | 读多写少 |

### 1.4 乐观锁的实现方式

#### 版本号机制

```python
class OptimisticEntity:
    def __init__(self, version: int = 0):
        self.version = version

    def update(self, changes: dict) -> bool:
        expected_version = self.version
        # SQL: UPDATE table SET ..., version = version + 1
        #      WHERE id = ? AND version = ?
        if update_success:
            self.version += 1
            return True
        return False  # 重试
```

#### CAS（Compare-And-Swap）

```python
def cas(old_value, new_value):
    """原子操作：比较并交换。"""
    if current_value == old_value:
        current_value = new_value
        return True
    return False
```

### 1.5 数据库的锁机制

**行级锁**：
- `SELECT ... FOR UPDATE`：悲观锁
- `SELECT ... FOR UPDATE NOWAIT`：立即返回，不等待
- `SELECT ... FOR UPDATE SKIP LOCKED`：跳过已锁定的行

**乐观锁**：
- version 列
- UPDATE WHERE version = old_version

### 1.6 实际应用

| 场景 | 选择 | 原因 |
|------|------|------|
| 数据库事务 | 悲观锁 | 强一致性 |
| 计数器 | 乐观锁 | 冲突少 |
| 电商库存 | 悲观锁 | 不能超卖 |
| 文章点赞 | 乐观锁 | 高并发读 |
| 配置中心 | 乐观锁 | 很少改 |

## 2. 代码示例

### 2.1 悲观锁实现（数据库）

```python
# 文件：pessimistic_lock.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

def update_account_pessimistic(account_id: int, amount: float) -> None:
    """悲观锁更新账户余额。"""
    engine = create_engine("postgresql://...")
    with Session(engine) as session:
        # 加行锁
        result = session.execute(
            text("SELECT balance FROM accounts WHERE id = :id FOR UPDATE"),
            {"id": account_id},
        )
        balance = result.scalar()

        # 业务逻辑
        new_balance = balance - amount
        if new_balance < 0:
            raise ValueError("余额不足")

        # 更新
        session.execute(
            text("UPDATE accounts SET balance = :balance WHERE id = :id"),
            {"balance": new_balance, "id": account_id},
        )
        session.commit()
```

### 2.2 乐观锁实现

```python
# 文件：optimistic_lock.py
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

@dataclass
class Document:
    id: str
    content: str
    version: int = 0

def update_document_optimistic(
    session: Session,
    doc_id: str,
    new_content: str,
) -> bool:
    """乐观锁更新文档。"""
    # 读当前 version
    result = session.execute(
        text("SELECT version FROM documents WHERE id = :id"),
        {"id": doc_id},
    )
    current_version = result.scalar()
    if current_version is None:
        return False

    # 带 version 条件更新
    result = session.execute(
        text("""
            UPDATE documents
            SET content = :content, version = version + 1
            WHERE id = :id AND version = :version
        """),
        {"id": doc_id, "content": new_content, "version": current_version},
    )

    if result.rowcount == 0:
        # 版本冲突
        return False
    session.commit()
    return True

def update_with_retry(doc_id: str, new_content: str, max_retries: int = 3) -> bool:
    """带重试的乐观锁更新。"""
    engine = create_engine("postgresql://...")
    for _ in range(max_retries):
        with Session(engine) as session:
            if update_document_optimistic(session, doc_id, new_content):
                return True
        time.sleep(0.01)  # 重试前短暂等待
    return False
```

### 2.3 内存中的乐观锁（CAS）

```python
# 文件：cas_demo.py
import threading

class OptimisticCounter:
    """用 CAS 实现线程安全的计数器。"""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()  # 实际不需要锁

    def increment(self) -> bool:
        """CAS 操作：原子地 +1。"""
        while True:
            old_value = self._value
            new_value = old_value + 1
            # 模拟 CAS（实际硬件指令）
            with self._lock:
                if self._value == old_value:
                    self._value = new_value
                    return True
            # 值变了，重试

# 测试
counter = OptimisticCounter()
threads = [threading.Thread(target=lambda: [counter.increment() for _ in range(1000)])
           for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(f"counter = {counter._value}")  # 应该是 10000
```

## 3. dify 仓库源码解读

### 3.1 dify 的文档更新（乐观锁）

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`
**核心代码**（行 50-90）：

```python
from sqlalchemy import Column, String, Integer, Text

class Document(Base):
    """数据集文档模型 - dify 的核心数据。

    用乐观锁（version 字段）避免并发更新冲突。
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    dataset_id = Column(String, index=True)
    content = Column(Text)
    # ... 其他字段
    version = Column(Integer, default=0, nullable=False)  # 乐观锁版本号


# dify 的文档处理场景：
# 1. 用户上传新文档 → 创建记录
# 2. 文档被多个 worker 处理（分块、embedding）
# 3. 文档被多个用户查询
# 4. 文档状态更新（待处理 → 处理中 → 已完成）

# 多 worker 并发更新同一个文档的状态：
# - worker A 读到 version=0，准备更新到 version=1
# - worker B 也读到 version=0，准备更新到 version=1
# - A 先更新成功，version=1
# - B 更新时 WHERE version=0 不匹配 → rowcount=0 → 重试

# dify 的代码实现：
def update_document_status(
    self,
    doc_id: str,
    new_status: str,
    max_retries: int = 3,
) -> bool:
    """乐观锁更新文档状态。"""
    for attempt in range(max_retries):
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            return False
        old_version = doc.version
        doc.status = new_status
        doc.version = old_version + 1
        try:
            session.commit()
            return True
        except StaleDataError:
            # 版本冲突，重试
            session.rollback()
            continue
    return False
```

**解读**：
- 第 16 行：`version` 字段实现乐观锁
- 第 49 行：捕获 `StaleDataError`（版本冲突）
- **设计意图**：多 worker 并发处理文档，用乐观锁避免冲突

## 4. 关键要点总结

- **悲观锁**：假设冲突必发生，加锁后再操作
- **乐观锁**：假设冲突少，更新时检查
- **实现**：版本号、CAS
- **数据库**：行锁（悲观） + version 字段（乐观）
- **选择**：写多用悲观，读多用乐观
- dify 用乐观锁管理文档状态

## 5. 练习题

### 练习 1：基础（必做）

实现一个线程安全的计数器，分别用悲观锁（Lock）和乐观锁（CAS）实现，对比性能。

### 练习 2：进阶

阅读 `api/models/dataset.py`，说明 dify 为何在文档模型用乐观锁而不是悲观锁。

### 练习 3：挑战（选做）

实现一个分布式乐观锁（用 Redis SETNX + 版本号），保证跨进程的一致性。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/dataset.py`
- 《数据库系统概念》第 16 章 并发控制
- 《Java 并发编程实战》第 15 章 原子变量与非阻塞同步

---

**文档版本**：v1.0
**最后更新**：2026-07-13