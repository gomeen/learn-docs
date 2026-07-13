# 4.4.5 事件驱动架构（EDA）

> 事件驱动架构（Event-Driven Architecture）通过事件的发布与订阅解耦服务，是现代分布式系统的主流设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解事件驱动架构的核心概念
- 区分事件通知、事件溯源、事件流三种模式
- 用 dify 的 BroadcastChannel 实现事件广播
- 评估 EDA 的优缺点与适用场景

## 📚 前置知识

- 消息队列基础
- Pub/Sub 与 Stream
- 23-mq-concepts.md、26-redis-pubsub-stream.md

## 1. 核心概念

### 1.1 什么是事件驱动架构？

**事件驱动架构** = 通过**事件**进行服务间通信的架构风格：

```
Event Producer ──publish event──→ Event Bus ──deliver──→ Event Consumer
                                       ↓
                                  (持久化)
```

**核心思想**：**事件发生 → 通知关心它的服务 → 各服务自行响应**。

### 1.2 三种 EDA 模式

#### 事件通知（Event Notification）

```
Order Service ──"OrderCreated"──→ Notification Service
                              ──→ Inventory Service
                              ──→ Shipping Service
```

- 事件**只包含最小信息**（如 order_id）
- Consumer 自己查 DB 拿详情
- **优点**：简单、解耦
- **缺点**：Consumer 必须可访问 DB

#### 事件溯源（Event Sourcing）

```
All changes ──→ Event Store ──→ Replay to build state
```

- **不存当前状态**，只存**事件流**
- 当前状态 = 重放所有事件
- **优点**：完整审计、可重放
- **缺点**：复杂、查询困难

#### 事件流（Event Streaming）

```
Producer ──→ Event Stream (Kafka) ──→ Consumer 1
                                  ──→ Consumer 2
                                  ──→ Consumer 3
```

- **持久化**事件流
- Consumer 可以**回放历史**
- 典型实现：Kafka、Pulsar

### 1.3 EDA 核心组件

| 组件 | 职责 |
|------|------|
| **Event** | 系统中发生的事实（不可变）|
| **Producer** | 发布事件的服务 |
| **Event Bus / Broker** | 事件传输层 |
| **Consumer** | 订阅并处理事件的服务 |
| **Schema Registry** | 事件 schema 管理 |

### 1.4 EDA 的优缺点

**优点**：
- **解耦**：Producer 不知道 Consumer
- **可扩展**：加新 Consumer 不用改 Producer
- **异步**：Producer 不阻塞
- **可观测**：所有事件流可监控

**缺点**：
- **最终一致**：不是强一致
- **调试困难**：事件链追踪复杂
- **消息可靠性**：需要 broker 保证
- **事务复杂**：跨服务事务难做

### 1.5 EDA vs 同步调用

```python
# ❌ 同步：订单服务调用通知 + 库存
def create_order(data):
    order = save_order(data)
    notification.send(order)  # 同步调用
    inventory.update(order)    # 同步调用
    return order
# 问题：notification 挂了订单创建失败

# ✅ 事件驱动：订单服务发事件，其他服务订阅
def create_order(data):
    order = save_order(data)
    event_bus.publish("OrderCreated", order)  # 异步
    return order
# notification 挂了不影响订单创建
```

## 2. 代码示例

### 2.1 简单事件总线（Redis Pub/Sub）

```python
import redis
import json

class EventBus:
    def __init__(self):
        self.r = redis.Redis(decode_responses=True)

    def publish(self, topic, event):
        self.r.publish(topic, json.dumps(event))

    def subscribe(self, topic, handler):
        """在独立线程中处理事件"""
        import threading
        pubsub = self.r.pubsub()
        pubsub.subscribe(topic)

        def run():
            for msg in pubsub.listen():
                if msg["type"] == "message":
                    event = json.loads(msg["data"])
                    try:
                        handler(event)
                    except Exception as e:
                        print(f"Handler error: {e}")

        t = threading.Thread(target=run, daemon=True)
        t.start()

# 使用
bus = EventBus()

# 订阅
def on_order_created(event):
    print(f"Sending notification for order {event['order_id']}")

bus.subscribe("order.created", on_order_created)

# 发布
bus.publish("order.created", {"order_id": 1, "amount": 99.9})
```

### 2.2 dify 的 BroadcastChannel 接口

**代码示例**（基于 dify 实际接口）：

```python
from libs.broadcast_channel.channel import BroadcastChannel
from extensions.ext_redis import redis_client

# 拿到 channel
channel = BroadcastChannel(redis_client)
topic = channel.topic("workflow_events")

# 发布
producer = topic.as_producer()
producer.publish(json.dumps({"event": "workflow_started", "id": "123"}).encode())

# 订阅（在独立线程/进程）
subscriber = topic.as_subscriber()
subscription = subscriber.subscribe()
for message in subscription:
    event = json.loads(message.decode())
    print(f"Received: {event}")
    if event["event"] == "stop":
        break
    subscription.close()
```

### 2.3 事件 schema 设计

