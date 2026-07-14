# 2.6 死信队列与重试机制

> 理解死信队列（DLX）的触发条件、设计模式和重试策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释死信队列的三大触发场景
- 区分延迟重试与立即重试的差异
- 设计指数退避重试策略
- 在 dify 中识别 Celery 的重试和异常处理

## 📚 前置知识

- 消息队列基本概念（`02-mq/01-concepts.md`）
- 消息可靠性语义（`02-mq/05-reliability.md`）
- HTTP 重试与熔断基础

## 1. 核心概念

### 1.1 为什么需要死信队列？

不是所有消息都能被成功处理。如果消费者一直处理失败：
- **无限重试**：消耗资源，消息堆积
- **直接丢弃**：丢失重要消息
- **人工干预**：需要"暂停失败消息 + 排查 + 重投"

**死信队列**就是为这个场景设计的——失败消息不丢失，但也不阻塞正常消费。

### 1.2 死信的三大触发场景

**RabbitMQ 的死信条件**（任意满足）：
1. 消费者 `basic.nack(requeue=false)` 拒绝消息
2. 消息 TTL 过期
3. 队列长度超过 max-length

**RocketMQ 的死信**：
- 消费重试达到最大次数（默认 16 次）
- 重试时间逐渐变长：10s → 30s → 1m → 2m → ... → 2h

**Kafka 没有原生 DLQ**，但可通过 `DeadLetterPublishingRecoverer`（Spring Kafka）实现。

### 1.3 死信队列的标准架构

```
                            主队列                       死信队列
Producer ──→ Exchange ──→  orders-queue ──→ Consumer     (处理失败)
                            (TTL=5min)         │
                                              ↓ NACK(requeue=false)
                                              ↓
                                          DLX (Dead Letter Exchange)
                                              │
                                              ↓
                                          DLQ (Dead Letter Queue)
                                              │
                                              ↓
                                          DLQ Consumer (人工/告警)
```

### 1.4 重试策略对比

| 策略 | 实现 | 适用场景 |
|------|------|---------|
| **立即重试** | `consumer.nack(requeue=true)` | 瞬时故障（网络抖动） |
| **延迟重试** | TTL + DLX 循环 | 业务暂时不可用（下游系统升级） |
| **指数退避** | 重试间隔指数增长（1s, 2s, 4s, 8s...） | 未知持续时间的故障 |
| **放弃重试** | 进入死信队列 | 永久失败（业务规则错误） |

### 1.5 指数退避实现

```python
def calculate_retry_delay(attempt: int, base: float = 1.0, cap: float = 300.0) -> float:
    """指数退避 + 抖动"""
    delay = min(base * (2 ** attempt), cap)
    jitter = random.uniform(0, delay * 0.1)   # 10% 抖动
    return delay + jitter

# 第一次重试：~1s
# 第二次重试：~2s
# 第三次重试：~4s
# 第八次重试：~256s（达到 cap=300）
```

**加抖动的原因**：避免"雷鸣群"——多个消费者同时重试同时撞到下游。

### 1.6 dify 的 Celery 重试

dify 用 Celery 的 `bind=True + max_retries + default_retry_delay`：

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task(self, ...):
    try:
        do_work()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)  # 60 秒后重试
```

**Celery 没有"指数退避"内置**，需要手动实现或使用 celery-retry 插件。

## 2. 代码示例

### 2.1 RabbitMQ 死信队列配置

```python
# 文件：example_dlq_rabbit.py
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 1. 声明死信 Exchange 和 Queue
channel.exchange_declare(exchange="dlx", exchange_type="direct", durable=True)
channel.queue_declare(queue="orders-dlq", durable=True)
channel.queue_bind(exchange="dlx", queue="orders-dlq", routing_key="order.failed")

# 2. 声明主队列（带死信参数）
channel.queue_declare(
    queue="orders",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "dlx",
        "x-dead-letter-routing-key": "order.failed",
        "x-message-ttl": 60000,        # 60 秒 TTL
        "x-max-length": 100000,        # 最大队列长度
    },
)

