# 2.2 Kafka 原理与实战

> 理解 Kafka 的高吞吐架构、分区机制和消费者组协议。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Kafka 的 broker / topic / partition / replica 架构
- 理解分区对顺序性、并发消费的影响
- 配置生产者（acks、幂等）和消费者（offset 管理）
- 用 kafka-python 实现简单 Producer/Consumer

## 📚 前置知识

- 消息队列基本概念（`02-mq/01-concepts.md`）
- Linux 文件 I/O 与零拷贝（sendfile）
- 分布式存储基础

## 1. 核心概念

### 1.1 Kafka 是什么？

Kafka 是**分布式、持久化、高吞吐**的消息中间件，最初由 LinkedIn 开发。它的设计目标是处理**日志收集**和**流式数据**场景（百万级 QPS）。

### 1.2 四大核心概念

| 概念 | 含义 | 类比 |
|------|------|------|
| **Broker** | Kafka 服务节点（一个 Kafka 进程） | RabbitMQ Server |
| **Topic** | 消息的逻辑分类（订单事件、用户事件） | RabbitMQ Exchange |
| **Partition** | Topic 的物理分片（每个是有序日志） | RabbitMQ Queue |
| **Replica** | Partition 的副本（leader + followers） | Redis Replica |

### 1.3 Partition：Kafka 的核心抽象

每个 Topic 由**多个 Partition** 组成，每个 Partition 是**有序、不可变**的消息日志：

```
Topic: "user-events"
├── Partition 0: [msg-1, msg-2, msg-3, msg-4, ...]
├── Partition 1: [msg-5, msg-6, msg-7, ...]
└── Partition 2: [msg-8, msg-9, msg-10, ...]
```

**关键点**：
- **同一个 Partition 内有序**，跨 Partition 无序
- 消息通过 `key` 决定进入哪个 Partition（`hash(key) % numPartitions`）
- 相同 key 的消息一定进入同一个 Partition（**保证顺序性**）

### 1.4 为什么 Kafka 这么快？

1. **顺序写盘**：Partition 是顺序追加日志，磁盘顺序 I/O 接近内存速度
2. **零拷贝（Zero-Copy）**：用 `sendfile()` 系统调用，数据直接从磁盘到网卡，不经过用户态
3. **批量发送**：Producer 累积一批消息再发送，减少网络往返
4. **Page Cache**：利用 OS 页面缓存，不强制刷盘
5. **分区并行**：多个 Partition 可被多个 Consumer 并行消费

### 1.5 Consumer Group（消费者组）

Kafka 的"消息被多个消费者分摊"机制：

```
Topic (3 partitions)
      │
      ↓
Group "order-processors"
      ├── Consumer 1  ←  Partition 0
      ├── Consumer 2  ←  Partition 1
      └── Consumer 3  ←  Partition 2

* 每个 Partition 只被组内一个 Consumer 消费
* Consumer 数 > Partition 数 → 多余的 Consumer 闲置
```

**关键点**：
- **同一个 Group 内**：消息被分摊（点对点）
- **不同 Group 间**：每个 Group 都收到全量消息（发布订阅）

### 1.6 Offset 管理

每个 Partition 维护一个 **offset**（消费进度）：
- Consumer 提交 offset 到 `__consumer_offsets` topic
- 重启后从上次 offset 继续消费
- 可选择 earliest（从最早）/ latest（从最新）开始

### 1.7 副本机制（Replication）

每个 Partition 有 **1 个 Leader + N-1 个 Follower**：
- Producer 只写 Leader
- Follower 从 Leader 拉取同步
- Leader 宕机时从 Follower 选举新 Leader
- `acks=all` 保证所有副本都写入才返回（强一致性）

## 2. 代码示例

### 2.1 Producer 配置与发送

```python
# 文件：example_kafka_producer.py
from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8") if k else None,
    acks="all",                       # 所有副本都写入才返回
    retries=3,
    compression_type="gzip",          # 压缩节省带宽
    linger_ms=10,                     # 批量发送延迟
)

# 发送消息（key 决定 partition）
for i in range(100):
    future = producer.send(
        topic="user-events",
        key=f"user-{i % 10}",        # 相同 user_id 进同一 partition
        value={"user_id": i, "action": "click", "ts": time.time()},
    )
    # 可选：阻塞等结果
    record_metadata = future.get(timeout=10)
    print(f"发送: partition={record_metadata.partition}, offset={record_metadata.offset}")

producer.flush()
producer.close()
```

### 2.2 Consumer 配置与消费

