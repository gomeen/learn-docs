# 4.2.3 分布式锁：RedLock 与 SETNX

> 多台机器需要互斥访问共享资源时，分布式锁是必备工具。Redis SETNX 是最简单方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式锁的核心需求（互斥、安全、死锁避免）
- 掌握 `SETNX + EXPIRE` 的实现方式
- 了解 RedLock 算法及其争议
- 在 dify 中用 `redis_client.lock()` 实现分布式锁

## 📚 前置知识

- Redis 基础
- 分布式系统基本概念
- 01-redis-data-structures.md

## 1. 核心概念

### 1.1 为什么需要分布式锁？

单机程序用 `threading.Lock()` 即可，多进程/多机器就需要**分布式锁**。

**典型场景**：
- 防止重复扣款（同一订单只扣一次）
- 秒杀场景（库存只有 1 件，不能超卖）
- 定时任务多机部署（不能重复执行）

### 1.2 分布式锁的核心需求

1. **互斥**：任意时刻只有一个客户端持有锁
2. **不死锁**：客户端崩溃后锁能自动释放
3. **容错**：只要多数 Redis 节点存活就能加锁
4. **可重入**：同一线程可多次加锁

### 1.3 最简单实现：SETNX + EXPIRE

```bash
SETNX lock:order:1  # 不存在则设置
EXPIRE lock:order:1 30  # 30 秒后过期
```

**问题**：两步操作非原子，SETNX 成功但 EXPIRE 失败 → 锁永久不释放。

### 1.4 原子实现：SET NX EX

```bash
SET lock:order:1 <token> NX EX 30
```

一条命令完成加锁和设置过期时间，**原子**。

### 1.5 释放锁：必须验证 token

```python
# ❌ 错误：直接 DEL
r.delete("lock:order:1")  # 可能误删别人的锁！

# ✅ 正确：用 Lua 脚本验证 token
script = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""
r.eval(script, 1, "lock:order:1", "<token>")
```

### 1.6 RedLock 算法（争议）

Redis 作者 antirez 提出的**多 Redis 实例**分布式锁算法：

```
1. 获取当前时间 T1
2. 依次向 N 个（>=3）独立 Redis 实例申请锁
3. 多数实例成功 + 总耗时 < 锁 TTL → 加锁成功
4. 实际持锁时间 = TTL - (T2 - T1)
```

**争议**：Martin Kleppmann 认为 RedLock **不严谨**（依赖时钟、GC 停顿可能导致问题），建议用 **ZooKeeper / etcd**。

**实践**：Redis 锁在 99% 场景下够用，强一致场景用 ZooKeeper。

## 2. 代码示例

### 2.1 redis-py 内置分布式锁

```python
import redis
import uuid

r = redis.Redis(decode_responses=True)

# redis-py 内置 Lock 实现
lock = r.lock("lock:order:1", timeout=30, blocking=True, blocking_timeout=5)

if lock.acquire():
    try:
        # 临界区
        process_order(1)
    finally:
        lock.release()
else:
    print("获取锁超时")
```

### 2.2 手动实现：SET NX EX

```python
import uuid
import time

def acquire_lock(r, lock_key, ttl=30):
    token = str(uuid.uuid4())
    # NX=True：仅当 key 不存在时设置
    # EX=ttl：过期时间（秒）
    success = r.set(lock_key, token, nx=True, ex=ttl)
    return token if success else None

def release_lock(r, lock_key, token):
    # Lua 脚本：验证 token 后删除
    script = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """
    return r.eval(script, 1, lock_key, token)

# 使用
def process_order(order_id):
    lock_key = f"lock:order:{order_id}"
    token = acquire_lock(r, lock_key, ttl=30)
    if token is None:
        raise Exception("获取锁失败")

    try:
        # 临界区业务
        db.execute("UPDATE orders SET status = 'paid' WHERE id = %s", order_id)
    finally:
        release_lock(r, lock_key, token)
```

### 2.3 可重入锁

```python
class ReentrantLock:
    """可重入分布式锁（用 Hash 存计数器）"""
    def __init__(self, r, lock_key, ttl=30):
        self.r = r
        self.lock_key = lock_key
        self.ttl = ttl
        self.token = str(uuid.uuid4())

    def acquire(self):
        # 用 Hash 存 {token: count}
        if self.r.hexists(self.lock_key, self.token):
            # 已持有，增加计数
            self.r.hincrby(self.lock_key, self.token, 1)
            return True

        # 第一次获取
        if self.r.hsetnx(self.lock_key, self.token, 1):
            self.r.expire(self.lock_key, self.ttl)
            return True
        return False

    def release(self):
        # 减少计数
        count = self.r.hincrby(self.lock_key, self.token, -1)
        if count <= 0:
            # 计数为 0，删除字段
            self.r.hdel(self.lock_key, self.token)
```

### 2.4 常见错误：锁过期但业务未完成

