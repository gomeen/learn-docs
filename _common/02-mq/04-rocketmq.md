# 2.4 RocketMQ 原理与实战

> 理解 RocketMQ 的 NameServer、CommitLog、ConsumeQueue 架构与顺序消息。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 RocketMQ 的 NameServer / Broker / Producer / Consumer 架构
- 理解 CommitLog + ConsumeQueue 的存储设计
- 区分全局顺序消息与分区顺序消息
- 用 rocketmq-client 实现 Java 客户端

## 📚 前置知识

- 消息队列基本概念（`02-mq/01-concepts.md`）
- Kafka 基础（`02-mq/02-kafka.md`，对比学习）
- Java 基础（ruoyi 用 Java 集成）

## 1. 核心概念

### 1.1 RocketMQ 是什么？

RocketMQ 是阿里巴巴开源的**分布式消息中间件**，2016 年捐赠给 Apache。它的设计目标是：
- **高吞吐**：百万级 QPS
- **严格顺序消息**：同一队列保证 FIFO
- **事务消息**：类似 XA 事务
- **亿级消息堆积**：不丢消息

### 1.2 四大角色

| 角色 | 职责 | 类比 |
|------|------|------|
| **NameServer** | 轻量级注册中心，提供 Broker 路由 | Zookeeper（但无状态） |
| **Broker** | 存储和投递消息 | Kafka Broker |
| **Producer** | 发送消息 | Kafka Producer |
| **Consumer** | 拉取消息 | Kafka Consumer |

### 1.3 核心架构

```
Producer ──→ NameServer ──→ Broker ──→ Consumer
              (集群1)        (集群1)     (集群1)
              (集群2)        (集群2)     (集群2)

* NameServer 无状态，多个实例互不通信
* Broker 向所有 NameServer 注册心跳
* Producer/Consumer 从任一 NameServer 获取路由
```

**NameServer 的设计巧妙**：
- **无状态**：不存储 Broker 列表（每个 NameServer 独立维护）
- **无通信**：NameServer 之间不互相同步
- **最终一致**：通过心跳维持，30 秒内可达一致

### 1.4 存储设计：CommitLog + ConsumeQueue

RocketMQ 用**混合存储**而非 Kafka 的"每个 Partition 一个文件"：

```
┌──────────────────────────────┐
│  CommitLog (1 个大文件)       │  ← 所有消息追加写入
│  [msg1][msg2][msg3]...        │
└──────────────────────────────┘
        │
        │ 索引
        ↓
┌──────────────────────────────┐
│  ConsumeQueue (每个队列一个)   │  ← 轻量索引：offset/msg_size/tag_hash
│  [0][1][2]...                 │
└──────────────────────────────┘
```

**关键点**：
- **CommitLog** 顺序写，性能极高
- **ConsumeQueue** 是定长 20 字节/条目，支持二分查找
- Consumer 读消息：先读 ConsumeQueue 定位，再读 CommitLog

### 1.5 消息模型：Topic + Queue

```
Topic: "OrderTopic"（4 个 Queue）
├── Queue 0: [msg1, msg5, msg9, ...]
├── Queue 1: [msg2, msg6, msg10, ...]
├── Queue 2: [msg3, msg7, msg11, ...]
└── Queue 3: [msg4, msg8, msg12, ...]

* 默认 4 个 Queue（可配置）
* 同一 Queue 内严格有序
* 跨 Queue 无序
```

### 1.6 三种消息类型

| 类型 | 含义 | 实现 |
|------|------|------|
| **普通消息** | 不保证顺序，不保证事务 | 默认 |
| **顺序消息** | 同一 Queue 内 FIFO | `MessageQueueSelector` |
| **事务消息** | 两阶段提交 + 回查机制 | `TransactionMQProducer` |

### 1.7 与 Kafka 的核心差异

| 维度 | RocketMQ | Kafka |
|------|----------|-------|
| 存储 | CommitLog（大文件追加） | Partition（每个独立文件） |
| 注册中心 | NameServer（无状态） | Zookeeper（强一致） |
| 顺序消息 | 单 Queue 严格 FIFO | 单 Partition 有序 |
| 事务消息 | 原生支持 | 0.11+ 支持（EOS） |
| 消息过滤 | Tag / SQL92 表达式 | 仅根据 offset |

## 2. 代码示例

### 2.1 Producer 发送普通消息

```java
// 文件：RocketMQProducerExample.java
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.common.message.Message;

public class RocketMQProducerExample {
    public static void main(String[] args) throws Exception {
        // 1. 创建 Producer，指定 Producer Group
        DefaultMQProducer producer = new DefaultMQProducer("order-producer-group");
        producer.setNamesrvAddr("localhost:9876");
        producer.start();

        // 2. 发送 3 条消息
        for (int i = 0; i < 3; i++) {
            Message msg = new Message(
                "OrderTopic",                          // topic
                "orderTag",                            // tag（用于过滤）
                ("order-" + i).getBytes()              // body
            );
            // 3. 发送并获取结果
            SendResult result = producer.send(msg);
            System.out.println("发送结果: " + result.getSendStatus()
                + ", queueId=" + result.getMessageQueue().getQueueId());
        }

        producer.shutdown();
    }
}
```

### 2.2 顺序消息：同一订单进同一 Queue

