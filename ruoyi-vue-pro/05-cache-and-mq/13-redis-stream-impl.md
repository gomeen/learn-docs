# 3.3 Redis Stream 实现

> 深入了解 ruoyi 如何基于 Redis Stream 实现消息队列，掌握消费者组、ack、重试机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis Stream 的消费者组与消息确认机制
- 掌握 ruoyi 中 `StreamMessageListenerContainer` 的配置方式
- 理解 `AbstractRedisStreamMessageListener` 的反序列化 + ack 流程
- 知道 Redis 5.0+ 才支持 Stream

## 📚 前置知识

- Redis Stream 命令（详见 [Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)）
- ruoyi 消息抽象（详见 [ruoyi 消息抽象](./02-ruoyi-message.md)）
- Spring 容器和 Bean 生命周期（详见 [Bean 生命周期](../02-spring-boot/02-bean-lifecycle.md)）
- 消息可靠性语义（详见 [消息可靠性](../../_common/02-mq/05-reliability.md)）
- 死信与重试（详见 [死信队列](../../_common/02-mq/06-dead-letter.md)）

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

## 3. 关键要点总结

- ruoyi 用 `spring.application.name` 作为 consumer group，天然集群消费
- `autoAcknowledge(false)` + 业务完成后手动 ack，保证至少一次语义
- `cancelOnError(false)`：单条坏消息不影响其他消息
- 5 分钟未 ack 的 pending 消息由定时任务自动重投
- Redis 5.0+ 才支持 Stream

---

**文档版本**：v1.0
**最后更新**：2026-07-13
