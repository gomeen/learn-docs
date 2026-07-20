# 05 - 缓存与消息队列

> ruoyi-vue-pro 使用 Redisson 做缓存，支持 Redis/RabbitMQ/Kafka/RocketMQ 多种 MQ。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Redis 数据结构 / 持久化 / 集群 | [_common/01-redis/](../../_common/01-redis/) | 本地基础文待补；优先公共 + 下方 Redisson 文档 |
| Redisson 客户端 | [_common/01-redis/](../../_common/01-redis/) | [01-redisson.md](./01-redisson.md) |
| 消息队列概念 / Kafka / RabbitMQ / RocketMQ | [_common/02-mq/](../../_common/02-mq/) | [02-ruoyi-message.md](./02-ruoyi-message.md) |
| 缓存穿透 / 击穿 / 雪崩 | [02-three-problems](../../_common/03-cache-patterns/02-three-problems.md) | 项目视角文待补 |
| 分布式锁 | [02-redis-redlock](../../_common/04-distributed-locks/02-redis-redlock.md) | [03-redisson-lock.md](./03-redisson-lock.md) |
| 限流 | [04-rate-limiting](../../_common/03-cache-patterns/04-rate-limiting.md) | [04-redisson-rate-limiter.md](./04-redisson-rate-limiter.md) |
| 分布式 Session | [05-distributed-session](../../_common/03-cache-patterns/05-distributed-session.md) | 项目视角文待补 |
| 分布式 ID | [06-distributed-id](../../_common/03-cache-patterns/06-distributed-id.md) | 项目视角文待补 |

## 模块 5.1 Redis 与 Redisson

- [ ] Redis 数据结构与命令（公共见 [_common/01-redis/01-data-structures](../../_common/01-redis/01-data-structures.md)）
- [ ] [1.2 Redisson 客户端](./01-redisson.md)
- [ ] [1.3 Redisson 分布式锁](./03-redisson-lock.md)
- [ ] [1.4 Redisson 限流：RRateLimiter](./04-redisson-rate-limiter.md)
- [ ] [1.5 Redisson 集合：RList / RMap / RQueue](./05-redisson-collections.md)
- [ ] Redis 发布订阅 / Stream（公共见 [_common/01-redis/06-pubsub-stream](../../_common/01-redis/06-pubsub-stream.md)）
- [ ] [1.7 ruoyi 的 RedisUtils 工具类](./06-ruoyi-redis-utils.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-redisson: Redisson 与工具类](./07-*-redisson.md)
  - 覆盖：01-redisson.md, 03-redisson-lock.md, 04-redisson-rate-limiter.md, 05-redisson-collections.md, 06-ruoyi-redis-utils.md


## 模块 5.2 Spring Cache

- [ ] [2.1 Spring Cache 抽象层](./08-spring-cache.md)
- [ ] [2.2 @Cacheable / @CacheEvict / @CachePut](./09-cache-annotation.md)
- [ ] [2.3 Redis 作为 Spring Cache 后端](./10-spring-cache-redis.md)
- [ ] [2.4 ruoyi 的缓存使用场景](./11-ruoyi-cache-usage.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [12-*-spring-cache: Spring Cache 与 ruoyi 用法](./12-*-spring-cache.md)
  - 覆盖：08-spring-cache.md, 09-cache-annotation.md, 10-spring-cache-redis.md, 11-ruoyi-cache-usage.md


## 模块 5.3 消息队列

- [ ] 消息队列核心概念（公共见 [_common/02-mq/01-concepts](../../_common/02-mq/01-concepts.md)）
- [ ] [3.2 ruoyi 消息抽象：Message](./02-ruoyi-message.md)
- [ ] [3.3 Redis Stream 实现](./13-redis-stream-impl.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [14-*-mq: ruoyi 消息抽象与 Redis Stream](./14-*-mq.md)
  - 覆盖：02-ruoyi-message.md, 13-redis-stream-impl.md

- [ ] RabbitMQ（公共见 [_common/02-mq/03-rabbitmq](../../_common/02-mq/03-rabbitmq.md)；ruoyi 集成文待补）
- [ ] Kafka（公共见 [_common/02-mq/02-kafka](../../_common/02-mq/02-kafka.md)；ruoyi 集成文待补）
- [ ] RocketMQ（公共见 [_common/02-mq/04-rocketmq](../../_common/02-mq/04-rocketmq.md)；ruoyi 集成文待补）
- [ ] 消息可靠性（公共见 [_common/02-mq/05-reliability](../../_common/02-mq/05-reliability.md)）
- [ ] 死信队列与重试（公共见 [_common/02-mq/06-dead-letter](../../_common/02-mq/06-dead-letter.md)）

## 模块 5.4 业务场景应用

- [ ] 分布式 Session（公共见 [_common/03-cache-patterns/05-distributed-session](../../_common/03-cache-patterns/05-distributed-session.md)；项目文待补）
- [ ] 分布式 ID / Snowflake（公共见 [_common/03-cache-patterns/06-distributed-id](../../_common/03-cache-patterns/06-distributed-id.md)；项目文待补）
- [ ] 全局唯一短 ID（公共见 [_common/03-cache-patterns/07-short-id](../../_common/03-cache-patterns/07-short-id.md)；项目文待补）
- [ ] 缓存穿透 / 击穿 / 雪崩（公共见 [_common/03-cache-patterns/02-three-problems](../../_common/03-cache-patterns/02-three-problems.md)；项目文待补）

## 🎯 ruoyi-vue-pro 仓库对应位置

- Redis Starter：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- MQ Starter：`yudao-framework/yudao-spring-boot-starter-mq/`
- 消息生产者：`yudao-module-system/.../mq/producer/`
- 消息消费者：`yudao-module-system/.../mq/consumer/`
