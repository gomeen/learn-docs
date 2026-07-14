# 1.3 Redisson 分布式锁

> 理解分布式锁的核心概念，掌握 Redisson `RLock` 的使用方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式锁的需求场景（秒杀、定时任务防重）
- 掌握 Redisson `RLock` 的 `tryLock` / `lock` / `unlock` 三种用法
- 理解看门狗（Watch Dog）续期机制
- 能识别 ruoyi 中 `RLock` 的实际使用位置

## 📚 前置知识

- Redis 基础（参见 `01-redis-basics.md`）
- Redisson 客户端（参见 `02-redisson.md`）
- Java 并发基础（Lock 接口）

## 1. 核心概念

### 1.1 为什么需要分布式锁？

单机下，`synchronized` / `ReentrantLock` 就能互斥。但在多 JVM 集群下，多个 JVM 进程并发改同一行 DB，单机锁失效。需要一个**所有进程共享的锁**，即分布式锁。

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

## 3. ruoyi 仓库源码解读

### 3.1 RedisPendingMessageResendJob 抢占锁防止重复执行

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
**核心代码**（行 46-62）：

```java
/**
 * 一分钟执行一次,这里选择每分钟的 35 秒执行，是为了避免整点任务过多的问题
 */
@Scheduled(cron = "35 * * * * ?")
public void messageResend() {
    RLock lock = redissonClient.getLock(resendLockKey);
    if (lock.tryLock()) {
        try {
            execute();
        } catch (Exception ex) {
            log.error("[messageResend][执行异常][lockKey={}]", resendLockKey, ex);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    } else {
        log.debug("[messageResend][未获取到锁，跳过本轮][lockKey={}]", resendLockKey);
    }
}
```

**解读**：
- 第 48 行：`getLock("redis:stream:pending-message-resend:lock")` 是**全局唯一**的锁 key
- 第 49 行：`tryLock()` 非阻塞获取——如果多个实例都部署了定时任务，只有抢到锁的那个会执行重发逻辑
- 第 55 行：`isHeldByCurrentThread()` 检查锁是否还归当前线程持有，避免因超时导致误删别人的锁
- **设计意图**：分布式定时任务"只让一个实例干活"，避免重复消费消息

### 3.2 ruoyi 的 lockKey 常量设计

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
**核心代码**（行 26-28）：

```java
public static final String DEFAULT_RESEND_LOCK_KEY = "redis:stream:pending-message-resend:lock";

public static final String IOT_RESEND_LOCK_KEY = "redis:stream:pending-message-resend:lock:iot";
```

**解读**：
- DEFAULT 与 IOT 两个常量：因为 IoT 模块有专属的 Stream，单独用一个锁 key，避免影响主流程
- 这是一种**业务隔离**的实践——同名锁容易导致业务互相阻塞

## 4. 关键要点总结

- Redisson 分布式锁基于 Redis 实现，支持可重入、自动续期
- `tryLock(timeout, leaseTime, unit)` 推荐：可控超时、自动过期
- 不传 `leaseTime` 触发看门狗自动续期，适合长任务
- 释放锁前必须判断 `isHeldByCurrentThread()`
- ruoyi 在定时任务里用 `RLock` 保证集群下"只有一个实例干活"

## 5. 练习题

### 练习 1：基础（必做）

写一个 `tryLock(3, 10, TimeUnit.SECONDS)` 的调用，说明：
1. 等待时间和锁过期时间分别是多少？
2. 如果 3 秒后还拿不到锁，行为是什么？

**参考答案**：等待 3 秒、过期 10 秒；3 秒后拿不到锁则返回 false 不阻塞。

### 练习 2：进阶

阅读 `RedisPendingMessageResendJob.messageResend()`，思考：
- 为什么用 `tryLock()` 而不是 `lock()`？
- 如果不用分布式锁，多个实例同时跑这个定时任务会出什么问题？

### 练习 3：挑战（选做）

实现一个"商品秒杀"扣库存方法，要求：
- 用 `RLock` 防止超卖
- 锁 key 是 `seckill:product:{productId}`
- 业务异常时正确释放锁

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
- Redisson 分布式锁文档：https://redisson.org/docs/data-and-services/locks-and-synchronizers/

---

**文档版本**：v1.0
**最后更新**：2026-07-13