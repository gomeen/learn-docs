# 3.2 ruoyi 消息抽象：Message

> 深入理解 ruoyi 中 `Message` 抽象的设计，掌握消息发送、拦截器、消费者编排机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的"消息即类"设计哲学
- 掌握 `RedisMQTemplate` 的发送 API
- 看懂拦截器的注册和触发顺序
- 能写出符合 ruoyi 风格的消息生产者

## 📚 前置知识

- 消息队列基础（详见 [MQ 核心概念](../../_common/02-mq/01-concepts.md)）
- Spring 事件机制（详见 [Spring Event](../02-spring-boot/05-event.md)）
- Java 泛型
- Redis Pub/Sub 与 Stream（详见 [Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)）

## 1. 核心概念

### 1.1 ruoyi 的"消息即类"哲学

ruoyi 把消息当作 Java 类来设计：
- `AbstractRedisChannelMessage`：广播消息父类（Pub/Sub）
- `AbstractRedisStreamMessage`：集群消费消息父类（Stream，实现详见 [Redis Stream 实现](./13-redis-stream-impl.md)）
- `AbstractRedisMessage`：公共父类（含 headers）

**好处**：
- 类型安全，IDE 自动补全
- Channel / Stream Key 默认用类名，避免硬编码
- 多 MQ 后端共用一套消息结构（Kafka / RabbitMQ / RocketMQ 原理详见 [_common/02-mq](../../_common/02-mq/)）

### 1.2 消息发送流程

```
业务代码
  → MailProducer.sendMailSendMessage(...)
    → applicationContext.publishEvent(message)  // Spring Event
      → MessageListener (内置)
        → RedisMQTemplate.send(message)  // 转给真正 MQ
          → Redis Stream XADD
```

### 1.3 拦截器链

```
sendMessageBefore（正序：[1, 2, 3]）
  → 发送消息
sendMessageAfter（倒序：[3, 2, 1]）
```

## 2. 代码示例

### 2.1 定义消息

```java
@Data
@Accessors(chain = true)
public class OrderPaidMessage extends AbstractRedisStreamMessage {
    private Long orderId;
    private BigDecimal amount;
    // getStreamKey() 默认 = "OrderPaidMessage"
}
```

### 2.2 定义消费者

```java
@Component
public class OrderPaidListener extends AbstractRedisStreamMessageListener<OrderPaidMessage> {
    @Override
    public void onMessage(OrderPaidMessage message) {
        log.info("订单 {} 已支付，金额 {}", message.getOrderId(), message.getAmount());
        // 处理逻辑...
    }
}
```

### 2.3 发送消息

```java
@Resource
private RedisMQTemplate redisMQTemplate;

public void payCallback(Order order) {
    OrderPaidMessage msg = new OrderPaidMessage()
        .setOrderId(order.getId())
        .setAmount(order.getAmount());
    redisMQTemplate.send(msg);  // 返回 RecordId
}
```

## 3. 关键要点总结

- ruoyi 用类继承区分 Pub/Sub vs Stream：`AbstractRedisChannelMessage` vs `AbstractRedisStreamMessage`
- `RedisMQTemplate.send()` 统一封装：拦截器 + 序列化 + 发送
- 拦截器 before 正序、after 倒序，模拟 try-with-resources
- 业务代码用 `ApplicationContext.publishEvent` 或 `redisMQTemplate.send` 发送消息

---

**文档版本**：v1.0
**最后更新**：2026-07-13
