# 5.3 Redis Stream 实现

> 深入理解 yudao 基于 Redis Stream 的消息队列实现，能在生产环境使用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis Stream 的核心概念
- 掌握 yudao 的 Redis Stream 封装
- 理解消费者组、ACK、PEL 机制
- 能用 Redis Stream 解决实际问题

## 📚 前置知识

- [27-message.md](./27-message.md)
- Redis 5.0+ 的 Stream 数据类型（详见 [Redis Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)）
- 消息队列基础（详见 [MQ 概念](../../_common/02-mq/01-concepts.md)）

## 1. 核心概念

### 1.1 Redis Stream 是什么？

Redis 5.0+ 引入的**日志型数据结构**，类似 Kafka：
- 每个消息有唯一 ID
- 消息持久化（不会因消费者离线丢失）
- 支持**消费者组**（每个消息只被一个消费者消费）
- 支持**ACK 机制**（消费完成后才删除）

### 1.2 与 Pub/Sub 对比

| 特性 | Pub/Sub | Stream |
|------|---------|--------|
| 持久化 | 否 | 是 |
| 消费者组 | 不支持 | 支持 |
| ACK | 不需要 | 需要 |
| 历史回放 | 不支持 | 支持 |
| 性能 | 高 | 中 |

### 1.3 Redis Stream 关键命令

```
XADD key * field value            # 添加消息
XREAD COUNT n BLOCK ms STREAMS key id  # 阻塞读
XGROUP CREATE key group id         # 创建消费者组
XREADGROUP GROUP group consumer COUNT n STREAMS key id  # 组读
XACK key group id                  # ACK
XPENDING key group                 # 未确认消息
```

## 2. 代码示例

### 2.1 业务消息定义

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class OrderCreateMessage extends AbstractRedisStreamMessage {
    private Long orderId;
    private Long userId;
    private BigDecimal amount;
}
```

### 2.2 发送消息

```java
@Resource
private RedisMQTemplate redisMQTemplate;

public void createOrder(OrderCreateReq req) {
    OrderDO order = ...;
    orderMapper.insert(order);
    // 发送消息
    redisMQTemplate.send(new OrderCreateMessage()
        .setOrderId(order.getId())
        .setUserId(order.getUserId())
        .setAmount(order.getAmount()));
}
```

### 2.3 消费消息

```java
@Component
public class OrderCreateMessageListener extends AbstractRedisStreamMessageListener<OrderCreateMessage> {
    @Override
    public void onMessage(OrderCreateMessage message) {
        // 扣减库存
        inventoryService.deduct(message.getOrderId());
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AbstractRedisStreamMessage

```java
public abstract class AbstractRedisStreamMessage extends AbstractRedisMessage {
    @JsonIgnore
    public String getStreamKey() {
        return getClass().getSimpleName();
    }
}
```

### 3.2 AbstractRedisStreamMessageListener 核心流程

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
**核心代码**（行 62-80）：

```java
@Override
public void onMessage(ObjectRecord<String, String> message) {
    // 1. 反序列化
    T messageObj = JsonUtils.parseObject(message.getValue(), messageType);
    try {
        // 2. 消费前拦截器
        consumeMessageBefore(messageObj);
        // 3. 业务处理
        this.onMessage(messageObj);
        // 4. ACK（关键）
        redisMQTemplate.getRedisTemplate().opsForStream().acknowledge(group, message);
    } finally {
        // 5. 消费后拦截器
        consumeMessageAfter(messageObj);
    }
}
```

**解读**：
- **3 步**核心：反序列化 → 业务处理 → ACK
- ACK **必须**调用，否则消息会一直在 PEL（Pending Entries List）

### 3.3 YudaoRedisMQConsumerAutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/config/YudaoRedisMQConsumerAutoConfiguration.java`

**核心代码**（节选）：

```java
@Bean
public StreamMessageListenerContainer<String, ObjectRecord<String, String>> redisStreamMessageListener(
        RedisMQTemplate redisTemplate) {
    // 1. 创建 StreamMessageListenerContainer
    StreamMessageListenerContainer.StreamMessageListenerContainerOptions<String, ObjectRecord<String, String>> options =
            StreamMessageListenerContainer.StreamMessageListenerContainerOptions.builder()
                    .pollTimeout(Duration.ofSeconds(3))
                    .targetType(...)
                    .build();
    StreamMessageListenerContainer<String, ObjectRecord<String, String>> container =
            StreamMessageListenerContainer.create(redisTemplate.getRedisTemplate().getConnectionFactory(), options);

    // 2. 注册所有 Listener
    Map<String, AbstractRedisStreamMessageListener> listenerMap =
            applicationContext.getBeansOfType(AbstractRedisStreamMessageListener.class);
    listenerMap.forEach((beanName, listener) -> {
        // 2.1 启动 Listener
        container.receive(
                Consumer.from(listener.getGroup(), listener.getStreamKey()),
                StreamOffset.create(listener.getStreamKey(), ReadOffset.lastConsumed()),
                listener);
        // 2.2 创建消费者组
        redisTemplate.getRedisTemplate().opsForStream().createGroup(listener.getStreamKey(), ReadOffset.from("0"), listener.getGroup());
    });
    // 3. 启动容器
    container.start();
    return container;
}
```

**解读**：
- **自动**发现所有 `AbstractRedisStreamMessageListener` Bean
- 每个 Listener **自动**加入消费者组
- 用 `ReadOffset.lastConsumed()` 从最新消息开始读

### 3.4 RedisPendingMessageResendJob（PEL 修复）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`

**核心代码**（节选）：

```java
public class RedisPendingMessageResendJob implements JobHandler {
    @Override
    public String execute(String param) {
        // 1. 找出 PEL 中超过 10 分钟未 ACK 的消息
        PendingMessages pendingMessages = redisTemplate.opsForStream().pending(
            streamKey, Consumer.from(group, "consumer"));
        for (PendingMessage msg : pendingMessages) {
            // 2. 重新投递
            redisTemplate.opsForStream().claim(streamKey, group, "consumer",
                Duration.ofMinutes(10), msg.getId());
        }
        return "重投完成";
    }
}
```

**解读**：
- 消费者崩溃后，未 ACK 的消息会留在 PEL
- 定时任务扫描 PEL，把超时的消息**重新投递**给其他消费者
- 解决**消费者故障**问题

### 3.5 RedisStreamMessageCleanupJob

清理老的已 ACK 消息，避免 Redis 内存增长。

## 4. 关键要点总结

- **Redis Stream = 日志型 MQ**
- **消费者组**：每个消息只被一个消费者消费
- **ACK 机制**：消费完成后才删除
- **PEL**：消费者崩溃后消息保留在此
- **`RedisPendingMessageResendJob`** 修复 PEL
- **yudao 自动注册**所有 Listener

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中实现"订单创建事件"：发送 Stream 消息 + Listener 扣库存。

### 练习 2：进阶

实现"消息重试"：Listener 失败时重试 3 次，最终进入死信队列。

### 练习 3：挑战（选做）

实现"消息顺序消费"：同一订单的消息必须按发送顺序处理。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/config/YudaoRedisMQConsumerAutoConfiguration.java`
- Redis Stream 文档：https://redis.io/docs/data-types/streams/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
