# 3.8 死信队列与重试

> 理解死信队列（DLQ）的概念，掌握 ruoyi 中的消息重试和清理机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解死信队列的产生背景和作用
- 掌握消息重试的常见策略（立即重试、延迟重试、指数退避）
- 看懂 ruoyi 的 `RedisStreamMessageCleanupJob` 清理逻辑
- 在业务中合理使用重试和死信

## 📚 前置知识

- Redis Stream（参见 `14-redis-stream-impl.md`）
- 消息可靠性（参见 `18-mq-reliability.md`）

## 1. 核心概念

### 1.1 什么是死信队列？

**死信（Dead Letter）**：消息被消费失败 N 次后，不再投递，进入"死信队列"，等待人工介入。

常见触发条件：
- 重试次数耗尽
- 消息超时未 ack
- 消息被 reject/nack 且不重投

### 1.2 重试策略对比

| 策略 | 描述 | 优缺点 |
|------|------|--------|
| 立即重试 | 失败立刻再试 | 简单，但易压垮下游 |
| 固定间隔 | 每 N 秒重试一次 | 简单，但浪费资源 |
| 指数退避 | 间隔指数增长（1s, 2s, 4s...） | 推荐，平衡性能和恢复 |
| 延迟队列 | 用 RocketMQ 延迟级别 | 灵活，但需 RocketMQ |

### 1.3 ruoyi 的死信实现

ruoyi 没有完整 DLQ，但有：
- **5 分钟 pending 重投**（`RedisPendingMessageResendJob`）
- **历史消息清理**（`RedisStreamMessageCleanupJob`）

## 2. 代码示例

### 2.1 指数退避重试（Spring Retry）

```java
@Service
public class OrderProcessor {
    @Retryable(
        value = Exception.class,
        maxAttempts = 3,
        backoff = @Backoff(delay = 1000, multiplier = 2)
    )
    public void process(Order order) {
        // 业务逻辑
    }

    @Recover
    public void recover(Exception e, Order order) {
        log.error("处理失败，进入死信：{}", order, e);
        // 写入死信队列
    }
}
```

### 2.2 基于 Redis 的延迟重试

```java
// 用 ZSet 实现延迟队列
public void delayRetry(String messageId, long delaySeconds) {
    long executeTime = System.currentTimeMillis() + delaySeconds * 1000;
    redisTemplate.opsForZSet().add("retry:queue", messageId, executeTime);
}

// 定时任务扫描到期的消息
@Scheduled(fixedDelay = 1000)
public void consumeRetry() {
    Set<String> messages = redisTemplate.opsForZSet().rangeByScore("retry:queue",
        0, System.currentTimeMillis());
    messages.forEach(msg -> {
        redisTemplate.opsForZSet().remove("retry:queue", msg);
        // 重新投递
    });
}
```

## 3. ruoyi 仓库源码解读

### 3.1 RedisStreamMessageCleanupJob 历史消息清理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisStreamMessageCleanupJob.java`

```java
@Slf4j
@AllArgsConstructor
public class RedisStreamMessageCleanupJob {

    public static final String DEFAULT_CLEANUP_LOCK_KEY = "redis:stream:cleanup:lock";

    private final List<AbstractRedisStreamMessageListener<?>> listeners;
    private final RedisMQTemplate redisTemplate;
    private final RedissonClient redissonClient;
    private final String cleanupLockKey;

    @Scheduled(cron = "0 0 3 * * ?") // 每天凌晨 3 点清理
    public void cleanup() {
        RLock lock = redissonClient.getLock(cleanupLockKey);
        if (lock.tryLock()) {
            try {
                execute();
            } finally {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            }
        }
    }

    private void execute() {
        // 略：遍历所有 stream key，调用 XTRIM 限制长度
    }
}
```

**解读**：
- 每天凌晨 3 点清理：避免 stream 无限增长占满 Redis
- 用 Redisson 分布式锁保证多实例只有一个执行
- **核心命令**：`XTRIM stream MAXLEN ~ 10000`（保留最近 10000 条）

### 3.2 重试机制：5 分钟 pending 重投

参见 `RedisPendingMessageResendJob`（已在 18 节详述）：
- 业务异常 → 5 分钟未 ack → 定时任务重投
- 本质上是**简单的延迟重试**

### 3.3 ruoyi 的局限与建议

ruoyi 的"死信/重试"机制比较基础：
- 无重试次数限制
- 无真正的 DLQ（重投到同一 stream）
- 无指数退避

生产建议：
- 业务层用 Spring Retry 实现指数退避
- 真正的 DLQ 需要额外表（`mq_dead_letter`）+ 定时任务扫描

## 4. 关键要点总结

- 死信队列：消费失败 N 次后进入 DLQ，等待人工介入
- 常见重试策略：立即、固定、指数退避
- ruoyi 用 `XTRIM` 限制 stream 长度，避免内存爆炸
- ruoyi 用 5 分钟 pending 重投代替 DLQ
- 生产建议：Spring Retry + 业务幂等 + 真正的 DLQ 表

## 5. 练习题

### 练习 1：基础（必做）

解释指数退避为什么比"立即重试"更好？

### 练习 2：进阶

阅读 `RedisStreamMessageCleanupJob`，解释为什么清理任务需要 Redisson 分布式锁？

### 练习 3：挑战（选做）

设计一个完整的死信方案：3 次重试失败后写入 `mq_dead_letter` 表，含 messageId、payload、error、retry_count 等字段。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisStreamMessageCleanupJob.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
- Spring Retry 文档：https://github.com/spring-projects/spring-retry

---

**文档版本**：v1.0
**最后更新**：2026-07-13