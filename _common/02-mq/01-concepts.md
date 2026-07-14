# 2.1 消息队列核心概念：Producer / Consumer / Topic / Queue

> 理解消息队列的基本模型、四大核心角色和消息生命周期。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Producer / Consumer / Broker / Queue / Topic 五大概念
- 理解点对点（Queue）和发布订阅（Topic）两种消息模型
- 掌握消息的 at-most-once / at-least-once / exactly-once 三种语义
- 能在 dify 中找到 Celery 任务的实际应用

## 📚 前置知识

- 进程间通信基础（Socket / 共享内存）
- 数据库事务的 ACID 概念
- 分布式系统基本思想

## 1. 核心概念

### 1.1 为什么需要消息队列？

假设用户注册后要做 3 件事：发送欢迎邮件、写注册日志、推荐系统初始化。如果**同步串行执行**：

```
用户注册 → 发邮件（200ms）→ 写日志（50ms）→ 推荐初始化（500ms）→ 返回
总耗时 750ms，用户体验差
```

引入 MQ 后：

```
用户注册 → 投递消息到 MQ（5ms）→ 返回
                       ↓
                  MQ Broker
              ┌────┼────┐
              ↓    ↓    ↓
           发邮件 写日志 推荐初始化  （消费者各自异步处理）
```

**核心收益**：
1. **解耦**：生产者只管发消息，不关心谁消费
2. **异步**：快速返回，后台慢慢处理
3. **削峰**：突发流量积压在 MQ，消费者按能力拉取
4. **可恢复**：消费者宕机后消息仍在，重启后继续消费

### 1.2 五大核心角色

| 角色 | 职责 | 例子 |
|------|------|------|
| **Producer（生产者）** | 创建并发送消息 | 注册服务发送 "user.created" 事件 |
| **Consumer（消费者）** | 从 Broker 拉取/接收消息并处理 | 邮件服务接收事件并发邮件 |
| **Broker（代理）** | 消息的中转站，负责存储和投递 | Kafka / RabbitMQ / RocketMQ |
| **Queue（队列）** | 消息的物理容器，点对点语义 | Kafka 的 partition、RabbitMQ 的 queue |
| **Topic（主题）** | 逻辑分类，发布订阅语义 | Kafka 的 topic、RabbitMQ 的 exchange |

### 1.3 两种消息模型

**点对点（Point-to-Point，Queue）**：
- 一条消息**只被一个消费者**消费
- 适合任务分发（如订单处理）

**发布订阅（Publish-Subscribe，Topic）**：
- 一条消息**被所有订阅者**消费
- 适合事件广播（如配置变更）

### 1.4 消息的可靠性语义

| 语义 | 含义 | 实现方式 | 代价 |
|------|------|---------|------|
| **at-most-once**（最多一次） | 消息可能丢失，但不重复 | 不 ACK、不重试 | 性能最高 |
| **at-least-once**（至少一次） | 消息不丢失，但可能重复 | 消费前持久化 + ACK + 重试 | 中等性能 |
| **exactly-once**（恰好一次） | 消息不丢、不重 | 事务 / 幂等 + 去重表 | 性能最低 |

**dify 的选择**：Celery 默认提供 **at-least-once**（任务持久化 + ACK），通过 `max_retries` 控制重试次数。

### 1.5 消息的组成

```
Message {
    Headers: {
        messageId, timestamp, correlationId
    }
    Properties: {
        contentType, deliveryMode, priority, expiration
    }
    Body: {
        payload (业务数据，通常 JSON)
    }
}
```

### 1.6 消息的生命周期

1. **生产**：Producer 创建消息并发送给 Broker
2. **存储**：Broker 持久化消息（可选）
3. **投递**：Broker 推送给 Consumer（或 Consumer 拉取）
4. **消费**：Consumer 处理消息
5. **ACK**：Consumer 确认消费成功
6. **删除**：Broker 从存储中移除消息（可选，Kafka 默认保留 N 天）

## 2. 代码示例

### 2.1 用 Python `queue` 模块模拟简单 MQ

```python
# 文件：example_mq_simple.py
import queue
import threading
import time
import json

# 1. 创建消息队列（模拟 Broker）
message_queue = queue.Queue(maxsize=100)

# 2. 定义消息格式
class Message:
    def __init__(self, topic: str, body: dict):
        self.id = f"msg-{time.time_ns()}"
        self.topic = topic
        self.body = body

    def __repr__(self):
        return f"Message(id={self.id}, topic={self.topic}, body={self.body})"


# 3. Producer：发送消息
def producer():
    for i in range(5):
        msg = Message("user.created", {"user_id": i, "name": f"user-{i}"})
        message_queue.put(msg)
        print(f"[Producer] 发送: {msg}")
        time.sleep(0.1)


# 4. Consumer：拉取并处理
def consumer(name: str):
    while True:
        try:
            msg = message_queue.get(timeout=2)
            print(f"[{name}] 处理: {msg}")
            time.sleep(0.2)  # 模拟处理耗时
            message_queue.task_done()
        except queue.Empty:
            print(f"[{name}] 队列空，退出")
            break


# 5. 启动
threading.Thread(target=producer).start()
threading.Thread(target=consumer, args=("Worker-1",)).start()
threading.Thread(target=consumer, args=("Worker-2",)).start()
```

### 2.2 Celery 的 Producer/Consumer（dify 风格）

