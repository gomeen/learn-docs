# 1.6 Redis 发布订阅：RTopic

> 理解 Redis Pub/Sub 与 Redis Stream 的差异，掌握 Redisson `RTopic` 和 ruoyi 自研的发布订阅实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis Pub/Sub 的工作原理
- 区分 Pub/Sub 和 Stream（消息持久化能力）
- 掌握 Redisson `RTopic` 的使用
- 看懂 ruoyi 中 `AbstractRedisChannelMessage` 和 `AbstractRedisChannelMessageListener` 的设计

## 📚 前置知识

- Redis 基础（参见 `01-redis-basics.md`）
- 观察者模式

## 1. 核心概念

### 1.1 Pub/Sub 模型

Redis 发布订阅是**广播**模式：
- **Publisher**：往 channel 发消息
- **Subscriber**：订阅 channel 收消息
- **Broker**：Redis 自身
- **关键缺陷**：消息不持久化，订阅者不在线就丢失

### 1.2 Pub/Sub vs Stream

| 维度 | Pub/Sub | Stream |
|------|---------|--------|
| 持久化 | 否 | 是 |
| 消费模式 | 广播（所有订阅者收到） | 消费者组（一个组只一份） |
| 确认 ack | 不需要 | 需要 |
| 适用场景 | 实时通知 | 业务消息 |

### 1.3 ruoyi 的双实现策略

ruoyi 同时实现了 Pub/Sub 和 Stream：
- **Pub/Sub**：`AbstractRedisChannelMessage`（广播场景，如配置刷新）
- **Stream**：`AbstractRedisStreamMessage`（业务消息场景）

## 2. 代码示例

### 2.1 Redis 命令版 Pub/Sub

```bash
# 订阅端
SUBSCRIBE order.notify

# 发布端
PUBLISH order.notify "订单创建成功"
```

### 2.2 Redisson RTopic 版

```java
// 文件：PubSubDemo.java
import org.redisson.api.RTopic;
import org.redisson.api.RedissonClient;
import javax.annotation.Resource;
import org.springframework.stereotype.Service;

@Service
public class PubSubDemo {

    @Resource
    private RedissonClient redissonClient;

    public void subscribe() {
        RTopic topic = redissonClient.getTopic("order.notify");
        topic.addListener(String.class, (charSequence, msg) -> {
            System.out.println("收到：" + msg);
        });
    }

    public void publish(String msg) {
        RTopic topic = redissonClient.getTopic("order.notify");
        topic.publish(msg);
    }
}
```

### 2.3 ruoyi 风格的发布订阅

```java
// 定义消息
public class OrderNotifyMessage extends AbstractRedisChannelMessage {
    private String orderId;
}

// 发布
RedisMQTemplate mqTemplate;
mqTemplate.send(new OrderNotifyMessage().setOrderId("123"));

// 订阅
@Component
public class OrderNotifyListener extends AbstractRedisChannelMessageListener<OrderNotifyMessage> {
    @Override
    public void onMessage(OrderNotifyMessage message) {
        System.out.println("订单：" + message.getOrderId());
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AbstractRedisChannelMessage 消息抽象

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/pubsub/AbstractRedisChannelMessage.java`
**核心代码**（行 11-23）：

```java
public abstract class AbstractRedisChannelMessage extends AbstractRedisMessage {

    /**
     * 获得 Redis Channel，默认使用类名
     *
     * @return Channel
     */
    @JsonIgnore // 避免序列化。原因是，Redis 发布 Channel 消息的时候，已经会指定。
    public String getChannel() {
        return getClass().getSimpleName();
    }

}
```

**解读**：
- 第 19 行：channel 默认是类名，`OrderNotifyMessage` → channel `OrderNotifyMessage`
- 第 18 行：`@JsonIgnore` 避免 channel 字段在 JSON 中重复（Redis 命令已指定 channel）
- **设计意图**：业务类即频道，避免硬编码字符串出错

### 3.2 AbstractRedisChannelMessageListener 监听抽象

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/pubsub/AbstractRedisChannelMessageListener.java`
**核心代码**（行 54-64）：

```java
@Override
public final void onMessage(Message message, byte[] bytes) {
    T messageObj = JsonUtils.parseObject(message.getBody(), messageType);
    try {
        consumeMessageBefore(messageObj);
        // 消费消息
        this.onMessage(messageObj);
    } finally {
        consumeMessageAfter(messageObj);
    }
}
```

**解读**：
- 第 56 行：用 `JsonUtils` 把 Redis 的字节流反序列化成具体的消息类型
- 第 57-63 行：消费前/后钩子（`consumeMessageBefore/After`），用于日志、链路追踪
- 第 60 行：`this.onMessage(messageObj)` 调用子类的实际业务逻辑
- `final` 关键字禁止子类覆写，保证**反序列化+拦截器**流程不被破坏

### 3.3 Pub/Sub 的 Spring 容器装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/config/YudaoRedisMQConsumerAutoConfiguration.java`
**核心代码**（行 46-62）：

```java
@Bean
@ConditionalOnBean(AbstractRedisChannelMessageListener.class) // 只有 AbstractChannelMessageListener 存在的时候，才需要注册 Redis pubsub 监听
public RedisMessageListenerContainer redisMessageListenerContainer(
        RedisMQTemplate redisMQTemplate, List<AbstractRedisChannelMessageListener<?>> listeners) {
    // 创建 RedisMessageListenerContainer 对象
    RedisMessageListenerContainer container = new RedisMessageListenerContainer();
    // 设置 RedisConnection 工厂。
    container.setConnectionFactory(redisMQTemplate.getRedisTemplate().getRequiredConnectionFactory());
    // 添加监听器
    listeners.forEach(listener -> {
        listener.setRedisMQTemplate(redisMQTemplate);
        container.addMessageListener(listener, new ChannelTopic(listener.getChannel()));
        log.info("[redisMessageListenerContainer][注册 Channel({}) 对应的监听器({})]",
                listener.getChannel(), listener.getClass().getName());
    });
    return container;
}
```

**解读**：
- `@ConditionalOnBean(AbstractRedisChannelMessageListener.class)`：只有项目里**有 pubsub 监听器**才装配这个 Bean
- `RedisMessageListenerContainer` 是 Spring Data Redis 提供的容器，专门管理 pub/sub 监听
- 每个 listener 自动注册到自己的 channel，零配置

## 4. 关键要点总结

- Pub/Sub 是广播、不持久化，适合实时通知
- Stream 是消费者组、持久化、需 ack，适合业务消息
- ruoyi 用类名作为 channel/stream key，统一规范
- `consumeMessageBefore/After` 是拦截器钩子，可用于日志/链路追踪

## 5. 练习题

### 练习 1：基础（必做）

写一个 `ConfigRefreshMessage extends AbstractRedisChannelMessage`，再写一个监听器打印"配置刷新"。

### 练习 2：进阶

思考：以下场景用 Pub/Sub 还是 Stream？为什么？
1. 用户登录成功后发短信
2. 配置中心推送"配置变更"通知
3. 订单创建后扣减库存

### 练习 3：挑战（选做）

实现 `AbstractRedisChannelMessageListener` 的拦截器：消费前打印消息体、消费后打印耗时。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/pubsub/AbstractRedisChannelMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/pubsub/AbstractRedisChannelMessageListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/config/YudaoRedisMQConsumerAutoConfiguration.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13