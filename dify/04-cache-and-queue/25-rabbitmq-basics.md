# 4.4.3 RabbitMQ 入门

> RabbitMQ 是老牌消息队列，主打低延迟、灵活路由、AMQP 标准，是企业级消息中间件的标杆。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RabbitMQ 的核心概念（Exchange / Queue / Binding / Routing Key）
- 用 pika 发送和消费消息
- 区分 RabbitMQ 的 4 种 Exchange 类型
- 理解 RabbitMQ vs Kafka 的选型

## 📚 前置知识

- 消息队列基础
- AMQP 协议基础（可选）
- 23-mq-concepts.md

## 1. 核心概念

### 1.1 什么是 RabbitMQ？

RabbitMQ 是用 **Erlang** 实现的 **AMQP（Advanced Message Queuing Protocol）** 消息代理：

- **低延迟**：1-10 ms
- **灵活路由**：4 种 Exchange 类型
- **企业特性**：死信队列、镜像队列、联邦
- **成熟稳定**：2007 年发布，金融行业广泛使用

### 1.2 核心架构

```
                   ┌─── Queue A ─── Consumer A
Producer → Exchange┤
                   ├─── Queue B ─── Consumer B
                   └─── Queue C ─── Consumer C
```

| 组件 | 含义 |
|------|------|
| **Producer** | 消息生产者 |
| **Exchange** | 交换机（路由消息）|
| **Queue** | 队列（存储消息）|
| **Binding** | 绑定（路由规则）|
| **Routing Key** | 路由键（消息属性）|
| **Consumer** | 消费者 |

### 1.3 四种 Exchange 类型

#### Direct（直连）

```
Producer → "info" → Direct Exchange ── routing_key="info" ──→ Queue A
                                                        ──→ Queue B (binding="error")
```

按 routing_key 精确匹配。

#### Fanout（扇出）

```
Producer → Fanout Exchange ──┬──→ Queue A
                           ├──→ Queue B
                           └──→ Queue C
```

**广播**到所有绑定队列（忽略 routing_key）。

#### Topic（主题）

```
Producer → "order.paid.fast" → Topic Exchange
                                    ├── *.paid.*  ──→ Queue A
                                    ├── order.*    ──→ Queue B
                                    └── *.fast     ──→ Queue C
```

**通配符匹配**：
- `*` 匹配一个单词
- `#` 匹配多个单词

#### Headers（头部）

按消息 header 路由（少用）。

### 1.4 消息可靠性

RabbitMQ 通过**确认机制**保证可靠性：

| 机制 | 含义 |
|------|------|
| **Publisher Confirm** | Publisher 收到 broker 确认 |
| **Consumer Ack** | Consumer 处理完后 ack |
| **持久化** | Queue + Message 持久化到磁盘 |
| **镜像队列** | Queue 复制到多节点 |

### 1.5 死信队列（DLQ）

消息被拒绝、过期、队列满 → 进入 **死信交换机（DLX）** → 死信队列。

```
Normal Queue ──(失败/过期)──→ DLX ──→ Dead Letter Queue
```

用于**失败重试**和**异常排查**。

## 2. 代码示例

### 2.1 安装与启动

```bash
# Docker 启动
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# 管理界面：http://localhost:15672 (guest/guest)
```

### 2.2 Producer 示例

```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 声明 Exchange（不存在则创建）
channel.exchange_declare(exchange="logs", exchange_type="topic")

# 发送消息
channel.basic_publish(
    exchange="logs",
    routing_key="order.paid.fast",
    body=b'{"order_id": 1, "amount": 99.9}',
    properties=pika.BasicProperties(
        delivery_mode=2,  # 持久化
        content_type="application/json",
    ),
)

connection.close()
```

### 2.3 Consumer 示例

```python
import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 声明队列
channel.queue_declare(queue="order_processor", durable=True)
channel.queue_bind(queue="order_processor", exchange="logs", routing_key="order.*")

def callback(ch, method, properties, body):
    msg = json.loads(body)
    print(f"Received: {msg}, routing_key={method.routing_key}")
    try:
        process_order(msg)
        ch.basic_ack(delivery_tag=method.delivery_tag)  # 确认
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # 重投

channel.basic_consume(queue="order_processor", on_message_callback=callback)

print("Waiting for messages...")
channel.start_consuming()
```

### 2.4 Fanout（广播）

```python
# Producer
channel.exchange_declare(exchange="broadcast", exchange_type="fanout")
channel.basic_publish(exchange="broadcast", routing_key="", body=b"hello all")

# Consumer
channel.queue_declare(queue="subscriber_a", exclusive=True)
channel.queue_bind(queue="subscriber_a", exchange="broadcast")
# 启动 consumer 接收
```

