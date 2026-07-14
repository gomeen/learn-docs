# 2.3 RabbitMQ 原理与实战

> 理解 RabbitMQ 的 Exchange/Queue/Binding 模型与消息确认机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 RabbitMQ 的四种 Exchange 类型
- 理解消息确认（Publisher Confirms / Consumer ACK）
- 掌握死信队列（DLX）和延迟队列的实现
- 用 pika 实现 Python 客户端

## 📚 前置知识

- 消息队列基本概念（`02-mq/01-concepts.md`）
- AMQP 协议基础
- 网络通信基础

## 1. 核心概念

### 1.1 RabbitMQ 是什么？

RabbitMQ 是基于 **AMQP 0.9.1** 协议的**功能丰富**的消息中间件，由 Erlang 编写。它的设计目标是**灵活的路由**和**可靠投递**，适合企业级应用集成。

### 1.2 核心架构

```
                    ┌─────────────────┐
Producer ────→   Exchange  (路由)
                    └────────┬────────┘
                             │ Binding (路由规则)
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
           Queue-1        Queue-2        Queue-3
              ↓              ↓              ↓
           Consumer-1     Consumer-2     Consumer-3
```

### 1.3 四种 Exchange 类型

| 类型 | 路由规则 | 典型场景 |
|------|---------|---------|
| **Direct** | routing key 完全匹配 | 点对点、按业务名分发 |
| **Topic** | routing key 模式匹配（`*` 一个词 / `#` 多个词） | 按类别订阅（`order.*` / `user.#`） |
| **Fanout** | 忽略 routing key，广播到所有绑定 queue | 事件广播、配置变更 |
| **Headers** | 根据消息 headers 匹配（不常用） | 复杂路由 |

### 1.4 消息生命周期

1. **Producer** 发送消息到 **Exchange**，附带 routing key
2. **Exchange** 根据类型和 binding 规则路由到一个或多个 **Queue**
3. **Queue** 存储消息（持久化到磁盘）
4. **Consumer** 从 Queue 拉取（或 Broker 推送）消息
5. **Consumer** 处理后发送 ACK
6. **Broker** 收到 ACK 后从 Queue 删除消息

### 1.5 消息确认机制

RabbitMQ 提供**两层确认**，确保可靠投递：

**Producer → Broker（Publisher Confirms）**：
- `confirm.select` 开启确认模式
- Broker 收到消息后发送 `basic.ack`，失败发 `basic.nack`

**Broker → Consumer（Consumer ACK）**：
- `basic.ack`：处理成功，删除消息
- `basic.nack` / `basic.reject`：处理失败，重投或丢弃
- `basic.qos(prefetch_count=N)`：限制未确认消息数（流量控制）

### 1.6 死信队列（Dead Letter Exchange, DLX）

消息变成"死信"的 3 种情况：
1. 消费者 `basic.nack(requeue=false)`
2. 消息 TTL 过期
3. 队列长度超过 max-length

死信会被重新投递到 **DLX**（专门的 Exchange），由专门的 DLQ 消费者处理（人工排查）。

### 1.7 与 Kafka 的核心差异

| 维度 | RabbitMQ | Kafka |
|------|----------|-------|
| 设计目标 | 灵活路由、可靠投递 | 高吞吐、日志收集 |
| 存储 | 消费后删除（默认） | 持久化日志（保留 N 天） |
| 路由 | Exchange + 4 种规则 | 仅 key hash 分区 |
| 吞吐量 | 万级 QPS | 百万级 QPS |
| 顺序性 | 单 queue 内有序 | 单 partition 内有序 |

## 2. 代码示例

### 2.1 Producer 发送消息

```python
# 文件：example_rabbitmq_producer.py
import pika

# 1. 建立连接
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 2. 声明 Exchange 和 Queue（幂等）
channel.exchange_declare(exchange="order-events", exchange_type="topic", durable=True)
channel.queue_declare(queue="order-fulfillment", durable=True)

# 3. 绑定 Queue 到 Exchange
channel.queue_bind(exchange="order-events", queue="order-fulfillment", routing_key="order.created")

# 4. 开启 Publisher Confirms
channel.confirm_delivery()

# 5. 发送消息（开启 delivery_mode=2 持久化）
try:
    channel.basic_publish(
        exchange="order-events",
        routing_key="order.created",
        body='{"order_id": "12345", "amount": 99.9}',
        properties=pika.BasicProperties(
            delivery_mode=2,        # 持久化
            content_type="application/json",
        ),
    )
    print("消息已发送并确认")
except pika.exceptions.UnroutableError:
    print("消息无法路由！")

connection.close()
```

### 2.2 Consumer 消费消息

```python
# 文件：example_rabbitmq_consumer.py
import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 限制未确认消息数（避免消费者内存爆炸）
channel.basic_qos(prefetch_count=10)

def callback(ch, method, properties, body):
    """消息处理回调"""
    try:
        order = json.loads(body)
        print(f"处理订单: {order['order_id']}")
        # 业务处理...
        ch.basic_ack(delivery_tag=method.delivery_tag)    # 确认消费
    except Exception as e:
        print(f"处理失败: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # 不重回队列


channel.basic_consume(queue="order-fulfillment", on_message_callback=callback)
print("等待消息...")
channel.start_consuming()
```

