# 4.1 分布式锁的核心要求：互斥 / 安全 / 死锁 / 容错

> 理解分布式锁必须满足的四大基本要求及实现要点。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出分布式锁的四大核心要求
- 解释为什么"锁"在分布式环境比单机复杂
- 识别常见分布式锁的边界条件问题
- 在 dify 中找到分布式锁的实际应用

## 📚 前置知识

- Java/Python 多线程与锁
- 网络通信基础（TCP / UDP）
- Redis SETNX 命令（数据结构见 [01-redis](../01-redis/01-data-structures.md)）

## 1. 核心概念

### 1.1 为什么需要分布式锁？

**单机锁的局限**：
- `threading.Lock()` / `synchronized` 只在**单进程内**生效
- 多服务器、多进程的微服务架构下完全失效

**分布式锁的场景**：
- 防止多个实例同时执行定时任务
- 防止并发下单导致库存超卖
- 防止多个节点同时修改同一资源

### 1.2 分布式锁的四大核心要求

Martin Kleppmann 在《How to do distributed locking》中提出：

| 要求 | 含义 |
|------|------|
| **互斥（Mutual Exclusion）** | 任意时刻只有一个客户端持有锁 |
| **死锁避免（Dead Lock Free）** | 持锁客户端崩溃后锁必须能被释放 |
| **容错（Fault Tolerance）** | 锁服务故障时不能影响业务（最多短时不可用） |
| **可重入（Reentrancy）** | 同一线程可多次获取同一把锁（可选） |

### 1.3 三个隐藏的关键问题

#### 1.3.1 时钟漂移

很多分布式锁方案（如 Zookeeper）依赖时钟，时钟跳变会导致锁失效。

#### 1.3.2 GC 停顿 / 长时间阻塞

客户端持锁后发生长时间 GC，锁过期被其他客户端获取，原客户端恢复后误以为还持有锁。

#### 1.3.3 网络分区

持锁客户端与锁服务失联，不知道自己已失锁，可能产生并发问题。

### 1.4 与分布式锁相关的"fencing token"

为解决 GC 停顿问题，引入**递增 token**：
- 每次获取锁时返回一个递增的 token
- 修改资源时带上 token
- 资源服务端拒绝 token 小于当前最大值的请求

**效果**：即使客户端失联后误操作，也会被资源服务端拒绝。

### 1.5 分布式锁的实现方案对比

| 方案 | 一致性 | 性能 | 复杂度 |
|------|-------|------|-------|
| **MySQL 行锁** | 强 | 低 | 低 |
| **Redis SETNX** | 弱 | 高 | 低 |
| **Redis [RedLock](./02-redis-redlock.md)** | 中 | 高 | 中 |
| **[Zookeeper](./03-zookeeper-etcd.md)** | 强 | 中 | 中 |
| **[etcd](./03-zookeeper-etcd.md)** | 强 | 中 | 中 |

## 2. 代码示例

### 2.1 最简单的 Redis 锁（SETNX + EXPIRE）

```python
# 文件：example_simple_lock.py
import redis
import time

r = redis.Redis(host="localhost", port=6379)


def acquire_lock(lock_key: str, ttl: int = 10) -> bool:
    """尝试获取锁"""
    # SETNX 语义：key 不存在才设置
    return r.set(lock_key, "1", nx=True, ex=ttl)


def release_lock(lock_key: str):
    """释放锁"""
    r.delete(lock_key)


# 使用
if acquire_lock("order:lock:1001", ttl=10):
    try:
        print("获取锁成功，处理订单...")
        time.sleep(3)
        print("订单处理完成")
    finally:
        release_lock("order:lock:1001")
else:
    print("锁被占用，稍后重试")
```

### 2.2 带 fencing token 的锁（解决 GC 停顿）

```python
# 文件：example_fencing_lock.py
import redis
import time

r = redis.Redis(host="localhost", port=6379)


def acquire_lock_with_token(lock_key: str, ttl: int = 10) -> int | None:
    """获取锁并返回递增 token"""
    # 用 Lua 脚本保证原子性
    script = """
    local current = redis.call('INCR', KEYS[2])
    if redis.call('SET', KEYS[1], current, 'NX', 'EX', tonumber(ARGV[1])) then
        return current
    else
        return 0
    end
    """
    token = r.eval(script, 2, lock_key, f"{lock_key}:token", ttl)
    return token if token > 0 else None


def write_with_token(resource_key: str, value: str, token: int):
    """带 fencing token 写入资源"""
    # 资源服务端只接受 token >= 当前最大 token 的请求
    script = """
    local current_token = tonumber(redis.call('GET', KEYS[2]) or "0")
    if tonumber(ARGV[2]) >= current_token then
        redis.call('SET', KEYS[1], ARGV[1])
        redis.call('SET', KEYS[2], ARGV[2])
        return 1
    else
        return 0
    end
    """
    return r.eval(script, 2, resource_key, f"{resource_key}:max_token", value, token)


# 使用
token = acquire_lock_with_token("resource:lock", ttl=30)
if token:
    try:
        # 即使 GC 停顿 60 秒，token=100 也会被后续的 token=101 拒绝
        write_with_token("resource:data", "new_value", token)
    finally:
        r.delete("resource:lock")
```

### 2.3 常见错误：客户端崩溃导致死锁

```python
# ❌ 反例：没有 TTL 的锁
def acquire_lock_bad(lock_key):
    return r.setnx(lock_key, "1")     # 永不过期！

# 问题：
# 客户端拿到锁后崩溃 → 锁永远不释放 → 业务卡死

# ✅ 正例：必须设置 TTL
def acquire_lock_good(lock_key, ttl=10):
    return r.set(lock_key, "1", nx=True, ex=ttl)   # 自动过期
```

