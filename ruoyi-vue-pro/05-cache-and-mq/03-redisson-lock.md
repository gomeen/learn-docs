# 1.3 Redisson 分布式锁

> 理解分布式锁的核心概念，掌握 Redisson `RLock` 的使用方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式锁的需求场景（秒杀、定时任务防重）
- 掌握 Redisson `RLock` 的 `tryLock` / `lock` / `unlock` 三种用法
- 理解看门狗（Watch Dog）续期机制
- 能识别 ruoyi 中 `RLock` 的实际使用位置

## 📚 前置知识

- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- Redisson 客户端（详见 [Redisson 客户端](./01-redisson.md)）
- Java 并发基础（Lock 接口）
- 分布式锁核心要求（详见 [分布式锁要求](../../_common/04-distributed-locks/01-requirements.md)）

## 1. 核心概念

### 1.1 为什么需要分布式锁？

单机下，`synchronized` / `ReentrantLock` 就能互斥。但在多 JVM 集群下，多个 JVM 进程并发改同一行 DB，单机锁失效。需要一个**所有进程共享的锁**，即分布式锁（通用原理详见 [Redis 分布式锁与 RedLock](../../_common/04-distributed-locks/02-redis-redlock.md)）。

### 1.2 Redisson 分布式锁特性

| 特性 | 说明 |
|------|------|
| 互斥 | 任意时刻只有一个客户端持锁 |
| 防死锁 | 客户端崩溃后，锁自动释放（基于 Redis 过期） |
| 容错 | 只要大部分 Redis 节点存活，就能提供服务（RedLock 算法） |
| 可重入 | 同一线程可多次 `lock` |
| 看门狗 | 默认 30 秒过期，每 10 秒续期到 30 秒，防止长任务锁过期 |

## 2. 代码示例

### 2.1 基础用法：tryLock 非阻塞

```java
// 文件：DistributedLockDemo.java
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import javax.annotation.Resource;
import org.springframework.stereotype.Service;
import java.util.concurrent.TimeUnit;

@Service
public class DistributedLockDemo {

    @Resource
    private RedissonClient redissonClient;

    public void doOrder(Long orderId) {
        RLock lock = redissonClient.getLock("lock:order:" + orderId);
        try {
            // 尝试获取锁，等待 5 秒，锁自动释放时间 30 秒
            if (lock.tryLock(5, 30, TimeUnit.SECONDS)) {
                // 执行业务逻辑
                System.out.println("获取锁成功，处理订单");
            } else {
                System.out.println("获取锁失败");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            // 必须判断 isHeldByCurrentThread，否则可能释放别人的锁
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

### 2.2 阻塞用法：lock()

```java
// 一直阻塞，直到拿到锁（不推荐生产用，可能导致线程池耗尽）
lock.lock();
try {
    // 业务
} finally {
    lock.unlock();
}
```

### 2.3 看门狗自动续期

```java
// 不传过期时间 → 触发看门狗，默认 30 秒，每 10 秒续期
lock.lock();
try {
    // 业务逻辑可能耗时很久，看门狗会一直续期不释放
} finally {
    lock.unlock();
}
```

## 3. 关键要点总结

- Redisson 分布式锁基于 Redis 实现，支持可重入、自动续期
- `tryLock(timeout, leaseTime, unit)` 推荐：可控超时、自动过期
- 不传 `leaseTime` 触发看门狗自动续期，适合长任务
- 释放锁前必须判断 `isHeldByCurrentThread()`
- ruoyi 在定时任务里用 `RLock` 保证集群下"只有一个实例干活"

---

**文档版本**：v1.0
**最后更新**：2026-07-13
