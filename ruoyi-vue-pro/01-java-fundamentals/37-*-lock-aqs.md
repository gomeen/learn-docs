# 小验证：锁 / 原子类 / AQS / ThreadLocal

> 覆盖：
- [锁机制](./33-lock.md)
- [原子类](./34-atomic.md)
- [AQS](./35-aqs.md)
- [ThreadLocal](./36-threadlocal.md)
>
> 预计：30～45 分钟 · 本地练习或对照 ruoyi-vue-pro

## 背景

会选锁与原子工具，并正确使用 ThreadLocal 上下文（对应 ruoyi 的 Holder 清理模式）。

## 需求

本地完成一个「简易访问统计器」：

1. `ConcurrentHashMap<String, AtomicLong>` 记录 path → 命中次数；多线程 `incrementAndGet`。
2. 提供 `snapshot()`：在读多写少场景下用 `ReentrantReadWriteLock` 保护一份周期性拷贝的 `Map` 快照（或说明为何 CHM 本身可无锁读）。
3. 用 `ThreadLocal<String>` 模拟 `traceId`：入口 set，业务方法读取并写入日志，finally remove。
4. 起多线程验证计数总和正确；日志中不同线程 traceId 隔离。
5. 简短注释：AQS 与 `ReentrantLock` 的关系；`LongAdder` 何时更合适。

## 提示

- ThreadLocal 必须 `remove`，对应 ruoyi 的 `TenantContextHolder` 等清理模式。
- 对照文档理解 AQS 即可，不必手写 AQS。
- 在 ruoyi 中指出一处 ThreadLocal / 上下文 Holder。

## 验收标准

- [ ] 多线程计数总和精确正确
- [ ] 使用了 Atomic*（或 LongAdder）与某种显式锁
- [ ] ThreadLocal 在 finally 中清理，线程隔离可证
- [ ] AQS / LongAdder 有简短注释
- [ ] 能指出 ruoyi 中一处 Holder 用途

## 延伸（选做）

- 用 JMH 或简单计时对比 AtomicLong vs LongAdder。
- 阅读一次 `ReentrantLock` 源码中 sync 内部类（不必写长文）。
