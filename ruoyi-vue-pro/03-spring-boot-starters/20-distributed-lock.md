# 3.4 分布式锁：RLock

> 深入理解分布式锁的原理与 Redisson 的实现，能在 yudao 中熟练使用分布式锁。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式锁的核心要求（互斥、防死锁、可重入）
- 掌握 Redisson `RLock` 的工作原理
- 理解 WatchDog 自动续期机制
- 能在 yudao 中选择合适的锁策略

## 📚 前置知识

- [18-redisson.md](./18-redisson.md)
- [19-redis-utils.md](./19-redis-utils.md)
- 分布式锁理论（详见 [分布式锁要求](../../_common/04-distributed-locks/01-requirements.md) / [Redis Redlock](../../_common/04-distributed-locks/02-redis-redlock.md)）
- 本地锁对比见 [27-lock](../01-java-fundamentals/33-lock.md)

## 1. 核心概念

### 1.1 分布式锁的三大要求

| 要求 | 含义 |
|------|------|
| 互斥性 | 任何时刻只有一个客户端持有锁 |
| 不会死锁 | 即使客户端崩溃，锁也能释放 |
| 容错性 | 只要多数 Redis 节点存活，就能加锁 |

### 1.2 Redisson 的实现

Redisson 实现了**Java 并发包**的接口（如 `Lock`），用 Redis 作为后端存储：

```java
RLock lock = redissonClient.getLock("myLock");
lock.lock();          // 阻塞等待
lock.tryLock();       // 尝试加锁
lock.tryLock(5, 30, TimeUnit.SECONDS);  // 等待 5s，租约 30s
lock.unlock();
```

### 1.3 WatchDog（看门狗）机制

默认情况下，`lock.lock()` 的租约是 **30 秒**，但 WatchDog 会**每 10 秒续期一次**（续到 30 秒），保证业务执行完才释放。

## 2. 代码示例

### 2.1 基础分布式锁

```java
RLock lock = redissonClient.getLock("order:create:" + orderId);
try {
    // 阻塞等待直到获取锁
    lock.lock();
    // 执行业务
    doBusiness();
} finally {
    lock.unlock();  // 必须释放
}
```

### 2.2 tryLock（限时等待）

```java
RLock lock = redissonClient.getLock("order:create:" + orderId);
try {
    // 等待 5 秒，租约 30 秒
    if (lock.tryLock(5, 30, TimeUnit.SECONDS)) {
        doBusiness();
    } else {
        throw new ServiceException("系统繁忙，请稍后重试");
    }
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

### 2.3 yudao 封装

```java
// 用 yudao 的 RedisLockUtils
String result = RedisLockUtils.executeWithLock(
    "order:create:" + orderId,
    () -> doBusiness(),
    5, 30
);
```

### 2.4 公平锁

```java
// 公平锁：按请求顺序获取
RLock fairLock = redissonClient.getFairLock("fair-lock");
fairLock.lock();
```

## 3. 关键要点总结

- **分布式锁 = Redis + Lua + Watch Dog**
- **`RLock`** 是 Redisson 最常用的锁
- **Watch Dog 每 10 秒续期**到 30 秒，防止业务未完成就释放
- **`tryLock(timeout)`** 必须用 `isHeldByCurrentThread()` 二次判断再 unlock
- **yudao 封装了 `RedisLockUtils.executeWithLock`**，业务方更简洁

---

**文档版本**：v1.0
**最后更新**：2026-07-13
