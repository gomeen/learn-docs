# 小验证：GC 调优视角与并发集合

> 覆盖：
- [GC 详解](./29-jvm-gc-detail.md)
- [JVM 调优](./30-jvm-tuning.md)
- [并发集合](./31-concurrent-collections.md)
>
> 预计：30～45 分钟 · 本地练习

## 背景

从“会写多线程”进到“会看 GC、会选并发集合”。本验证用 CHM 压一点负载，并会读基础 GC 日志。

## 需求

本地完成：

1. 用 `ConcurrentHashMap<String, Long>`（或 `LongAdder` 值）模拟 path 计数；8 线程各循环 1 万次随机 path 自增，总和应为 `8 * 10000`。
2. 对比注释：若改成无同步 `HashMap` 在多线程下可能出现什么问题。
3. 用 `-Xms`/`-Xmx`/`-XX:+PrintGCDetails`（或 JDK 9+ ` -Xlog:gc*`）跑一小段分配密集代码，截取/记录一段 GC 日志。
4. 书面说明：G1 与 Parallel 各适合什么粗略场景（3～5 行）；本机默认收集器是什么（`java -XX:+PrintCommandLineFlags -version` 或文档）。
5. 说明为何 `CopyOnWriteArrayList` 不适合高频写计数场景。

## 提示

- 验证总和时不要在遍历 CHM 的同时无协调地 clear。
- GC 参数因 JDK 版本略有差异，以本机为准。
- 不必深入源码，能对照文档解释日志字段即可。

## 验收标准

- [ ] 多线程计数总和精确正确
- [ ] 使用了 ConcurrentHashMap（或等价并发结构）
- [ ] 有一段 GC 日志或启动参数记录
- [ ] 收集器选型有简短说明
- [ ] COW 与 CHM 适用场景对比到位

## 延伸（选做）

- 用简单计时对比 `AtomicLong` 与 `LongAdder`。
- 阅读一次 G1 区域（Region）概念对照文档。
