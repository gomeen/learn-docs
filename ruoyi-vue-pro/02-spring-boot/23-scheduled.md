# 23 定时任务：@Scheduled

> 掌握 Spring `@Scheduled` 定时任务，能在 ruoyi-vue-pro 中实现定时清理、定时同步等场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@Scheduled` 的工作原理
- 掌握 cron 表达式的写法
- 启用 `@EnableScheduling` + 配置 `TaskScheduler`
- 能在 ruoyi-vue-pro 中读懂 `RedisStreamMessageCleanupJob` 定时任务

## 📚 前置知识

- 22-async.md
- 04-transaction.md

## 1. 核心概念

### 1.1 `@Scheduled` 三种写法

```java
// 方式 1：fixedRate（毫秒）—— 上次执行开始后间隔 N 毫秒
@Scheduled(fixedRate = 5000)
public void task1() { ... }

// 方式 2：fixedDelay（毫秒）—— 上次执行结束后间隔 N 毫秒
@Scheduled(fixedDelay = 5000)
public void task2() { ... }

// 方式 3：cron 表达式 —— 指定时间
@Scheduled(cron = "0 0 * * * ?")  // 每小时执行
public void task3() { ... }
```

### 1.2 Cron 表达式

```
秒 分 时 日 月 周 年(可选)
*  *  *  *  *  ?  
```

| 字段 | 范围 | 特殊字符 |
|------|------|---------|
| 秒 | 0-59 | `,` `-` `*` `/` |
| 分 | 0-59 | `,` `-` `*` `/` |
| 时 | 0-23 | `,` `-` `*` `/` |
| 日 | 1-31 | `,` `-` `*` `?` `/` `L` `W` |
| 月 | 1-12 | `,` `-` `*` `/` |
| 周 | 1-7 (1=周一) | `,` `-` `*` `?` `/` `L` `#` |

**常用例子**：
- `0 0 0 * * ?` 每天 0 点
- `0 0 * * * ?` 每小时
- `0 */5 * * * ?` 每 5 分钟
- `0 0 0 1 * ?` 每月 1 号

### 1.3 `@Scheduled` vs Quartz / XXL-Job

| 特性 | `@Scheduled` | Quartz | XXL-Job |
|------|-------------|--------|---------|
| 分布式 | ❌ | ✅（需配库） | ✅（原生） |
| 动态配置 | ❌ | ✅ | ✅ |
| 集群部署会重复执行 | ✅ | 可避免 | 自动避免 |
| 复杂度 | 低 | 中 | 中 |

ruoyi-vue-pro 用 **XXL-Job** 做分布式定时任务，`@Scheduled` 仅用于单 JVM 任务。

## 2. 代码示例

### 2.1 基础定时任务

```java
// 文件：MyJob.java
@Component
public class MyJob {

    @Scheduled(fixedRate = 5000)  // 每 5 秒
    public void reportStatus() {
        log.info("[reportStatus] 系统正常");
    }

    @Scheduled(cron = "0 0 3 * * ?")  // 每天凌晨 3 点
    public void cleanCache() {
        log.info("[cleanCache] 清理过期缓存");
        redisTemplate.delete("temp:*");
    }
}

// 启动类
@SpringBootApplication
@EnableScheduling  // 启用定时任务
public class MyApplication { ... }
```

### 2.2 异常处理

```java
@Scheduled(cron = "0 0 3 * * ?")
public void cleanCache() {
    try {
        redisTemplate.delete("temp:*");
    } catch (Exception e) {
        log.error("[cleanCache] 失败", e);
        // 不抛异常，否则后续任务不再执行
    }
}
```

### 2.3 自定义线程池

```java
@Configuration
public class SchedulerConfig implements SchedulingConfigurer {
    @Override
    public void configureTasks(ScheduledTaskRegistrar taskRegistrar) {
        taskRegistrar.setScheduler(Executors.newScheduledThreadPool(10));
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Redis Stream 消息清理任务

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisStreamMessageCleanupJob.java`
**核心代码**（行 50-70）：

```java
/**
 * 每小时执行一次清理任务
 */
@Scheduled(cron = "0 0 * * * ?")
public void cleanup() {
    RLock lock = redissonClient.getLock(cleanupLockKey);
    if (lock.tryLock()) {
        try {
            execute();
        } catch (Exception ex) {
            log.error("[cleanup][执行异常][lockKey={}]", cleanupLockKey, ex);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    } else {
        log.debug("[cleanup][未获取到锁，跳过本轮][lockKey={}]", cleanupLockKey);
    }
}
```

**解读**：
- 第 3 行：`@Scheduled(cron = "0 0 * * * ?")` 每小时执行一次
- 第 4 行：`redissonClient.getLock(cleanupLockKey)` 获取分布式锁
- 第 5 行：`lock.tryLock()` 非阻塞获取锁，**获取失败直接跳过**（避免重复执行）
- 第 6-12 行：try-catch-finally 确保锁释放
- **关键设计**：
  - 单 JVM 场景下 `@Scheduled` 会定时执行
  - 集群部署时，多个实例同时触发，但**只有一个能获取锁**
  - 失败的实例跳过本轮，等待下一小时