```python
# 文件：example_kafka_consumer.py
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "user-events",
    bootstrap_servers=["localhost:9092"],
    group_id="analytics-group",       # 消费者组
    auto_offset_reset="earliest",     # 从最早开始
    enable_auto_commit=True,          # 自动提交 offset
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    key_deserializer=lambda k: k.decode("utf-8") if k else None,
)

print("开始消费...")
for message in consumer:
    print(
        f"partition={message.partition}, "
        f"offset={message.offset}, "
        f"key={message.key}, "
        f"value={message.value}"
    )
    # 处理业务逻辑...
```

### 2.3 常见错误：消费者数 > 分区数

```python
# ❌ 反例：3 个 Partition 启动 5 个 Consumer
# 结果：2 个 Consumer 永远空闲，分区只能分配给 3 个

# ✅ 正例：Consumer 数 <= Partition 数
# 推荐：Partition 数 = Consumer 数（每个 Consumer 处理一个 Partition）
```

## 3. dify 仓库源码解读

### 3.1 dify 不用 Kafka，但用 Celery（MQ 思想一致）

**文件位置**：`/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
**核心代码**（行 17-30）：

```python
@shared_task(queue="dataset", bind=True, max_retries=3, default_retry_delay=60)
def add_annotation_to_index_task(
    annotation_id: str, question: str, tenant_id: str, app_id: str, collection_binding_id: str
):
    """
    Add annotation to index.

    Usage: clean_dataset_task.delay(dataset_id, tenant_id, indexing_technique, index_struct)
    """
    logger.info(click.style(f"Start build index for annotation: {annotation_id}", fg="green"))
    start_at = time.perf_counter()

    try:
        with session_factory.create_session() as session:
```

**解读**：
- 第 1 行：`@shared_task(queue="dataset")` 把任务路由到 `dataset` 队列——**与 Kafka 的 Partition 思想一致**：不同业务用不同队列隔离
- 第 1 行 `bind=True, max_retries=3`：支持任务重试（at-least-once 语义）
- 第 13 行：`add_annotation_to_index_task.delay(...)` 是 Producer 调用，把任务投递到 Redis（Celery Broker）
- **与 Kafka 的关键差异**：Celery 没有原生的"消息分区"和"消费者组"概念，所有任务进同一个队列，由多个 Worker 抢占消费——**适合任务分发场景，不适合高吞吐日志收集**

### 3.2 ruoyi 的 Kafka 集成（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// KafkaProducerConfig.java
@Configuration
@ConditionalOnProperty(prefix = "yudao.mq", name = "type", havingValue = "kafka")
public class KafkaProducerConfig {
    @Bean
    public ProducerFactory<String, Object> producerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);  // 幂等 Producer
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, Object> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }
}

// KafkaConsumerConfig.java - 消费者组配置
@Bean
public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory() {
    ConcurrentKafkaListenerContainerFactory<String, Object> factory = new ConcurrentKafkaListenerContainerFactory<>();
    factory.setConsumerFactory(consumerFactory());
    factory.setConcurrency(3);    // 启动 3 个 Consumer 线程
    return factory;
}
```

**解读**：
- 第 12 行：`ENABLE_IDEMPOTENCE_CONFIG=true` 启用 Kafka 幂等 Producer，配合 `acks=all` 实现 exactly-once
- 第 24 行：`factory.setConcurrency(3)` 启动 3 个 Consumer 线程，相当于 3 个 Partition 并行消费
- 业务代码用 `@KafkaListener(topics = "user-events", groupId = "analytics")` 订阅

## 4. 关键要点总结

- **Partition 是 Kafka 的核心抽象**：保证顺序 + 支持并行消费
- **Consumer Group**：同组分摊，异组全量
- **acks=all + idempotence** 实现 exactly-once
- **顺序性边界**：只在同一 Partition 内有序，跨 Partition 无序
- Kafka 适合**高吞吐日志收集**和**流式处理**；Celery 适合**任务分发**

## 5. 练习题

### 练习 1：基础（必做）

用 `kafka-python` 写一个脚本：
1. 创建一个 3-partition 的 topic `test`
2. Producer 发送 100 条消息，key 从 0 到 9 循环
3. Consumer 用 group `g1` 消费，观察每条消息落在哪个 partition

### 练习 2：进阶

解释为什么 Kafka 的 Consumer 数不能超过 Partition 数？假设有 10 个 Partition、20 个 Consumer，会发生什么？

### 练习 3：挑战（选做）

对比 Kafka 的 **ISR（In-Sync Replicas）机制** 和 Redis Sentinel 的 **quorum 选举**：
- 两者如何判断"副本同步"？
- 为什么 ISR 需要 producer `acks=all` 才算真正持久化？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- Kafka 官方文档：https://kafka.apache.org/documentation/
- kafka-python：https://kafka-python.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-14