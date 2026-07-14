# 3.4.1 死锁：四个必要条件 / 银行家算法

> 死锁是并发编程的"陷阱"，理解它才能避免它。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解死锁的四个必要条件
- 掌握死锁预防、避免、检测、恢复策略
- 知道银行家算法的原理
- 能在 dify 中识别潜在死锁并避免

## 📚 前置知识

- 02-thread.md
- 15-lock-types.md

## 1. 核心概念

### 1.1 死锁的定义

**死锁**：两个或多个进程/线程**互相等待对方释放资源**，导致永远无法继续。

```
线程 A 持有 lock1，等待 lock2
线程 B 持有 lock2，等待 lock1
→ 互相等待 → 死锁！
```

### 1.2 死锁的四个必要条件

1. **互斥**：资源同时只能被一个线程持有
2. **持有并等待**：线程持有资源的同时等待其他资源
3. **不可剥夺**：线程持有的资源不能被强制夺走
4. **循环等待**：形成循环等待链（A 等 B，B 等 A）

**打破任一条件**就能避免死锁。

### 1.3 死锁的示例

```python
# ❌ 死锁代码
lock_a = threading.Lock()
lock_b = threading.Lock()

def thread_1():
    lock_a.acquire()
    time.sleep(0.1)
    lock_b.acquire()  # 等待 lock_b（被 thread_2 持有）

def thread_2():
    lock_b.acquire()
    time.sleep(0.1)
    lock_a.acquire()  # 等待 lock_a（被 thread_1 持有）
```

### 1.4 死锁的处理策略

| 策略 | 说明 |
|------|------|
| **预防** | 破坏四个条件之一 |
| **避免** | 银行家算法，动态检查安全状态 |
| **检测** | 定期检测死锁，发现后处理 |
| **恢复** | 杀掉某些线程、回滚操作 |

### 1.5 银行家算法

**核心思想**：分配资源前检查是否会导致死锁。

**数据结构**：
```
Max[i][j]：进程 i 对资源 j 的最大需求
Allocation[i][j]：进程 i 已分配资源 j
Available[j]：系统可用资源 j
Need[i][j] = Max[i][j] - Allocation[i][j]：进程 i 还需资源 j
```

**算法步骤**：
1. 检查请求是否 ≤ Need
2. 检查请求是否 ≤ Available
3. 试探性分配
4. 检查是否所有进程都能完成（安全性算法）
5. 如果安全 → 分配；否则 → 拒绝

### 1.6 死锁的实际处理

**工程实践**（而不是死板理论）：

1. **避免嵌套锁**：一次只持有一个锁
2. **按顺序加锁**：所有线程按相同顺序获取锁
3. **使用超时**：`try_lock(timeout=1)`
4. **使用高级同步原语**：`Semaphore`、`Condition`
5. **减少锁的粒度**：用细粒度锁

## 2. 代码示例

### 2.1 死锁演示

```python
# 文件：deadlock_demo.py
import threading
import time

lock_a = threading.Lock()
lock_b = threading.Lock()

def thread_1():
    print("Thread 1: 尝试获取 lock_a")
    with lock_a:
        print("Thread 1: 持有 lock_a")
        time.sleep(0.1)
        print("Thread 1: 尝试获取 lock_b")
        with lock_b:  # 死锁！thread 2 持有 lock_b
            print("Thread 1: 持有 lock_b")

def thread_2():
    print("Thread 2: 尝试获取 lock_b")
    with lock_b:
        print("Thread 2: 持有 lock_b")
        time.sleep(0.1)
        print("Thread 2: 尝试获取 lock_a")
        with lock_a:  # 死锁！thread 1 持有 lock_a
            print("Thread 2: 持有 lock_a")

# 运行会卡住
# t1 = threading.Thread(target=thread_1)
# t2 = threading.Thread(target=thread_2)
# t1.start(); t2.start()
# t1.join(); t2.join()
```

### 2.2 解决死锁（按顺序加锁）

```python
# 文件：no_deadlock.py
import threading
import time

lock_a = threading.Lock()
lock_b = threading.Lock()

def thread_1_safe():
    """按相同顺序获取锁 - 不会死锁。"""
    print("Thread 1: 尝试获取 lock_a")
    with lock_a:
        print("Thread 1: 持有 lock_a")
        time.sleep(0.1)
        print("Thread 1: 尝试获取 lock_b")
        with lock_b:
            print("Thread 1: 持有 lock_b")

def thread_2_safe():
    """同样的顺序。"""
    print("Thread 2: 尝试获取 lock_a")
    with lock_a:
        print("Thread 2: 持有 lock_a")
        time.sleep(0.1)
        print("Thread 2: 尝试获取 lock_b")
        with lock_b:
            print("Thread 2: 持有 lock_b")

# 不会死锁
t1 = threading.Thread(target=thread_1_safe)
t2 = threading.Thread(target=thread_2_safe)
t1.start(); t2.start()
t1.join(); t2.join()
print("完成")
```

### 2.3 银行家算法