- 这是"分布式定时任务"的轻量级实现方案

### 3.2 任务注解 + 锁

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisStreamMessageCleanupJob.java`
**核心代码**（行 25-48）：

```java
@Slf4j
@AllArgsConstructor
public class RedisStreamMessageCleanupJob {

    /**
     * 业务 MQ（Spring 容器内 AbstractRedisStreamMessageListener）清理任务使用的分布式锁
     */
    public static final String DEFAULT_CLEANUP_LOCK_KEY = "redis:stream:message-cleanup:lock";

    /**
     * IoT Redis 总线清理任务使用的分布式锁（须与 {@link #DEFAULT_CLEANUP_LOCK_KEY} 区分，
     * 否则会共抢一把锁，同一时刻只有一侧能执行 XTRIM，另一侧 Stream 可能无限积压）
     */
    public static final String IOT_CLEANUP_LOCK_KEY = "redis:stream:message-cleanup:lock:iot";

    /**
     * 保留的消息数量，默认保留最近 10000 条消息
     */
    private static final long MAX_COUNT = 10000;

    private final List<AbstractRedisStreamMessageListener<?>> listeners;
    private final RedisMQTemplate redisTemplate;
    private final RedissonClient redissonClient;
    /**
     * Redisson 锁键（多 Bean 注册清理任务时必须各不相同）
     */
    private final String cleanupLockKey;
```

**解读**：
- 第 2 行：`@AllArgsConstructor` 注入 `listeners`、`redisTemplate`、`redissonClient`、`cleanupLockKey`
- 第 5-6 行：业务 MQ 用的锁 key
- 第 11-12 行：IoT 用的锁 key（**注意要区分！** 否则两个任务会争抢同一把锁）
- 第 18 行：`MAX_COUNT = 10000` 保留最近 10000 条消息
- 第 22 行：构造器注入 `cleanupLockKey`，不同 Bean 用不同 key
- **设计细节**：常量定义在类中，便于复用和修改

### 3.3 核心清理逻辑

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisStreamMessageCleanupJob.java`
**核心代码**（行 72-87）：

```java
/**
 * 执行清理逻辑
 */
private void execute() {
    StreamOperations<String, Object, Object> ops = redisTemplate.getRedisTemplate().opsForStream();
    listeners.forEach(listener -> {
        try {
            // 使用 XTRIM MAXLEN 精确裁剪（approximate=false），避免 ~ 模式下长期明显高于上限
            Long trimCount = ops.trim(listener.getStreamKey(), MAX_COUNT, false);
            if (trimCount != null && trimCount > 0) {
                log.info("[execute][Stream({}) 清理消息数量({})]", listener.getStreamKey(), trimCount);
            }
        } catch (Exception ex) {
            log.error("[execute][Stream({}) 清理异常]", listener.getStreamKey(), ex);
        }
    });
}
```

**解读**：
- 第 4 行：获取 Redis Stream 操作对象
- 第 5-15 行：遍历所有 listener，逐个清理
- 第 7 行：`XTRIM MAXLEN` 精确裁剪（`approximate=false`）—— `~` 模式虽然快但会超出上限
- 第 11 行：单独 try-catch 某个 listener 失败不影响其他
- **设计要点**：
  - 关键注释"使用 XTRIM MAXLEN 精确裁剪"说明作者踩过坑
  - 详尽的日志（INFO 和 ERROR）便于排查

## 4. 关键要点总结

- **`@Scheduled`**：Spring 定时任务注解
- **`@EnableScheduling`**：启动类启用
- **3 种写法**：`fixedRate`、`fixedDelay`、`cron`
- **集群部署会重复执行**，需配合分布式锁（Redisson）
- **ruoyi 用 `@Scheduled` + Redisson Lock** 实现轻量级分布式任务
- **重任务用 XXL-Job**（支持动态配置、可视化）
- **失败处理**：try-catch 防止单个任务失败影响后续

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `DailyReportJob`，每天凌晨 0 点生成前一天的用户注册数据报告（用 `@Scheduled(cron = "0 0 0 * * ?")`）。

### 练习 2：进阶

阅读 `RedisStreamMessageCleanupJob`，解释为什么需要 `tryLock()` 而不是 `lock()`？这两种锁的区别是什么？

### 练习 3：挑战（选做）

实现一个分布式定时任务：每 5 分钟清理 Redis 中的过期订单。要求集群部署时只有一个节点执行（用 Redisson 分布式锁），执行失败不影响下次调度。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisStreamMessageCleanupJob.java`
- Spring `@Scheduled` 文档：https://docs.spring.io/spring-framework/reference/integration/scheduling.html
- 芋道定时任务：https://doc.iocoder.cn/spring-boot-scheduled/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
