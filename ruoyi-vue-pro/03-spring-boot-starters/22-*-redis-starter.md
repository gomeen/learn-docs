# 小验证：Redis Starter / Redisson / 分布式锁 / 限流

> 覆盖：
- [redis starter](./17-redis-starter.md)
- [Redisson](./18-redisson.md)
- [RedisUtils](./19-redis-utils.md)
- [分布式锁](./20-distributed-lock.md)
- [限流](./21-rate-limiter.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

ruoyi 缓存与锁基本建立在 Redisson 之上。用真实 Redis 做一次锁与限流验证。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` + 本地 Redis：

1. 使用项目 `RedisUtils` 或 `StringRedisTemplate`/`RedissonClient`：set 一个 key，设置 TTL，get 验证。
2. **分布式锁**：写一段双线程/双实例逻辑，抢同一把锁执行临界区（sleep 1s），证明同一时刻只有一个执行（日志时间戳）。
3. **限流**：用 Redisson `RRateLimiter` 或项目封装，配置每秒 2 次，连续请求 5 次，观察后 3 次失败或阻塞。
4. 阅读 starter 中 Redisson 的自动配置类，记录编解码与 key 前缀相关配置。

## 提示

- 锁一定要在 finally unlock，或用 tryLock 超时。
- 注意项目是否统一加了 key 前缀。
- 限流器名称不要与线上关键业务冲突。

## 验收标准

- [ ] Redis 读写 + TTL 验证通过
- [ ] 锁互斥日志可证明
- [ ] 限流行为符合配置（允许轻微边界误差）
- [ ] 记录 Redisson 自动配置类路径
- [ ] 说明锁续期（看门狗）是否开启及影响

## 延伸（选做）

- 用 `@RateLimiter` 类注解（若项目有）挂到 demo 接口。
- 对比 setnx 手写锁与 Redisson 锁的差异。
