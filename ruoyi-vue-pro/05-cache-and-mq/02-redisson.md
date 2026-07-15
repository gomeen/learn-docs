# 1.2 Redisson 客户端

> 了解 Redisson 是什么、它与 Jedis/Lettuce 的区别，掌握 ruoyi 如何集成 Redisson。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redisson 的定位和核心能力
- 区分 Redisson、Jedis、Lettuce 三大客户端
- 知道 ruoyi 通过 `RedissonAutoConfigurationV2` 自动装配 RedissonClient
- 能正确使用 `RedissonClient` Bean 注入

## 📚 前置知识

- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- Spring Boot 自动装配原理（详见 [自动配置](../02-spring-boot/08-auto-config.md)）

## 1. 核心概念

### 1.1 什么是 Redisson

Redisson 是 Redis 官方推荐的 Java 客户端，提供**分布式**和**可伸缩**的 Java 数据结构：
- 分布式锁 `RLock`（详见 [Redisson 分布式锁](./03-redisson-lock.md)）、分布式集合 `RMap`、分布式队列 `RQueue`（详见 [Redisson 集合](./05-redisson-collections.md)）
- 限流器 `RRateLimiter`（详见 [Redisson 限流](./04-redisson-rate-limiter.md)）、布隆过滤器 `RBloomFilter`
- 主题发布订阅 `RTopic`（Redis Pub/Sub 原理详见 [Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)）
- 远程调用 `RRemoteService`

它底层**基于 Netty**，性能比 Jedis 高，比 Lettuce 功能丰富得多。

### 1.2 三大客户端对比

| 客户端 | 底层 | 线程安全 | 分布式能力 | 性能 |
|--------|------|---------|-----------|------|
| Jedis | 阻塞 IO | 否（需连接池） | 无 | 中 |
| Lettuce | Netty | 是 | 无 | 高 |
| Redisson | Netty | 是 | **强**（分布式锁/集合） | 高 |

**结论**：ruoyi 选 Redisson 的核心理由是**内置分布式能力**，省得自己实现。

## 2. 代码示例

### 2.1 application.yml 配置

```yaml
spring:
  redis:
    host: 127.0.0.1
    port: 6379
    password:  # 默认无密码
    database: 0
```

### 2.2 注入 RedissonClient

```java
// 文件：RedissonDemo.java
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

@Service
public class RedissonDemo {

    @Resource
    private RedissonClient redissonClient; // Redisson 自动装配的客户端

    public void demo() {
        // 获取分布式 Key
        RBucket<String> bucket = redissonClient.getBucket("name");
        bucket.set("yudao", 30, TimeUnit.SECONDS);
        System.out.println(bucket.get());
    }
}
```

**说明**：
- `RedissonClient` 是 Redisson 提供的**门面**，所有分布式对象都从这里拿
- Spring Boot 引入 `redisson-spring-boot-starter` 依赖后自动装配

## 3. ruoyi 仓库源码解读

### 3.1 YudaoRedisAutoConfiguration 与 Redisson 协作

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
**核心代码**（行 16-17）：

```java
@AutoConfiguration(before = RedissonAutoConfigurationV2.class) // 目的：使用自己定义的 RedisTemplate Bean
public class YudaoRedisAutoConfiguration {
```

**解读**：
- `@AutoConfiguration(before = RedissonAutoConfigurationV2.class)`：ruoyi 自己的 Redis 自动装配在 Redisson 自动装配**之前**执行
- 这样确保后续的 `RedisTemplate` Bean 用的是 ruoyi 自定义的 JSON 序列化版本，而不是 Redisson 默认的
- **设计意图**：让 ruoyi 接管 RedisTemplate 的配置，Redisson 只贡献 `RedissonClient`

### 3.2 RedissonClient 用于分布式锁

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
**核心代码**（行 46-50）：

```java
/**
 * 一分钟执行一次,这里选择每分钟的 35 秒执行，是为了避免整点任务过多的问题
 */
@Scheduled(cron = "35 * * * * ?")
public void messageResend() {
    RLock lock = redissonClient.getLock(resendLockKey);
    if (lock.tryLock()) {
```

**解读**：
- 第 48 行：`redissonClient.getLock(key)` 拿到 Redisson 的分布式锁（`RLock`）
- 第 49 行：`tryLock()` 尝试非阻塞获取锁，拿到锁的实例才有资格重发消息
- 这就是 Redisson 相对 Lettuce 的核心价值——**一行代码搞定分布式锁**

## 4. 关键要点总结

- Redisson 是基于 Netty 的 Java 客户端，内置分布式数据结构
- ruoyi 通过 `redisson-spring-boot-starter` 自动装配 `RedissonClient`
- ruoyi 自定义 `RedisTemplate` 用 JSON 序列化，且在 Redisson 之前装配
- `RLock` / `RBucket` / `RMap` 等都是分布式对象，可在多 JVM 间共享

## 5. 练习题

### 练习 1：基础（必做）

写一个 `application.yml`，配置 Redis 主机为 `127.0.0.1`，端口 `6379`。

### 练习 2：进阶

阅读 `YudaoRedisAutoConfiguration` 第 16 行的 `before` 注解，思考：
- 如果没有 `before`，会出现什么问题？
- Redisson 的默认 `RedisTemplate` 和 ruoyi 自定义的有什么差异？

### 练习 3：挑战（选做）

用 `RedissonClient.getBucket()` 实现一个简单的"分布式计数器"：
- 多实例同时调用 `incrementAndGet()`，最终值 = 所有实例调用次数之和
- 提示：`RBucket` 只能整体 set，要实现原子自增需要用 `RAtomicLong`

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
- Redisson 官方文档：https://redisson.org/docs/getting-started/

---

**文档版本**：v1.0
**最后更新**：2026-07-13