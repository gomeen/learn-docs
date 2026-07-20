# 5.2 统一消息抽象：Message

> 深入理解 yudao 消息抽象的设计，掌握自定义消息类型。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 消息的继承体系
- 掌握 `AbstractMessage` 的字段与作用
- 能定义自己的业务消息类型
- 理解消息序列化与拦截器机制

## 📚 前置知识

- [32-mq-starter.md](./32-mq-starter.md)
- Java 泛型
- Jackson 序列化

## 1. 核心概念

### 1.1 yudao 消息继承体系

```
AbstractMessage (公共字段)
├── AbstractRedisMessage
│   ├── AbstractRedisChannelMessage (Pub/Sub)
│   └── AbstractRedisStreamMessage (Stream)
├── AbstractRabbitMQMessage
├── AbstractKafkaMessage
└── AbstractRocketMQMessage
```

### 1.2 AbstractMessage 的设计

```java
public abstract class AbstractMessage {
    private String key;        // 消息去重 key
    private String content;    // 冗余字段（内容）
    private Long timestamp;    // 发送时间
}
```

## 2. 代码示例

### 2.1 Redis Pub/Sub 消息

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class OrderPaidMessage extends AbstractRedisChannelMessage {
    @NotNull
    private Long orderId;
    @NotNull
    private BigDecimal amount;

    @Override
    public String getChannel() {
        return "order:paid";
    }
}
```

### 2.2 Redis Stream 消息

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class SmsSendMessage extends AbstractRedisStreamMessage {
    @NotNull
    private String phone;
    @NotNull
    private String code;
    // 自动从 getStreamKey() 获取 stream 名
}
```

### 2.3 自定义消息头

```java
public class TenantMessage extends AbstractRedisStreamMessage {
    private Long tenantId;
    private String businessData;

    public Map<String, String> getHeaders() {
        return Map.of("tenantId", String.valueOf(tenantId));
    }
}
```

## 3. 关键要点总结

- **yudao 消息 = 抽象类 + 泛型 + JSON 序列化**
- **业务方只需继承 + 写字段**
- **Stream Key = 类名**（自动）
- **拦截器链**是扩展点
- **多租户自动传递**通过 `TenantRedisMessageInterceptor`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
