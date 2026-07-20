# 04 - 缓存与消息队列

> Dify 使用 Redis 做缓存 + Celery 做异步任务，理解这两者是构建可扩展后端的关键。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

> 以下主题的**通用原理**已抽取到 [`../../_common/`](../../_common/) 目录。本阶段本地仅保留 dify 侧正文与 Celery/事件相关篇。

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Redis 数据结构 / 持久化 / 集群 | [`_common/01-redis`](../../_common/01-redis/) | [13-redis-in-dify](./01-redis-in-dify.md) |
| 消息队列概念 / Kafka / RabbitMQ | [`_common/02-mq`](../../_common/02-mq/) | 23–26 等（待补） |
| 缓存穿透 / 击穿 / 雪崩 | [`_common/03-cache-patterns/02-three-problems`](../../_common/03-cache-patterns/02-three-problems.md) | 09（待补） |
| 分布式锁 | [`_common/04-distributed-locks/02-redis-redlock`](../../_common/04-distributed-locks/02-redis-redlock.md) | 10（待补） |
| 限流 | [`_common/03-cache-patterns/04-rate-limiting`](../../_common/03-cache-patterns/04-rate-limiting.md) | 11（待补） |

## 前置依赖

- `01-fundamentals` 全部
- `02-backend` 的 DDD 分层基础

## 模块 4.1 Redis 基础

- [ ] [1.1 Redis 数据结构：String / Hash / List / Set / Sorted Set](../../_common/01-redis/01-data-structures.md)
- [ ] [1.2 Redis 持久化：RDB / AOF](../../_common/01-redis/02-persistence.md)
- [ ] [1.3 Redis 主从复制与 Sentinel](../../_common/01-redis/03-replication-sentinel.md)
- [ ] [1.4 Redis Cluster 集群模式](../../_common/01-redis/04-cluster.md)
- [ ] [1.5 Redis 内存淘汰策略](../../_common/01-redis/05-eviction.md)
- [ ] [1.6 Redis 事务与 Lua 脚本](./02-redis-transaction.md)
- [ ] [1.7 Redis Python 客户端：`redis-py`](./03-redis-py.md)

## 模块 4.2 Redis 应用场景

- [ ] [2.1 Redis 作为缓存：缓存策略与失效](../../_common/03-cache-patterns/01-strategies.md)
- [ ] [2.2 缓存穿透 / 击穿 / 雪崩](../../_common/03-cache-patterns/02-three-problems.md)
- [ ] [2.3 分布式锁：RedLock 与 `SETNX`](../../_common/04-distributed-locks/02-redis-redlock.md)
- [ ] [2.4 限流：滑动窗口 / 令牌桶](../../_common/03-cache-patterns/04-rate-limiting.md)
- [ ] [2.5 Session 与 Token 存储](../../_common/03-cache-patterns/05-distributed-session.md)
- [ ] [2.6 dify 中 Redis 的使用场景分析](./01-redis-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [04-*-redis: Redis 事务/客户端与 dify 用法](./04-*-redis.md)
  - 覆盖：02-redis-transaction.md, 03-redis-py.md, 01-redis-in-dify.md


## 模块 4.3 Celery 异步任务

- [ ] [3.1 Celery 架构：Broker / Worker / Beat / Result Backend](./05-celery-architecture.md)
- [ ] [3.2 任务定义：@shared_task 与绑定](./06-celery-tasks.md)
- [ ] [3.3 任务调用：`delay` / `apply_async` / 任务签名](./07-celery-invoke.md)
- [ ] [3.4 任务路由与队列优先级](./08-celery-routing.md)
- [ ] [3.5 定时任务：Celery Beat 调度](./09-celery-beat.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [10-*-celery-and-events: Celery 架构到 Beat](./10-*-celery-and-events.md)
  - 覆盖：05-celery-architecture.md, 06-celery-tasks.md, 07-celery-invoke.md, 08-celery-routing.md, 09-celery-beat.md


- [ ] [3.6 任务结果存储与查询](./11-celery-result.md)
- [ ] [3.7 任务幂等性设计](./12-celery-idempotency.md)
- [ ] [3.8 任务重试与死信队列](./13-celery-retry.md)
- [ ] [3.9 dify 的 `async_workflow_service` 与任务分发](./14-celery-in-dify.md)

## 模块 4.4 消息队列与事件流

- [ ] [4.1 消息队列核心概念：Producer / Consumer / Topic](../../_common/02-mq/01-concepts.md)
- [ ] [4.2 Kafka 入门](../../_common/02-mq/02-kafka.md)
- [ ] [4.3 RabbitMQ 入门](../../_common/02-mq/03-rabbitmq.md)
- [ ] [4.4 Redis Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)
- [ ] [4.5 事件驱动架构（EDA）](./15-event-driven.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [16-*-celery-reliability-events: Celery 结果/幂等/重试与事件驱动](./16-*-celery-reliability-events.md)
  - 覆盖：11-celery-result.md, 12-celery-idempotency.md, 13-celery-retry.md, 14-celery-in-dify.md, 15-event-driven.md, 15-event-driven.md

- 4.x 本仓补充文（若有）：08–12、23–26 等（待补）

## 🎯 dify 仓库对应位置

- Redis 扩展：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- 异步任务：`/Users/xu/code/github/dify/api/tasks/`
- 任务分发：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- Celery 配置：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
- Celery 入口：`/Users/xu/code/github/dify/api/celery_entrypoint.py`
