# 3.7 消息可靠性：至少一次 / 最多一次

> 理解消息可靠性三个语义的区别，掌握 ruoyi 如何保证"至少一次"。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解三种消息可靠性语义（至多 / 至少 / 恰好一次）
- 掌握 Redis Stream 的 ack 机制如何保证至少一次
- 看懂 ruoyi 的 pending 重投如何兜底
- 在业务中实现幂等性来兼容"至少一次"的重复投递

## 📚 前置知识

- Redis Stream（参见 `14-redis-stream-impl.md`）
- ruoyi 消息抽象（参见 `13-ruoyi-message.md`）

## 1. 核心概念

### 1.1 三种语义对比

| 语义 | 描述 | 实现难度 | 典型应用 |
|------|------|---------|---------|
| 至多一次 | 可能丢，不重复 | 简单 | 日志收集 |
| 至少一次 | 不丢，可能重 | 中等 | 业务消息 |
| 恰好一次 | 不丢不重 | 难 | 金融交易 |

### 1.2 至少一次的实现方式

```
生产者：发送 → 等 ack（broker 收到才算成功）
Broker：消息持久化到磁盘
消费者：消费业务执行成功 → ack；否则不 ack
故障兜底：pending 消息由定时任务重新投递
```

### 1.3 幂等性

"至少一次"会有重复消息风险，业务必须**幂等**：
- 用唯一业务 ID（如订单号）作为去重 key
- 用 Redis `SETNX` 或 DB 唯一索引去重

## 2. 代码示例

### 2.1 至少一次的发送

```java
public void send(Order order) {
    // 同步发送：等 broker 确认收到
    SendResult result = kafkaTemplate.send("order", order).get();
    if (result.getRecordMetadata() == null) {
        throw new RuntimeException("发送失败");
    }
}
```

### 2.2 幂等消费

```java
public void handleOrder(Order order) {
    // 用 Redis SETNX 做幂等判断
    String key = "order:processed:" + order.getId();
    Boolean firstTime = redisTemplate.opsForValue().setIfAbsent(key, "1", Duration.ofDays(7));
    if (Boolean.FALSE.equals(firstTime)) {
        log.info("订单已处理过，跳过：{}", order.getId());
        return;
    }
    // 真正处理
    doProcess(order);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 手动 ack 保证至少一次

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
**核心代码**（行 62-80）：

```java
@Override
public void onMessage(ObjectRecord<String, String> message) {
    // 消费消息
    T messageObj = JsonUtils.parseObject(message.getValue(), messageType);
    try {
        consumeMessageBefore(messageObj);
        // 消费消息
        this.onMessage(messageObj);
        // ack 消息消费完成
        redisMQTemplate.getRedisTemplate().opsForStream().acknowledge(group, message);
        // TODO 芋艿：需要额外考虑以下几个点：
        // 1. 处理异常的情况
        // 2. 发送日志；以及事务的结合
        // 3. 消费日志；以及通用的幂等性
        // 4. 消费失败的重试，https://zhuanlan.zhihu.com/p/60501638
    } finally {
        consumeMessageAfter(messageObj);
    }
}
```

**解读**：
- 第 71 行：`acknowledge` 只在业务方法 `this.onMessage(messageObj)` **成功后**才执行
- 如果业务抛异常 → 没有 ack → 消息留在 pending 队列 → 5 分钟后定时任务重投
- 这是至少一次语义的实现：**不丢，但可能重**

### 3.2 Pending 消息 5 分钟重投

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
**核心代码**（行 30-36, 82-101）：

```java
/**
 * 消息超时时间，默认 5 分钟
 *
 * 1. 超时的消息才会被重新投递
 * 2. 由于定时任务 1 分钟一次，消息超时后不会被立即重投，极端情况下消息 5 分钟过期后，再等 1 分钟才会被扫瞄到
 */
private static final int EXPIRE_TIME = 5 * 60;

...

pendingMessages.forEach(pendingMessage -> {
    // 获取消息上一次传递到 consumer 的时间,
    long lastDelivery = pendingMessage.getElapsedTimeSinceLastDelivery().getSeconds();
    if (lastDelivery < EXPIRE_TIME){
        return;
    }
    // 获取指定 id 的消息体
    List<MapRecord<String, Object, Object>> records = ops.range(listener.getStreamKey(),
            Range.of(Range.Bound.inclusive(pendingMessage.getIdAsString()), Range.Bound.inclusive(pendingMessage.getIdAsString())));
    if (CollUtil.isEmpty(records)) {
        return;
    }
    // 重新投递消息
    redisTemplate.getRedisTemplate().opsForStream().add(StreamRecords.newRecord()
            .ofObject(records.get(0).getValue()) // 设置内容
            .withStreamKey(listener.getStreamKey()));
    // ack 消息消费完成
    redisTemplate.getRedisTemplate().opsForStream().acknowledge(listener.getGroup(), records.get(0));
});
```

**解读**：
- `EXPIRE_TIME = 5 * 60`：5 分钟未 ack 的消息会被重投
- `if (lastDelivery < EXPIRE_TIME) return`：5 分钟内不重投（避免反复）
- **重投机制**：
  1. 把 pending 消息重新 XADD 到 stream
  2. 给原 pending 消息发 XACK（清掉 pending 状态）
- 这是**双重保障**：业务代码 ack 失败 + 定时任务兜底重投

### 3.3 TODO 注释：ruoyi 已知待优化点

代码注释里写了 TODO：
```
// 1. 处理异常的情况
// 2. 发送日志；以及事务的结合
// 3. 消费日志；以及通用的幂等性
// 4. 消费失败的重试
```

这些是"至少一次"必须配套做的：
- **幂等性**：业务层必须处理重复消息
- **事务结合**：DB 操作和 ack 的原子性
- **失败重试**：异常情况的退避策略

## 4. 关键要点总结

- 至少一次 = "不丢但可能重"，最常用的业务语义
- Redis Stream 通过"手动 ack + pending 重投"实现至少一次
- 业务必须配套幂等性：唯一 ID + SETNX / DB 唯一索引
- ruoyi 用 5 分钟重投机制兜底，但要求业务层幂等

## 5. 练习题

### 练习 1：基础（必做）

解释"至少一次"和"最多一次"的区别，举一个场景分别适合哪种。

### 练习 2：进阶

阅读 `RedisPendingMessageResendJob.execute()`，解释重投的具体步骤：是否需要 XACK 原消息？

### 练习 3：挑战（选做）

实现一个幂等消息处理器：用 `SETNX order:processed:{id}` 防止重复扣库存。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractRedisStreamMessageListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13