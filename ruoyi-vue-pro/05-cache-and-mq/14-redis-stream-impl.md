# 3.3 Redis Stream 实现

> 深入了解 ruoyi 如何基于 Redis Stream 实现消息队列，掌握消费者组、ack、重试机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis Stream 的消费者组与消息确认机制
- 掌握 ruoyi 中 `StreamMessageListenerContainer` 的配置方式
- 理解 `AbstractRedisStreamMessageListener` 的反序列化 + ack 流程
- 知道 Redis 5.0+ 才支持 Stream

## 📚 前置知识

- Redis Stream 命令（参见 `01-redis-basics.md`）
- ruoyi 消息抽象（参见 `13-ruoyi-message.md`）
- Spring 容器和 Bean 生命周期

## 1. 核心概念

### 1.1 Redis Stream 关键概念

| 概念 | 含义 |
|------|------|
| Stream Key | 消息流的 Redis key |
| Consumer Group | 消费组，组内消息只投递给一个消费者 |
| Pending | 已投递但未 ack 的消息（pending 队列） |
| XADD | 添加消息 |
| XREADGROUP | 消费者组读取消息 |
| XACK | 确认消费完成 |

### 1.2 ruoyi Stream 实现的关键角色

- `AbstractRedisStreamMessage`：消息抽象（含 stream key）
- `AbstractRedisStreamMessageListener`：消费者抽象（含 onMessage）
- `YudaoRedisMQConsumerAutoConfiguration`：消费者容器装配
- `RedisPendingMessageResendJob`：pending 消息重投
- `RedisStreamMessageCleanupJob`：历史消息清理

## 2. 代码示例

### 2.1 发送消息

```java
@Resource
private RedisMQTemplate redisMQTemplate;

public void publish(Order order) {
    OrderPaidMessage msg = new OrderPaidMessage().setOrderId(order.getId());
    RecordId recordId = redisMQTemplate.send(msg);
    System.out.println("消息 id：" + recordId);
}
```

### 2.2 消费者

```java
@Component
public class OrderPaidListener extends AbstractRedisStreamMessageListener<OrderPaidMessage> {
    @Override
    public void onMessage(OrderPaidMessage message) {
        // 业务处理
        System.out.println("订单支付：" + message.getOrderId());
        // 容器自动 ack（在 AbstractRedisStreamMessageListener.onMessage 中）
    }
}
```

### 2.3 配置 application.yml

```yaml
spring:
  application:
    name: order-service  # 作为 consumer group 名
  redis:
    host: 127.0.0.1
```

## 3. ruoyi 仓库源码解读

### 3.1 AbstractRedisStreamMessageListener 核心 onMessage

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
**核心代码**（行 62-80）：

```java
@Override
public void onMessage(ObjectRecord<String, String> message) {
    // 消费消息
    T messageObj = JsonUtils.parseObject(message.getValue(), messageType);
    try {
        consumeMessageBefore(messageObj);
        // 消费消息
        this.onMessage(messageObj);
        // ack 消息消费完成
        redisMQTemplate.getRedisTemplate().opsForStream().acknowledge(group, message);
        // TODO 芋艿：需要额外考虑以下几个点：
        // 1. 处理异常的情况
        // 2. 发送日志；以及事务的结合
        // 3. 消费日志；以及通用的幂等性
        // 4. 消费失败的重试，https://zhuanlan.zhihu.com/p/60501638
    } finally {
        consumeMessageAfter(messageObj);
    }
}
```

**解读**：
- 第 65 行：用泛型 `T` 把 JSON 反序列化为具体类型
- 第 67 行：消费前钩子（拦截器）
- 第 69 行：调用子类业务方法
- 第 71 行：**手动 ack**——只有业务执行成功才确认，否则留在 pending 队列
- 第 78 行：消费后钩子
- TODO 注释是 ruoyi 团队留的待办——重试、幂等等

### 3.2 消费者分组名 = 应用名

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
**核心代码**（行 38-44）：

```java
/**
 * Redis 消费者分组，默认使用 spring.application.name 名字
 */
@Value("${spring.application.name}")
@Getter
private String group;
```

**解读**：
- ruoyi 用 `spring.application.name` 作为 Redis Stream 的 consumer group 名
- 这意味着：**同一个应用（多个实例）共享一个组**，组内消息只被一个实例消费
- 不同应用（不同组）各自消费——天然支持"集群消费 + 广播订阅"

### 3.3 Stream 容器装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/config/YudaoRedisMQConsumerAutoConfiguration.java`
**核心代码**（行 93-136）：

