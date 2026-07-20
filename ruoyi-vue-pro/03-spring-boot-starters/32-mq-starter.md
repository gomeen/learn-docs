# 5.1 yudao-spring-boot-starter-mq 架构

> 理解 yudao MQ Starter 的统一消息抽象，掌握 Redis/RabbitMQ/Kafka/RocketMQ 的统一接入。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao MQ Starter 的整体设计
- 掌握统一消息抽象（`Message` 接口）
- 了解 4 种消息中间件的适配方式
- 能根据业务选择合适的消息中间件

## 📚 前置知识

- Spring Messaging
- MQ 通用概念（详见 [MQ 概念](../../_common/02-mq/01-concepts.md)）
- Redis Pub/Sub / Stream（详见 [Redis Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)）
- RabbitMQ / Kafka / RocketMQ 基础（见 [RabbitMQ](../../_common/02-mq/03-rabbitmq.md) / [Kafka](../../_common/02-mq/02-kafka.md) / [RocketMQ](../../_common/02-mq/04-rocketmq.md)）

## 1. 核心概念

### 1.1 什么是统一消息抽象？

不同 MQ 的 API 差异很大（`RabbitTemplate`、`KafkaTemplate`、`RocketMQTemplate`），yudao 抽象出一个统一的 `Message` 接口 + `MQTemplate`，业务方只写**业务消息**，不关心底层 MQ。

### 1.2 yudao 的 4 种实现

| MQ | 抽象 | 适用场景 |
|----|------|---------|
| Redis Pub/Sub | `AbstractRedisChannelMessage` | 实时通知、广播 |
| Redis Stream | `AbstractRedisStreamMessage` | 集群消费、轻量 MQ |
| RabbitMQ | `AbstractRabbitMQMessage` | 传统企业 MQ |
| Kafka | `AbstractKafkaMessage` | 大数据、日志 |
| RocketMQ | `AbstractRocketMQMessage` | 事务消息、顺序消息 |

### 1.3 yudao 的核心组件

| 组件 | 职责 |
|------|------|
| `AbstractMessage` | 消息基类（channel/key + content） |
| `MQTemplate` | 统一发送接口 |
| `MQProducer` | 生产者抽象 |
| `MQConsumer` | 消费者抽象 |
| `AbstractRedisMessage` | Redis 消息基类 |
| `RedisMQTemplate` | Redis 发送 |
| `AbstractRedisStreamMessageListener` | Redis Stream 监听器 |

## 2. 代码示例

### 2.1 定义业务消息（Redis Stream 风格）

```java
// 文件：SmsSendMessage.java
public class SmsSendMessage extends AbstractRedisStreamMessage {
    @NotNull
    private String phone;
    @NotNull
    private String code;
}
```

**自动**：
- Stream Key = `SmsSendMessage`（类名）
- 内容通过 JSON 序列化

### 2.2 发送消息

```java
@Service
public class AuthServiceImpl {
    @Resource
    private RedisMQTemplate redisMQTemplate;

    public void sendSmsCode(String phone, String code) {
        SmsSendMessage message = new SmsSendMessage();
        message.setPhone(phone);
        message.setCode(code);
        redisMQTemplate.send(message);
    }
}
```

### 2.3 消费消息

```java
@Component
public class SmsSendMessageListener extends AbstractRedisStreamMessageListener<SmsSendMessage> {
    @Override
    public void onMessage(SmsSendMessage message) {
        log.info("收到发送短信消息: phone={}, code={}", message.getPhone(), message.getCode());
        smsService.send(message.getPhone(), message.getCode());
    }
}
```

## 3. 关键要点总结

- **yudao MQ Starter = 4 种 MQ 的统一抽象**
- **核心 API**：`AbstractMessage` + `MQTemplate` + 抽象 Listener
- **多租户**通过 `RedisMessageInterceptor` 自动传播
- **Redis Stream** 是 yudao 的轻量级 MQ 首选
- **业务方零感知**底层 MQ 切换

---

**文档版本**：v1.0
**最后更新**：2026-07-13