```java
// 文件：RocketMQOrderProducer.java
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.client.producer.MessageQueueSelector;
import org.apache.rocketmq.common.message.Message;
import org.apache.rocketmq.common.message.MessageQueue;
import java.util.List;

public class RocketMQOrderProducer {
    public static void main(String[] args) throws Exception {
        DefaultMQProducer producer = new DefaultMQProducer("order-group");
        producer.setNamesrvAddr("localhost:9876");
        producer.start();

        // 同一 orderId 的消息进同一 Queue，保证顺序
        for (int orderId = 1000; orderId < 1003; orderId++) {
            for (int step = 1; step <= 3; step++) {
                Message msg = new Message("OrderTopic", "step",
                    ("order-" + orderId + "-step-" + step).getBytes());

                producer.send(msg, new MessageQueueSelector() {
                    @Override
                    public MessageQueue select(List<MessageQueue> queues, Message msg, Object arg) {
                        Integer id = (Integer) arg;
                        // 相同 orderId 哈希到同一队列
                        int index = id % queues.size();
                        return queues.get(index);
                    }
                }, orderId);
            }
        }

        producer.shutdown();
    }
}
```

### 2.3 常见错误：未指定 Queue 导致顺序错乱

```java
// ❌ 反例：不指定 Queue，相同 orderId 的消息分散到不同 Queue
for (int step = 1; step <= 3; step++) {
    Message msg = new Message("OrderTopic", "step", ("step-" + step).getBytes());
    producer.send(msg);   // 默认轮询发送到不同 Queue
}

// 问题：消费者可能先收到 step-3 再收到 step-1（顺序错乱）

// ✅ 正例：用 MessageQueueSelector 强制同 orderId 进同 Queue
producer.send(msg, (queues, m, arg) -> {
    int orderId = (Integer) arg;
    return queues.get(orderId % queues.size());
}, orderId);
```

## 3. dify 仓库源码解读

### 3.1 dify 不用 RocketMQ，但 Celery 的任务路由类似

**文件位置**：`/Users/xu/code/github/dify/api/tasks/mail_inner_task.py`
**核心代码**（行 45-50）：

```python
@shared_task(queue="mail")
def send_inner_email_task(to: list[str], subject: str, body: str, substitutions: Mapping[str, str]):
    if not mail.is_inited():
        return

    logger.info(click.style(f"Start enterprise mail to {to} with subject {subject}", fg="green"))
```

**解读**：
- 第 1 行 `queue="mail"`：把邮件任务路由到 `mail` 队列——**与 RocketMQ 的 Topic 类似**
- **dify 的"队列"机制**：每个 Celery Worker 通过 `celery -A app worker -Q mail,dataset,workflow_storage` 启动时指定消费的队列列表，**类似 RocketMQ 的订阅关系**
- **与 RocketMQ 的关键差异**：Celery 的"队列"是逻辑概念，所有任务最终落到 Redis 的同一个 List；RocketMQ 的 Queue 是物理分区，支持并行消费

### 3.2 ruoyi 的 RocketMQ 集成（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// RocketMQProducerConfig.java
@Configuration
@ConditionalOnProperty(prefix = "yudao.mq", name = "type", havingValue = "rocketmq")
public class RocketMQProducerConfig {
    @Bean
    public DefaultMQProducer mqProducer() throws Exception {
        DefaultMQProducer producer = new DefaultMQProducer("yudao-producer-group");
        producer.setNamesrvAddr("localhost:9876");
        producer.setRetryTimesWhenSendFailed(3);
        producer.start();
        return producer;
    }
}

// RocketMQConsumerConfig.java - 消费者配置
@Bean
public DefaultMQPushConsumer mqConsumer() throws Exception {
    DefaultMQPushConsumer consumer = new DefaultMQPushConsumer("yudao-consumer-group");
    consumer.setNamesrvAddr("localhost:9876");
    consumer.subscribe("OrderTopic", "orderTag");      // 订阅 Topic + Tag 过滤
    consumer.registerMessageListener((MessageListenerConcurrently) (msgs, context) -> {
        for (MessageExt msg : msgs) {
            try {
                processOrder(new String(msg.getBody()));
            } catch (Exception e) {
                return ConsumeConcurrentlyStatus.RECONSUME_LATER;  // 重试
            }
        }
        return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;
    });
    consumer.start();
    return consumer;
}
```

**解读**：
- 第 17 行：`subscribe("OrderTopic", "orderTag")` 订阅 Topic 并按 Tag 过滤——**RocketMQ 的 Tag 过滤比 Kafka 灵活**
- 第 25 行：`RECONSUME_LATER` 表示重试，类似 RabbitMQ 的 `basic.nack(requeue=true)`
- 第 18-22 行：Push 模式消费（Broker 主动推送），区别于 Kafka 的 Pull 模式

## 4. 关键要点总结

- **NameServer 无状态**：相比 Zookeeper 更简单、可水平扩展
- **CommitLog + ConsumeQueue**：混合存储设计，兼顾写入和查询性能
- **顺序消息**：通过 `MessageQueueSelector` 把同一业务键的消息路由到同一 Queue
- **Tag 过滤**：比 Kafka 的 topic+partition 灵活，适合多类型消息
- RocketMQ 适合**电商、金融**等需要严格顺序和事务消息的场景

## 5. 练习题

### 练习 1：基础（必做）

启动 RocketMQ（推荐用 Docker Compose），写一个 Java Producer：
1. 创建 topic `test-topic`
2. 发送 100 条消息，tag 分别为 `tagA`、`tagB`、`tagC`
3. 观察消息分布

### 练习 2：进阶

解释 RocketMQ 为什么用 NameServer 而不是 Zookeeper？这种设计有什么优缺点？

### 练习 3：挑战（选做）

设计一个 RocketMQ **事务消息** 流程：用户下单成功后需要扣减库存，用事务消息保证"先创建订单，扣库存失败则回滚"。画出消息流转时序图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/mail_inner_task.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- RocketMQ 官方文档：https://rocketmq.apache.org/docs/
- RocketMQ 架构详解：https://cloud.tencent.com/developer/article/1540495

---

**文档版本**：v1.0
**最后更新**：2026-07-14