# 3. 消费者处理失败时 NACK 进 DLX
def callback(ch, method, properties, body):
    try:
        process_order(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        # 不重回主队列，路由到死信
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

channel.basic_consume(queue="orders", on_message_callback=callback)
channel.start_consuming()
```

### 2.2 指数退避重试（Python 自实现）

```python
# 文件：example_exponential_backoff.py
import time
import random
import functools

def exponential_backoff(max_retries: int = 5, base: float = 1.0, cap: float = 60.0):
    """指数退避装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt >= max_retries:
                        raise  # 重试次数耗尽，抛出
                    delay = min(base * (2 ** attempt), cap)
                    delay += random.uniform(0, delay * 0.1)  # 抖动
                    print(f"[{func.__name__}] 第 {attempt+1} 次失败，{delay:.2f}s 后重试: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator


@exponential_backoff(max_retries=3, base=1.0, cap=30.0)
def call_external_api():
    """调用外部 API"""
    import requests
    r = requests.get("https://api.example.com/data")
    r.raise_for_status()
    return r.json()


# 测试：失败重试
try:
    result = call_external_api()
    print(f"成功: {result}")
except Exception as e:
    print(f"重试 3 次后仍失败: {e}")
    # 进入死信队列人工处理
```

### 2.3 Celery 指数退避（手动实现）

```python
# 文件：example_celery_backoff.py
from celery import shared_task

@shared_task(bind=True, max_retries=5)
def task_with_backoff(self, data):
    try:
        process(data)
    except Exception as exc:
        # 计算指数退避延迟
        delay = 2 ** self.request.retries   # 1, 2, 4, 8, 16 秒
        raise self.retry(exc=exc, countdown=delay)
```

### 2.4 常见错误：无限重试堆积消息

```python
# ❌ 反例：不设上限，无限重试
@shared_task(bind=True, max_retries=None)   # 无限重试
def bad_task(self, data):
    process(data)

# 问题：下游故障时，所有任务永远在重试队列
# → 内存耗尽、磁盘爆满

# ✅ 正例：限制最大重试次数
@shared_task(bind=True, max_retries=5)
def good_task(self, data):
    try:
        process(data)
    except Exception as exc:
        if self.request.retries >= 5:
            # 进入死信队列 / 告警 / 人工处理
            send_to_dlq(data)
            return
        delay = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=delay)
```

## 3. dify 仓库源码解读

### 3.1 dify 的重试机制

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
- 第 1 行 `max_retries=3, default_retry_delay=60`：固定间隔 60 秒，最多 3 次
- 第 24 行 `try/except`：失败时调用 `self.retry(exc=exc)` 触发重试
- **没有指数退避**：dify 选用简单策略，因为保存执行结果通常瞬时失败
- **重试耗尽后**：Celery 会把任务标记为 `FAILED`，可通过 Celery 的 `task_failure` 信号接入 DLQ

### 3.2 ruoyi 的死信队列（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// RabbitMQConfig.java - 死信队列声明
@Bean
public Queue orderQueue() {
    Map<String, Object> args = new HashMap<>();
    args.put("x-dead-letter-exchange", "order-dlx");
    args.put("x-dead-letter-routing-key", "order.failed");
    args.put("x-message-ttl", 30000);  // 30 秒 TTL

    return new Queue("order-queue", true, false, false, args);
}

@Bean
public Queue orderDeadLetterQueue() {
    return new Queue("order-dlq", true);
}

// RetryConsumer.java - 指数退避消费者
@RabbitListener(queues = "order-queue")
public void onMessage(Message message, Channel channel) throws Exception {
    try {
        processOrder(message);
        channel.basicAck(message.getMessageProperties().getDeliveryTag(), false);
    } catch (Exception e) {
        // 解析重试次数
        Integer retryCount = (Integer) message.getMessageProperties().getHeaders()
            .getOrDefault("x-retry-count", 0);

        if (retryCount >= 3) {
            // 重试耗尽，进入死信
            channel.basicNack(message.getMessageProperties().getDeliveryTag(), false, false);
            alertService.sendAlert("order-dlq", "消息处理失败: " + message);
            return;
        }

        // 指数退避：1s, 2s, 4s
        long delay = (long) Math.pow(2, retryCount) * 1000;
        retryProducer.publishWithDelay(message, retryCount + 1, delay);
        channel.basicAck(message.getMessageProperties().getDeliveryTag(), false);
    }
}
```

**解读**：
- 第 4-7 行：在 queue 声明时通过 `x-dead-letter-exchange` 参数指定 DLX
- 第 30-31 行：通过消息 header `x-retry-count` 跟踪重试次数（与 dify 的 `self.request.retries` 思路一致）
- 第 35 行：指数退避 `2^retryCount * 1000` 毫秒

## 4. 关键要点总结

- **死信队列处理"永久失败"**：避免无限重试阻塞队列
- **三大触发条件**：NACK、TTL 过期、队列满
- **指数退避 + 抖动**是工业级标准，避免雷鸣群
- **必须限制最大重试次数**，否则故障期间会耗尽资源
- dify 用 `max_retries + default_retry_delay` 实现固定间隔重试
- 完整方案：主队列 → 重试队列（指数退避） → 死信队列（人工处理）

## 5. 练习题

### 练习 1：基础（必做）

实现一个指数退避重试装饰器：
1. 最多重试 5 次
2. 延迟依次为 1s, 2s, 4s, 8s, 16s
3. 加 10% 抖动

### 练习 2：进阶

阅读 `dify/api/tasks/workflow_execution_tasks.py`：
- 如果任务重试 3 次后仍失败，Celery 怎么处理？
- 如何监听 `task_failure` 信号，把失败任务写入 dify 的死信队列？

### 练习 3：挑战（选做）

设计一个完整的重试架构：
1. 主队列消费失败 → 进入 retry-1（TTL=1s）→ 失败 → retry-2（TTL=4s）→ ... → 失败 → DLQ
2. 画出 RabbitMQ 的 queue 拓扑图
3. 解释为什么这种设计比"队列内重试"更优

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- RabbitMQ DLX 文档：https://www.rabbitmq.com/dlx.html
- Celery 重试：https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying

---

**文档版本**：v1.0
**最后更新**：2026-07-14