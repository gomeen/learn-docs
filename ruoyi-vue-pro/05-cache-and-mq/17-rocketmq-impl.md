# 3.6 RocketMQ 集成

> 了解 RocketMQ 的核心特性，掌握 ruoyi 通过 Spring RocketMQ 集成 RocketMQ 的方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RocketMQ 的 NameServer / Broker / Producer / Consumer 模型
- 掌握 RocketMQ 的事务消息、顺序消息特性
- 看懂 ruoyi 在 WebSocket 场景使用 RocketMQ
- 能区分 RocketMQ 与 Kafka 的使用场景

## 📚 前置知识

- 消息队列基础（参见 `12-mq-concepts.md`）
- Kafka 集成（参见 `16-kafka-impl.md`）

## 1. 核心概念

### 1.1 RocketMQ 四大组件

| 组件 | 作用 |
|------|------|
| NameServer | 路由中心（轻量，类似 DNS） |
| Broker | 消息存储服务器 |
| Producer | 消息生产者 |
| Consumer | 消息消费者 |

### 1.2 RocketMQ 特色功能

- **事务消息**：2PC 实现分布式事务
- **顺序消息**：严格保证消息顺序
- **延迟消息**：支持 18 个延迟级别
- **消息回溯**：按时间戳回溯消费

### 1.3 RocketMQ vs Kafka

| 维度 | RocketMQ | Kafka |
|------|---------|-------|
| 性能 | 十万 QPS | 百万 QPS |
| 事务消息 | 原生支持 | 需自实现 |
| 顺序消息 | 强 | 分区内 |
| 适用 | 业务消息、金融交易 | 日志、大数据 |

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>org.apache.rocketmq</groupId>
    <artifactId>rocketmq-spring-boot-starter</artifactId>
    <version>2.2.3</version>
</dependency>
```

### 2.2 application.yml

```yaml
rocketmq:
  name-server: 127.0.0.1:9876
  producer:
    group: order-producer
```

### 2.3 生产者

```java
@Resource
private RocketMQTemplate rocketMQTemplate;

public void send(Order order) {
    rocketMQTemplate.syncSend("order-paid-topic", order);
}
```

### 2.4 消费者

```java
@Component
@RocketMQMessageListener(topic = "order-paid-topic", consumerGroup = "order-service")
public class OrderConsumer implements RocketMQListener<Order> {
    @Override
    public void onMessage(Order order) {
        // 处理
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 RocketMQ WebSocket 消息

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/src/main/java/cn/iocoder/yudao/framework/websocket/core/sender/rocketmq/RocketMQWebSocketMessage.java`

```java
@Data
public class RocketMQWebSocketMessage {
    private String sessionId;
    private String messageType;
    private String messageContent;
}
```

**解读**：
- ruoyi 在 WebSocket 场景支持 Redis / RabbitMQ / Kafka / RocketMQ 四种后端
- 通过不同实现类，让业务可按需切换
- 这是 ruoyi 的"适配器模式"应用

### 3.2 四种 WebSocket 消息后端

| 后端 | 实现类 | 适用 |
|------|--------|------|
| Redis | `RedisWebSocketMessage` | 小型项目 |
| RabbitMQ | `RabbitMQWebSocketMessage` | 复杂路由 |
| Kafka | `KafkaWebSocketMessage` | 高吞吐 |
| RocketMQ | `RocketMQWebSocketMessage` | 事务场景 |

通过 `WebSocketSender` 工厂，根据配置选择具体实现，业务代码无感知。

### 3.3 ruoyi RocketMQ 的事务消息使用

ruoyi 在支付、订单场景使用 RocketMQ 事务消息：
- 生产者发送事务消息（half 消息）
- 本地事务执行（更新订单 DB）
- 根据本地事务结果 commit 或 rollback 消息

这是 RocketMQ 相对 Kafka 的核心优势——**原生事务消息**，无需自实现 2PC。

## 4. 关键要点总结

- RocketMQ 是阿里开源的消息中间件，专为业务场景设计
- 核心优势：事务消息、顺序消息、延迟消息
- ruoyi 主要在 WebSocket 广播使用 RocketMQ
- 选型：业务消息 + 事务 → RocketMQ；日志 + 大数据 → Kafka

## 5. 练习题

### 练习 1：基础（必做）

列出 RocketMQ 至少三个 Kafka 没有的特性。

### 练习 2：进阶

阅读 `RocketMQWebSocketMessage`，思考为什么 ruoyi 在 WebSocket 场景支持四种 MQ 后端？

### 练习 3：挑战（选做）

写一个 RocketMQ 事务消息示例：发送 half 消息 → 执行本地事务 → commit/rollback。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/src/main/java/cn/iocoder/yudao/framework/websocket/core/sender/rocketmq/RocketMQWebSocketMessage.java`
- RocketMQ 官方文档：https://rocketmq.apache.org/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13