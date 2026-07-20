# 5.4 RabbitMQ 实现

> 掌握 yudao 对 RabbitMQ 的封装与多租户集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 对 RabbitMQ 的封装
- 掌握多租户在 RabbitMQ 中的传递
- 能在 yudao 中使用 RabbitMQ
- 了解 RabbitMQ 的核心概念

## 📚 前置知识

- [32-mq-starter.md](./32-mq-starter.md)
- [33-message.md](./33-message.md)
- RabbitMQ 基础（详见 [RabbitMQ](../../_common/02-mq/03-rabbitmq.md)；可靠性见 [可靠性](../../_common/02-mq/05-reliability.md)）

## 1. 核心概念

### 1.1 RabbitMQ 核心概念

| 概念 | 作用 |
|------|------|
| Exchange | 交换机，接收消息 |
| Queue | 队列，存储消息 |
| Binding | 绑定规则 |
| Routing Key | 路由 key |
| VHost | 虚拟主机 |

### 1.2 yudao 的 RabbitMQ 封装

| 组件 | 作用 |
|------|------|
| `AbstractRabbitMQMessage` | 消息基类 |
| `RabbitMQTemplate` | 发送 |
| `RabbitMQMessageListener` | 监听 |
| `TenantRabbitMQInitializer` | 多租户 Exchange/Queue 自动创建 |
| `TenantRabbitMQMessagePostProcessor` | 多租户消息头 |

## 2. 代码示例

### 2.1 定义业务消息

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class OrderCreateRabbitMessage extends AbstractRabbitMQMessage {
    private Long orderId;
    private Long userId;

    @Override
    public String getExchange() {
        return "order.event";
    }

    @Override
    public String getRoutingKey() {
        return "order.created";
    }
}
```

### 2.2 发送消息

```java
@Resource
private RabbitMQTemplate rabbitMQTemplate;

public void createOrder(OrderCreateReq req) {
    OrderDO order = ...;
    orderMapper.insert(order);
    rabbitMQTemplate.send(new OrderCreateRabbitMessage()
        .setOrderId(order.getId())
        .setUserId(order.getUserId()));
}
```

### 2.3 消费消息

```java
@Component
public class OrderCreateRabbitMessageListener
        extends AbstractRabbitMQMessageListener<OrderCreateRabbitMessage> {
    @Override
    public void onMessage(OrderCreateRabbitMessage message) {
        log.info("收到订单创建消息: {}", message);
        inventoryService.deduct(message.getOrderId());
    }
}
```

## 3. 关键要点总结

- **yudao 对 RabbitMQ 的封装** 与 Redis Stream 一致
- **多租户**：启动时为每个租户创建 Exchange/Queue
- **命名规则**：`{tenantId}-{exchange}` / `{tenantId}-{queue}`
- **多租户消息头**通过 `MessagePostProcessor` 注入

---

**文档版本**：v1.0
**最后更新**：2026-07-13
