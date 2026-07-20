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
- Spring Boot 自动装配原理（详见 [自动配置](../02-spring-boot/09-auto-config.md)）

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

## 3. 关键要点总结

- Redisson 是基于 Netty 的 Java 客户端，内置分布式数据结构
- ruoyi 通过 `redisson-spring-boot-starter` 自动装配 `RedissonClient`
- ruoyi 自定义 `RedisTemplate` 用 JSON 序列化，且在 Redisson 之前装配
- `RLock` / `RBucket` / `RMap` 等都是分布式对象，可在多 JVM 间共享

---

**文档版本**：v1.0
**最后更新**：2026-07-13
