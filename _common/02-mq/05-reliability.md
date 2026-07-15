# 2.5 消息可靠性：至少一次 / 最多一次 / 恰好一次

> 深入理解消息投递的三种可靠性语义及其工程实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 at-most-once / at-least-once / exactly-once 三种语义
- 理解各种 MQ 如何实现这三种语义
- 用幂等设计解决 at-least-once 的副作用
- 在 dify 中识别可靠性保障机制

## 📚 前置知识

- 消息队列基本概念（[01-concepts](./01-concepts.md)）
- 数据库事务与隔离级别
- 分布式系统一致性基础
- 失败与重试：[死信队列](./06-dead-letter.md)

## 1. 核心概念

### 1.1 三种语义的精确定义

| 语义 | 定义 | 可能发生的情况 |
|------|------|---------------|
| **at-most-once** | 消息最多被消费一次 | 消息**可能丢失**，但不会重复 |
| **at-least-once** | 消息至少被消费一次 | 消息**不会丢失**，但可能重复 |
| **exactly-once** | 消息恰好被消费一次 | 既不丢失也不重复（最难实现） |

### 1.2 为什么没有"免费的 exactly-once"？

分布式系统的本质限制（CAP 定理 + 网络分区）：
- **网络不可靠**：消息可能丢失
- **消费者崩溃**：处理结果可能没回传
- **重复消费**：为了不丢消息必须重试，重试必然产生重复

### 1.3 at-most-once 的实现

**最简单的语义**——消息发出就不管，最快：

```
Producer ──→ Broker ──→ Consumer
            (不持久化)    (收到即处理，不 ACK)
```

**典型场景**：
- 日志收集（丢一条无所谓）
- 实时统计（轻微误差可接受）

### 1.4 at-least-once 的实现

**最常用的语义**——保证不丢，可能重复：

```
Producer ──→ Broker ──→ Consumer
   (持久化)     (持久化)    (ACK 失败重试)
```

**三道防线**：
1. **Producer 端**：开启 Publisher Confirms / Transaction
2. **Broker 端**：消息持久化 + 多副本
3. **Consumer 端**：处理成功后才 ACK，失败重试

**dify 用 Celery**：通过 `acks_late=True` + `max_retries=3` 实现。

### 1.5 exactly-once 的实现方式

**最难的语义**——通常通过**幂等 + 事务**实现：

**方式 1：业务幂等**
- Consumer 用唯一 key（订单 ID）做去重
- 处理前先查"是否已处理"

**方式 2：消息幂等（Kafka 0.11+）**
- Producer 启用 `enable.idempotence=true`
- Broker 给每条消息分配唯一 PID + sequence number
- 重复消息自动去重

**方式 3：事务消息（RocketMQ）**
- 两阶段提交 + 回查机制
- 保证"本地事务 + 消息投递"原子性

### 1.6 幂等设计的关键

无论哪种语义，幂等设计都是核心：

```python
# 幂等检查 3 种常见方案
# 1. 唯一索引（数据库层）
INSERT INTO orders (id, ...) VALUES (?, ...)  -- id 冲突则跳过

# 2. 状态机（业务层）
if order.status == "paid":
    return  # 已处理过

# 3. 去重表（中间层）
if dedup_table.exists(message_id):
    return
dedup_table.add(message_id, ttl=86400)
```

## 2. 代码示例

### 2.1 at-most-once：RabbitMQ 自动 ACK

```python
# 文件：example_at_most_once.py
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# auto_ack=True 表示消费者收到消息立即 ACK（无论是否处理成功）
# → 消息可能丢失，但不会重复
channel.basic_consume(
    queue="logs",
    on_message_callback=lambda ch, method, properties, body: print(f"日志: {body}"),
    auto_ack=True,    # at-most-once
)

channel.start_consuming()
```

### 2.2 at-least-once：手动 ACK + 幂等

```python
# 文件：example_at_least_once.py
import pika
import redis

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()
r = redis.Redis()

def callback(ch, method, properties, body):
    msg_id = properties.message_id

    # Step 1: 幂等检查（用 Redis SETNX 去重）
    if not r.set(f"processed:{msg_id}", "1", nx=True, ex=86400):
        print(f"重复消息，跳过: {msg_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Step 2: 处理业务
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)    # 处理成功才 ACK
    except Exception as e:
        # 处理失败，删除幂等标记 + NACK 重试
        r.delete(f"processed:{msg_id}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


channel.basic_consume(queue="orders", on_message_callback=callback, auto_ack=False)
channel.start_consuming()
```

### 2.3 exactly-once：Kafka 幂等 Producer

```python
# 文件：example_exactly_once.py
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode(),
    acks="all",                           # 所有副本写入
    enable_idempotence=True,              # 幂等 Producer
    transactional_id="my-transactional-id", # 事务 ID（必填）
)

# 开启事务
producer.begin_transaction()

try:
    producer.send("orders", {"order_id": "123", "amount": 100})
    producer.send("audit-log", {"event": "order_created", "order_id": "123"})

    # 业务数据库操作
    db.execute("INSERT INTO orders VALUES ('123', 100)")

    # 全部成功，提交事务
    producer.commit_transaction()
except Exception:
    # 任何失败，回滚（消息不会发出）
    producer.abort_transaction()
```

