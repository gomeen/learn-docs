# 1.1 Redis 数据结构与命令

> 了解 Redis 核心数据结构与常用命令，掌握 ruoyi-vue-pro 缓存与 MQ 的底层基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis 五大核心数据结构（String / Hash / List / Set / ZSet）及其典型场景
- 掌握键的过期策略与淘汰策略
- 熟练使用 `SET` / `GET` / `DEL` / `EXPIRE` / `INCR` 等高频命令
- 能看懂 ruoyi 中 `RedisTemplate` 调用背后的 Redis 命令

## 📚 前置知识

- Java 基础语法
- Spring Boot 入门
- 了解键值存储的概念

## 1. 核心概念

### 1.1 为什么需要 Redis？

Redis 是一个**基于内存**的键值数据库，读写性能可达 10 万 QPS，常用于：
- **缓存**：把热点数据从 DB 搬到内存
- **分布式锁**：用 `SETNX` 实现
- **消息队列**：基于 List/Stream 实现
- **计数器 / 排行榜**：INCR / ZSet

### 1.2 五大核心数据结构

| 数据结构 | 用途 | 典型命令 |
|---------|------|---------|
| String | 缓存值、计数器、分布式锁 | `SET` `GET` `INCR` `SETNX` |
| Hash | 对象存储 | `HSET` `HGET` `HGETALL` |
| List | 队列、最新列表 | `LPUSH` `RPOP` `LRANGE` |
| Set | 标签、共同好友 | `SADD` `SISMEMBER` `SINTER` |
| ZSet (Sorted Set) | 排行榜、延迟队列 | `ZADD` `ZRANGE` `ZRANK` |

### 1.3 Redis Stream（Redis 5.0+）

Stream 是 Redis 内置的**消息队列**，支持消费者组、消息确认、阻塞读取。ruoyi 的 Redis Stream MQ 就是基于它实现的。

核心概念：
- **Stream Key**：消息流的名字
- **Consumer Group**：消费者分组，组内消息只被消费一次
- **XADD**：生产者添加消息
- **XREADGROUP**：消费者组读取消息
- **XACK**：消费者确认消息

## 2. 代码示例

### 2.1 字符串与过期

```bash
# 设置 key=10s
SET user:1:name "yudao" EX 10

# 获取
GET user:1:name

# 自增（计数器场景）
INCR article:1:view_count

# 分布式锁（SETNX + 过期）
SET lock:order 1 NX EX 30
```

### 2.2 Hash 存储对象

```bash
# 存储用户对象
HSET user:1 name "yudao" age 18
HGET user:1 name
HGETALL user:1

# 更新单个字段
HSET user:1 age 19
```

### 2.3 ZSet 实现排行榜

```bash
# 添加分数
ZADD leaderboard 100 "alice" 90 "bob" 95 "charlie"

# 取 Top 3
ZREVRANGE leaderboard 0 2 WITHSCORES
```

### 2.4 Redis Stream 最简示例

```bash
# 添加消息
XADD my-stream * field1 value1 field2 value2

# 创建消费者组（MKSTREAM 自动创建流）
XGROUP CREATE my-stream group1 $ MKSTREAM

# 消费者读取（阻塞 5 秒）
XREADGROUP GROUP group1 consumer1 COUNT 1 BLOCK 5000 STREAMS my-stream >

# 确认消费
XACK my-stream group1 1691234567890-0
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 通过 RedisTemplate 使用 String

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
**核心代码**（行 22-36）：

```java
@Bean
public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
    // 创建 RedisTemplate 对象
    RedisTemplate<String, Object> template = new RedisTemplate<>();
    // 设置 RedisConnection 工厂。😈 它就是实现多种 Java Redis 客户端接入的秘密工厂。感兴趣的胖友，可以自己去撸下。
    template.setConnectionFactory(factory);
    // 使用 String 序列化方式，序列化 KEY 。
    template.setKeySerializer(RedisSerializer.string());
    template.setHashKeySerializer(RedisSerializer.string());
    // 使用 JSON 序列化方式，序列化 VALUE
    RedisSerializer<?> redisSerializer = buildRedisSerializer();
    template.setValueSerializer(redisSerializer);
    template.setHashValueSerializer(redisSerializer);
    return template;
}
```

**解读**：
- 第 28 行：KEY 用 String 序列化，意味着 Redis 里 key 是人类可读的 `user:1:name`，而不是 Java 的 `\xac\xed\x00\x05`
- 第 33 行：VALUE 用 JSON 序列化，存进去的对象可以被 Redis CLI 直接看
- **设计意图**：让运维/开发同学能用 `redis-cli` 排查数据，避免序列化乱码

### 3.2 Stream Key 由类名决定

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessage.java`
**核心代码**（行 11-23）：

```java
public abstract class AbstractRedisStreamMessage extends AbstractRedisMessage {

    /**
     * 获得 Redis Stream Key，默认使用类名
     *
     * @return Channel
     */
    @JsonIgnore // 避免序列化
    public String getStreamKey() {
        return getClass().getSimpleName();
    }

}
```

**解读**：
- 第 20 行：Stream Key 默认是消息类的**简单类名**（如 `MailSendMessage`）
- 这就是 Redis Stream 的 `XADD MailSendMessage * ...`
- 类名作为 Topic，避免硬编码字符串拼写错误

## 4. 关键要点总结

- Redis 是**内存**数据库 + 可选持久化，性能极高
- 五大基础类型：String、Hash、List、Set、ZSet
- Stream（≥ 5.0）让 Redis 具备消息队列能力，支持消费组、ack、pending
- ruoyi 用类名作为 Stream Key / Channel 名，实现"类即队列"
- ruoyi 配置 String KEY + JSON VALUE，方便人眼排查

## 5. 练习题

### 练习 1：基础（必做）

用 `redis-cli` 模拟分布式锁：
```bash
SET lock:order 1 NX EX 10
# 在另一个连接里再次执行，看返回值是 OK 还是 nil？
```

**参考答案**：第二次会返回 `nil`（因为 NX 限制只能设置一次），10 秒后过期可再次设置。

### 练习 2：进阶

阅读 `YudaoRedisAutoConfiguration`，思考为什么要把 KEY 用 String 序列化、VALUE 用 JSON 序列化？如果都用 String 会怎样？

### 练习 3：挑战（选做）

写一段 Java 代码，用 `RedisTemplate` 实现"文章阅读数+1"功能，要求：
- key 是 `article:{id}:view`
- 自动过期 1 天
- 阅读数从 1 开始自增

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessage.java`
- Redis 官方文档：https://redis.io/docs/data-types/
- Redis Stream 教程：https://redis.io/docs/data-types/streams/

---

**文档版本**：v1.0
**最后更新**：2026-07-13