```python
# 文件：example_celery.py
from celery import Celery, shared_task

app = Celery("dify_demo", broker="redis://localhost:6379/1", backend="redis://localhost:6379/2")


# === Consumer：Celery 任务 ===
@app.shared_task(queue="dataset", bind=True, max_retries=3, default_retry_delay=60)
def add_document_to_index(self, document_id: str, content: str):
    """消费消息：把文档加入索引"""
    try:
        # 业务逻辑
        print(f"索引文档 {document_id}: {content[:50]}")
        return {"status": "ok", "document_id": document_id}
    except Exception as exc:
        # 重试（at-least-once 语义）
        raise self.retry(exc=exc)


# === Producer：发送任务 ===
def publish_document(document_id: str, content: str):
    """投递消息到 MQ"""
    result = add_document_to_index.delay(document_id, content)
    return result.id


# 调用
task_id = publish_document("doc-001", "这是 dify 文档索引任务")
print(f"任务已投递: {task_id}")
```

### 2.3 常见错误：消息未做幂等

```python
# ❌ 反例：消费者不幂等，重试导致重复扣款
@shared_task
def process_payment(order_id: str):
    order = db.get_order(order_id)
    wallet.balance -= order.amount    # 扣款
    wallet.save()
    order.status = "paid"
    order.save()

# 问题：MQ 重试 → 同一个 order 被处理两次 → 扣两次款

# ✅ 正例：用订单状态做幂等检查
@shared_task
def process_payment(order_id: str):
    order = db.get_order(order_id)
    if order.status == "paid":        # 幂等键
        return  # 已处理过，跳过
    wallet.balance -= order.amount
    wallet.save()
    order.status = "paid"
    order.save()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Celery 任务定义

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

    Args:
        execution_data: Serialized WorkflowExecution data
        tenant_id: Tenant id for multi-tenancy
        ...
    Returns:
        True if successful, False otherwise
    """
    try:
        with session_factory.create_session() as session:
            # Deserialize execution data
```

**解读**：
- 第 1 行：`@shared_task` 装饰器把 Python 函数注册为 Celery 任务——**这就是 Consumer**
- 第 1 行的关键参数：
  - `queue="workflow_storage"`：指定队列名，可让不同 Worker 只消费特定队列（队列隔离）
  - `bind=True`：把 task 实例作为第一参数 `self`，便于调用 `self.retry()`
  - `max_retries=3`：最多重试 3 次
  - `default_retry_delay=60`：失败后等 60 秒再重试
- 第 27 行：用 `try/except` 显式捕获异常，避免任务崩溃影响整个 Worker 进程

**整体设计意图**：把"保存工作流执行结果"这种 I/O 操作从 API 请求链路剥离，放到异步任务队列，**保证 API 响应速度**。

### 3.2 ruoyi 的 MQ 抽象（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// MessageProducer.java - 统一 Producer 接口
public interface MessageProducer {
    void send(String topic, Object message);   // 异步发送
    <T> T sendAndReceive(String topic, Object message, Class<T> respType);  // 同步等响应
}

// RabbitMQProducer.java - RabbitMQ 实现
@Service
@ConditionalOnProperty(prefix = "yudao.mq", name = "type", havingValue = "rabbitmq")
public class RabbitMQProducer implements MessageProducer {
    @Resource
    private RabbitTemplate rabbitTemplate;

    @Override
    public void send(String topic, Object message) {
        rabbitTemplate.convertAndSend(topic, message);
    }
}

// RedisStreamProducer.java - Redis Stream 实现
@Service
@ConditionalOnProperty(prefix = "yudao.mq", name = "type", havingValue = "redis-stream")
public class RedisStreamProducer implements MessageProducer {
    @Override
    public void send(String topic, Object message) {
        redisTemplate.opsForStream().add(topic, Map.of("payload", objectMapper.writeValueAsString(message)));
    }
}
```

**解读**：
- 第 2-5 行：抽象 `MessageProducer` 接口，业务方只调 `send(topic, message)`，不关心底层是 RabbitMQ / Kafka / RocketMQ / Redis Stream
- 第 8-9 行：用 `@ConditionalOnProperty` 按配置动态注入对应实现，**类似 dify 的 `PUBSUB_REDIS_CHANNEL_TYPE`**
- 第 17-21 行：Redis Stream 实现就是简单的 `XADD`

## 4. 关键要点总结

- **五大角色**：Producer / Consumer / Broker / Queue / Topic
- **两种模型**：点对点（一条消息被一个消费者）、发布订阅（一条消息被所有订阅者）
- **三种可靠性语义**：at-most-once / at-least-once / exactly-once
- **幂等性是消费者的必修课**：MQ 至少一次投递必须配合消费端去重
- **dify 用 Celery 实现 Producer/Consumer 模式**，通过 `queue=` 参数隔离不同业务

## 5. 练习题

### 练习 1：基础（必做）

写一个 Python 脚本模拟消息队列：
1. 创建一个 `queue.Queue`
2. Producer 投递 5 个任务
3. 启动 2 个 Consumer 并发消费
4. 验证 2 个 Consumer 收到的任务不重叠

### 练习 2：进阶

阅读 `dify/api/tasks/mail_inner_task.py`，解释 `send_inner_email_task` 任务为什么不需要 `bind=True` 和 `max_retries`？如果邮件发送失败，dify 会怎么处理？

### 练习 3：挑战（选做）

对比 Celery 的 at-least-once 语义与 Kafka 的 exactly-once 语义：
- 实现层面有什么本质差异？
- 为什么 Kafka 能做到 exactly-once（事务 + 幂等 producer）？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
- `/Users/xu/code/github/dify/api/tasks/mail_inner_task.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- Celery 官方文档：https://docs.celeryq.dev/

---

**文档版本**：v1.0
**最后更新**：2026-07-14