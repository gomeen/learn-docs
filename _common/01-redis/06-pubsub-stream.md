# 1.6 Redis Pub/Sub 与 Stream

> 掌握 Redis 的两种消息传递机制：传统 Pub/Sub 与 Redis 5.0 引入的 Stream。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Pub/Sub 与 Stream 的核心差异（持久化、消费组）
- 用 redis-py 实现 Pub/Sub 发布订阅
- 用 Stream 实现可靠的消费者组模式
- 在 dify 中找到 BroadcastChannel 的实现

## 📚 前置知识

- Redis 基础数据结构（`01-redis/01-data-structures.md`）
- 消息队列基本概念（Producer / Consumer）
- 事件驱动编程基础

## 1. 核心概念

### 1.1 为什么 Redis 不只是缓存？

Redis 常被用作**轻量级消息中间件**，提供两种消息传递能力：
- **Pub/Sub**：发布订阅，**不持久化**消息
- **Stream**：消息流，**持久化 + 消费者组**，类似简化版 [Kafka](../02-mq/02-kafka.md)

### 1.2 Pub/Sub：发布订阅

**核心命令**：
```redis
SUBSCRIBE channel1            # 订阅频道
PUBLISH channel1 "msg"        # 发布消息
PSUBSCRIBE news.*             # 模式订阅
```

**特性**：
- **实时**：消息立即推送给所有订阅者
- **无持久化**：订阅者下线期间的消息**全部丢失**
- **无消费者组**：每个订阅者都收到**全量**消息（fanout 模式）
- **无 ACK**：客户端无法告诉服务端"我收到了"

**适用场景**：
- 实时通知（聊天室、系统事件广播）
- 缓存失效广播（集群内多个应用实例收到失效信号）

### 1.3 Stream：消息流（Redis 5.0+）

**核心命令**：
```redis
XADD mystream * field1 v1 field2 v2        # 追加消息
XLEN mystream                               # 消息总数
XRANGE mystream - +                         # 范围读取
XREAD COUNT 10 BLOCK 0 STREAMS mystream 0   # 阻塞读
XREADGROUP GROUP g1 c1 COUNT 10 STREAMS mystream >   # 消费者组读
XACK mystream g1 <id>                       # 确认消费
```

**特性**：
- **持久化**：消息存到 AOF / RDB，重启不丢
- **消费者组**：每个消息只被组内一个消费者处理（类似 Kafka）
- **ACK 机制**：消费者处理完后调用 `XACK`，消息才从 PEL（Pending Entries List）移除
- **历史回放**：可读取任意时间点的消息
- **消息 ID**：单调递增的 `ms-seq` 格式（如 `1234567890123-0`）

### 1.4 关键概念对比

| 特性 | Pub/Sub | Stream |
|------|---------|--------|
| 持久化 | 否 | 是 |
| 消费者组 | 否（fanout） | 是 |
| ACK | 否 | 是 |
| 历史回放 | 否 | 是（XRANGE） |
| 适用 | 实时通知、广播 | 可靠消息队列、事件溯源 |

### 1.5 Stream 的消费者组机制

```
Producers --> [mystream] ---> Group "g1"
                                  |
                                  ├──> Consumer A  ---> XACK
                                  └──> Consumer B  ---> XACK

* 消息先入 PEL（Pending Entries List）
* 消费者处理完后 XACK，从 PEL 移除
* 崩溃的消费者消息留在 PEL，可被其他消费者"claim"
```

### 1.6 dify 中的 BroadcastChannel 抽象

dify 抽象了多种广播通道：
- `pubsub_channel.py`：基于 Pub/Sub
- `sharded_channel.py`：基于 Redis Sharded Pub/Sub（Cluster 友好）
- `streams_channel.py`：基于 Stream（持久化）

通过配置 `PUBSUB_REDIS_CHANNEL_TYPE=pubsub|sharded|streams` 选择实现。

## 2. 代码示例

### 2.1 Pub/Sub 基础用法

```python
# 文件：example_pubsub.py
import redis
import threading
import time

r = redis.Redis(host="localhost", port=6379)

def subscriber():
    """订阅者线程"""
    pubsub = r.pubsub()
    pubsub.subscribe("news")
    for message in pubsub.listen():
        if message["type"] == "message":
            print(f"收到: {message['data']}")

# 启动订阅线程
t = threading.Thread(target=subscriber, daemon=True)
t.start()

time.sleep(0.5)  # 等待订阅生效

# 发布 3 条消息
r.publish("news", "消息 1")
r.publish("news", "消息 2")
r.publish("news", "消息 3")

time.sleep(0.5)
```

### 2.2 Stream 消费者组模式

```python
# 文件：example_stream.py
import redis

r = redis.Redis(host="localhost", port=6379)
STREAM = "events"
GROUP = "workers"

# 1. 创建消费者组（MKSTREAM 表示 stream 不存在则创建）
try:
    r.xgroup_create(STREAM, GROUP, id="$", mkstream=True)
except redis.ResponseError:
    pass  # 组已存在

# 2. 生产者写入消息
for i in range(5):
    r.xadd(STREAM, {"event": f"click-{i}", "user_id": str(i)})

# 3. 消费者读取新消息
messages = r.xreadgroup(GROUP, "consumer-1", {STREAM: ">"}, count=10, block=5000)
print(f"读到 {len(messages[0][1])} 条消息")

# 4. 处理后 ACK
for _, msg_list in messages:
    for msg_id, data in msg_list:
        print(f"处理 {msg_id}: {data}")
        r.xack(STREAM, GROUP, msg_id)

# 5. 查看 PEL（Pending Entries List）
pending = r.xpending(STREAM, GROUP)
print(f"待处理消息: {pending}")
```

