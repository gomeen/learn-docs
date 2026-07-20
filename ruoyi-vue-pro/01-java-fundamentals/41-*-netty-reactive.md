# 小验证：Netty 与响应式入门

> 覆盖：
- [虚拟线程](./38-virtual-thread.md)
- [Netty](./39-netty.md)
- [Reactor / 响应式](./40-reactive.md)
>
> 预计：60～90 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

ruoyi 本体偏 Servlet，但中间件/网关/消息场景会碰到 Netty 与响应式概念。本验证做最小可运行示例。

## 需求

任选 **A 或 B**（推荐 A+B 都做，时间不够做 A）：

**A. Netty Echo**
1. 写一个 Netty Server：监听本地端口，收到文本后回显 `ECHO: ` 前缀。
2. 用 `telnet`/`nc` 或小 Client 验证往返。

**B. Reactor 管道**
1. 用 `Flux.range` 生成 1..20，`filter` 偶数，`map` 平方，`collectList` 阻塞取结果。
2. 再写一个 `Mono.fromCallable` 模拟 IO（sleep），`subscribeOn(Schedulers.boundedElastic())`，主线程订阅并打印线程名差异。

**虚拟线程（若 JDK 21+）**
3. 用 `Executors.newVirtualThreadPerTaskExecutor()` 提交 1000 个 sleep 任务，对比平台线程池的创建耗时（数量级即可）。

## 提示

- Netty 别忘了 `boss/worker` 与 `shutdownGracefully`。
- Reactor 依赖 `io.projectreactor:reactor-core`。
- 虚拟线程示例在低版本 JDK 可跳过并在验收中注明。

## 验收标准

- [ ] （A）Echo 服务可本地连通并正确回显
- [ ] （B）Flux 结果为偶数平方列表
- [ ] （B）能观察到 callable 与主线程线程名不同（或有等价证明）
- [ ] 资源（EventLoopGroup / Executor）正确关闭
- [ ] 用 3 句话说明这些技术与 ruoyi-vue-pro 主路径的关系（主路径是否必需）

## 延伸（选做）

- Netty pipeline 加一个简单的字符串解码/编码器。
- 用 WebClient（若引入 Spring WebFlux）访问一个公共 HTTP API。
