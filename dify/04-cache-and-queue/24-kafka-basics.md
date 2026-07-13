# 4.4.2 Kafka 入门

> Kafka 是分布式事件流平台，主打高吞吐、持久化、可重放，是大数据和事件驱动架构的事实标准。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Kafka 的核心概念（Broker / Topic / Partition / Offset）
- 用 kafka-python 发送和消费消息
- 区分 Kafka 与 RabbitMQ 的使用场景
- 理解为什么 dify 当前未使用 Kafka

## 📚 前置知识

- 消息队列基础
- 分布式系统
- 23-mq-concepts.md

## 1. 核心概念

### 1.1 什么是 Kafka？

Apache Kafka 是**分布式事件流平台**：
- **高吞吐**：每秒百万级消息
- **持久化**：消息存磁盘，可重放
- **可扩展**：水平扩展（增加 broker）
- **流处理**：内置 Kafka Streams

**主要用途**：
- 日志收集（替代 Flume）
- 事件溯源（Event Sourcing）
- 流式数据处理（实时分析）
- 消息队列（替代 RabbitMQ）

### 1.2 Kafka 核心概念

```
┌─────────┐
│Producer │
└────┬────┘
     ↓
┌──────────────────────────┐
│ Topic: orders            │
│  ┌──────┬──────┬──────┐  │
│  │P0    │P1    │P2    │  │
│  │[m][m] │[m][m]│[m][m]│  │
│  │[m][m] │[m]   │[m]   │  │
│  └──────┴──────┴──────┘  │
└──────────┬───────────────┘
           ↓
   ┌──────────────┐
   │Consumer Group│
   │  C1   C2   C3│
   └──────────────┘
```

| 概念 | 含义 |
|------|------|
| **Broker** | Kafka 服务器节点 |
| **Topic** | 消息主题（分类）|
| **Partition** | Topic 的分区（并行单位）|
| **Offset** | 分区内的消息位置 |
| **Consumer Group** | 一组消费者，共同消费 Topic |
| **Replication** | 分区副本（高可用）|
| **ZooKeeper / KRaft** | 集群协调（旧 / 新）|

### 1.3 Topic 与 Partition

- **Topic** 是逻辑概念（消息分类）
- **Partition** 是物理概念（一个有序的日志文件）
- 一个 Topic 分成多个 Partition，**分布在不同 Broker**
- 分区内消息**严格有序**，跨分区**不保证顺序**

### 1.4 Consumer Group

- 一组消费者**共同消费**一个 Topic
- 每个 Partition **只分给** group 内的一个消费者
- 例：Topic 有 3 个分区，group 有 3 个消费者 → 1 个对应 1 个
- **扩展消费能力**：增加消费者数量（不超过分区数）

### 1.5 Offset 与消费语义

- 每条消息有**唯一 Offset**（分区级别）
- Consumer 提交 Offset 表示"已消费到这里"
- **At-least-once**：处理完再 commit（默认）
- **At-most-once**：先 commit 再处理（可能丢）
- **Exactly-once**：事务 + 幂等（复杂）

### 1.6 Kafka vs RabbitMQ

| 特性 | Kafka | RabbitMQ |
|------|-------|----------|
| 模型 | 分布式日志 | 消息代理 |
| 吞吐 | 极高（百万/s）| 中（万/s）|
| 延迟 | 中（10-100ms）| 低（1-10ms）|
| 持久化 | 磁盘（默认）| 内存（可持久）|
| 消息重放 | ✅（重置 offset）| ❌ |
| 适用 | 事件流、日志、监控 | 任务队列、RPC |

## 2. 代码示例

### 2.1 安装与启动

```bash
# 安装 Kafka（KRaft 模式，无需 ZooKeeper）
docker run -d --name kafka -p 9092:9092 \
  -e KAFKA_NODE_ID=1 \
  -e KAFKA_PROCESS_ROLES=broker,controller \
  -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
  apache/kafka:latest
```

### 2.2 Producer 示例

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8") if k else None,
)

# 同步发送
future = producer.send("orders", key="order-1", value={"amount": 99.9, "user": "alice"})
metadata = future.get(timeout=10)
print(f"Partition: {metadata.partition}, Offset: {metadata.offset}")

