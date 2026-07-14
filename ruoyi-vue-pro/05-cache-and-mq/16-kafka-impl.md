# 3.5 Kafka 集成

> 了解 Kafka 的核心模型，掌握 ruoyi 通过 Spring Kafka 集成 Kafka 的方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Kafka 的 Topic / Partition / ConsumerGroup 模型
- 掌握 Spring Kafka 的 `KafkaTemplate` 和 `@KafkaListener`
- 看懂 ruoyi 在哪里使用 Kafka
- 能区分 Kafka 和 RabbitMQ 的使用场景

## 📚 前置知识

- 消息队列基础（参见 `12-mq-concepts.md`）
- Spring 生态基础

## 1. 核心概念

### 1.1 Kafka 三大概念

| 概念 | 含义 |
|------|------|
| Topic | 消息主题 |
| Partition | Topic 的分区（并行单位） |
| Consumer Group | 消费组（一个分区只被组内一个消费者消费） |

### 1.2 Kafka 与 RabbitMQ 对比

| 维度 | Kafka | RabbitMQ |
|------|-------|---------|
| 性能 | 高吞吐（百万 QPS） | 中等（万级 QPS） |
| 持久化 | 天然落盘 | 需配置 |
| 消息顺序 | 分区内有序 | 队列内有序 |
| 路由 | 不支持复杂路由 | 支持多种 Exchange |
| 延迟 | 较高（批量发送） | 较低 |

### 1.3 ruoyi 的 Kafka 使用场景

- **支付回调**（pay 模块）
- **WebSocket 消息广播**（`KafkaWebSocketMessage`）
- **大数据量日志同步**

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>
</dependency>
```

### 2.2 application.yml

```yaml
spring:
  kafka:
    bootstrap-servers: 127.0.0.1:9092
    consumer:
      group-id: order-service
      auto-offset-reset: earliest
    producer:
      acks: all  # 强一致性
```

### 2.3 生产者

```java
@Resource
private KafkaTemplate<String, String> kafkaTemplate;

public void send(Order order) {
    kafkaTemplate.send("order.paid", JSON.toJSONString(order));
}
```

### 2.4 消费者

```java
@Component
public class OrderConsumer {
    @KafkaListener(topics = "order.paid", groupId = "order-service")
    public void onMessage(String message) {
        Order order = JSON.parseObject(message, Order.class);
        // 处理
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 Kafka WebSocket 消息实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/src/main/java/cn/iocoder/yudao/framework/websocket/core/sender/kafka/KafkaWebSocketMessage.java`

```java
@Data
public class KafkaWebSocketMessage {
    private String sessionId;
    private String messageType;
    private String messageContent;
}
```

**解读**：
- ruoyi 在 WebSocket 模块用 Kafka 做**跨实例消息广播**
- 一个实例收到消息 → 发到 Kafka → 所有实例消费 → 推给本地连接的 WebSocket 客户端
- 这是经典的"消息总线 + WebSocket"架构

### 3.2 ruoyi Kafka 在 Pay 模块的使用

ruoyi 在支付模块用 Kafka 做**支付回调的异步处理**：
- 支付网关回调 → Kafka → 多个订单服务实例消费 → 各自更新本地订单状态

这种架构的好处：
- 支付网关无需知道订单服务实例数
- 订单服务可水平扩展（每实例消费不同分区）
- 支付回调可重放（Kafka 消息持久化）

### 3.3 ruoyi 对 Kafka 的"轻抽象"

和 RabbitMQ 一样，ruoyi 没有自研 Kafka 抽象：
- 直接用 `KafkaTemplate`
- 直接用 `@KafkaListener`
- 业务代码遵循 Spring Kafka 标准

## 4. 关键要点总结

- Kafka 高吞吐、天然持久化，适合大数据场景
- ruoyi 用 Kafka 主要在 WebSocket 广播、支付回调、大数据同步
- ruoyi 不为 Kafka 写抽象，直接用 Spring Kafka
- 选型：高吞吐 + 日志 → Kafka；复杂路由 → RabbitMQ

## 5. 练习题

### 练习 1：基础（必做）

用 kafka-topics 创建一个 topic：
```bash
kafka-topics.sh --create --topic test --bootstrap-server localhost:9092 --partitions 3
```

### 练习 2：进阶

阅读 `KafkaWebSocketMessage`，解释为什么 WebSocket 广播要用 Kafka 而不是 Redis Pub/Sub？

### 练习 3：挑战（选做）

写一个 Kafka 生产者发送订单消息到 `order.paid` topic，消费者用 `@KafkaListener` 处理。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/src/main/java/cn/iocoder/yudao/framework/websocket/core/sender/kafka/KafkaWebSocketMessage.java`
- Spring Kafka 文档：https://docs.spring.io/spring-kafka/reference/

---

**文档版本**：v1.0
**最后更新**：2026-07-13