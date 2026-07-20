# 5.3 Redis Stream 实现

> 深入理解 yudao 基于 Redis Stream 的消息队列实现，能在生产环境使用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis Stream 的核心概念
- 掌握 yudao 的 Redis Stream 封装
- 理解消费者组、ACK、PEL 机制
- 能用 Redis Stream 解决实际问题

## 📚 前置知识

- [33-message.md](./33-message.md)
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

## 3. 关键要点总结

- **Redis Stream = 日志型 MQ**
- **消费者组**：每个消息只被一个消费者消费
- **ACK 机制**：消费完成后才删除
- **PEL**：消费者崩溃后消息保留在此
- **`RedisPendingMessageResendJob`** 修复 PEL
- **yudao 自动注册**所有 Listener

---

**文档版本**：v1.0
**最后更新**：2026-07-13
