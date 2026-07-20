# 5.5 Kafka 实现

> 掌握 yudao 对 Kafka 的封装与多租户集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 对 Kafka 的封装
- 掌握多租户在 Kafka 中的传递
- 能在 yudao 中使用 Kafka
- 了解 Kafka 的核心概念

## 📚 前置知识

- [32-mq-starter.md](./32-mq-starter.md)
- [33-message.md](./33-message.md)
- Kafka 基础（详见 [Kafka](../../_common/02-mq/02-kafka.md)）

## 1. 核心概念

### 1.1 Kafka 核心概念

| 概念 | 作用 |
|------|------|
| Topic | 主题 |
| Partition | 分区（顺序保证） |
| Consumer Group | 消费者组（每条消息只被一个组内消费者消费） |
| Broker | Kafka 服务器 |
| Offset | 消费进度 |

### 1.2 Kafka vs Redis Stream vs RabbitMQ

| 特性 | Kafka | Redis Stream | RabbitMQ |
|------|-------|-------------|----------|
| 吞吐量 | 极高 | 中 | 中 |
| 延迟 | 低 | 低 | 极低 |
| 持久化 | 强 | 中 | 中 |
| 顺序保证 | 分区内 | Stream 内 | 队列内 |
| 适用场景 | 大数据、日志 | 轻量 MQ | 传统 MQ |

### 1.3 yudao 的 Kafka 封装

yudao 通过 `spring-kafka` 集成 Kafka，抽象 `AbstractKafkaMessage` 基类。

## 2. 代码示例

### 2.1 定义 Kafka 消息

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class UserBehaviorMessage extends AbstractKafkaMessage {
    private String userId;
    private String action;
    private Long timestamp;

    @Override
    public String getTopic() {
        return "user.behavior";
    }
}
```

### 2.2 发送消息

```java
@Resource
private KafkaTemplate<String, Object> kafkaTemplate;

public void trackUserBehavior(String userId, String action) {
    kafkaTemplate.send("user.behavior", new UserBehaviorMessage()
        .setUserId(userId)
        .setAction(action)
        .setTimestamp(System.currentTimeMillis()));
}
```

### 2.3 消费消息

```java
@KafkaListener(topics = "user.behavior", groupId = "user-behavior-group")
public void onMessage(UserBehaviorMessage message) {
    log.info("收到用户行为: {}", message);
    analyticsService.track(message);
}
```

## 3. 关键要点总结

- **yudao 通过 `spring-kafka` 集成 Kafka**
- **多租户**通过 Kafka 拦截器传递
- **适用场景**：大数据、日志、行为分析
- **Kafka 优势**：高吞吐、可扩展

---

**文档版本**：v1.0
**最后更新**：2026-07-13
