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

## 3. ruoyi 仓库源码解读

### 3.1 AbstractMessage 基类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/core/message/AbstractMessage.java`
**核心代码**（节选）：

```java
public abstract class AbstractMessage {
    /** 消息键（用于去重、查询） */
    private String key;
    /** 消息内容 */
    private String content;
    /** 时间戳 */
    private Long timestamp;
}
```

### 3.2 AbstractRedisStreamMessage

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessage.java`
**核心代码**：

```java
public abstract class AbstractRedisStreamMessage extends AbstractRedisMessage {

    @JsonIgnore
    public String getStreamKey() {
        return getClass().getSimpleName();
    }
}
```

**解读**：
- 业务方只需继承 + 加字段
- Stream Key = 类名（自动）

### 3.3 AbstractRedisStreamMessageListener

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
**核心代码**（行 62-80）：

```java
@Override
public void onMessage(ObjectRecord<String, String> message) {
    T messageObj = JsonUtils.parseObject(message.getValue(), messageType);
    try {
        consumeMessageBefore(messageObj);
        this.onMessage(messageObj);
        // ack 消息消费完成
        redisMQTemplate.getRedisTemplate().opsForStream().acknowledge(group, message);
    } finally {
        consumeMessageAfter(messageObj);
    }
}
```

**解读**：
- 实现 Spring 的 `StreamListener` 接口
- 业务方只重写 `onMessage(T message)` 即可
- 自动 ack + 拦截器

### 3.4 RedisMQTemplate 统一发送

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/RedisMQTemplate.java`
**核心代码**（行 38-64）：

```java
public <T extends AbstractRedisChannelMessage> void send(T message) {
    try {
        sendMessageBefore(message);
        redisTemplate.convertAndSend(message.getChannel(), JsonUtils.toJsonString(message));
    } finally {
        sendMessageAfter(message);
    }
}

public <T extends AbstractRedisStreamMessage> RecordId send(T message) {
    try {
        sendMessageBefore(message);
        return redisTemplate.opsForStream().add(StreamRecords.newRecord()
                .ofObject(JsonUtils.toJsonString(message))
                .withStreamKey(message.getStreamKey()));
    } finally {
        sendMessageAfter(message);
    }
}
```

**解读**：
- **两个 `send` 方法** 通过泛型区分 Pub/Sub 和 Stream
- 发送前/后有**拦截器链**（`RedisMessageInterceptor`）
- 业务方完全无感

### 3.5 多租户消息拦截器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/redis/TenantRedisMessageInterceptor.java`

```java
public class TenantRedisMessageInterceptor implements RedisMessageInterceptor {
    @Override
    public void sendMessageBefore(AbstractRedisMessage message) {
        // 把租户 ID 加到消息头
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId != null) {
            message.addHeader(HEADER_TENANT_ID, tenantId.toString());
        }
    }

    @Override
    public void consumeMessageBefore(AbstractRedisMessage message) {
        // 消费时设置租户
        String tenantId = message.getHeader(HEADER_TENANT_ID);
        if (StrUtil.isNotEmpty(tenantId)) {
            TenantContextHolder.setTenantId(Long.valueOf(tenantId));
        }
    }
}
```

**解读**：
- **租户上下文跨线程传递** 的关键
- 发送方携带 tenantId，消费者自动恢复
- 通过拦截器实现，**业务方无感**

## 4. 关键要点总结

- **yudao MQ Starter = 4 种 MQ 的统一抽象**
- **核心 API**：`AbstractMessage` + `MQTemplate` + 抽象 Listener
- **多租户**通过 `RedisMessageInterceptor` 自动传播
- **Redis Stream** 是 yudao 的轻量级 MQ 首选
- **业务方零感知**底层 MQ 切换

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到一个继承 `AbstractRedisStreamMessage` 的类，理解其结构。

### 练习 2：进阶

实现"订单支付成功"事件：发送 Redis Stream 消息 + 监听器更新订单状态。

### 练习 3：挑战（选做）

实现"消息重试 + 死信队列"：监听器失败时重试 3 次，最终进入死信队列。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
- Spring Messaging 文档：https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-methods/messaging.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
