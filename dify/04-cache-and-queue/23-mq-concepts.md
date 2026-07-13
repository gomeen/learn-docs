# 4.4.1 消息队列核心概念：Producer / Consumer / Topic

> 消息队列（MQ）是分布式系统的"神经系统"——本节是后续 Kafka、RabbitMQ、Redis Pub/Sub 的概念基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解消息队列的核心概念（Producer / Consumer / Topic）
- 区分点对点（P2P）和发布订阅（Pub/Sub）模型
- 掌握消息可靠性的关键保证（持久化、确认、重试）
- 理解 dify 何时用 MQ、何时用 Celery

## 📚 前置知识

- 分布式系统基础
- 网络通信（TCP）

## 1. 核心概念

### 1.1 什么是消息队列？

**消息队列**是分布式系统中**异步通信**的中间件：

```
Producer ──→ [Queue] ──→ Consumer
              (Broker)
```

**核心价值**：
- **解耦**：Producer 和 Consumer 不需要知道对方
- **异步**：Producer 立即返回，不等待 Consumer
- **削峰**：突发流量由队列缓冲
- **广播**：一个消息多个 Consumer

### 1.2 两种通信模型

#### 点对点（P2P）模型

```
Producer ──→ Queue ──→ Consumer（只有一个能收到）
```

- 一条消息**只被一个** Consumer 处理
- 经典场景：订单处理、任务分发
- 例子：RabbitMQ Queue、Celery

#### 发布订阅（Pub/Sub）模型

```
Producer ──→ Topic ──┬──→ Consumer 1
                     ├──→ Consumer 2
                     └──→ Consumer 3
```

- 一条消息被**所有订阅者**收到
- 经典场景：通知、实时事件、缓存更新
- 例子：Kafka Topic、Redis Pub/Sub

### 1.3 消息生命周期

```
Producer 发送 → Broker 持久化 → Consumer 拉取/推送 → 消费确认 → 删除/归档
```

### 1.4 核心组件

| 组件 | 职责 |
|------|------|
| **Producer** | 消息生产者 |
| **Broker** | 消息存储与转发 |
| **Consumer** | 消息消费者 |
| **Topic / Queue** | 消息分类 |
| **Partition** | 主题分区（Kafka 概念）|
| **Offset** | 消费进度 |

### 1.5 消息可靠性等级

| 等级 | 描述 | 实现 |
|------|------|------|
| **At most once** | 最多一次（可能丢）| 不持久化、不确认 |
| **At least once** | 至少一次（可能重）| 持久化 + 确认 |
| **Exactly once** | 精确一次 | 事务 + 幂等 |

**常见选择**：At least once + **消费端幂等**（最实用）。

### 1.6 消息顺序性

- **全局有序**：单分区单消费者
- **分区内有序**：同一 key 路由到同分区
- **无序**：多分区并行消费

## 2. 代码示例

### 2.1 Producer 示例（伪代码）

```python
# 同步发送
producer.send("orders", {"order_id": 1, "amount": 99.9})
producer.flush()  # 等待发送完成

# 异步发送 + 回调
def on_success(metadata):
    print(f"Sent to partition {metadata.partition}, offset {metadata.offset}")

def on_error(exc):
    print(f"Send failed: {exc}")

producer.send("orders", payload, callback=on_success, error_callback=on_error)
```

### 2.2 Consumer 示例

```python
# 拉模式（Pull）
while True:
    msg = consumer.poll(timeout=1000)  # 1 秒
    if msg:
        process(msg)
        consumer.commit()  # 提交 offset

# 推模式（Push）
def handle_message(msg):
    try:
        process(msg)
        msg.ack()
    except Exception:
        msg.nack()  # 不 ack，消息会重投

consumer.subscribe("orders", handler=handle_message)
```

### 2.3 P2P vs Pub/Sub

```python
# P2P：每条消息只有一个消费者处理
queue.publish("task_1")  # 3 个 worker 中只有 1 个会收到

# Pub/Sub：每个订阅者都收到
topic.publish("event")  # 3 个订阅者都收到这条消息
```

### 2.4 常见错误：消费者慢导致消息积压

```python
# ❌ 错误：单线程消费 + 慢处理
def handle(msg):
    time.sleep(1)  # 每条 1 秒
    process(msg)

# ✅ 正确：增加并发消费者
consumer.start_consuming(num_workers=10)
```