```python
from typing import TypedDict
from datetime import datetime

class OrderCreatedEvent(TypedDict):
    event_type: str  # "order.created"
    event_id: str    # UUID，唯一标识
    occurred_at: str # ISO 时间戳
    data: dict       # 业务数据

def make_order_event(order):
    return OrderCreatedEvent(
        event_type="order.created",
        event_id=str(uuid.uuid4()),
        occurred_at=datetime.now().isoformat(),
        data={
            "order_id": order.id,
            "user_id": order.user_id,
            "amount": order.amount,
        },
    )
```

### 2.4 常见错误：事件循环依赖

```python
# ❌ 错误：服务 A 发布事件 → 服务 B 处理 → 触发服务 A 的事件 → 死循环
# 服务 A
bus.publish("order.created", order)

# 服务 B
@bus.subscribe("order.created")
def handle(event):
    bus.publish("inventory.reserved", event)  # 又触发其他事件

# 服务 A 监听了 inventory.reserved
@bus.subscribe("inventory.reserved")
def handle2(event):
    bus.publish("order.created", event)  # 死循环！
```

## 3. dify 仓库源码解读

### 3.1 BroadcastChannel 抽象接口

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/channel.py`

**解读**（基于接口推断）：
- `BroadcastChannel` 是 dify 的**事件总线抽象**
- 三种实现（Pub/Sub / Sharded Pub/Sub / Stream）共享同一接口
- 业务代码不感知底层用哪种
- **典型用途**：工作流执行进度实时推送给前端

### 3.2 Stream 模式的事件保留

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
**核心代码**（行 55-68）：

```python
self.max_length = 5000

def as_producer(self) -> Producer:
    return self

def publish(self, payload: bytes) -> None:
    self._client.xadd(self._key, {b"data": payload}, maxlen=self.max_length)
    if self._retention_seconds > 0:
        try:
            self._client.expire(self._key, self._retention_seconds)
        except Exception as e:
            logger.warning("Failed to set expire for stream key %s: %s", self._key, e, exc_info=True)
```

**解读**：
- **`maxlen=5000`**：每个 topic Stream 最多保留 5000 条事件
- **`retention_seconds`**：Stream 闲置 N 秒后过期（节省存储）
- **平衡**：够历史回放，又不无限增长

### 3.3 gevent 兼容的异步接收

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
**核心代码**（行 174-191）：

```python
@override
def receive(self, timeout: float | None = 0.1) -> bytes | None:
    with self._lock:
        if self._closed:
            raise SubscriptionClosedError("The Redis streams subscription is closed")
        self._start_if_needed()

    try:
        if timeout is None:
            item = self._queue.get()
        else:
            item = self._queue.get(timeout=timeout)
    except queue.Empty:
        return None

    if item is self._SENTINEL:
        raise SubscriptionClosedError("The Redis streams subscription is closed")
    assert isinstance(item, (bytes, bytearray)), "Unexpected item type in stream queue"
    return bytes(item)
```

**解读**：
- **生产者 - 消费者模型**：listener 线程从 Redis XREAD → 推到内存队列
- **消费者**（业务代码）从内存队列 `get()`，不直接阻塞 Redis
- **gevent 友好**：listener 用独立线程，业务代码可以 await 队列
- **SENTINEL**：listener 关闭时放入队列的标志

### 3.4 事件订阅的生命周期

```python
# 创建订阅
subscription = topic.subscribe()

# 在 try-finally 中使用
try:
    for message in subscription:  # 阻塞接收
        process(message)
finally:
    subscription.close()  # 释放资源（线程、连接）
```

**解读**：
- **资源管理**：必须显式 `close()` 否则线程泄漏
- `subscription.close()` 发送 `SIG_CLOSE` 让 listener 退出
- `daemon=True`：listener 线程是守护线程，主程序退出时自动结束

## 4. 关键要点总结

- **EDA**：通过事件解耦服务
- **三种模式**：通知 / 溯源 / 流
- **优点**：解耦、可扩展、异步
- **缺点**：最终一致、调试复杂
- dify 用 **Redis Pub/Sub / Stream** 实现事件总线
- **Stream 模式** 提供持久化（适合审计、回放）
- **Pub/Sub 模式** 更轻量（适合实时通知）

## 5. EDA 适用场景

| 场景 | 推荐模式 |
|------|---------|
| 实时通知（聊天、推送）| Pub/Sub |
| 订单处理（多服务联动）| 事件通知 |
| 审计日志（合规要求）| 事件溯源 |
| 大数据处理（日志、监控）| 事件流 |
| 工作流进度推送 | Pub/Sub / Stream |

## 6. 练习题

### 练习 1：基础（必做）

用 Redis Pub/Sub 实现简单事件总线：发布 `order.created` 事件，多个订阅者各自处理（邮件、库存、日志）。

### 练习 2：进阶

用 Redis Stream 实现可靠事件系统：
- Producer 发布事件
- 消费者崩溃后重启能从历史 Offset 继续处理
- 用 `xpending` 查看未 ack 消息

### 练习 3：挑战（选做）

阅读 `libs/broadcast_channel/channel.py`（抽象接口），设计一个**新的实现**：用 Kafka 作为后端（实现相同的 `Topic` / `Subscription` 接口）。

## 7. 参考资料

- `/Users/xu/code/github/dify/api/libs/broadcast_channel/channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/sharded_channel.py`
- EDA 模式：https://martinfowler.com/articles/201701-event-driven.html
- 事件驱动微服务：https://microservices.io/patterns/data/event-driven-architecture.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13