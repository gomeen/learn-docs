# 3.4 RabbitMQ 集成

> 了解 RabbitMQ 的核心概念，掌握 ruoyi 通过 Spring AMQP 集成 RabbitMQ 的方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RabbitMQ 的 Exchange / Queue / RoutingKey 模型
- 掌握 Spring AMQP 的 `@RabbitListener` 用法
- 看懂 ruoyi 的 `YudaoRabbitMQAutoConfiguration` 配置
- 在 ruoyi 中切换为 RabbitMQ 后端

## 📚 前置知识

- AMQP 协议基础
- Spring Boot 消息中间件
- ruoyi 消息抽象（参见 `13-ruoyi-message.md`）

## 1. 核心概念

### 1.1 RabbitMQ 三大组件

| 组件 | 作用 |
|------|------|
| Exchange | 接收生产者消息，按规则路由到 Queue |
| Queue | 存储消息，等待消费者消费 |
| Binding | Exchange 和 Queue 的绑定关系（带 RoutingKey） |

### 1.2 四种 Exchange 类型

| 类型 | 路由规则 |
|------|---------|
| direct | 完全匹配 RoutingKey |
| topic | 模式匹配（`*` 一个词，`#` 多个词） |
| fanout | 广播，忽略 RoutingKey |
| headers | 匹配消息头（极少用） |

### 1.3 ruoyi 的 RabbitMQ 集成策略

ruoyi 没有自己实现 RabbitMQ 抽象，而是直接用 Spring AMQP：
- `spring-boot-starter-amqp` 自动装配
- 业务代码用 `@RabbitListener` 监听
- ruoyi 只做 starter 启用

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-amqp</artifactId>
</dependency>
```

### 2.2 application.yml

```yaml
spring:
  rabbitmq:
    host: 127.0.0.1
    port: 5672
    username: guest
    password: guest
    listener:
      simple:
        acknowledge-mode: manual  # 手动 ack
```

### 2.3 生产者

```java
@Resource
private RabbitTemplate rabbitTemplate;

public void send(Order order) {
    rabbitTemplate.convertAndSend("order.exchange", "order.paid", order);
}
```

### 2.4 消费者

```java
@Component
public class OrderConsumer {
    @RabbitListener(queues = "order.paid.queue")
    public void onMessage(Order order) {
        System.out.println("收到：" + order);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 YudaoRabbitMQAutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/rabbitmq/config/YudaoRabbitMQAutoConfiguration.java`

```java
package cn.iocoder.yudao.framework.mq.rabbitmq.config;

@AutoConfiguration
public class YudaoRabbitMQAutoConfiguration {
}
```

**解读**：
- ruoyi 的 RabbitMQ 配置类**几乎为空**——只标记 `@AutoConfiguration` 触发装配
- 真正干活的是 Spring Boot 的 `RabbitAutoConfiguration`
- 这是 ruoyi 的策略：**Redis Stream 自研一套，RabbitMQ/Kafka/RocketMQ 走 Spring 生态**

### 3.2 ruoyi 业务层使用 RabbitMQ

ruoyi 的 RabbitMQ 业务代码主要在：
- `yudao-module-pay`（支付回调）
- `yudao-module-mall`（订单事件）

通过 `@RabbitListener` + `RabbitTemplate` 直接使用，没有强制走 `RedisMQTemplate` 抽象。这是**务实**的选择：
- Redis 自研抽象是为了屏蔽 Stream 的复杂 API
- RabbitMQ/Kafka 生态成熟，Spring AMQP 已经做得很好了

### 3.3 三种 MQ 后端的选型对比

| MQ | ruoyi 抽象方式 | 适用场景 |
|----|--------------|---------|
| Redis Stream | 自研 `RedisMQTemplate` | 单 Redis、简单业务 |
| RabbitMQ | 直接用 Spring AMQP | 复杂路由、事务消息 |
| Kafka | 直接用 Spring Kafka | 大数据量、日志聚合 |
| RocketMQ | 直接用 Spring RocketMQ | 阿里系、事务消息 |

## 4. 关键要点总结

- RabbitMQ 三大组件：Exchange、Queue、Binding
- ruoyi 没有强抽象 RabbitMQ，而是依赖 Spring AMQP 生态
- `@RabbitListener` + `RabbitTemplate` 是核心 API
- 业务根据场景选择：Redis Stream（简单）/ RabbitMQ（复杂路由）/ Kafka（日志）

## 5. 练习题

### 练习 1：基础（必做）

用 RabbitMQ Management 创建一个 exchange `test.exchange`、queue `test.queue`、binding 用 routing key `test.key`。

### 练习 2：进阶

思考：为什么 ruoyi 不像 Redis Stream 那样给 RabbitMQ 也写一套抽象？

### 练习 3：挑战（选做）

写一个生产者发送 `Order` 对象到 `order.exchange`（topic），消费者监听 `order.*.paid` 通配路由。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/rabbitmq/config/YudaoRabbitMQAutoConfiguration.java`
- Spring AMQP 文档：https://docs.spring.io/spring-amqp/reference/

---

**文档版本**：v1.0
**最后更新**：2026-07-13