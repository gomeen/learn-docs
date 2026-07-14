# 04 - 缓存与消息队列

> Dify 使用 Redis 做缓存 + Celery 做异步任务，理解这两者是构建可扩展后端的关键。

## 🌐 公共部分

> 以下主题的**通用原理**已抽取到 [`../../_common/`](../../_common/) 目录。

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Redis 数据结构 / 持久化 / 集群 | [_common/01-redis](../../_common/01-redis/) | 13-redis-in-dify.md（dify 实战） |
| 消息队列概念 / Kafka / RabbitMQ | [_common/02-mq](../../_common/02-mq/) | 23-mq-concepts.md（概念补充） |
| 缓存穿透 / 击穿 / 雪崩 | [_common/03-cache-patterns/02-three-problems](../../_common/03-cache-patterns/02-three-problems.md) | 09-cache-problems.md（dify 处理） |
| 分布式锁 | [_common/04-distributed-locks/02-redis-redlock](../../_common/04-distributed-locks/02-redis-redlock.md) | 10-distributed-lock.md（dify 实现） |
| 限流 | [_common/03-cache-patterns/04-rate-limiting](../../_common/03-cache-patterns/04-rate-limiting.md) | 11-rate-limit-redis.md（dify 实现） |

## 前置依赖

- `01-fundamentals` 全部
- `02-backend` 的 DDD 分层基础

## 模块 4.1 Redis 基础

- [ ] [1.1 Redis 数据结构：String / Hash / List / Set / Sorted Set](./01-redis-data-structures.md)
- [ ] [1.2 Redis 持久化：RDB / AOF](./02-redis-persistence.md)
- [ ] [1.3 Redis 主从复制与 Sentinel](./03-redis-replication.md)
- [ ] [1.4 Redis Cluster 集群模式](./04-redis-cluster.md)
- [ ] [1.5 Redis 内存淘汰策略](./05-redis-eviction.md)
- [ ] [1.6 Redis 事务与 Lua 脚本](./06-redis-transaction.md)
- [ ] [1.7 Redis Python 客户端：`redis-py`](./07-redis-py.md)

## 模块 4.2 Redis 应用场景

- [ ] [2.1 Redis 作为缓存：缓存策略与失效](./08-redis-cache.md)
- [ ] [2.2 缓存穿透 / 击穿 / 雪崩](./09-cache-problems.md)
- [ ] [2.3 分布式锁：RedLock 与 `SETNX`](./10-distributed-lock.md)
- [ ] [2.4 限流：滑动窗口 / 令牌桶](./11-rate-limit-redis.md)
- [ ] [2.5 Session 与 Token 存储](./12-session-storage.md)
- [ ] [2.6 dify 中 Redis 的使用场景分析](./13-redis-in-dify.md)

## 模块 4.3 Celery 异步任务

- [ ] [3.1 Celery 架构：Broker / Worker / Beat / Result Backend](./14-celery-architecture.md)
- [ ] [3.2 任务定义：@shared_task 与绑定](./15-celery-tasks.md)
- [ ] [3.3 任务调用：`delay` / `apply_async` / 任务签名](./16-celery-invoke.md)
- [ ] [3.4 任务路由与队列优先级](./17-celery-routing.md)
- [ ] [3.5 定时任务：Celery Beat 调度](./18-celery-beat.md)
- [ ] [3.6 任务结果存储与查询](./19-celery-result.md)
- [ ] [3.7 任务幂等性设计](./20-celery-idempotency.md)
- [ ] [3.8 任务重试与死信队列](./21-celery-retry.md)
- [ ] [3.9 dify 的 `async_workflow_service` 与任务分发](./22-celery-in-dify.md)

## 模块 4.4 消息队列与事件流

- [ ] [4.1 消息队列核心概念：Producer / Consumer / Topic](./23-mq-concepts.md)
- [ ] [4.2 Kafka 入门](./24-kafka-basics.md)
- [ ] [4.3 RabbitMQ 入门](./25-rabbitmq-basics.md)
- [ ] [4.4 Redis Pub/Sub 与 Stream](./26-redis-pubsub-stream.md)
- [ ] [4.5 事件驱动架构（EDA）](./27-event-driven.md)

## 🎯 dify 仓库对应位置

- Redis 扩展：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- 异步任务：`/Users/xu/code/github/dify/api/tasks/`
- 任务分发：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- Celery 配置：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
- Celery 入口：`/Users/xu/code/github/dify/api/celery_entrypoint.py`
