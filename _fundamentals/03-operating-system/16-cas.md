# 3.4.3 CAS（Compare-And-Swap）

> CAS 是乐观锁的底层实现，是无锁编程的基石。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 CAS 的原理和 ABA 问题
- 掌握 Java AtomicInteger 等原子类的实现
- 能在 dify 中识别 CAS 的应用（Redis 原子操作）；可见性相关见 [17-memory-model](./17-memory-model.md) / [18-volatile](./18-volatile.md)

## 📚 前置知识

- [15-lock-types](./15-lock-types.md)

## 1. 核心概念

### 1.1 CAS 定义

**CAS**（Compare-And-Swap）是**硬件原子指令**：

```c
bool CAS(int *addr, int expected, int new_value) {
    if (*addr == expected) {
        *addr = new_value;
        return true;
    }
    return false;
}
```

**三要素**：
1. **内存地址**
2. **期望值**
3. **新值**

### 1.2 CAS 的工作流程

```
线程 A：CAS(&counter, 5, 6)
1. 读 counter = 5（期望值）
2. 比较 counter 是否仍为 5
3. 是 → counter = 6，返回 true
4. 否 → 返回 false（重试）

线程 B：CAS(&counter, 5, 7)
1. 读 counter = 6（不是 5）
2. 返回 false（重试）
```

### 1.3 CAS vs 锁

| 维度 | CAS | 锁 |
|------|-----|-----|
| 阻塞 | **无**（自旋） | 阻塞 |
| 上下文切换 | **0 次** | 多次 |
| 适用 | 短临界区 | 长临界区 |
| 复杂度 | 复杂（ABA 问题） | 简单 |

### 1.4 ABA 问题

```
1. 线程 A 读 value = 5
2. 线程 B 修改 value = 6
3. 线程 B 又修改 value = 5  ← ABA！
4. 线程 A CAS(value, 5, 8) → 成功，但实际中间被改过
```

**解决**：加版本号

```c
bool CAS(VersionedValue *addr, VersionedValue expected, VersionedValue new) {
    if (addr->value == expected.value && addr->version == expected.version) {
        addr->version++;
        addr->value = new.value;
        return true;
    }
    return false;
}
```

### 1.5 CPU 指令

- **x86**：`cmpxchg` 指令
- **ARM**：`ldrex` + `strex`（load-linked / store-conditional）

### 1.6 Java 的 CAS 应用

**java.util.concurrent.atomic**：
- `AtomicInteger`
- `AtomicLong`
- `AtomicReference`

**底层**：Unsafe 类的 CAS 操作

### 1.7 Python 的 CAS

**没有真正的硬件 CAS**，但可以用：
- `threading.Lock`：悲观锁
- `queue.Queue`：线程安全队列
- `multiprocessing.Value`：原子操作

**Redis**：单线程模型，命令本身就是原子的（INCR、SETNX）。

## 2. 代码示例

### 2.1 模拟 CAS

```python
# 文件：cas_simulate.py
import threading

class SimulatedCAS:
    """用 Lock 模拟 CAS（实际生产用硬件指令）。"""

    def __init__(self, initial_value: int):
        self._value = initial_value
        self._lock = threading.Lock()

    def compare_and_set(self, expected: int, new_value: int) -> bool:
        """CAS：原子比较并交换。"""
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False

    def get(self) -> int:
        return self._value


# 测试
cas = SimulatedCAS(0)

def increment():
    while True:
        old = cas.get()
        if cas.compare_and_set(old, old + 1):
            break

threads = [threading.Thread(target=lambda: [increment() for _ in range(1000)])
           for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(f"counter = {cas.get()}")  # 应该是 10000
```

### 2.2 ABA 问题演示

```python
# 文件：aba_demo.py
class NaiveCAS:
    """无版本号的 CAS - 有 ABA 问题。"""

    def __init__(self):
        self._value = 0

    def cas(self, expected, new_value):
        if self._value == expected:
            self._value = new_value
            return True
        return False

cas = NaiveCAS()

# 线程 1
cas.cas(0, 1)
# 线程 2 修改两次
cas.cas(1, 0)  # 改回 0（ABA！）
# 线程 1 再次 CAS
print(cas.cas(0, 5))  # 成功！但实际中间被改过
```

### 2.3 带版本号的 CAS