## 3. dify 仓库源码解读

### 3.1 Celery 作为 P2P 队列

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`

```python
@shared_task(queue=AsyncWorkflowQueue.PROFESSIONAL_QUEUE)
def execute_workflow_professional(task_data_dict: dict[str, Any]):
    ...
```

**解读**：
- Celery 本质是 **P2P 队列**（每个任务一个 worker 处理）
- 用 `queue` 参数分配到不同队列
- 适用场景：工作流执行、数据清理（一个任务只能处理一次）

### 3.2 Redis Pub/Sub 作为广播

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`

```python
class Topic:
    def publish(self, payload: bytes) -> None:
        self._client.publish(self._redis_topic, payload)

    def subscribe(self) -> Subscription:
        return _RedisSubscription(
            client=self._client,
            pubsub=self._client.pubsub(),
            topic=self._redis_topic,
        )
```

**解读**：
- dify 用 Redis Pub/Sub 实现**广播**：
  - 工作流执行进度通知
  - 多实例间的事件同步
- **特点**：发布后**立即推送**，**不持久化**（订阅者不在线就丢失）
- **缺点**：不保证可靠性，适用"实时通知"而非"关键消息"

### 3.3 Redis Streams 作为可靠队列

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`

```python
class StreamsTopic:
    def publish(self, payload: bytes) -> None:
        self._client.xadd(self._key, {b"data": payload}, maxlen=self.max_length)
        if self._retention_seconds > 0:
            try:
                self._client.expire(self._key, self._retention_seconds)
            except Exception as e:
                logger.warning("Failed to set expire for stream key %s: %s", self._key, e, exc_info=True)
```

**解读**：
- dify 也支持 **Redis Streams**（更可靠的 Pub/Sub）：
  - 消息**持久化**到 Redis Stream
  - **保留时间**（`retention_seconds`）
  - **最大长度**（`max_length=5000`）
- **特点**：消费者可以"追赶历史消息"（XREAD）
- **适用**：要求可靠性的广播场景

### 3.4 Celery 路由 = 主题分类

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`

```python
class QueuePriority(StrEnum):
    """Queue priorities for different subscription tiers"""

    PROFESSIONAL = "workflow_professional"
    TEAM = "workflow_team"
    SANDBOX = "workflow_sandbox"
```

**解读**：
- `QueuePriority` 是**主题（Topic）的命名空间**
- 不同订阅级别 → 不同 topic → 不同 Worker 消费
- 主题设计：
  - `workflow_professional`（高优先级）
  - `workflow_team`（中优先级）
  - `workflow_sandbox`（低优先级，免费用户）

## 4. 关键要点总结

- 消息队列 = 异步通信中间件
- **P2P**：一条消息一个消费者（Celery、RabitMQ Queue）
- **Pub/Sub**：一条消息多个订阅者（Kafka、Redis Pub/Sub）
- 可靠性：At-least-once + 幂等消费
- dify 用 **Celery 做 P2P**（任务），**Redis Pub/Sub 做广播**（实时通知）

## 5. MQ 对比

| 特性 | Celery | Redis Pub/Sub | Kafka | RabbitMQ |
|------|--------|---------------|-------|----------|
| 模型 | P2P | Pub/Sub | Pub/Sub | P2P / Pub/Sub |
| 持久化 | ✅ Redis | ❌ | ✅ | ✅ |
| 吞吐量 | 中 | 高 | 极高 | 中 |
| 延迟 | 低 | 极低 | 中 | 低 |
| 适用 | Python 任务 | 实时通知 | 事件流 | 通用 MQ |

## 6. 练习题

### 练习 1：基础（必做）

用 redis-py 实现简单的 Pub/Sub：
- Publisher 发布 `"hello"`
- Subscriber 接收并打印

### 练习 2：进阶

用 Redis Streams 实现可靠的消息队列：
- Producer 用 XADD 发送
- Consumer 用 XREADGROUP 创建消费组
- 模拟 Consumer 崩溃后的消息重投

### 练习 3：挑战（选做）

阅读 `libs/broadcast_channel/` 完整源码，对比 `pubsub_channel.py` 和 `streams_channel.py` 的差异，理解 dify 何时用哪种。

## 7. 参考资料

- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- 消息队列对比：https://www.cloudamqp.com/blog/when-to-use-rabbitmq-or-apache-kafka.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13