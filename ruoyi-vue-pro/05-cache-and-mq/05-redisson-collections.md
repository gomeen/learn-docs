# 1.5 Redisson 集合：RList / RMap / RQueue

> 了解 Redisson 提供的分布式集合，掌握它们与 Java 原生集合的区别。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redisson `RList`、`RMap`、`RQueue` 的核心 API
- 区分分布式集合与本地集合的使用场景
- 掌握 Redisson 集合的本地缓存、监听器等高级特性
- 在 ruoyi 中能识别这些集合的使用方式

## 📚 前置知识

- Redis 基础数据结构（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- Redisson 客户端（详见 [Redisson 客户端](./02-redisson.md)）
- Java 集合框架

## 1. 核心概念

### 1.1 什么是分布式集合？

Java 自带的 `ArrayList`、`HashMap` 都在**单个 JVM 内存**里。Redisson 提供的 `RList`、`RMap` 把数据存到 Redis，多个 JVM 实例共享同一份数据。

### 1.2 主要集合类型

| 类型 | Redis 底层 | 典型场景 |
|------|-----------|---------|
| `RBucket<T>` | String | 单值缓存、计数器 |
| `RList<T>` | List | 最新 N 条、消息队列 |
| `RMap<K,V>` | Hash | 分布式 Map |
| `RSet<T>` | Set | 标签、共同好友 |
| `RQueue<T>` | List | 阻塞队列、延迟队列 |
| `RDeque<T>` | List | 双端队列 |
| `RScoredSortedSet<T>` | ZSet | 排行榜 |

### 1.3 核心特性

- **可观测**：通过 `addListener` 监听数据变化
- **本地缓存**：通过 `.cache()` 配置本地缓存，兼顾性能与一致性
- **原子操作**：内置 `compute`、`merge` 等原子方法

## 2. 代码示例

### 2.1 RBucket 单值

```java
// 文件：RCollectionsDemo.java
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import javax.annotation.Resource;
import org.springframework.stereotype.Service;
import java.util.concurrent.TimeUnit;

@Service
public class RCollectionsDemo {

    @Resource
    private RedissonClient redissonClient;

    public void bucketDemo() {
        RBucket<String> bucket = redissonClient.getBucket("user:1:name");
        bucket.set("yudao", 30, TimeUnit.SECONDS);
        System.out.println(bucket.get());
    }
}
```

### 2.2 RMap 分布式 Map

```java
import org.redisson.api.RMap;

public void mapDemo() {
    RMap<String, Integer> map = redissonClient.getMap("article:view");
    map.put("a1", 100);
    map.incrementAndGet("a1"); // 原子自增
    map.addListener((k, v) -> System.out.println("key " + k + " 变成 " + v));
}
```

### 2.3 RQueue 阻塞队列

```java
import org.redisson.api.RQueue;

public void queueDemo() throws InterruptedException {
    RQueue<String> queue = redissonClient.getQueue("queue:order");
    queue.offer("order-1");

    // 阻塞式消费
    String task = queue.poll(5, TimeUnit.SECONDS);
    System.out.println("消费：" + task);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 分布式锁锁集合（IoT RTC 通话）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-im/src/main/java/cn/iocoder/yudao/module/im/dal/redis/rtc/ImRtcCallLockRedisDAO.java`

```java
@Repository
public class ImRtcCallLockRedisDAO {
    @Resource
    private RedissonClient redissonClient;

    public boolean lock(Long callId, Long timeoutMillis) {
        RLock lock = redissonClient.getLock("im:rtc:call:lock:" + callId);
        try {
            return lock.tryLock(0, timeoutMillis, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            return false;
        }
    }
}
```

**解读**：
- ruoyi 在 IoT/IM 模块使用 RedissonClient 提供的 `RLock`，确保同一通通话只有一个端能加锁
- 这就是 Redisson 集合（锁也是一种集合对象）的真实业务场景

### 3.2 ruoyi 缓存抽象走 RedisTemplate

注意：ruoyi 在**业务层**主要用 `RedisTemplate`（Spring Data Redis API）而非 Redisson 集合。原因是 Spring Cache 注解体系更通用。Redisson 集合用于**特定高性能场景**（如 IoT RTC）。

## 4. 关键要点总结

- Redisson 集合是 Redis 数据结构的 Java 封装，跨 JVM 共享
- `RBucket` / `RMap` / `RQueue` / `RSet` / `RScoredSortedSet` 对应 Redis 五大类型
- 支持监听器和本地缓存扩展
- ruoyi 业务层以 `RedisTemplate` 为主，Redisson 集合在分布式锁/IoT 等场景使用

## 5. 练习题

### 练习 1：基础（必做）

写代码：用 `RMap` 存 3 个商品库存，key 是 productId，value 是库存数。

### 练习 2：进阶

思考：什么场景下用 `RMap`，什么场景下用 `RedisTemplate.opsForHash()`？两者底层都是 Redis Hash，有什么区别？

### 练习 3：挑战（选做）

用 `RScoredSortedSet` 实现文章点赞排行榜：分数 = 点赞数，取 Top 10。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-im/src/main/java/cn/iocoder/yudao/module/im/dal/redis/rtc/ImRtcCallLockRedisDAO.java`
- Redisson 数据集合文档：https://redisson.org/docs/data-and-services/collections/

---

**文档版本**：v1.0
**最后更新**：2026-07-13