### 2.4 常见错误：at-least-once 业务不幂等

```python
# ❌ 反例：消费者不幂等
@shared_task
def add_credits(user_id: str, amount: int):
    user = db.get_user(user_id)
    user.credits += amount
    user.save()

# MQ 重试 → 同一 user_id 被加 credits 两次

# ✅ 正例：用事务保证原子性
@shared_task
def add_credits(user_id: str, amount: int, message_id: str):
    with db.transaction():
        # 用 message_id 做幂等键（唯一索引）
        result = db.execute(
            "INSERT INTO credit_logs (message_id, user_id, amount) "
            "VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            message_id, user_id, amount,
        )
        if result.rowcount == 0:
            return  # 重复消息
        db.execute(
            "UPDATE users SET credits = credits + ? WHERE id = ?",
            amount, user_id,
        )
```

## 3. dify 仓库源码解读

### 3.1 dify 的 at-least-once + 幂等设计

**文件位置**：`/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
**核心代码**（行 17-40）：

```python
@shared_task(queue="dataset", bind=True, max_retries=3, default_retry_delay=60)
def add_annotation_to_index_task(
    annotation_id: str, question: str, tenant_id: str, app_id: str, collection_binding_id: str
):
    """
    Add annotation to index.
    """
    logger.info(click.style(f"Start build index for annotation: {annotation_id}", fg="green"))
    start_at = time.perf_counter()

    try:
        with session_factory.create_session() as session:
            dataset_collection_binding = DatasetCollectionBindingService.get_dataset_collection_binding_by_id_and_type(
                collection_binding_id, session, "annotation"
            )
```

**解读**：
- 第 1 行 `bind=True, max_retries=3`：失败重试 3 次（at-least-once）
- 第 13 行 `try/except` + 异常处理：捕获异常后**返回不抛**——Celery 看到函数正常返回就 ACK
- **幂等性保障**：
  - 第 18 行：`DatasetCollectionBindingService.get_dataset_collection_binding_by_id_and_type(...)` 用 `collection_binding_id` 查找
  - 第 52 行：`vector.create([document], duplicate_check=True)`——`duplicate_check=True` 参数让 Vector 数据库自动去重

**整体设计意图**：dify 用 Celery 的 `max_retries=3` + `default_retry_delay=60` 提供 at-least-once，并在业务层通过 `duplicate_check` 避免重复索引。

### 3.2 ruoyi 的可靠性保障（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// MqConsumerAspect.java - 统一消费切面（处理重试和幂等）
@Aspect
@Component
public class MqConsumerAspect {
    @Around("@annotation(rabbitListener)")
    public Object around(ProceedingJoinPoint pjp, RabbitListener rabbitListener) throws Throwable {
        String messageId = extractMessageId(pjp);    // 从消息头提取 messageId

        // Step 1: 幂等检查（Redis SETNX）
        if (!redisTemplate.opsForValue().setIfAbsent("mq:processed:" + messageId, "1", 24, TimeUnit.HOURS)) {
            log.warn("重复消息，跳过: {}", messageId);
            return null;
        }

        try {
            // Step 2: 执行消费逻辑
            return pjp.proceed();
        } catch (Exception e) {
            // Step 3: 删除幂等标记，允许重试
            redisTemplate.delete("mq:processed:" + messageId);
            throw e;   // 抛异常 → 触发 NACK 重试
        }
    }
}
```

**解读**：
- 第 9-12 行：用 Redis SETNX 做去重，TTL 24 小时（与 dify 思想一致）
- 第 13-22 行：AOP 切面统一处理所有 `@RabbitListener` 方法，业务代码无需关心幂等
- 第 20 行：失败时删除幂等标记，避免"标记占着但消息没了"的悬挂问题

## 4. 关键要点总结

- **at-most-once**：用于不重要的场景（日志），实现最简单
- **at-least-once**：绝大多数生产系统的选择，必须配合幂等
- **exactly-once**：要么用 Kafka 幂等 Producer，要么用业务幂等 + 事务
- **幂等是消费者的必修课**：用 messageId + Redis SETNX 是最简单方案
- dify 的 Celery 任务用 `max_retries + duplicate_check` 实现 at-least-once + 幂等

## 5. 练习题

### 练习 1：基础（必做）

写一个 Python 脚本：
1. 模拟 Producer 投递 100 条相同 messageId 的消息
2. 模拟 Consumer 用 Redis SETNX 做幂等
3. 验证只处理了 1 次

### 练习 2：进阶

阅读 `dify/api/tasks/annotation/add_annotation_to_index_task.py`，解释：
- `max_retries=3` 和 `duplicate_check=True` 分别保障什么？
- 如果 Vector 数据库不支持 `duplicate_check`，你如何在外层实现幂等？

### 练习 3：挑战（选做）

设计一个 Kafka **exactly-once** 场景：转账业务（A 减 100，B 加 100），用 Kafka 事务 + 数据库事务实现，画出消息和数据流的时序图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- Kafka 可靠性语义：https://kafka.apache.org/documentation/#semantics
- RocketMQ 事务消息：https://rocketmq.apache.org/docs/transaction-example/

---

**文档版本**：v1.0
**最后更新**：2026-07-14