# 异步发送
producer.send("orders", value={"amount": 50, "user": "bob"})
producer.flush()
```

### 2.3 Consumer 示例

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "orders",
    bootstrap_servers=["localhost:9092"],
    group_id="order-processor",
    auto_offset_reset="earliest",  # 从最早开始
    enable_auto_commit=False,       # 手动 commit
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

for message in consumer:
    print(f"Partition: {message.partition}, Offset: {message.offset}, Value: {message.value}")
    try:
        process_order(message.value)
        consumer.commit()  # 处理成功后提交
    except Exception as e:
        logger.error(f"Failed to process: {e}")
        # 不 commit，下次会重试
```

### 2.4 Consumer Group 扩展

```python
# 启动 3 个消费者（partition 也配 3 个）
# group_id 相同，自动负载均衡
for i in range(3):
    consumer = KafkaConsumer(
        "orders",
        group_id="order-processor",
        # ...
    )
    # Kafka 自动分配 partition 给 3 个消费者
```

### 2.5 手动管理 Offset

```python
from kafka import TopicPartition

# 指定从某个 offset 开始
consumer = KafkaConsumer(
    bootstrap_servers=["localhost:9092"],
    group_id="my-group",
    enable_auto_commit=False,
)

# 手动分配 partition
tp = TopicPartition("orders", 0)
consumer.assign([tp])

# 从 offset 100 开始
consumer.seek(tp, 100)

for msg in consumer:
    process(msg)
    consumer.commit({tp: OffsetAndMetadata(msg.offset + 1, None)})
```

### 2.6 常见错误：消费者数超过分区数

```python
# Topic 有 3 个 partition
# 启动 5 个消费者（同 group）
# 结果：3 个消费者空闲，2 个消费者没分配到 partition
# **解决**：增加 partition 数量
```

## 3. dify 仓库源码解读

### 3.1 dify 当前未使用 Kafka

**观察**：dify 后端代码中没有 Kafka 相关导入。

```bash
# 在 dify 仓库搜索
$ grep -r "kafka" /Users/xu/code/github/dify/api/ | grep -v "binary" | grep -v ".git"
# 无业务代码匹配
```

**原因分析**：
- dify 是 **LLM 应用平台**，核心业务是工作流执行
- 任务执行用 **Celery + Redis** 足够
- 没有"事件流"需求（不需要重放历史消息）
- Kafka 的优势（高吞吐、持久化、消息重放）在 dify 场景用不上

### 3.2 dify 的替代方案：Redis Streams

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
- Redis Streams 提供 Kafka-like 的能力（持久化、消费组、Offset）
- 单机 Redis 也能支持**几千 QPS**（够用）
- 部署更简单（不需要 Kafka 集群）
- **缺点**：扩展性不如 Kafka（单机瓶颈）

### 3.3 Pub/Sub 频道使用

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
- dify 默认用 Redis Pub/Sub（最轻量）
- 适合"实时通知"（不要求持久化）
- **对比 Kafka**：Kafka 更适合"事件流处理"（需要持久化、重放、分区）

### 3.4 三种 BroadcastChannel 对比

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/`

| Channel | 实现 | 持久化 | 可靠性 |
|---------|------|--------|--------|
| `RedisBroadcastChannel` | Pub/Sub | ❌ | 低 |
| `ShardedRedisBroadcastChannel` | Sharded Pub/Sub | ❌ | 中（Cluster 友好）|
| `StreamsBroadcastChannel` | Streams | ✅ | 高 |

**解读**：
- 通过 `PUBSUB_REDIS_CHANNEL_TYPE` 配置切换
- 默认 `pubsub`（最快）
- 需要持久化 → `streams`

## 4. 关键要点总结

- Kafka = 分布式事件流平台，主打高吞吐
- **Topic / Partition / Offset** 是核心概念
- **Consumer Group** 实现负载均衡
- 可靠性：At-least-once + 幂等消费
- Kafka vs RabbitMQ：高吞吐 vs 低延迟
- **dify 当前未用 Kafka**，用 Redis Streams / Pub/Sub 替代
- **何时引入 Kafka**：日均消息 > 1000 万、需持久化重放、复杂流处理

## 5. 练习题

### 练习 1：基础（必做）

本地启动 Kafka（用 Docker），用 kafka-python 实现 Producer + Consumer：发送 100 条消息，全部接收。

### 练习 2：进阶

用 Consumer Group 实现并行消费：创建 3 个 partition，启动 3 个消费者，验证消息分散处理。

### 练习 3：挑战（选做）

对比测试：在单机 Redis 上用 Streams 实现类似 Kafka 的功能（持久化、消费组、Offset），测量吞吐量差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
- Kafka 官方文档：https://kafka.apache.org/documentation/
- kafka-python 文档：https://kafka-python.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13