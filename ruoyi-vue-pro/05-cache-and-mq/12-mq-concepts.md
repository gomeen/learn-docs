# 3.1 消息队列核心概念

> 理解消息队列的核心概念、模型和常见协议，掌握 ruoyi 抽象出的 Message 体系。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解消息队列的产生背景和解决的问题
- 掌握消息模型：点对点 vs 发布订阅
- 理解消息语义：至少一次、至多一次、恰好一次
- 看懂 ruoyi 中 `AbstractRedisMessage` 抽象的设计意图

## 📚 前置知识

- Redis 基础（参见 `01-redis-basics.md`）
- Java 基础

## 1. 核心概念

### 1.1 为什么需要消息队列？

传统调用是**同步**的：A → B → C，A 必须等 B 完成才能继续。MQ 把链路变成**异步**：
- A 发消息到 MQ，立即返回
- B 任意时刻从 MQ 拉消息消费
- A 和 B 解耦，可独立伸缩

### 1.2 两大消息模型

| 模型 | 描述 | 代表 |
|------|------|------|
| 点对点（Queue） | 消息被一个消费者消费 | RabbitMQ Queue |
| 发布订阅（Topic） | 消息被多个订阅者消费 | Kafka Topic / Redis Pub/Sub |

### 1.3 三种消息语义

- **至多一次（at most once）**：消息可能丢，但不重复
- **至少一次（at least once）**：消息不丢，但可能重复（消费后再 ack）
- **恰好一次（exactly once）**：消息不丢不重（最难，常用幂等性模拟）

### 1.4 消息的四个生命周期

```
生产者 → [发送] → Broker（持久化？） → [投递] → 消费者 → [确认/失败重试]
```

## 2. 代码示例

### 2.1 同步调用 vs 异步 MQ

```java
// ❌ 同步调用：用户请求 → 邮件服务（阻塞 1s）→ 返回
public void register(User user) {
    userMapper.insert(user);
    mailService.sendWelcome(user); // 阻塞
    return "ok";
}

// ✅ MQ 异步：用户请求 → 发消息 → 返回
public void register(User user) {
    userMapper.insert(user);
    mqTemplate.send(new WelcomeMailMessage().setUserId(user.getId())); // 立即返回
    return "ok";
}

// 消费者（另线程）
@EventListener
public void onWelcome(WelcomeMailMessage msg) {
    mailService.sendWelcome(userService.getById(msg.getUserId()));
}
```

### 2.2 消息通用字段

```java
public abstract class AbstractRedisMessage {
    private Map<String, String> headers = new HashMap<>();
    public String getHeader(String key) { return headers.get(key); }
    public void addHeader(String key, String value) { headers.put(key, value); }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AbstractRedisMessage 通用消息抽象

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/message/AbstractRedisMessage.java`
**核心代码**（行 13-29）：

```java
@Data
public abstract class AbstractRedisMessage {

    /**
     * 头
     */
    private Map<String, String> headers = new HashMap<>();

    public String getHeader(String key) {
        return headers.get(key);
    }

    public void addHeader(String key, String value) {
        headers.put(key, value);
    }

}
```

**解读**：
- 所有 ruoyi Redis 消息都继承这个类
- `headers` 是 key-value 字典：可用于传递租户 ID、链路 traceId 等上下文
- `@Data` Lombok 自动生成 getter/setter/equals/hashCode
- **设计意图**：让所有 MQ 实现（Redis Stream / RabbitMQ / Kafka）共享一套消息结构

### 3.2 拦截器钩子

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/interceptor/RedisMessageInterceptor.java`
**核心代码**（行 12-26）：

```java
public interface RedisMessageInterceptor {

    default void sendMessageBefore(AbstractRedisMessage message) {
    }

    default void sendMessageAfter(AbstractRedisMessage message) {
    }

    default void consumeMessageBefore(AbstractRedisMessage message) {
    }

    default void consumeMessageAfter(AbstractRedisMessage message) {
    }

}
```

**解读**：
- 拦截器是插件化扩展点
- `sendMessageBefore`：发送前可添加 traceId、租户 ID 到 headers
- `consumeMessageAfter`：消费后可记录日志、统计耗时
- `default` 让实现类按需重写

### 3.3 生产示例：发邮件消息

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/mq/producer/mail/MailProducer.java`
**核心代码**（行 38-48）：

```java
public void sendMailSendMessage(Long sendLogId,
                                Collection<String> toMails, Collection<String> ccMails, Collection<String> bccMails,
                                Long accountId, String nickname, String title, String content,
                                File[] attachments) {
    MailSendMessage message = new MailSendMessage()
            .setLogId(sendLogId)
            .setToMails(toMails).setCcMails(ccMails).setBccMails(bccMails)
            .setAccountId(accountId).setNickname(nickname)
            .setTitle(title).setContent(content).setAttachments(attachments);
    applicationContext.publishEvent(message);
}
```

**解读**：
- 第 42-46 行：构造消息（链式 setter，Lombok @Accessors(chain=true)）
- 第 47 行：`applicationContext.publishEvent` 走 Spring Event 机制
- 这是 ruoyi 默认的"本地 MQ"实现——单 JVM 内异步
- 通过 `YudaoMqAutoConfiguration` 切换为 Redis Stream / RabbitMQ 时无需改业务代码

## 4. 关键要点总结

- MQ 解耦生产者和消费者，提升系统弹性
- 消息模型：点对点（队列）vs 发布订阅（主题）
- 三种语义：at most / at least / exactly once
- ruoyi 用 `AbstractRedisMessage` 抽象消息结构、`RedisMessageInterceptor` 抽象插件
- 业务代码用 `ApplicationContext.publishEvent` 发送，与具体 MQ 实现解耦

## 5. 练习题

### 练习 1：基础（必做）

用一句话解释：MQ 解决了同步调用的哪些问题？

### 练习 2：进阶

阅读 `AbstractRedisMessage.headers`，思考 traceId 应该在 `sendMessageBefore` 还是 `consumeMessageBefore` 设置？为什么？

### 练习 3：挑战（选做）

设计一个简单的"订单完成后发消息给库存系统扣减"的消息结构，包含订单 ID、商品列表、操作人等字段。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/message/AbstractRedisMessage.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/interceptor/RedisMessageInterceptor.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/mq/producer/mail/MailProducer.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13