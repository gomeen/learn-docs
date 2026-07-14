# 3.4 分布式锁：RLock

> 深入理解分布式锁的原理与 Redisson 的实现，能在 yudao 中熟练使用分布式锁。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式锁的核心要求（互斥、防死锁、可重入）
- 掌握 Redisson `RLock` 的工作原理
- 理解 WatchDog 自动续期机制
- 能在 yudao 中选择合适的锁策略

## 📚 前置知识

- [15-redisson.md](./15-redisson.md)
- [16-redis-utils.md](./16-redis-utils.md)
- CAP 理论与分布式一致性

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

## 3. ruoyi 仓库源码解读

### 3.1 Redisson 配置

yudao 引入 `redisson-spring-boot-starter`，由 Redisson 自动读取 `spring.redis.*` 配置。

### 3.2 yudao 中的分布式锁应用

**应用 1：防重复提交**

```java
// yudao-server 中某个 Service
public CommonResult<Long> createOrder(OrderCreateReqVO req) {
    // 同一个用户 1 秒内不能重复提交
    RLock lock = redissonClient.getLock("order:submit:" + userId);
    if (lock.tryLock(0, 1, TimeUnit.SECONDS)) {
        try {
            // 创建订单
        } finally {
            lock.unlock();
        }
    } else {
        return CommonResult.error("请勿重复提交");
    }
}
```

**应用 2：库存扣减**

```java
public void deductStock(Long skuId, Integer count) {
    RLock lock = redissonClient.getLock("stock:deduct:" + skuId);
    lock.lock();
    try {
        // 1. 查库存
        Integer stock = stockMapper.selectBySkuId(skuId);
        if (stock < count) {
            throw new ServiceException("库存不足");
        }
        // 2. 扣减
        stockMapper.deduct(skuId, count);
    } finally {
        lock.unlock();
    }
}
```

**应用 3：幂等执行**

```java
public void idempotentProcess(String bizId) {
    RLock lock = redissonClient.getLock("idempotent:" + bizId);
    if (lock.tryLock()) {
        try {
            // 处理（其他线程直接跳过）
            process(bizId);
        } finally {
            lock.unlock();
        }
    }
}
```

### 3.3 多锁联用

```java
// 同时获取多个锁
RLock lock1 = redissonClient.getLock("lock1");
RLock lock2 = redissonClient.getLock("lock2");
RedissonMultiLock multiLock = redissonClient.getMultiLock(lock1, lock2);
multiLock.lock();
try {
    // 业务
} finally {
    multiLock.unlock();
}
```

## 4. 关键要点总结

- **分布式锁 = Redis + Lua + Watch Dog**
- **`RLock`** 是 Redisson 最常用的锁
- **Watch Dog 每 10 秒续期**到 30 秒，防止业务未完成就释放
- **`tryLock(timeout)`** 必须用 `isHeldByCurrentThread()` 二次判断再 unlock
- **yudao 封装了 `RedisLockUtils.executeWithLock`**，业务方更简洁

## 5. 练习题

### 练习 1：基础（必做）

写一个分布式锁保护的"用户注册"方法，确保同一用户名只创建一个用户。

### 练习 2：进阶

实现"红包秒杀"：1000 个用户抢 100 个红包，确保不超卖。提示：分布式锁 + Lua 脚本。

### 练习 3：挑战（选做）

研究 `RedissonLock` 的 Lua 脚本，理解 WatchDog 续期的实现细节。

## 6. 参考资料

- Redisson 分布式锁：https://github.com/redisson/redisson/wiki/8.-distributed-locks-and-synchronizers
- Redisson Watch Dog：https://github.com/redisson/redisson/wiki/8.-distributed-locks-and-synchronizers#81-lock
- Martin Kleppmann《How to do distributed locking》

---

**文档版本**：v1.0
**最后更新**：2026-07-13
