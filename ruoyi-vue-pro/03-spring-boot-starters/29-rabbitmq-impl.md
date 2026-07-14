# 5.4 RabbitMQ 实现

> 掌握 yudao 对 RabbitMQ 的封装与多租户集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 对 RabbitMQ 的封装
- 掌握多租户在 RabbitMQ 中的传递
- 能在 yudao 中使用 RabbitMQ
- 了解 RabbitMQ 的核心概念

## 📚 前置知识

- [26-mq-starter.md](./26-mq-starter.md)
- [27-message.md](./27-message.md)
- RabbitMQ 基础

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

## 3. ruoyi 仓库源码解读

### 3.1 YudaoRabbitMQAutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/rabbitmq/config/YudaoRabbitMQAutoConfiguration.java`
**核心代码**（节选）：

```java
@AutoConfiguration
public class YudaoRabbitMQAutoConfiguration {
    // 让 yudao-common 的 RabbitMQTemplate 生效
}
```

### 3.2 TenantRabbitMQInitializer（多租户）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/rabbitmq/TenantRabbitMQInitializer.java`

**核心代码**（节选）：

```java
@Component
public class TenantRabbitMQInitializer implements RabbitTemplate.ConfirmCallback, ApplicationRunner {

    @Override
    public void run(ApplicationArguments args) {
        // 启动时为每个租户创建 Exchange/Queue
        for (Long tenantId : tenantApi.getTenantIds()) {
            for (AbstractRabbitMQMessage msg : messageClasses) {
                String exchange = tenantId + "-" + msg.getExchange();
                String queue = tenantId + "-" + msg.getQueue();
                // 创建 Exchange / Queue / Binding
                admin.declareExchange(new TopicExchange(exchange));
                admin.declareQueue(new Queue(queue));
                admin.declareBinding(BindingBuilder.bind(queue).to(exchange).with(msg.getRoutingKey()));
            }
        }
    }
}
```

**解读**：
- **启动时**为每个租户创建独立的 Exchange/Queue
- 命名规则：`{tenantId}-{exchange}` / `{tenantId}-{queue}`
- 租户间**完全隔离**

### 3.3 TenantRabbitMQMessagePostProcessor

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/rabbitmq/TenantRabbitMQMessagePostProcessor.java`

```java
public class TenantRabbitMQMessagePostProcessor implements MessagePostProcessor {
    @Override
    public Message postProcessMessage(Message message) throws AmqpException {
        // 发送时把 tenantId 加到消息头
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId != null) {
            message.getMessageProperties().setHeader(HEADER_TENANT_ID, tenantId);
        }
        return message;
    }
}
```

## 4. 关键要点总结

- **yudao 对 RabbitMQ 的封装** 与 Redis Stream 一致
- **多租户**：启动时为每个租户创建 Exchange/Queue
- **命名规则**：`{tenantId}-{exchange}` / `{tenantId}-{queue}`
- **多租户消息头**通过 `MessagePostProcessor` 注入

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 RabbitMQ 相关的消息定义，理解 exchange/queue 的命名。

### 练习 2：进阶

实现"订单超时关闭"：发送 RabbitMQ 延迟消息（用 TTL + DLX）。

### 练习 3：挑战（选做）

对比 Redis Stream vs RabbitMQ 在 yudao 中的使用场景，给出选型建议。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/rabbitmq/config/YudaoRabbitMQAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/rabbitmq/TenantRabbitMQInitializer.java`
- RabbitMQ 文档：https://www.rabbitmq.com/documentation.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
