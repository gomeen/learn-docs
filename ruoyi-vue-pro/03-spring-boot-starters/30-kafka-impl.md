# 5.5 Kafka 实现

> 掌握 yudao 对 Kafka 的封装与多租户集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 对 Kafka 的封装
- 掌握多租户在 Kafka 中的传递
- 能在 yudao 中使用 Kafka
- 了解 Kafka 的核心概念

## 📚 前置知识

- [26-mq-starter.md](./26-mq-starter.md)
- [27-message.md](./27-message.md)
- Kafka 基础

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

## 3. ruoyi 仓库源码解读

### 3.1 Kafka 集成位置

Kafka 相关代码在 yudao 的 `yudao-spring-boot-starter-mq` 模块的 `kafka` 子包下（如果存在）。

### 3.2 多租户 Kafka 集成

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/kafka/TenantKafkaProducerInterceptor.java`

```java
public class TenantKafkaProducerInterceptor implements ProducerInterceptor<Object, Object> {

    @Override
    public ProducerRecord<Object, Object> onSend(ProducerRecord<Object, Object> record) {
        // 发送时把 tenantId 加到消息头
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId != null) {
            record.headers().add(HEADER_TENANT_ID, tenantId.toString().getBytes());
        }
        return record;
    }
}
```

**解读**：
- 用 Kafka 的 `ProducerInterceptor` 注入 tenantId
- 消费端通过 `ConsumerInterceptor` 恢复

### 3.3 Kafka 配置

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      acks: all
      retries: 3
    consumer:
      group-id: yudao
      auto-offset-reset: earliest
```

## 4. 关键要点总结

- **yudao 通过 `spring-kafka` 集成 Kafka**
- **多租户**通过 Kafka 拦截器传递
- **适用场景**：大数据、日志、行为分析
- **Kafka 优势**：高吞吐、可扩展

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 Kafka 相关的消息定义。

### 练习 2：进阶

实现"用户行为埋点"：发送 Kafka 消息，下游消费者写入 ClickHouse。

### 练习 3：挑战（选做）

对比 Kafka vs Redis Stream vs RabbitMQ 在 yudao 中的使用场景。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/mq/kafka/TenantKafkaProducerInterceptor.java`
- Kafka 文档：https://kafka.apache.org/documentation/
- Spring Kafka 文档：https://docs.spring.io/spring-kafka/docs/current/reference/html/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