### 2.3 常见错误：忘记 ACK 导致消息堆积

```python
# ❌ 反例：Consumer 接收后不 ACK
def bad_callback(ch, method, properties, body):
    print(f"收到: {body}")
    # 忘记 ch.basic_ack(...)

# 问题：
# 1. 消息一直留在 queue（Unacked 状态）
# 2. 当 channel 关闭时消息重新入队
# 3. 最终队列撑爆磁盘

# ✅ 正例：处理成功 ACK，失败 NACK
def good_callback(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # 进 DLX
```

## 3. dify 仓库源码解读

### 3.1 dify 不用 RabbitMQ，但 Celery 的 ACK 机制类似

**文件位置**：`/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
**核心代码**（行 24-50）：

```python
@shared_task(queue="workflow_storage", bind=True, max_retries=3, default_retry_delay=60)
def save_workflow_execution_task(
    self,
    execution_data: dict[str, Any],
    tenant_id: str,
    app_id: str,
    triggered_from: str,
    creator_user_id: str,
    creator_user_role: str,
) -> bool:
    """
    Asynchronously save or update a workflow execution to the database.
    """
    try:
        with session_factory.create_session() as session:
            # Deserialize execution data
```

**解读**：
- Celery 与 RabbitMQ 的 ACK 机制对应关系：
  - Celery 任务**正常返回** → 自动 ACK（消息从队列移除）
  - Celery 任务**抛异常** → 重试（或进 dead-letter）
- 第 1 行 `max_retries=3`：最多重试 3 次，对应 RabbitMQ 的 `requeue=true`
- 第 1 行 `bind=True`：拿到 `self` 后可以调用 `self.retry()`，**类似 RabbitMQ 的 `basic.nack(requeue=true)`**

### 3.2 ruoyi 的 RabbitMQ 集成（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// RabbitMQConfig.java
@Configuration
@ConditionalOnProperty(prefix = "yudao.mq", name = "type", havingValue = "rabbitmq")
public class RabbitMQConfig {
    @Bean
    public TopicExchange orderExchange() {
        return ExchangeBuilder.topicExchange("order-events").durable(true).build();
    }

    @Bean
    public Queue orderQueue() {
        return QueueBuilder.durable("order-queue")
            .deadLetterExchange("order-dlx")             // 死信 Exchange
            .deadLetterRoutingKey("order.failed")
            .ttl(60000)                                  // 60 秒 TTL
            .build();
    }

    @Bean
    public Binding orderBinding(Queue orderQueue, TopicExchange orderExchange) {
        return BindingBuilder.bind(orderQueue).to(orderExchange).with("order.#");
    }

    // 消费者（手动 ACK）
    @RabbitListener(queues = "order-queue")
    public void handleOrder(OrderMessage message, Channel channel, @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
        try {
            processOrder(message);
            channel.basicAck(tag, false);                  // 手动 ACK
        } catch (Exception e) {
            channel.basicNack(tag, false, false);          // 失败 NACK，进死信
        }
    }
}
```

**解读**：
- 第 10-13 行：用 `QueueBuilder` 声明死信 Exchange、TTL——**一个 queue 同时定义业务消费者和死信消费者**
- 第 17 行：Topic Exchange 的 routing pattern `order.#` 匹配 `order.created` / `order.paid` / `order.refund` 等所有 order.* 消息
- 第 22-29 行：手动 ACK 模式（`acknowledge-mode: manual`），处理成功 `basicAck`、失败 `basicNack`

## 4. 关键要点总结

- **Exchange 是 RabbitMQ 的路由核心**：4 种类型决定消息如何分发到 Queue
- **消息确认有两层**：Publisher Confirms（生产端）+ Consumer ACK（消费端）
- **死信队列**用于处理失败消息，避免无限重试
- **prefetch_count** 限制未确认消息数，防止消费者内存爆炸
- RabbitMQ 适合**企业应用集成**（复杂路由、可靠投递），不适合超大规模日志

## 5. 练习题

### 练习 1：基础（必做）

用 `pika` 实现：
1. 声明一个 `direct` exchange `test-exchange` 和 queue `test-queue`
2. Producer 发送 3 条 routing key 分别为 `a`/`b`/`c` 的消息
3. Consumer 接收并打印

### 练习 2：进阶

用 `pika` 实现一个**死信队列**：
1. 主队列 TTL = 5 秒
2. 5 秒未消费的消息自动进入死信队列
3. 死信消费者打印 "死信：{message}"

### 练习 3：挑战（选做）

对比 RabbitMQ 的 **manual ACK** 和 Kafka 的 **enable.auto.commit**：
- 两者在"消息可靠性"和"消费速度"上各有什么取舍？
- 如何在保证可靠性的同时最大化消费吞吐？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- RabbitMQ 官方教程：https://www.rabbitmq.com/tutorials/
- pika 文档：https://pika.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-14