### 2.5 死信队列

```python
# 声明 DLX
channel.exchange_declare(exchange="dlx", exchange_type="direct")

# 声明 DLQ
channel.queue_declare(queue="dead_letter", durable=True)
channel.queue_bind(queue="dead_letter", exchange="dlx", routing_key="failed")

# 主队列，配置 DLX
channel.queue_declare(
    queue="orders",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "dlx",
        "x-dead-letter-routing-key": "failed",
    },
)
```

### 2.6 常见错误：消息丢失

```python
# ❌ 错误：Consumer 处理失败但 ack 了
def callback(ch, method, properties, body):
    process(body)  # 可能失败
    ch.basic_ack(delivery_tag=method.delivery_tag)  # 失败也 ack → 消息丢失

# ✅ 正确：失败时 nack + requeue
def callback(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # 进 DLQ
```

## 3. dify 仓库源码解读

### 3.1 dify 当前未使用 RabbitMQ

```bash
# 搜索 RabbitMQ 相关
$ grep -r "rabbitmq\|pika\|amqp" /Users/xu/code/github/dify/api/
# 仅配置文件中有 CELERY_BROKER_URL 的相关字段，无业务代码
```

**原因分析**：
- dify 用 **Celery + Redis** 做任务队列
- Redis 已经够用（dify 单机部署为主）
- RabbitMQ 的优势（灵活路由、死信）在 dify 场景未充分利用
- **何时引入 RabbitMQ**：
  - 需要复杂路由（多类型任务）
  - 需要持久化的可靠消息（Celery Redis Broker 也支持）
  - 团队已熟悉 RabbitMQ

### 3.2 Celery Broker 配置（支持 RabbitMQ）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`

```python
celery_app = Celery(
    app.name,
    task_cls=FlaskTask,
    broker=dify_config.CELERY_BROKER_URL,
    backend=dify_config.CELERY_RESULT_BACKEND,
)
```

**解读**：
- Celery 的 `broker` URL 可以是 `redis://...` 或 `amqp://...`
- **切换到 RabbitMQ**：
  ```bash
  # 设置环境变量
  CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
  ```
- 业务代码无需修改（Celery 抽象了 broker 差异）

### 3.3 dify 的"死信队列"等价物

dify 用 **trigger_log + 重试 API** 模拟死信队列：

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`

```python
@classmethod
def get_failed_logs_for_retry(
    cls, tenant_id: str, max_retry_count: int = 3, limit: int = 100
) -> list[WorkflowTriggerLogDict]:
    """
    Get failed logs eligible for retry
    """
```

**解读**：
- 失败的 `WorkflowTriggerLog` 存 PostgreSQL
- 定时任务扫描"可重试"log → 调用 `reinvoke_trigger()`
- 超过 `max_retry_count` 不再重试（**等效于 DLQ 的人工处理**）

## 4. 关键要点总结

- RabbitMQ = AMQP 标准消息代理，主打灵活路由 + 低延迟
- **4 种 Exchange**：Direct / Fanout / Topic / Headers
- **可靠性**：Publisher Confirm + Consumer Ack + 持久化
- **死信队列**：失败消息路由到 DLX
- dify 当前用 Celery + Redis，未用 RabbitMQ
- 何时用 RabbitMQ：复杂路由、低延迟、金融级可靠性

## 5. MQ 对比（再次对比）

| 特性 | Celery+Redis | RabbitMQ | Kafka |
|------|-------------|----------|-------|
| 协议 | Redis | AMQP | 自定义 |
| 路由 | ❌ | ✅ 4 种 | ✅ |
| 持久化 | ✅ | ✅ | ✅ |
| 吞吐量 | 中 | 中 | 极高 |
| 延迟 | 低 | 极低 | 中 |
| 重放 | ❌ | ❌ | ✅ |
| Python 集成 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 运维复杂度 | 低 | 中 | 高 |

## 6. 练习题

### 练习 1：基础（必做）

用 pika 实现：
- 声明 Topic Exchange
- 创建两个队列绑定不同 routing_key（`order.*` 和 `*.paid`）
- 发送 3 条消息验证路由

### 练习 2：进阶

实现带死信队列的消息处理：
- 主队列处理失败 → 进 DLQ
- DLQ 单独 consumer 记录 + 报警

### 练习 3：挑战（选做）

修改 dify 的 Celery 配置，把 broker 从 Redis 切换到 RabbitMQ，验证任务正常调度。

## 7. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`
- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- RabbitMQ 官方文档：https://www.rabbitmq.com/documentation.html
- pika 文档：https://pika.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13