# 4.4.4 Redis Pub/Sub 与 Stream

> Redis 提供 Pub/Sub 和 Stream 两种消息机制，前者轻量实时，后者可靠持久。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Redis Pub/Sub 实现实时广播
- 用 Redis Streams 实现可靠消息队列
- 区分两者的使用场景
- 在 dify 中识别它们的实际应用

## 📚 前置知识

- Redis 基础
- 消息队列基础
- 01-redis-data-structures.md、23-mq-concepts.md

## 1. 核心概念

### 1.1 两种机制对比

| 特性 | Pub/Sub | Stream |
|------|---------|--------|
| 持久化 | ❌ | ✅ |
| 消费组 | ❌ | ✅ |
| 历史回放 | ❌ | ✅ |
| 延迟 | 极低 | 低 |
| 适用 | 实时通知 | 事件流、可靠消息 |

### 1.2 Pub/Sub：轻量实时广播

**核心命令**：
```bash
SUBSCRIBE channel       # 订阅
PUBLISH channel message # 发布
UNSUBSCRIBE channel     # 取消订阅
```

**特点**：
- **发布后立即推送**，不存磁盘
- **订阅者不在线就丢失**
- 无确认机制（fire-and-forget）

### 1.3 Stream：可靠消息队列

**核心命令**：
```bash
XADD key * field value   # 添加消息
XLEN key                  # 消息数量
XRANGE key - +            # 范围查询
XREAD BLOCK 0 STREAMS key 0  # 阻塞读取
XREADGROUP GROUP g c COUNT n STREAMS key >  # 消费组读取
```

**特点**：
- 消息**持久化**到 Stream
- 支持**消费组**（Consumer Group）
- **Offset 跟踪**消费进度
- 可重放历史消息

### 1.4 Stream 消费组

类似 Kafka 的 Consumer Group：
```bash
XGROUP CREATE mystream group1 $ MKSTREAM  # 创建消费组

# 消费者读取（$ 表示"新消息"）
XREADGROUP GROUP group1 consumer1 COUNT 10 STREAMS mystream >

# 确认消费
XACK mystream group1 1234567890-0
```

### 1.5 Sharded Pub/Sub（Cluster 友好）

Cluster 模式下，普通 Pub/Sub 限制较多，**Sharded Pub/Sub** 在每个 shard 独立发布：
- **更高吞吐**
- Cluster 友好
- 同样不持久化

## 2. 代码示例

### 2.1 Pub/Sub Publisher

```python
import redis

r = redis.Redis(decode_responses=True)

# 发布到 channel
r.publish("notifications", "Hello subscribers!")
```

### 2.2 Pub/Sub Subscriber

```python
import redis

r = redis.Redis(decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe("notifications")

print("Waiting for messages...")
for message in pubsub.listen():
    if message["type"] == "message":
        print(f"Received: {message['data']}")
        if message["data"] == "stop":
            break

pubsub.unsubscribe()
pubsub.close()
```

### 2.3 Stream Producer

```python
import redis

r = redis.Redis(decode_responses=True)

# 添加消息
msg_id = r.xadd("events:user_actions", {
    "user_id": 123,
    "action": "login",
    "timestamp": "2024-01-01T12:00:00",
})
print(f"Added message: {msg_id}")
```

### 2.4 Stream Consumer（消费组）

```python
import redis

r = redis.Redis(decode_responses=True)

# 创建消费组（不存在则创建）
try:
    r.xgroup_create("events:user_actions", "processors", id="$", mkstream=True)
except redis.ResponseError:
    pass  # 已存在

# 读取新消息
while True:
    messages = r.xreadgroup(
        groupname="processors",
        consumername="consumer-1",
        streams={"events:user_actions": ">"},
        count=10,
        block=5000,
    )

    for stream, entries in messages:
        for msg_id, fields in entries:
            print(f"Processing {msg_id}: {fields}")
            try:
                process(fields)
                r.xack("events:user_actions", "processors", msg_id)
            except Exception:
                # 不 ack，下次会重投
                pass
```

### 2.5 Stream 历史回放

```python
# 读取历史所有消息
all_messages = r.xrange("events:user_actions", min="-", max="+")
print(f"Total messages: {len(all_messages)}")

# 从特定 ID 开始
recent = r.xrange("events:user_actions", min="1234567890-0", max="+")
```

### 2.6 常见错误：Pub/Sub 订阅者掉线丢消息

```python
# ❌ 错误：用 Pub/Sub 处理关键业务消息
r.publish("payment", json.dumps({"order_id": 1}))
# 如果订阅者宕机，消息永久丢失！

# ✅ 正确：用 Stream 处理关键业务消息
r.xadd("payments", {"order_id": 1})
# 订阅者上线后可读取历史消息
```

## 3. dify 仓库源码解读

### 3.1 三种 Broadcast Channel 实现

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 464-473）：

```python
def get_pubsub_broadcast_channel() -> BroadcastChannelProtocol:
    assert _pubsub_redis_client is not None, "PubSub redis Client should be initialized here."
    if dify_config.PUBSUB_REDIS_CHANNEL_TYPE == "sharded":
        return ShardedRedisBroadcastChannel(_pubsub_redis_client)
    if dify_config.PUBSUB_REDIS_CHANNEL_TYPE == "streams":
        return StreamsBroadcastChannel(
            _pubsub_redis_client,
            retention_seconds=dify_config.PUBSUB_STREAMS_RETENTION_SECONDS,
        )
    return RedisBroadcastChannel(_pubsub_redis_client)
```