### 2.4 常见错误：超时释放但未完成业务

```python
# ❌ 反例：业务处理超过 TTL，但锁已过期
if acquire_lock("task:lock", ttl=5):
    long_running_task()  # 耗时 30 秒！
    # 5 秒后锁过期，其他客户端也拿到锁
    # → 两个客户端同时处理同一任务

# ✅ 正例：业务 + 续约（Redisson 看门狗）
def acquire_with_renewal(lock_key, ttl=10):
    """获取锁并启动续约线程"""
    if r.set(lock_key, "1", nx=True, ex=ttl):
        def renew():
            while r.exists(lock_key):
                r.expire(lock_key, ttl)
                time.sleep(ttl / 3)
        threading.Thread(target=renew, daemon=True).start()
        return True
    return False
```

## 3. dify 仓库源码解读

### 3.1 dify 的锁 Key 构造（触发器刷新保护）

**文件位置**：`/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
**核心代码**（行 1-12）：

```python
from collections.abc import Sequence
from itertools import starmap


def build_trigger_refresh_lock_key(tenant_id: str, subscription_id: str) -> str:
    """Build the Redis lock key for trigger subscription refresh in-flight protection."""
    return f"trigger_provider_refresh_lock:{tenant_id}_{subscription_id}"


def build_trigger_refresh_lock_keys(pairs: Sequence[tuple[str, str]]) -> list[str]:
    """Build Redis lock keys for a sequence of (tenant_id, subscription_id) pairs."""
    return list(starmap(build_trigger_refresh_lock_key, pairs))
```

**解读**：
- 第 6 行：`f"trigger_provider_refresh_lock:{tenant_id}_{subscription_id}"`——**统一的 key 前缀 + 业务标识**
- 第 11 行：`starmap` 高效地把 `[(t1, s1), (t2, s2)]` 映射为锁 key 列表
- **设计意图**：dify 在"触发器订阅刷新"场景用分布式锁防止**同一租户的同一订阅被并发刷新**（避免第三方 API 被打爆）
- **核心要求体现**：
  - **互斥**：Redis SETNX 保证
  - **死锁避免**：必须配合 TTL（代码中未体现，由 Redis 客户端库保证）
  - **容错**：Redis 不可用时业务应降级（不在此函数中）

**整体设计意图**：dify 把"锁 key 构造"封装成函数，避免业务代码硬编码字符串。

### 3.2 ruoyi 的 Redisson 锁（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**（简化）：

```java
// RedisLock4j.java - 基于 Redisson 的分布式锁
@Component
public class RedisLock4j {
    @Resource
    private RedissonClient redissonClient;

    public <T> T executeWithLock(String lockKey, int waitSeconds, Supplier<T> action) {
        RLock lock = redissonClient.getLock(lockKey);
        try {
            // 尝试获取锁，最多等 waitSeconds 秒
            if (lock.tryLock(waitSeconds, 30, TimeUnit.SECONDS)) {
                try {
                    return action.get();   // 执行业务
                } finally {
                    lock.unlock();          // 释放锁
                }
            } else {
                throw new LockException("获取锁超时");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new LockException("获取锁被中断");
        }
    }
}

// 使用
redisLock4j.executeWithLock("order:lock:1001", 5, () -> {
    // 处理订单
    orderService.process(orderId);
    return orderId;
});
```

**解读**：
- 第 9 行：`lock.tryLock(5, 30, TimeUnit.SECONDS)`：等最多 5 秒，**持锁后 30 秒自动过期**
- **Redisson 看门狗**：持锁期间自动续约（每 1/3 TTL 续期一次），避免超时问题
- 第 11-13 行：自动释放（finally），简化业务代码
- **对比 dify**：dify 的锁 key 构造简单（直接字符串），ruoyi 抽象成工具方法，业务代码更简洁

## 4. 关键要点总结

- 分布式锁必须满足**互斥 / 死锁避免 / 容错 / 可重入**
- **死锁避免**靠 TTL：所有锁必须有过期时间
- **超时释放**靠看门狗：Redisson 内置实现
- **防 GC 停顿**靠 fencing token：递增 token 拒绝过期请求
- dify 用 Redis 锁保护触发器刷新场景（key 构造函数在 `locks.py`）
- ruoyi 用 Redisson 封装，简化业务代码

## 5. 练习题

### 练习 1：基础（必做）

实现一个完整 Redis 锁：
1. `acquire(lock_key, ttl=10)` 用 SETNX
2. `release(lock_key)` 用 Lua 脚本（只删自己的锁，防误删）
3. 测试并发场景

### 练习 2：进阶

阅读 `dify/api/core/trigger/utils/locks.py`，分析：
- 为什么用 `f-string` 拼接 lock key？
- 为什么需要 `build_trigger_refresh_lock_keys(pairs)` 函数？
- 在 dify 中实际是怎么用这个锁的？（搜索 `build_trigger_refresh_lock_key`）

### 练习 3：挑战（选做）

设计一个**高可靠的分布式锁服务**：
1. 实现 RedLock 算法（5 个独立 Redis 实例）
2. 大多数成功才算获取锁
3. 处理时钟漂移、网络分区
4. 给出 Python 实现的关键代码

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
- Martin Kleppmann 分布式锁：https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- Redisson 文档：https://redisson.org/docs/data-and-services/locks-and-synchronizers/

---

**文档版本**：v1.0
**最后更新**：2026-07-14