```java
@Bean(initMethod = "start", destroyMethod = "stop")
@ConditionalOnBean(AbstractRedisStreamMessageListener.class)
public StreamMessageListenerContainer<String, ObjectRecord<String, String>> redisStreamMessageListenerContainer(
        RedisMQTemplate redisMQTemplate, List<AbstractRedisStreamMessageListener<?>> listeners) {
    RedisTemplate<String, ?> redisTemplate = redisMQTemplate.getRedisTemplate();
    checkRedisVersion(redisTemplate);
    // 创建 StreamMessageListenerContainer 容器
    StreamMessageListenerContainer.StreamMessageListenerContainerOptions<String, ObjectRecord<String, String>> containerOptions =
            StreamMessageListenerContainer.StreamMessageListenerContainerOptions.builder()
                    .batchSize(10) // 一次性最多拉取多少条消息
                    .targetType(String.class) // 目标类型。统一使用 String，通过自己封装的 AbstractStreamMessageListener 去反序列化
                    .build();
    StreamMessageListenerContainer<String, ObjectRecord<String, String>> container =
            StreamMessageListenerContainer.create(redisMQTemplate.getRedisTemplate().getRequiredConnectionFactory(), containerOptions);

    // 第二步，注册监听器，消费对应的 Stream 主题
    String consumerName = buildConsumerName();
    listeners.parallelStream().forEach(listener -> {
        // 创建 listener 对应的消费者分组
        try {
            redisTemplate.opsForStream().createGroup(listener.getStreamKey(), listener.getGroup());
        } catch (Exception ignore) {
        }
        listener.setRedisMQTemplate(redisMQTemplate);
        Consumer consumer = Consumer.from(listener.getGroup(), consumerName);
        StreamOffset<String> streamOffset = StreamOffset.create(listener.getStreamKey(), ReadOffset.lastConsumed());
        StreamMessageListenerContainer.StreamReadRequestBuilder<String> builder = StreamMessageListenerContainer.StreamReadRequest
                .builder(streamOffset).consumer(consumer)
                .autoAcknowledge(false) // 不自动 ack
                .cancelOnError(throwable -> false); // 默认配置，发生异常就取消消费，显然不符合预期；因此，我们设置为 false
        container.register(builder.build(), listener);
    });
    return container;
}
```

**解读**：
- 第 95 行：`@Bean(initMethod = "start")` 启动时自动 start 容器
- 第 98 行：`checkRedisVersion` 检查 Redis ≥ 5.0
- 第 102 行：`batchSize(10)` 每次最多拉 10 条
- 第 104 行：`targetType(String.class)` 统一用 String，ruoyi 自己反序列化
- 第 117 行：尝试创建 group（已存在就忽略）
- 第 123 行：consumer name = `IP@进程号`，参考 RocketMQ
- 第 125 行：`ReadOffset.lastConsumed()` 只消费**新增**消息
- 第 129 行：`autoAcknowledge(false)` 关键！ruoyi 手动 ack
- 第 130 行：`cancelOnError(false)` 出错不取消监听（否则一条坏消息能拖垮所有）

### 3.4 Pending 消息重投

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
**核心代码**（行 69-104 摘选）：

```java
private void execute() {
    StreamOperations<String, Object, Object> ops = redisTemplate.getRedisTemplate().opsForStream();
    listeners.forEach(listener -> {
        PendingMessagesSummary pendingMessagesSummary = Objects.requireNonNull(ops.pending(listener.getStreamKey(), listener.getGroup()));
        Map<String, Long> pendingMessagesPerConsumer = pendingMessagesSummary.getPendingMessagesPerConsumer();
        pendingMessagesPerConsumer.forEach((consumerName, pendingMessageCount) -> {
            // 每个消费者的 pending消息的详情信息
            PendingMessages pendingMessages = ops.pending(listener.getStreamKey(), Consumer.from(listener.getGroup(), consumerName), Range.unbounded(), pendingMessageCount);
            if (pendingMessages.isEmpty()) {
                return;
            }
            pendingMessages.forEach(pendingMessage -> {
                // 获取消息上一次传递到 consumer 的时间
                long lastDelivery = pendingMessage.getElapsedTimeSinceLastDelivery().getSeconds();
                if (lastDelivery < EXPIRE_TIME){ // 5 分钟内的不重投
                    return;
                }
                // 重新投递消息
                redisTemplate.getRedisTemplate().opsForStream().add(StreamRecords.newRecord()
                        .ofObject(records.get(0).getValue())
                        .withStreamKey(listener.getStreamKey()));
                // ack 消息消费完成
                redisTemplate.getRedisTemplate().opsForStream().acknowledge(listener.getGroup(), records.get(0));
            });
        });
    });
}
```

**解读**：
- 这是 ruoyi 的**死信重试机制**：5 分钟未 ack 的消息，自动重新投递
- 通过定时任务（每分钟第 35 秒执行）+ 分布式锁保证多实例只有一个执行
- `if (lastDelivery < EXPIRE_TIME) return;`：避免反复重投刚发出去的消息

## 4. 关键要点总结

- ruoyi 用 `spring.application.name` 作为 consumer group，天然集群消费
- `autoAcknowledge(false)` + 业务完成后手动 ack，保证至少一次语义
- `cancelOnError(false)`：单条坏消息不影响其他消息
- 5 分钟未 ack 的 pending 消息由定时任务自动重投
- Redis 5.0+ 才支持 Stream

## 5. 练习题

### 练习 1：基础（必做）

用 redis-cli 创建一个 stream 消费者组，并读一条消息：
```bash
XADD my-stream * field1 v1
XGROUP CREATE my-stream group1 $
XREADGROUP GROUP group1 c1 COUNT 1 STREAMS my-stream >
```

### 练习 2：进阶

阅读 `redisStreamMessageListenerContainer` 方法，解释为什么 `autoAcknowledge(false)` 比 `autoAcknowledge(true)` 更安全？

### 练习 3：挑战（选做）

实现一个 `RedisStreamMessageListener<OrderPaidMessage>`，业务异常时模拟"5 分钟后重投"行为。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/config/YudaoRedisMQConsumerAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13