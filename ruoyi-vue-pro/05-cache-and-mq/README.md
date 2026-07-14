# 05 - 缓存与消息队列

> ruoyi-vue-pro 使用 Redisson 做缓存，支持 Redis/RabbitMQ/Kafka/RocketMQ 多种 MQ。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Redis 数据结构 / 持久化 / 集群 | [_common/01-redis/](../../_common/01-redis/) | 01-redis-basics.md（ruoyi 视角） |
| Redisson 客户端 | [_common/01-redis/](../../_common/01-redis/) | 02-redisson.md（ruoyi 特有） |
| 消息队列概念 / Kafka / RabbitMQ / RocketMQ | [_common/02-mq/](../../_common/02-mq/) | 13-ruoyi-message.md（ruoyi 抽象） |
| 缓存穿透 / 击穿 / 雪崩 | [_common/03-cache-patterns/02-three-problems](../../_common/03-cache-patterns/02-three-problems.md) | 23-cache-problems.md（ruoyi 视角） |
| 分布式锁 | [_common/04-distributed-locks/02-redis-redlock](../../_common/04-distributed-locks/02-redis-redlock.md) | 03-redisson-lock.md（ruoyi Redisson） |
| 限流 | [_common/03-cache-patterns/04-rate-limiting](../../_common/03-cache-patterns/04-rate-limiting.md) | 04-redisson-rate-limiter.md（Redisson） |
| 分布式 Session | [_common/03-cache-patterns/05-distributed-session](../../_common/03-cache-patterns/05-distributed-session.md) | 20-distributed-session.md |
| 分布式 ID | [_common/03-cache-patterns/06-distributed-id](../../_common/03-cache-patterns/06-distributed-id.md) | 21-snowflake.md |

## 模块 5.1 Redis 与 Redisson

- [ ] [1.1 Redis 数据结构与命令](./01-redis-basics.md)
- [ ] [1.2 Redisson 客户端](./02-redisson.md)
- [ ] [1.3 Redisson 分布式锁](./03-redisson-lock.md)
- [ ] [1.4 Redisson 限流：RRateLimiter](./04-redisson-rate-limiter.md)
- [ ] [1.5 Redisson 集合：RList / RMap / RQueue](./05-redisson-collections.md)
- [ ] [1.6 Redis 发布订阅：RTopic](./06-redis-pubsub.md)
- [ ] [1.7 ruoyi 的 RedisUtils 工具类](./07-ruoyi-redis-utils.md)

## 模块 5.2 Spring Cache

- [ ] [2.1 Spring Cache 抽象层](./08-spring-cache.md)
- [ ] [2.2 @Cacheable / @CacheEvict / @CachePut](./09-cache-annotation.md)
- [ ] [2.3 Redis 作为 Spring Cache 后端](./10-spring-cache-redis.md)
- [ ] [2.4 ruoyi 的缓存使用场景](./11-ruoyi-cache-usage.md)

## 模块 5.3 消息队列

- [ ] [3.1 消息队列核心概念](./12-mq-concepts.md)
- [ ] [3.2 ruoyi 消息抽象：Message](./13-ruoyi-message.md)
- [ ] [3.3 Redis Stream 实现](./14-redis-stream-impl.md)
- [ ] [3.4 RabbitMQ 集成](./15-rabbitmq-impl.md)
- [ ] [3.5 Kafka 集成](./16-kafka-impl.md)
- [ ] [3.6 RocketMQ 集成](./17-rocketmq-impl.md)
- [ ] [3.7 消息可靠性：至少一次 / 最多一次](./18-mq-reliability.md)
- [ ] [3.8 死信队列与重试](./19-dead-letter.md)

## 模块 5.4 业务场景应用

- [ ] [4.1 分布式 Session](./20-distributed-session.md)
- [ ] [4.2 分布式 ID：Snowflake](./21-snowflake.md)
- [ ] [4.3 全局唯一短 ID 生成](./22-short-id.md)
- [ ] [4.4 缓存穿透 / 击穿 / 雪崩](./23-cache-problems.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- Redis Starter：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- MQ Starter：`yudao-framework/yudao-spring-boot-starter-mq/`
- 消息生产者：`yudao-module-system/.../mq/producer/`
- 消息消费者：`yudao-module-system/.../mq/consumer/`
