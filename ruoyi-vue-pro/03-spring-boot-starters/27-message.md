# 5.2 统一消息抽象：Message

> 深入理解 yudao 消息抽象的设计，掌握自定义消息类型。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 消息的继承体系
- 掌握 `AbstractMessage` 的字段与作用
- 能定义自己的业务消息类型
- 理解消息序列化与拦截器机制

## 📚 前置知识

- [26-mq-starter.md](./26-mq-starter.md)
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

## 3. ruoyi 仓库源码解读

### 3.1 AbstractMessage

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/core/message/AbstractMessage.java`
**核心代码**（节选）：

```java
public abstract class AbstractMessage implements Serializable {
    /** 消息 key（用于消费去重） */
    private String key;
    /** 消息内容（冗余字段） */
    private String content;
    /** 时间戳 */
    private Long timestamp;
    /** 自定义 header */
    private Map<String, String> headers = new HashMap<>();
}
```

### 3.2 AbstractRedisMessage

**核心代码**（节选）：

```java
public abstract class AbstractRedisMessage extends AbstractMessage {
    // Redis 消息的公共字段
}
```

### 3.3 AbstractRedisChannelMessage（Pub/Sub）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/pubsub/AbstractRedisChannelMessage.java`

```java
public abstract class AbstractRedisChannelMessage extends AbstractRedisMessage {
    /**
     * 获得 Redis Channel
     */
    @JsonIgnore
    public abstract String getChannel();
}
```

**解读**：
- 业务方实现 `getChannel()` 返回 Redis Channel 名
- Channel 名在子类中硬编码

### 3.4 AbstractRedisStreamMessage

**核心代码**（已读）：

```java
public abstract class AbstractRedisStreamMessage extends AbstractRedisMessage {
    @JsonIgnore
    public String getStreamKey() {
        return getClass().getSimpleName();
    }
}
```

**解读**：
- Stream Key = **类名**（自动）
- 业务方不需指定

### 3.5 AbstractRedisStreamMessageListener（消费者）

**核心代码**（行 50-60）：

```java
@SneakyThrows
protected AbstractRedisStreamMessageListener() {
    this.messageType = getMessageClass();
    this.streamKey = messageType.getDeclaredConstructor().newInstance().getStreamKey();
}

@SuppressWarnings("unchecked")
private Class<T> getMessageClass() {
    Type type = TypeUtil.getTypeArgument(getClass(), 0);
    if (type == null) {
        throw new IllegalStateException(String.format("类型(%s) 需要设置消息类型", getClass().getName()));
    }
    return (Class<T>) type;
}
```

**解读**：
- 泛型 `T` 自动推导消息类型
- `TypeUtil.getTypeArgument(getClass(), 0)` 反射获取泛型
- **业务方必须写泛型**：`extends AbstractRedisStreamMessageListener<SmsSendMessage>`

### 3.6 RedisMessageInterceptor

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/interceptor/RedisMessageInterceptor.java`

```java
public interface RedisMessageInterceptor {
    default void sendMessageBefore(AbstractRedisMessage message) {}
    default void sendMessageAfter(AbstractRedisMessage message) {}
    default void consumeMessageBefore(AbstractRedisMessage message) {}
    default void consumeMessageAfter(AbstractRedisMessage message) {}
}
```

**用途**：
- 多租户传递（TenantRedisMessageInterceptor）
- 日志埋点
- 监控
- 链路追踪

## 4. 关键要点总结

- **yudao 消息 = 抽象类 + 泛型 + JSON 序列化**
- **业务方只需继承 + 写字段**
- **Stream Key = 类名**（自动）
- **拦截器链**是扩展点
- **多租户自动传递**通过 `TenantRedisMessageInterceptor`

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 3 个 `AbstractRedisStreamMessage` 子类，理解其字段设计。

### 练习 2：进阶

实现"订单创建事件"：包含订单 ID、用户 ID、商品列表。

### 练习 3：挑战（选做）

实现一个 `TraceRedisMessageInterceptor`，记录消息从发送到消费的全链路时间。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/core/message/AbstractMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/pubsub/AbstractRedisChannelMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/interceptor/RedisMessageInterceptor.java`
- Spring Messaging 文档：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-methods/messaging.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