```python
# ❌ 错误：业务执行太久，锁自动过期，其他客户端加锁
def slow_task():
    lock = r.lock("lock:slow", timeout=10)
    lock.acquire()
    time.sleep(30)  # 业务执行 30 秒，锁 10 秒就过期了
    lock.release()  # 此时可能已不是自己的锁

# ✅ 正确：后台线程续期（Watch Dog）
def task_with_renewal():
    lock = r.lock("lock:slow", timeout=10)
    lock.acquire()

    def renew():
        while not lock.locked():
            r.expire("lock:slow", 10)
            time.sleep(5)

    threading.Thread(target=renew, daemon=True).start()

    try:
        time.sleep(30)  # 锁会自动续期
    finally:
        lock.release()
```

## 3. dify 仓库源码解读

### 3.1 RedisClientWrapper.lock() 方法

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 147-163）：

```python
def lock(
    self,
    name: str,
    timeout: float | None = None,
    sleep: float = 0.1,
    blocking: bool = True,
    blocking_timeout: float | None = None,
    thread_local: bool = True,
) -> Any:
    return self._require_client().lock(
        _serialize_redis_name(name, self._get_prefix()),
        timeout=timeout,
        sleep=sleep,
        blocking=blocking,
        blocking_timeout=blocking_timeout,
        thread_local=thread_local,
    )
```

**解读**：
- dify 用 redis-py 内置的 `lock()` 方法，**底层就是 SET NX EX + Lua 释放**
- `_serialize_redis_name` 自动加 key 前缀
- `thread_local=True`：同一线程可重入（threading.local 记录 token）
- `blocking=True`：阻塞等待直到获取锁

### 3.2 限流器用 lock 防超扣

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 239-249）：

```python
@staticmethod
@redis_fallback(default_return=True)
def _should_refresh_account_last_active(account_id: str) -> bool:
    return bool(
        redis_client.set(
            AccountService._get_account_last_active_refresh_key(account_id),
            1,
            ex=int(ACCOUNT_LAST_ACTIVE_REFRESH_INTERVAL.total_seconds()),
            nx=True,
        )
    )
```

**解读**：
- 用 `SET ... NX EX` 实现"**轻量级分布式锁**"——60 秒内只能更新一次
- 比 `r.lock()` 更轻量，适合**防抖**场景
- **应用**：用户活跃时间更新，防止每分钟都写 DB
- **保证互斥**：Redis 单线程保证 SET 原子性
- **保证不死锁**：EX 60 秒自动释放

### 3.3 文档索引任务用 lock

**文件位置**：`/Users/xu/code/github/dify/api/tasks/retry_document_indexing_task.py`
**核心代码**（行 49-71）：

```python
for document_id in document_ids:
    retry_indexing_cache_key = f"document_{document_id}_is_retried"
    # check document limit
    features = FeatureService.get_features(tenant.id)
    try:
        if features.billing.enabled:
            vector_space = features.vector_space
            assert vector_space is not None
            if 0 < vector_space.limit <= vector_space.size:
                raise ValueError(
                    "Your total number of documents plus the number of uploads have over the limit of "
                    "your subscription."
                )
    except Exception as e:
        document = session.scalar(
            select(Document).where(Document.id == document_id, Document.dataset_id == dataset_id).limit(1)
        )
        if document:
            document.indexing_status = IndexingStatus.ERROR
            document.error = str(e)
            document.stopped_at = naive_utc_now()
            session.add(document)
            session.commit()
        redis_client.delete(retry_indexing_cache_key)
        return
```

**解读**：
- 第 49 行：用 `document_{id}_is_retried` 作为**重试状态标志**
- 第 71、110、118 行：任务结束（成功/失败）都 `redis_client.delete(key)` 清理
- **目的**：防止同一文档被**并发重试**（不同 Celery worker 同时跑同一任务）
- **简化版锁**：比完整分布式锁简单，只存"是否在重试"标志

## 4. 关键要点总结

- **SET NX EX** 是最简单实用的分布式锁
- 释放锁必须用 **Lua 脚本验证 token**，不能直接 DEL
- redis-py 内置 `r.lock()` 封装了完整逻辑
- 锁过期但业务未完成 → 需要**后台续期**（Watch Dog）
- RedLock 算法有争议，强一致场景建议用 ZooKeeper/etcd
- dify 用 `SET NX EX` 做轻量防抖，用 `r.lock()` 做互斥

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `acquire_lock/release_lock` 函数，支持 token 验证：

```python
def acquire_lock(r, key, ttl=30) -> str | None:
    # TODO
    pass

def release_lock(r, key, token) -> bool:
    # TODO
    pass
```

### 练习 2：进阶

用 `r.lock()` 实现**秒杀场景**：100 个并发请求抢 10 个库存，保证不超卖。

### 练习 3：挑战（选做）

实现一个**看门狗（Watch Dog）**自动续期线程，避免锁过期业务未完成的问题。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 147-163 行）
- `/Users/xu/code/github/dify/api/services/account_service.py`（第 239-249 行）
- `/Users/xu/code/github/dify/api/tasks/retry_document_indexing_task.py`
- Redis 分布式锁官方文档：https://redis.io/docs/manual/patterns/distributed-locks/
- RedLock 争议：https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13