### 2.3 常见错误：用 Pub/Sub 做可靠消息队列

```python
# ❌ 反例：用 Pub/Sub 传订单消息
def publish_order(order):
    r.publish("orders", json.dumps(order))

# 问题：
# 1. 订阅者下线时消息丢失
# 2. 消费者崩溃后消息不会重发
# 3. 无法保证"至少一次"投递

# ✅ 正例：用 Stream + 消费者组
def publish_order(order):
    r.xadd("orders", {"data": json.dumps(order)})

def consume_order():
    while True:
        msgs = r.xreadgroup("orders-group", "worker-1", {"orders": ">"}, block=5000)
        for _, msg_list in msgs:
            for msg_id, data in msg_list:
                try:
                    process_order(data)
                    r.xack("orders", "orders-group", msg_id)
                except Exception:
                    pass  # 不 ACK，下次重读
```

## 3. dify 仓库源码解读

### 3.1 dify 的 BroadcastChannel 选择

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
- 第 3 行：硬性断言 `_pubsub_redis_client` 已初始化，避免使用未配置的对象
- 第 4-5 行：`sharded` 模式使用 Redis 7+ 的 Sharded Pub/Sub，**Cluster 友好**（传统 Pub/Sub 在 Cluster 模式下所有消息会广播到所有节点）
- 第 6-10 行：`streams` 模式提供持久化和消费者组，适合**关键事件**（如工作流状态变更）
- 第 11 行：默认 `RedisBroadcastChannel` 使用传统 Pub/Sub，简单但消息可能丢失

**整体设计意图**：dify 把"消息传递"抽象成 `BroadcastChannel` 协议，业务代码不关心底层是 Pub/Sub 还是 Stream，部署时按需切换。

### 3.2 ruoyi 的 Redis Stream（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
**核心代码**（简化）：

```java
// RedisStreamConsumer.java
@Component
public class RedisStreamConsumer {
    @Resource
    private StringRedisTemplate redisTemplate;

    @PostConstruct
    public void init() {
        // 创建消费者组
        try {
            redisTemplate.opsForStream().createGroup("user-events", "user-events-group");
        } catch (Exception ignored) {}

        // 启动消费线程
        new Thread(this::consume).start();
    }

    private void consume() {
        while (true) {
            // XREADGROUP 阻塞读取
            List<MapRecord<String, Object, Object>> records = redisTemplate.opsForStream()
                .read(Consumer.from("user-events-group", "consumer-1"),
                      StreamReadOptions.empty().count(10).block(Duration.ofSeconds(5)),
                      StreamOffset.create("user-events", ReadOffset.lastConsumed()));

            for (MapRecord<String, Object, Object> record : records) {
                try {
                    handleEvent(record);
                    redisTemplate.opsForStream().acknowledge("user-events", "user-events-group", record.getId());
                } catch (Exception e) {
                    log.error("处理失败", e);
                }
            }
        }
    }
}
```

**解读**：
- 第 6-10 行：与 dify 相同的"先尝试创建组、捕获异常"模式（处理已存在的情况）
- 第 20 行：`StreamReadOptions.block(5s)` 阻塞读，无消息时等待 5 秒
- 第 24 行：`acknowledge()` 对应 XACK，从 PEL 移除

## 4. 关键要点总结

- **Pub/Sub**：实时、无持久化、无 ACK，适合通知广播
- **Stream**：持久化、消费者组、ACK、可靠消息队列
- 选 Pub/Sub 的场景：缓存失效广播、实时聊天、系统事件
- 选 Stream 的场景：订单处理、事件溯源、可靠任务分发
- Redis Cluster 必须用 **Sharded Pub/Sub** 或 **Stream**，传统 Pub/Sub 会广播到所有节点
- dify 通过 `PUBSUB_REDIS_CHANNEL_TYPE` 配置切换实现，业务代码无感知

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 实现：
1. 一个 producer 写入 10 条消息到 Stream `test-stream`
2. 一个 consumer 用消费者组读取并 ACK

### 练习 2：进阶

对比以下三个场景，应选 Pub/Sub 还是 Stream？
1. 用户登录后向 3 个微服务广播"用户已上线"
2. 订单创建后通知库存服务扣减
3. 配置变更后通知所有实例刷新本地缓存

### 练习 3：挑战（选做）

阅读 `dify/api/libs/broadcast_channel/streams_channel.py`（如果存在），分析 Stream 实现中如何处理**消费者崩溃**——PEL 中的消息多久会被重新投递？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/`
- Redis Pub/Sub 文档：https://redis.io/docs/pubsub/
- Redis Stream 文档：https://redis.io/docs/data-types/streams/

---

**文档版本**：v1.0
**最后更新**：2026-07-14