# 3.2 ruoyi 消息抽象：Message

> 深入理解 ruoyi 中 `Message` 抽象的设计，掌握消息发送、拦截器、消费者编排机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的"消息即类"设计哲学
- 掌握 `RedisMQTemplate` 的发送 API
- 看懂拦截器的注册和触发顺序
- 能写出符合 ruoyi 风格的消息生产者

## 📚 前置知识

- 消息队列基础（参见 `12-mq-concepts.md`）
- Spring 事件机制
- Java 泛型

## 1. 核心概念

### 1.1 ruoyi 的"消息即类"哲学

ruoyi 把消息当作 Java 类来设计：
- `AbstractRedisChannelMessage`：广播消息父类（Pub/Sub）
- `AbstractRedisStreamMessage`：集群消费消息父类（Stream）
- `AbstractRedisMessage`：公共父类（含 headers）

**好处**：
- 类型安全，IDE 自动补全
- Channel / Stream Key 默认用类名，避免硬编码
- 多 MQ 后端共用一套消息结构

### 1.2 消息发送流程

```
业务代码
  → MailProducer.sendMailSendMessage(...)
    → applicationContext.publishEvent(message)  // Spring Event
      → MessageListener (内置)
        → RedisMQTemplate.send(message)  // 转给真正 MQ
          → Redis Stream XADD
```

### 1.3 拦截器链

```
sendMessageBefore（正序：[1, 2, 3]）
  → 发送消息
sendMessageAfter（倒序：[3, 2, 1]）
```

## 2. 代码示例

### 2.1 定义消息

```java
@Data
@Accessors(chain = true)
public class OrderPaidMessage extends AbstractRedisStreamMessage {
    private Long orderId;
    private BigDecimal amount;
    // getStreamKey() 默认 = "OrderPaidMessage"
}
```

### 2.2 定义消费者

```java
@Component
public class OrderPaidListener extends AbstractRedisStreamMessageListener<OrderPaidMessage> {
    @Override
    public void onMessage(OrderPaidMessage message) {
        log.info("订单 {} 已支付，金额 {}", message.getOrderId(), message.getAmount());
        // 处理逻辑...
    }
}
```

### 2.3 发送消息

```java
@Resource
private RedisMQTemplate redisMQTemplate;

public void payCallback(Order order) {
    OrderPaidMessage msg = new OrderPaidMessage()
        .setOrderId(order.getId())
        .setAmount(order.getAmount());
    redisMQTemplate.send(msg);  // 返回 RecordId
}
```

## 3. ruoyi 仓库源码解读

### 3.1 RedisMQTemplate 的发送方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/RedisMQTemplate.java`
**核心代码**（行 54-64）：

```java
/**
 * 发送 Redis 消息，基于 Redis Stream 实现
 *
 * @param message 消息
 * @return 消息记录的编号对象
 */
public <T extends AbstractRedisStreamMessage> RecordId send(T message) {
    try {
        sendMessageBefore(message);
        // 发送消息
        return redisTemplate.opsForStream().add(StreamRecords.newRecord()
                .ofObject(JsonUtils.toJsonString(message)) // 设置内容
                .withStreamKey(message.getStreamKey())); // 设置 stream key
    } finally {
        sendMessageAfter(message);
    }
}
```

**解读**：
- 第 56 行：`sendMessageBefore` 触发所有拦截器的发送前钩子
- 第 58-60 行：调用 Spring Data Redis 的 `opsForStream().add(...)`
- 第 60 行：stream key 直接用消息类的 `getStreamKey()`（即类名）
- 第 63 行：`finally` 保证拦截器 after 钩子一定执行

### 3.2 拦截器正序/倒序调用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/RedisMQTemplate.java`
**核心代码**（行 75-86）：

```java
private void sendMessageBefore(AbstractRedisMessage message) {
    // 正序
    interceptors.forEach(interceptor -> interceptor.sendMessageBefore(message));
}

private void sendMessageAfter(AbstractRedisMessage message) {
    // 倒序
    for (int i = interceptors.size() - 1; i >= 0; i--) {
        interceptors.get(i).sendMessageAfter(message);
    }
}
```

**解读**：
- before 正序：模拟"调用栈"——先做 trace 上下文，再做业务埋点
- after 倒序：模拟"出栈"——先收业务埋点，再清理 trace
- 这是典型的 try-with-resources / AOP 拦截器设计模式

### 3.3 Pub/Sub 发送方法对比

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/RedisMQTemplate.java`
**核心代码**（行 38-46）：

```java
/**
 * 发送 Redis 消息，基于 Redis pub/sub 实现
 *
 * @param message 消息
 */
public <T extends AbstractRedisChannelMessage> void send(T message) {
    try {
        sendMessageBefore(message);
        // 发送消息
        redisTemplate.convertAndSend(message.getChannel(), JsonUtils.toJsonString(message));
    } finally {
        sendMessageAfter(message);
    }
}
```

**解读**：
- Pub/Sub 用 `convertAndSend(channel, json)`，Stream 用 `opsForStream().add(record)`
- 两者共用拦截器钩子
- 通过**方法签名泛型** `T extends AbstractRedisChannelMessage` 区分类型，避免误用

## 4. 关键要点总结

- ruoyi 用类继承区分 Pub/Sub vs Stream：`AbstractRedisChannelMessage` vs `AbstractRedisStreamMessage`
- `RedisMQTemplate.send()` 统一封装：拦截器 + 序列化 + 发送
- 拦截器 before 正序、after 倒序，模拟 try-with-resources
- 业务代码用 `ApplicationContext.publishEvent` 或 `redisMQTemplate.send` 发送消息

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `UserRegisteredMessage extends AbstractRedisChannelMessage`，包含 userId 和 username。

### 练习 2：进阶

解释为什么 `RedisMQTemplate.send` 用泛型 `<T extends AbstractRedisStreamMessage>` 而不是 `AbstractRedisMessage`？会带来什么好处？

### 练习 3：挑战（选做）

实现一个 `TraceIdInterceptor implements RedisMessageInterceptor`：在 `sendMessageBefore` 时给 headers 加 traceId。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/RedisMQTemplate.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/message/AbstractRedisMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/interceptor/RedisMessageInterceptor.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13