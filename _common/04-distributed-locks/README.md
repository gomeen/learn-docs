# 04 - 分布式锁

> 分布式系统的并发控制核心，跨语言通用的分布式锁原理与实现。

## 知识点

- [ ] [4.1 分布式锁的核心要求：互斥 / 安全 / 死锁 / 容错](./01-requirements.md)
- [ ] [4.2 Redis 分布式锁：SETNX / RedLock 原理与争议](./02-redis-redlock.md)
- [ ] [4.3 Zookeeper / etcd 分布式锁对比](./03-zookeeper-etcd.md)

## 🔗 项目特定实现

- **dify（Python）**：[`../../dify/04-cache-and-queue/10-distributed-lock.md`](../../dify/04-cache-and-queue/10-distributed-lock.md)
- **ruoyi（Java）**：[`../../ruoyi-vue-pro/05-cache-and-mq/03-redisson-lock.md`](../../ruoyi-vue-pro/05-cache-and-mq/03-redisson-lock.md)（基于 Redisson）
