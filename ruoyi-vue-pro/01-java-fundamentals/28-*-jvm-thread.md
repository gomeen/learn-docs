# 小验证：JVM / 线程 / 线程池 / JUC 基础

> 覆盖：
- [JVM 内存模型](./22-jvm-memory.md)
- [GC 基础](./23-gc.md)
- [类加载](./24-classloader.md)
- [线程基础](./25-thread.md)
- [线程池](./26-thread-pool.md)
- [JUC 工具类](./27-juc.md)
>
> 预计：60～90 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

把“内存/GC/类加载”的概念落到可观测现象，并用线程池 + CountDownLatch 完成一次并发批处理。

## 需求

本地完成：

1. 写一段故意创建大量短期对象的程序，用 JVM 参数 `-Xms64m -Xmx64m -XX:+PrintGCDetails`（或 `-Xlog:gc*`，按 JDK 版本）跑一遍，截取/记录至少一次 Young GC。
2. 用 `ClassLoader` API 打印当前类的加载器与父加载器链（Bootstrap 可用 null 表示）。
3. 实现任务批处理：
   - 固定线程池（core=4, max=4, queue=ArrayBlockingQueue(10), 拒绝策略 `CallerRunsPolicy`）
   - 提交 50 个任务，每个任务 sleep 50～100ms 后返回任务编号
   - 用 `CountDownLatch` 或 `invokeAll` 等待全部完成
4. 统计成功数与耗时；故意把 queue 调小并提交更多任务，观察拒绝策略是否触发（日志可证）。

## 提示

- JDK 9+ GC 日志参数是 `-Xlog:gc*`，不是 `PrintGCDetails`。
- 线程池务必 `shutdown()` + `awaitTermination`。
- 不要用 `Executors.newFixedThreadPool` 的无界队列做本验证结论。

## 验收标准

- [ ] 能展示一次 GC 日志片段，并指出堆相关参数
- [ ] 类加载器链打印正确
- [ ] 50 任务全部完成，线程池正常关闭
- [ ] 拒绝策略触发场景有日志或注释说明
- [ ] 用 3～5 句话说明 ruoyi 业务代码一般如何使用线程池（可结合文档）

## 延伸（选做）

- 改用 `CompletableFuture` 汇总结果。
- 用 `jcmd` 或 `jmap` 看一次堆摘要。