```python
# 文件：versioned_cas.py
class VersionedCAS:
    """带版本号的 CAS - 解决 ABA 问题。"""

    def __init__(self):
        self._value = 0
        self._version = 0

    def cas(self, expected_value, expected_version, new_value):
        """CAS：value 和 version 都要匹配。"""
        if self._value == expected_value and self._version == expected_version:
            self._value = new_value
            self._version += 1
            return True
        return False

# 测试 ABA
cas = VersionedCAS()
cas.cas(0, 0, 1)
cas.cas(1, 1, 0)  # version 变成 1
# 现在 expected_version = 0，匹配不上
print(cas.cas(0, 0, 5))  # False！ABA 被解决
```

### 2.4 Redis 原子操作

```python
# 文件：redis_atomic.py
import redis

client = redis.Redis()

# INCR 是原子的（基于 CAS）
client.set("counter", 0)
client.incr("counter")  # 原子 +1
client.incrby("counter", 10)  # 原子 +10
print(client.get("counter"))  # 11

# SETNX 是原子的（基于 CAS）
# 如果 key 不存在则设置（分布式锁基础）
if client.setnx("lock:resource", "owner"):
    print("获取锁成功")
    # ... 业务逻辑
    client.delete("lock:resource")  # 释放锁
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 分布式锁（CAS 思想）

**文件位置**：`/Users/xu/code/github/dify/api/libs/rate_limiter.py`
**核心代码**（行 1-50）：

```python
import redis
import time

class DistributedLock:
    """基于 Redis 的分布式锁 - 用 CAS 思想。

    Redis 单线程执行命令，SETNX 等命令天然原子。
    这是 CAS 在分布式场景的应用。
    """

    def __init__(self, redis_client: redis.Redis, key: str):
        self._redis = redis_client
        self._key = f"lock:{key}"
        self._owner = f"owner-{time.time()}-{threading.get_ident()}"

    def acquire(self, ttl: int = 30, retry: int = 3) -> bool:
        """获取锁 - 用 SET NX EX（原子操作）。"""
        # SETNX 原子操作：key 不存在则设置
        # 等价于 CAS(key, None, owner)
        result = self._redis.set(
            self._key,
            self._owner,
            nx=True,  # 只在不存在时设置
            ex=ttl,   # 自动过期
        )
        return bool(result)

    def release(self) -> None:
        """释放锁 - 用 Lua 脚本保证原子性。"""
        # Lua 脚本：检查 owner 后删除（避免释放别人的锁）
        lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self._redis.eval(lua, 1, self._key, self._owner)

    def renew(self, ttl: int = 30) -> bool:
        """续约锁 - 原子操作。"""
        # Lua 脚本：检查 owner 后续约
        lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = self._redis.eval(lua, 1, self._key, self._owner, str(ttl))
        return bool(result)


# dify 的应用场景：
# 1. 防止重复触发工作流（同一 workflow_run_id）
# 2. 防止重复处理文档（同一 document_id）
# 3. 限流（同一用户的请求去重）


# 使用示例：
def trigger_workflow_with_lock(workflow_id: str):
    """用分布式锁防止重复触发。"""
    lock = DistributedLock(redis_client, f"workflow:{workflow_id}")
    if lock.acquire(ttl=60):
        try:
            # 业务逻辑
            run_workflow(workflow_id)
        finally:
            lock.release()
    else:
        raise WorkflowAlreadyRunningError()
```

**解读**：
- 第 23 行：`SET NX EX` 是 Redis 的原子操作（CAS 思想）
- 第 31 行：用 Lua 脚本保证 owner 检查和删除的原子性
- **设计意图**：用 Redis 分布式锁防止重复触发

## 4. 关键要点总结

- **CAS**：硬件原子指令，**无锁并发**
- **ABA 问题**：用版本号解决
- **Java**：AtomicInteger 等基于 CAS
- **Redis**：单线程，命令原子（SETNX、INCR）
- **Python**：没有硬件 CAS，但可用 Redis 实现
- dify 用 Redis 分布式锁防止重复触发

## 5. 练习题

### 练习 1：基础（必做）

实现一个无锁的线程安全计数器，用 CAS（模拟）。

### 练习 2：进阶

阅读 `api/libs/rate_limiter.py`，说明 dify 为何用 Redis 分布式锁而不是进程内 Lock。

### 练习 3：挑战（选做）

实现一个**分布式限流器**（滑动窗口算法），用 Redis + Lua 保证原子性。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/rate_limiter.py`
- 《Java 并发编程实战》第 15 章 原子变量
- Redis 分布式锁：https://redis.io/docs/manual/patterns/distributed-locks/

---

**文档版本**：v1.0
**最后更新**：2026-07-13