**解读**：
- **三种实现可配置切换**：
  1. `RedisBroadcastChannel`（默认 Pub/Sub，最快）
  2. `ShardedRedisBroadcastChannel`（Cluster 友好）
  3. `StreamsBroadcastChannel`（持久化）
- 通过 `PUBSUB_REDIS_CHANNEL_TYPE` 配置选择

### 3.2 Pub/Sub Topic 实现

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
**核心代码**（行 36-60）：

```python
class Topic:
    def __init__(self, redis_client, topic):
        self._client = redis_client
        self._topic = topic
        self._redis_topic = serialize_redis_name(topic)

    def as_producer(self) -> Producer:
        return self

    def publish(self, payload: bytes) -> None:
        self._client.publish(self._redis_topic, payload)

    def as_subscriber(self) -> Subscriber:
        return self

    def subscribe(self) -> Subscription:
        return _RedisSubscription(
            client=self._client,
            pubsub=self._client.pubsub(),
            topic=self._redis_topic,
        )
```

**解读**：
- **Topic 是逻辑概念**，物理 key = `{prefix}:{topic}`
- `as_producer()` / `as_subscriber()` 同一对象扮演不同角色
- **发布者**：`publish(bytes)` 直接转发到 Redis
- **订阅者**：`pubsub.subscribe(topic)` 后阻塞 `get_message()`

### 3.3 Stream Topic 实现

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
**核心代码**（行 45-74）：

```python
class StreamsTopic:
    def __init__(
        self,
        redis_client,
        topic,
        *,
        retention_seconds: int = 600,
    ):
        self._client = redis_client
        self._topic = topic
        self._key = serialize_redis_name(f"stream:{topic}")
        self._retention_seconds = retention_seconds
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
- **Stream key**：`{prefix}:stream:{topic}`
- **`max_length=5000`**：防止 Stream 无限制增长
- **`retention_seconds`**：Stream 闲置 N 秒后自动过期
- **生产可靠性**：消息持久化到 Redis Stream

### 3.4 Stream 订阅的 Listener 线程

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
**核心代码**（行 110-140）：

```python
def _listen(self) -> None:
    # Setting initial last id to `$` to signal redis that we only want new messages.
    last_id = "$"
    try:
        while True:
            with self._lock:
                if self._closed:
                    break
            streams = self._client.xread({self._key: last_id}, block=1000, count=100)
            if not streams:
                continue

            for _, entries in streams:
                for entry_id, fields in entries:
                    data = None
                    if isinstance(fields, dict):
                        data = fields.get(b"data")
                    data_bytes: bytes | None = None
                    match data:
                        case str():
                            data_bytes = data.encode()
                        case bytes() | bytearray():
                            data_bytes = bytes(data)
                    if data_bytes is not None:
                        if data_bytes == SIG_CLOSE:
                            break
                        self._queue.put_nowait(data_bytes)
                    last_id = entry_id
```

**解读**：
- **专用监听线程**：`_listener` thread 持续从 Redis Stream XREAD
- **`$`**：从订阅时点之后的新消息开始
- **`block=1000`**：XREAD 阻塞 1 秒
- **`count=100`**：每次最多 100 条
- **线程安全**：用 `_lock` 保护 `_closed` 标志
- **SIG_CLOSE 信号**：通过发送特殊消息让 listener 退出

### 3.5 Sharded Pub/Sub

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/sharded_channel.py`

```python
class ShardedRedisBroadcastChannel:
    """Sharded Pub/Sub implementation for Redis Cluster."""
```

**解读**：
- Cluster 模式下，普通 Pub/Sub 消息需要广播到所有节点
- **Sharded Pub/Sub**：消息只发到**特定 shard**，订阅者也连该 shard
- **优势**：更高的吞吐、Cluster 友好
- **限制**：只支持 Cluster 模式

## 4. 关键要点总结

- **Pub/Sub**：实时广播，无持久化，适合通知
- **Stream**：持久化消息队列，支持消费组、Offset
- dify 通过 `PUBSUB_REDIS_CHANNEL_TYPE` 配置切换三种实现
- Stream 用**专用 listener 线程**异步读取
- **`max_length` + `retention_seconds`** 控制 Stream 大小
- **Sharded Pub/Sub**：Cluster 模式的 Pub/Sub

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Pub/Sub 聊天程序：
- 多个"用户"订阅同一频道
- 任何用户发布消息，其他用户都收到

### 练习 2：进阶

用 Redis Stream + 消费组实现可靠消息队列：
- Producer XADD 发送 100 条消息
- 启动 3 个 Consumer（同一消费组）
- 验证消息分散处理 + 崩溃后重投

### 练习 3：挑战（选做）

阅读 `streams_channel.py` 的 `_StreamsSubscription`，理解 listener 线程的设计，并思考为什么要用 `SENTINEL` 对象 + `queue.Queue` 而不是在主线程阻塞。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 464-473 行）
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/pubsub_channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/streams_channel.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/sharded_channel.py`
- Redis Pub/Sub 文档：https://redis.io/docs/manual/pubsub/
- Redis Streams 文档：https://redis.io/docs/data-types/streams/

---

**文档版本**：v1.0
**最后更新**：2026-07-13