```python
# 文件：banker.py
from typing import List

class BankerAlgorithm:
    """银行家算法模拟。"""

    def __init__(self, available: List[int], max_demand: List[List[int]],
                 allocation: List[List[int]]):
        self._available = available
        self._max = max_demand
        self._allocation = allocation
        self._need = [
            [max_demand[i][j] - allocation[i][j]
             for j in range(len(available))]
            for i in range(len(max_demand))
        ]
        self._num_processes = len(max_demand)
        self._num_resources = len(available)

    def is_safe_state(self) -> tuple[bool, list]:
        """检查是否处于安全状态，返回安全序列。"""
        work = list(self._available)
        finish = [False] * self._num_processes
        safe_sequence = []

        while len(safe_sequence) < self._num_processes:
            found = False
            for i in range(self._num_processes):
                if finish[i]:
                    continue
                # 检查 Need[i] ≤ Work
                if all(self._need[i][j] <= work[j]
                       for j in range(self._num_resources)):
                    # 假设进程 i 完成，释放资源
                    for j in range(self._num_resources):
                        work[j] += self._allocation[i][j]
                    finish[i] = True
                    safe_sequence.append(i)
                    found = True
                    break
            if not found:
                return False, []

        return True, safe_sequence

    def request_resources(self, pid: int, request: List[int]) -> bool:
        """进程 pid 请求资源 request。"""
        # 检查 Request ≤ Need
        if any(request[j] > self._need[pid][j]
               for j in range(self._num_resources)):
            return False

        # 检查 Request ≤ Available
        if any(request[j] > self._available[j]
               for j in range(self._num_resources)):
            return False

        # 试探性分配
        for j in range(self._num_resources):
            self._available[j] -= request[j]
            self._allocation[pid][j] += request[j]
            self._need[pid][j] -= request[j]

        # 检查是否安全
        is_safe, sequence = self.is_safe_state()
        if not is_safe:
            # 回滚
            for j in range(self._num_resources):
                self._available[j] += request[j]
                self._allocation[pid][j] -= request[j]
                self._need[pid][j] += request[j]
            return False

        return True

# 测试
available = [3, 3, 2]
max_demand = [
    [7, 5, 3],  # P0
    [3, 2, 2],  # P1
    [9, 0, 2],  # P2
    [2, 2, 2],  # P3
    [4, 3, 3],  # P4
]
allocation = [
    [0, 1, 0],
    [2, 0, 0],
    [3, 0, 2],
    [2, 1, 1],
    [0, 0, 2],
]
banker = BankerAlgorithm(available, max_demand, allocation)
print("安全状态:", banker.is_safe_state())
```

### 2.4 Python `with` 自动释放锁

```python
# 文件：lock_with.py
import threading

class SafeCounter:
    """线程安全的计数器 - 用 with 自动释放锁。"""
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:  # 自动获取和释放
            self._value += 1

    def get(self) -> int:
        with self._lock:
            return self._value
```

## 3. dify 仓库源码解读

### 3.1 dify 的数据库事务（避免死锁）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 100-140）：

```python
from sqlalchemy.orm import Session
from contextlib import contextmanager

class DatabaseManager:
    """数据库管理器 - dify 的事务处理。

    死锁避免策略：
    1. 按固定顺序获取行锁（先按 ID 排序再更新）
    2. 事务尽量短
    3. 用 SELECT ... FOR UPDATE NOWAIT（避免长时间等待）
    4. 用乐观锁（version 字段）
    """

    @contextmanager
    def transaction(self):
        """事务上下文管理器。"""
        session = Session(self._engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_documents(self, doc_ids: list[str], status: str):
        """批量更新文档状态 - 避免死锁。"""
        # 关键：按 ID 排序后更新，避免循环等待
        sorted_ids = sorted(doc_ids)
        with self.transaction() as session:
            for doc_id in sorted_ids:
                doc = session.query(Document).filter_by(id=doc_id).with_for_update().first()
                if doc:
                    doc.status = status

    def update_with_optimistic_lock(
        self,
        session: Session,
        doc_id: str,
        updates: dict,
    ):
        """乐观锁更新（避免悲观锁的死锁）。"""
        doc = session.query(Document).filter_by(id=doc_id).first()
        if doc is None:
            return

        # 版本号检查
        expected_version = updates.pop("_version", None)
        if expected_version is not None and doc.version != expected_version:
            raise OptimisticLockError("版本冲突")

        # 更新
        for key, value in updates.items():
            setattr(doc, key, value)
        doc.version += 1

# 死锁的常见场景：
# 1. 循环更新（A 更新 1,2；B 更新 2,1）
# 解决：按固定顺序（都按 ID 排序）

# 2. 嵌套事务
# 解决：避免在事务中调用可能开新事务的方法

# 3. 长事务
# 解决：事务尽量短，只包含必要的操作
```

**解读**：
- 第 36 行：按 ID 排序更新，避免循环等待
- 第 51 行：用版本号实现乐观锁
- **设计意图**：通过排序和乐观锁避免数据库死锁

## 4. 关键要点总结

- **死锁的 4 个条件**：互斥、持有并等待、不可剥夺、循环等待
- **打破任一条件**即可避免死锁
- **工程实践**：按顺序加锁、超时、乐观锁
- **银行家算法**：理论上的死锁避免，实际很少用
- dify 用乐观锁 + 排序更新避免死锁

## 5. 练习题

### 练习 1：基础（必做）

写两个线程互相等待对方锁的代码（产生死锁），然后改造成不死锁的版本。

### 练习 2：进阶

阅读 `api/extensions/ext_database.py`，说明 dify 为何用乐观锁 + 排序而不是悲观锁。

### 练习 3：挑战（选做）

实现银行家算法，模拟 5 个进程 3 类资源的死锁避免。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- 《操作系统概念》第 7 章 死锁
- 《Java 并发编程实战》第 10 章 避免活跃性危险

---

**文档版本**：v1.0
**最后更新**：2026-07-13