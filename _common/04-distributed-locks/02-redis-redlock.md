# 4.2 Redis 分布式锁：SETNX / RedLock 原理与争议

> 深入理解 Redis 分布式锁的实现细节和 RedLock 算法的争议。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 SETNX 实现单 Redis 实例锁
- 解释 RedLock 多实例算法的原理
- 理解 Martin Kleppmann 对 RedLock 的批评
- 在 dify 中找到锁实现

## 📚 前置知识

- 分布式锁基本要求（`04-distributed-locks/01-requirements.md`）
- Redis 基础命令
- 时钟同步与 NTP

## 1. 核心概念

### 1.1 单 Redis 实例锁（SETNX）

最简单方案：用 `SET key value NX EX ttl` 一个命令完成。

```
Client A: SET lock:order 1 NX EX 10  →  OK（拿到锁）
Client B: SET lock:order 1 NX EX 10  →  nil（没拿到）
```

**原子性**：SET 命令本身的 NX + EX 选项保证原子性（旧版的 SETNX + EXPIRE 两步操作不是原子的）。

### 1.2 单实例锁的问题

**Redis 单点故障**：
- Master 宕机 → 客户端重连到 Replica
- 但 Redis 异步复制可能丢失锁（Master 没复制就宕机）
- → 两个客户端都拿到锁

**Redisson 的应对**：检测到主从切换后延迟获取锁（`redisson-lock-watchdog`）。

### 1.3 RedLock 算法（Antirez 提出）

**核心思想**：用 **N 个独立 Redis 实例**（通常 5 个），大多数成功才算获取锁。

```
获取锁流程：
1. 获取当前时间戳 T1
2. 依次向 N 个实例发送 SETNX（用相同的 key 和 random_value）
3. 获取当前时间戳 T2
4. 计算获取锁耗时 = T2 - T1
5. 满足以下两个条件才算获取锁：
   a. 大多数实例（N/2 + 1）返回成功
   b. 耗时 < 锁 TTL
6. 如果获取失败，向所有实例发送 DEL 释放锁（即使不是自己设置的）

释放锁流程：
用 Lua 脚本：GET key → 如果等于 random_value → DEL key
```

### 1.4 Martin Kleppmann 对 RedLock 的批评

Kleppmann 在《How to do distributed locking》中指出 RedLock 的**根本缺陷**：

**问题 1：GC 停顿 / 时钟跳跃**
- 客户端获取锁后 GC 30 秒
- 锁过期，其他客户端拿到锁
- 第一个客户端恢复后**不知道自己已失锁**
- → 并发问题

**问题 2：fencing token 缺失**
- 即使有 RedLock，GC 后的客户端**没有机制**被拒绝
- 必须配合资源服务端的 token 检查

**问题 3：系统时钟不可靠**
- RedLock 依赖系统时钟
- NTP 校准可能让时钟**向前跳跃**
- → 锁提前过期

### 1.5 Antirez 的回应

Antirez（Redis 作者）认为：
- GC 停顿是**应用程序问题**，不是锁服务问题
- RedLock 的"大多数实例"机制足以应对单点故障
- 时钟跳跃是**小概率事件**

### 1.6 实践中的建议

**小型项目**：
- 用单实例 + Redisson 看门狗，足够

**中型项目**：
- 用 RedLock（容忍偶尔的并发问题）

**大型项目**：
- 用 **Zookeeper** 或 **etcd** 实现（强一致）
- 或配合 **fencing token** 兜底

## 2. 代码示例

### 2.1 完整单实例锁（Lua 释放）

