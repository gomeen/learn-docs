# 23 定时任务：@Scheduled

> 掌握 Spring `@Scheduled` 定时任务，能在 ruoyi-vue-pro 中实现定时清理、定时同步等场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@Scheduled` 的工作原理
- 掌握 cron 表达式的写法
- 启用 `@EnableScheduling` + 配置 `TaskScheduler`
- 能在 ruoyi-vue-pro 中读懂 `RedisStreamMessageCleanupJob` 定时任务

## 📚 前置知识

- [26-async.md](./26-async.md)
- [04-transaction.md](./04-transaction.md)
- 集群环境下更复杂的调度见 [34-xxl-job](../03-spring-boot-starters/41-xxl-job.md)

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

## 3. 关键要点总结

- **`@Scheduled`**：Spring 定时任务注解
- **`@EnableScheduling`**：启动类启用
- **3 种写法**：`fixedRate`、`fixedDelay`、`cron`
- **集群部署会重复执行**，需配合分布式锁（Redisson）
- **ruoyi 用 `@Scheduled` + Redisson Lock** 实现轻量级分布式任务
- **重任务用 XXL-Job**（支持动态配置、可视化）
- **失败处理**：try-catch 防止单个任务失败影响后续

---

**文档版本**：v1.0
**最后更新**：2026-07-13
