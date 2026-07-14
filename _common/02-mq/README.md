# 02 - 消息队列

> 后端异步通信的核心组件，跨语言通用的消息队列知识。

## 知识点

- [ ] [2.1 消息队列核心概念：Producer / Consumer / Topic / Queue](./01-concepts.md)
- [ ] [2.2 Kafka 原理与实战](./02-kafka.md)
- [ ] [2.3 RabbitMQ 原理与实战](./03-rabbitmq.md)
- [ ] [2.4 RocketMQ 原理与实战](./04-rocketmq.md)
- [ ] [2.5 消息可靠性：至少一次 / 最多一次 / 恰好一次](./05-reliability.md)
- [ ] [2.6 死信队列与重试机制](./06-dead-letter.md)

## 🔗 项目特定实现

- **dify（Python）**：用 Celery（不是标准 MQ），详见 [`../../dify/04-cache-and-queue/14-celery-architecture.md`](../../dify/04-cache-and-queue/14-celery-architecture.md)
- **ruoyi（Java）**：抽象了 4 种 MQ 的统一接口 [`../../ruoyi-vue-pro/05-cache-and-mq/13-ruoyi-message.md`](../../ruoyi-vue-pro/05-cache-and-mq/13-ruoyi-message.md)
