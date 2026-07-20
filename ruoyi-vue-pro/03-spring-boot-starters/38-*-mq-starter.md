# 小验证：MQ 抽象与多实现

> 覆盖：
- [mq starter](./32-mq-starter.md)
- [Message 抽象](./33-message.md)
- [Redis Stream](./34-redis-stream.md)
- [RabbitMQ](./35-rabbitmq-impl.md)
- [Kafka](./36-kafka-impl.md)
- [RocketMQ](./37-rocketmq-impl.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

ruoyi 用统一消息抽象切换 Redis Stream / Rabbit / Kafka / RocketMQ。本验证用默认实现跑通生产消费。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 确认当前启用的 MQ 实现（配置项 / 依赖）。
2. 找到一处现有 Producer/Consumer（system 模块常见），梳理消息类型与 channel/topic。
3. **最小自测**：新增一个 demo 消息（或复用测试消息）发送，消费者打印 payload；确保只消费一次（注意广播/集群模式）。
4. 对照文档：说明若切换到 RabbitMQ，业务代码哪些地方应尽量不改（抽象边界）。

## 提示

- Redis Stream 需 Redis 5+。
- 消费失败重试策略先观察再改。
- 本地配置不要连错环境。

## 验收标准

- [ ] 明确当前 MQ 实现与关键配置项
- [ ] 指出至少一对 Producer/Consumer 代码路径
- [ ] 自测消息从发到收日志闭环
- [ ] 说明统一 Message 抽象的价值（切换成本）
- [ ] 记录消息序列化方式（JSON 等）

## 延伸（选做）

- 模拟消费异常，观察是否重试/进死信（取决于实现）。
- 对比 Redis Stream 与 Rabbit 的 ack 模型。
