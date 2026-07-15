# 5.6 RocketMQ 实现

> 掌握 yudao 对 RocketMQ 的封装与多租户集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 对 RocketMQ 的封装
- 掌握多租户在 RocketMQ 中的传递
- 能在 yudao 中使用 RocketMQ
- 了解 RocketMQ 的核心概念

## 📚 前置知识

- [26-mq-starter.md](./26-mq-starter.md)
- [27-message.md](./27-message.md)
- RocketMQ 基础（详见 [RocketMQ](../../_common/02-mq/04-rocketmq.md)）

## 1. 核心概念

### 1.1 RocketMQ 核心概念

| 概念 | 作用 |
|------|------|
| Topic | 主题 |
| Message Queue | 消息队列（物理队列） |
| Producer Group | 生产者组 |
| Consumer Group | 消费者组 |
| Tag | 标签（用于消息过滤） |
| Broker | RocketMQ 服务器 |
| NameServer | 路由注册中心 |

### 1.2 RocketMQ 核心特性

- **事务消息**：发送 + 本地事务原子性
- **顺序消息**：FIFO 顺序
- **延迟消息**：指定延迟时间
- **死信队列**：消费失败的消息
- **消息回溯**：按时间重置消费进度

### 1.3 yudao 的 RocketMQ 集成

yudao 通过 `rocketmq-spring-boot-starter` 集成 RocketMQ，抽象 `AbstractRocketMQMessage` 基类。

## 2. 代码示例

### 2.1 定义 RocketMQ 消息

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class OrderPaidMessage extends AbstractRocketMQMessage {
    private Long orderId;
    private BigDecimal amount;

    @Override
    public String getTopic() {
        return "order-event";
    }
}
```

### 2.2 发送消息

```java
@Resource
private RocketMQTemplate rocketMQTemplate;

public void payOrder(Long orderId) {
    OrderDO order = orderMapper.selectById(orderId);
    // 普通消息
    rocketMQTemplate.syncSend("order-event:order-paid",
        new OrderPaidMessage()
            .setOrderId(orderId)
            .setAmount(order.getAmount()));
}
```

### 2.3 事务消息

```java
public void createOrderWithTransaction(OrderCreateReq req) {
    Message<OrderPaidMessage> message = MessageBuilder
        .withPayload(new OrderPaidMessage().setOrderId(1L))
        .build();
    // 发送事务消息
    rocketMQTemplate.sendMessageInTransaction("order-tx-producer", message, null);
}

// 事务监听器
@RocketMQTransactionListener
public class OrderTxListener implements RocketMQLocalTransactionListener {
    @Override
    public RocketMQLocalTransactionState executeLocalTransaction(Message msg, Object arg) {
        try {
            // 本地事务
            orderMapper.insert(new OrderDO());
            return RocketMQLocalTransactionState.COMMIT;
        } catch (Exception e) {
            return RocketMQLocalTransactionState.ROLLBACK;
        }
    }

    @Override
    public RocketMQLocalTransactionState checkLocalTransaction(Message msg) {
        // 消息回查
        return RocketMQLocalTransactionState.COMMIT;
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 TenantRocketMQInitializer

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/rocketmq/TenantRocketMQInitializer.java`

```java
@Component
public class TenantRocketMQInitializer implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) {
        // 启动时为每个租户创建 Topic
        for (Long tenantId : tenantApi.getTenantIds()) {
            for (AbstractRocketMQMessage msg : messageClasses) {
                String topic = tenantId + "-" + msg.getTopic();
                rocketMQTemplate.getProducer().createTopic(topic);
            }
        }
    }
}
```

**解读**：
- 启动时为每个租户创建独立 Topic
- 命名规则：`{tenantId}-{topic}`

### 3.2 RocketMQ 消息拦截器

类似 Kafka，通过 `RocketMQTemplate` 的拦截器机制传递 tenantId。

## 4. 关键要点总结

- **yudao 通过 `rocketmq-spring-boot-starter` 集成**
- **多租户**：启动时为每个租户创建独立 Topic
- **RocketMQ 优势**：事务消息、顺序消息、延迟消息
- **适用场景**：订单、支付、库存扣减

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 RocketMQ 相关的消息定义。

### 练习 2：进阶

实现"订单支付成功"的事务消息：保证本地订单更新 + 消息投递的原子性。

### 练习 3：挑战（选做）

实现"延迟消息"：订单 30 分钟未支付则自动关闭。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/rocketmq/TenantRocketMQInitializer.java`
- RocketMQ 文档：https://rocketmq.apache.org/docs/
- Spring Boot RocketMQ：https://github.com/apache/rocketmq-spring

---

**文档版本**：v1.0
**最后更新**：2026-07-13
