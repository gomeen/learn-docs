# 小验证：Redisson 与工具类

> 覆盖：
- [Redisson 客户端](./01-redisson.md)
- [分布式锁](./03-redisson-lock.md)
- [限流](./04-redisson-rate-limiter.md)
- [分布式集合](./05-redisson-collections.md)
- [ruoyi RedisUtils](./06-ruoyi-redis-utils.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

本阶段文档侧重 ruoyi 视角的 Redisson 能力；用锁、限流、集合做闭环。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` + Redis：

1. 用 RedisUtils/Redisson 完成 string + hash 读写。
2. 用 RLock 保护“库存 -1”伪代码（内存变量即可），多线程下不为负。
3. RRateLimiter：2 permits/秒，突发 5 次请求，记录成功/失败。
4. 使用 RMap 或 RBucket 存一个小对象，设置过期。

## 提示

- 锁 key 加业务前缀。
- 注意序列化一致。

## 验收标准

- [ ] 基础读写通过
- [ ] 并发扣减不为负
- [ ] 限流表现符合预期
- [ ] 过期 key 自动消失可验证
- [ ] 指出 RedisUtils 主要封装点

## 延伸（选做）

- 试 Redisson 公平锁与非公平锁差异。
- 用 RTopic 做一次 pub/sub 日志。