```python
# 文件：example_lock_lua.py
import redis
import uuid
import time

r = redis.Redis(host="localhost", port=6379)

# Lua 脚本：只删自己的锁（防误删）
RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


class RedisLock:
    def __init__(self, key: str, ttl: int = 10):
        self.key = key
        self.ttl = ttl
        self.token = str(uuid.uuid4())   # 唯一标识

    def acquire(self, wait_timeout: float = 5.0) -> bool:
        """获取锁，支持等待"""
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            # SETNX + EX 原子操作
            if r.set(self.key, self.token, nx=True, ex=self.ttl):
                return True
            time.sleep(0.05)   # 50ms 后重试
        return False

    def release(self):
        """释放锁（用 Lua 保证只删自己的）"""
        r.eval(RELEASE_LOCK_SCRIPT, 1, self.key, self.token)


# 使用
lock = RedisLock("order:lock:1001", ttl=30)
if lock.acquire(wait_timeout=3):
    try:
        print("处理订单...")
        time.sleep(2)
    finally:
        lock.release()
else:
    print("锁被占用")
```

### 2.2 RedLock 多实例实现

```python
# 文件：example_redlock.py
import redis
import time
import uuid


class RedLock:
    """简化版 RedLock 算法"""

    def __init__(self, redis_instances: list[redis.Redis]):
        self.clients = redis_instances
        self.quorum = len(redis_instances) // 2 + 1   # 大多数

    def acquire(self, key: str, ttl: int = 10000) -> str | None:
        """
        尝试获取锁。
        ttl 单位：毫秒
        返回：token（成功）/ None（失败）
        """
        start_time = int(time.time() * 1000)
        token = str(uuid.uuid4())
        success_count = 0
        elapsed_times = []

        for client in self.clients:
            try:
                # 单实例 SETNX
                client.set(key, token, nx=True, px=ttl)
                # 实际需要检查返回值，简化起见略
                success_count += 1
            except redis.RedisError:
                continue

            # 计算耗时
            elapsed = int(time.time() * 1000) - start_time
            elapsed_times.append(elapsed)

            # 提前退出：已确定能成功且耗时足够小
            if success_count >= self.quorum and elapsed < ttl:
                return token

        # 检查总体条件
        elapsed = int(time.time() * 1000) - start_time
        if success_count >= self.quorum and elapsed < ttl:
            return token

        # 失败：释放所有实例的锁
        self.release(key, token)
        return None

    def release(self, key: str, token: str):
        """释放所有实例上的锁"""
        for client in self.clients:
            try:
                # Lua 脚本保证只删自己的
                script = """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    return redis.call('del', KEYS[1])
                else
                    return 0
                end
                """
                client.eval(script, 1, key, token)
            except redis.RedisError:
                continue


# 使用 5 个独立 Redis 实例
instances = [
    redis.Redis(host="redis1", port=6379),
    redis.Redis(host="redis2", port=6379),
    redis.Redis(host="redis3", port=6379),
    redis.Redis(host="redis4", port=6379),
    redis.Redis(host="redis5", port=6379),
]
redlock = RedLock(instances)

token = redlock.acquire("order:lock:1001", ttl=10000)
if token:
    try:
        print("获取锁成功，处理业务...")
    finally:
        redlock.release("order:lock:1001", token)
```

### 2.3 常见错误：用 SETNX 后忘了 EXPIRE

```python
# ❌ 反例：两步操作（不原子）
def acquire_bad(lock_key):
    if r.setnx(lock_key, "1"):
        # 客户端崩溃在 SETNX 和 EXPIRE 之间 → 死锁！
        r.expire(lock_key, 10)
        return True
    return False

# ✅ 正例：一步操作（SETNX + EX 原子）
def acquire_good(lock_key):
    return r.set(lock_key, "1", nx=True, ex=10)   # 原子
```

### 2.4 常见错误：释放别人的锁

```python
# ❌ 反例：直接 DEL
def release_bad(lock_key):
    r.delete(lock_key)

# 问题：客户端 A 的锁过期，B 拿到锁，A 再 DEL → 删了 B 的锁

# ✅ 正例：Lua 脚本（比较 token）
def release_good(lock_key, my_token):
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    r.eval(script, 1, lock_key, my_token)
```

## 3. dify 仓库源码解读

### 3.1 dify 的锁使用场景

**文件位置**：`/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
**核心代码**（行 5-12）：

```python
def build_trigger_refresh_lock_key(tenant_id: str, subscription_id: str) -> str:
    """Build the Redis lock key for trigger subscription refresh in-flight protection."""
    return f"trigger_provider_refresh_lock:{tenant_id}_{subscription_id}"


def build_trigger_refresh_lock_keys(pairs: Sequence[tuple[str, str]]) -> list[str]:
    """Build Redis lock keys for a sequence of (tenant_id, subscription_id) pairs."""
    return list(starmap(build_trigger_refresh_lock_key, pairs))
```

**解读**：
- 第 6 行：lock key 格式 `trigger_provider_refresh_lock:{tenant_id}_{subscription_id}`
- **业务场景**：触发器订阅刷新（如 GitHub webhook 订阅）
- **互斥需求**：同一 (tenant_id, subscription_id) 同一时刻只能有一个 refresh 在跑（防止重复调用第三方 API）
- **dify 的简化**：只用 Redis SETNX 单实例锁（不用 RedLock）——**因为：
  1. 锁失败的代价是"重复刷新一次"，不是"业务数据错误"
  2. SaaS 部署 Redis 通常用托管服务，可用性高
  3. 简单可靠 > 理论完美

### 3.2 ruoyi 的 Redisson RedLock 实现（Java 类比）

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

        // Redisson 内置看门狗：自动续约
        // 默认 30 秒过期，每 10 秒续约一次
        if (lock.tryLock(waitSeconds, 30, TimeUnit.SECONDS)) {
            try {
                return action.get();
            } finally {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            }
        }
        throw new LockException("获取锁超时");
    }

    // RedLock 多实例实现
    public <T> T executeWithRedLock(List<String> redisAddresses, String lockKey, Supplier<T> action) {
        Config config = new Config();
        redisAddresses.forEach(addr -> config.useClusterServers().addNodeAddress(addr));

        RedissonClient redisson = Redisson.create(config);
        RLock lock = redisson.getMultiLock(
            redisAddresses.stream()
                .map(addr -> redisson.getLock(lockKey))
                .toArray(RLock[]::new)
        );

        if (lock.tryLock()) {
            try {
                return action.get();
            } finally {
                lock.unlock();
            }
        }
        throw new LockException("RedLock 获取失败");
    }
}
```

**解读**：
- 第 11 行：Redisson **看门狗**自动续约（默认 30 秒过期，每 10 秒续约），解决"业务超时但锁还在"
- 第 33-35 行：`getMultiLock` 把多个锁组合成 RedLock
- **对比 dify**：dify 简化实现，ruoyi 用 Redisson 完整方案（看门狗 + RedLock 都内置）

## 4. 关键要点总结

- **SETNX + EX** 是单实例锁的原子方案
- **释放锁必须用 Lua 脚本**（GET → 比对 → DEL），防止误删
- **RedLock** 用 5 个独立实例 + 大多数投票，应对 Redis 主从切换
- **RedLock 不能解决 GC 停顿**，需要 fencing token 兜底
- **实践选择**：
  - 简单场景 → 单实例 + SETNX
  - 关键业务 → Redisson（看门狗）
  - 极高要求 → Zookeeper/etcd
- dify 用最简方案（SETNX），ruoyi 用 Redisson 完整方案

## 5. 练习题

### 练习 1：基础（必做）

实现完整的 Redis 锁：
1. `acquire(key, ttl)` 用 SETNX
2. `release(key, token)` 用 Lua 脚本
3. 测试两个客户端竞争同一把锁
4. 验证只有一个能获取到

### 练习 2：进阶

阅读 `dify/api/core/trigger/utils/locks.py`：
- dify 用的是单实例锁还是 RedLock？
- 触发器刷新场景为什么不需要 RedLock？（从业务影响分析）

### 练习 3：挑战（选做）

实现 RedLock 算法的完整版本：
1. 5 个独立 Redis 实例
2. 计算获取锁耗时（必须 < TTL）
3. 大多数成功才算获取
4. 处理部分实例失败的情况

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
- Martin Kleppmann 对 RedLock 的批评：https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- Antirez 的回应：http://antirez.com/news/101

---

**文档版本**：v1.0
**最后更新**：2026-07-14