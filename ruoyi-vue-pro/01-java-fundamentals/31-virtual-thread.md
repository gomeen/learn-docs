# 1.4.8 虚拟线程（Java 21 / Project Loom）

> 理解虚拟线程的设计动机与原理，能识别其适用场景与局限，为 Java 21 升级做准备。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解虚拟线程与传统平台线程的本质差异
- 知道何时应该（不应该）使用虚拟线程
- 能用 `Thread.ofVirtual()` 和 `Executors.newVirtualThreadPerTaskExecutor()` 编写虚拟线程代码
- 识别 ruoyi-vue-pro 现有架构中哪些场景能受益于虚拟线程

## 📚 前置知识

- [21-thread.md](./21-thread.md)：线程基础
- [22-thread-pool.md](./22-thread-pool.md)：线程池
- [18-jvm-memory.md](./18-jvm-memory.md)：JVM 内存模型

> **重要**：ruoyi-vue-pro 当前 `main` 分支基于 **JDK 8 / Spring Boot 2.7**，虚拟线程需 JDK 21+（且依赖 Spring Boot 3.2+ 的 `spring.threads.virtual.enabled=true` 自动配置）。本节为前瞻性内容。

## 1. 核心概念

### 1.1 平台线程的瓶颈

```
┌──────────────────────────────────────────────┐
│ 平台线程（Platform Thread）= OS 线程 1:1     │
├──────────────────────────────────────────────┤
│ 线程栈：1 MB（默认）                         │
│ 上下文切换：OS 调度，几微秒                   │
│ 阻塞 I/O：线程挂起，占着栈空间不释放         │
│ 数量上限：几千到几万（受 OS / 内存限制）     │
└──────────────────────────────────────────────┘

问题：每个 HTTP 请求占一个线程处理 I/O 等待
     → 1 万并发请求 = 1 万线程 = 10 GB 栈空间
     → C10K（1 万并发）问题难解
```

### 1.2 虚拟线程的解决方案

```
┌──────────────────────────────────────────────┐
│ 虚拟线程（Virtual Thread）= JVM 用户态线程    │
├──────────────────────────────────────────────┤
│ 线程栈：几百字节（堆上分配）                 │
│ 上下文切换：JVM 调度，几纳秒                  │
│ 阻塞 I/O：释放载体线程，处理其他虚拟线程     │
│ 数量上限：百万级（受堆内存限制）             │
└──────────────────────────────────────────────┘

原理：M:N 调度（M 个虚拟线程 → N 个载体线程，通常 N = CPU 核数）
```

**关键设计**：
- **M:N 调度**：N 个 OS 线程（载体线程，Carrier Thread）承载 M 个虚拟线程
- **Continuation**：虚拟线程被阻塞时，JVM 把它的栈从载体线程"卸载"到堆；I/O 完成后重新"挂载"回某个载体线程
- **无对象池**：每个虚拟线程用完即丢，无线程池复用（因为创建成本极低）

### 1.3 虚拟线程 vs 平台线程 vs Goroutine

| 维度 | 平台线程（Java） | 虚拟线程（Java 21） | Goroutine（Go） |
|------|-----------------|---------------------|------------------|
| 模型 | 1:1 OS | M:N | M:N |
| 栈空间 | 1 MB（OS） | 几百字节（堆） | 几 KB（动态增长） |
| 创建成本 | ~1 ms | ~1 μs | ~1 μs |
| 上限 | 几千~几万 | 百万级 | 百万级 |
| 调度方 | OS | JVM ForkJoinPool | Go runtime |
| 阻塞处理 | OS 线程挂起 | Continuation 卸载 | goroutine 挂起 |

### 1.4 何时该用虚拟线程

**✅ 适合**：
- **I/O 密集型**：HTTP 请求、数据库查询、消息队列消费
- **高并发**：Web 服务器、API 网关
- **简单线程代码**：替代原来的 `Thread.start()` 或单线程 Executor

**❌ 不适合**：
- **CPU 密集型**：虚拟线程无法让 CPU 密集任务变快（CPU 核数是物理上限）
- **使用 `synchronized` 阻塞**：JDK 21 修复了大部分 `synchronized` 与虚拟线程的兼容问题，但仍有边界情况
- **使用 JNI / 第三方 native 阻塞调用**：虚拟线程在 native 阻塞时仍占着载体线程
- **线程局部变量（ThreadLocal）过多**：每个虚拟线程都有自己的 ThreadLocal 副本

### 1.5 JDK 21 虚拟线程的语法

#### 1.5.1 创建虚拟线程

```java
// 方式 1：直接启动
Thread.startVirtualThread(() -> {
    System.out.println("Hello from virtual thread");
});

// 方式 2：Builder 模式（可命名）
Thread vThread = Thread.ofVirtual()
        .name("vt-", 0)         // 前缀，自动追加 0,1,2...
        .start(() -> doWork());

// 方式 3：创建不启动
Thread unstarted = Thread.ofVirtual()
        .name("my-vt")
        .unstarted(() -> doWork());
unstarted.start();
```

#### 1.5.2 虚拟线程池

```java
// 每次任务一个虚拟线程（替代 newCachedThreadPool）
ExecutorService vPool = Executors.newVirtualThreadPerTaskExecutor();

Future<String> future = vPool.submit(() -> {
    return callExternalApi();   // 阻塞调用会释放载体线程
});

// 不用 shutdown（虚拟线程用完即丢）
```

#### 1.5.3 ThreadFactory 集成（兼容 Spring 等框架）

```java
ThreadFactory factory = Thread.ofVirtual()
        .name("vt-", 0)
        .factory();

ExecutorService pool = Executors.newFixedThreadPool(10, factory);
// 但固定 10 个虚拟线程没意义，应该用 newVirtualThreadPerTaskExecutor
```

### 1.6 Spring Boot 3.2+ 集成

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true   # 自动用虚拟线程处理 HTTP 请求
```

```java
// 显式使用
@Bean
public TomcatProtocolHandlerCustomizer<?> virtualThreadCustomizer() {
    return protocolHandler -> {
        protocolHandler.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
    };
}
```

**Tomcat**：从 Spring Boot 3.2 起，Tomcat 的请求处理线程默认就是虚拟线程（开启 `spring.threads.virtual.enabled=true` 后）。

### 1.7 synchronized 与虚拟线程

JDK 21 之前，`synchronized` 阻塞会"钉住"（pin）载体线程，破坏 M:N 调度优势。JDK 21 通过 **JEP 491** 修复了大部分场景，但仍需注意：

```java
// ❌ 仍可能 pin 住载体线程的边界场景
synchronized (someMonitor) {
    // 调用 native 方法（如某些 JNI）
    nativeBlockingCall();
}

// ✅ 优先用 ReentrantLock 替代 synchronized
ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    // 不会被 pin
} finally {
    lock.unlock();
}
```

## 2. 代码示例

### 2.1 基础：虚拟线程 + HTTP 请求

```java
// 文件：VirtualThreadHttpDemo.java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;

public class VirtualThreadHttpDemo {
    public static void main(String[] args) throws Exception {
        // JDK 11+ HttpClient（支持异步）
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();

        // 创建虚拟线程池：每个 HTTP 请求一个虚拟线程
        ExecutorService vPool = Executors.newVirtualThreadPerTaskExecutor();

        // 并发请求 100 个 URL
        List<Future<String>> futures = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            final int id = i;
            futures.add(vPool.submit(() -> {
                HttpRequest req = HttpRequest.newBuilder()
                        .uri(URI.create("https://api.example.com/data/" + id))
                        .timeout(Duration.ofSeconds(10))
                        .build();
                HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
                return "Task " + id + ": " + resp.statusCode();
            }));
        }

        // 收集结果
        for (Future<String> f : futures) {
            System.out.println(f.get());
        }
    }
}
```

### 2.2 平台线程 vs 虚拟线程对比

```java
// 文件：PlatformVsVirtual.java
import java.util.concurrent.*;

public class PlatformVsVirtual {
    public static void main(String[] args) throws Exception {
        int taskCount = 10_000;

        // 1. 平台线程池：100 个线程处理 10000 任务 → 每个任务平均等 100 个槽位
        long start1 = System.currentTimeMillis();
        ExecutorService platformPool = Executors.newFixedThreadPool(100);
        CountDownLatch latch1 = new CountDownLatch(taskCount);
        for (int i = 0; i < taskCount; i++) {
            platformPool.submit(() -> {
                try { Thread.sleep(100); } catch (InterruptedException e) {}
                latch1.countDown();
            });
        }
        latch1.await();
        long time1 = System.currentTimeMillis() - start1;
        platformPool.shutdown();

        // 2. 虚拟线程池：每个任务一个虚拟线程 → 几乎瞬时启动
        long start2 = System.currentTimeMillis();
        ExecutorService vPool = Executors.newVirtualThreadPerTaskExecutor();
        CountDownLatch latch2 = new CountDownLatch(taskCount);
        for (int i = 0; i < taskCount; i++) {
            vPool.submit(() -> {
                try { Thread.sleep(100); } catch (InterruptedException e) {}
                latch2.countDown();
            });
        }
        latch2.await();
        long time2 = System.currentTimeMillis() - start2;

        System.out.println("平台线程 100 线程: " + time1 + " ms");  // ~10 秒
        System.out.println("虚拟线程:           " + time2 + " ms");  // ~0.1 秒
    }
}
```

### 2.3 虚拟线程 + StructuredTaskScope（结构化并发，JDK 21+）

```java
// 文件：StructuredConcurrencyDemo.java
import java.util.concurrent.*;

public class StructuredConcurrencyDemo {
    public static void main(String[] args) throws Exception {
        // 同时调用 3 个外部服务，任一失败就取消其他
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            var userFuture = scope.fork(() -> callUserService());
            var orderFuture = scope.fork(() -> callOrderService());
            var productFuture = scope.fork(() -> callProductService());

            scope.join();              // 等待所有子任务完成
            scope.throwIfFailed();    // 任一失败就抛异常

            // 全部成功，获取结果
            User user = userFuture.get();
            Order order = orderFuture.get();
            Product product = productFuture.get();
            System.out.println("User: " + user + ", Order: " + order + ", Product: " + product);
        }
    }

    // 模拟方法
    static User callUserService() { return new User(); }
    static Order callOrderService() { return new Order(); }
    static Product callProductService() { return new Product(); }

    static class User {}
    static class Order {}
    static class Product {}
}
```

## 3. ruoyi-vue-pro 仓库源码解读

> ruoyi-vue-pro 当前 `main` 分支基于 JDK 8 / Spring Boot 2.7，**没有虚拟线程相关代码**。本节将基于 `jdk21` 分支（社区维护）和未来升级场景进行分析。

### 3.1 升级到 JDK 21 后的潜在改造点

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yml`
**改造示例**（jdk21 分支启用虚拟线程）：

```yaml
spring:
  threads:
    virtual:
      enabled: true   # ← 新增：所有 HTTP 请求用虚拟线程处理
```

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**改造示例**（自定义异步任务执行器）：

```java
/**
 * JDK 21+ 版本：用虚拟线程池替代平台线程池
 */
@Bean
public AsyncTaskExecutor applicationTaskExecutor() {
    // 每个 @Async 任务一个虚拟线程
    return new TaskExecutorAdapter(Executors.newVirtualThreadPerTaskExecutor());
}
```

### 3.2 异步任务（MQ 消费者）的虚拟线程改造

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/stream/AbstractStreamMessageListener.java`（典型 Redis Stream 消费者）

**改造方向**：

```java
// JDK 8 / Spring Boot 2.7 版本：固定大小平台线程池
@Bean
public ThreadPoolTaskExecutor redisStreamExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(8);
    executor.setMaxPoolSize(16);
    executor.setQueueCapacity(1000);
    return executor;
}

// JDK 21+ 改造：虚拟线程池
@Bean
public AsyncTaskExecutor redisStreamExecutor() {
    return new TaskExecutorAdapter(Executors.newVirtualThreadPerTaskExecutor());
    // 无需设置 corePoolSize/maxPoolSize：虚拟线程按需创建
}
```

**解读**：
- ruoyi-vue-pro 的 MQ 消费者处理 I/O 密集任务（DB 查询 + HTTP 调用），正是虚拟线程的最佳场景
- **改造成本低**：只需替换 `ThreadPoolTaskExecutor` 为 `Executors.newVirtualThreadPerTaskExecutor`
- **收益**：消费者并发数可从 16 → 数千，MQ 处理能力大幅提升

### 3.3 ruoyi 现有架构的虚拟线程适配分析

| 模块 | 当前实现 | 虚拟线程适配 |
|------|---------|-------------|
| **HTTP 请求处理** | Tomcat 线程池（默认 200） | `spring.threads.virtual.enabled=true` 自动启用 |
| **`@Async` 任务** | `ThreadPoolTaskExecutor` | 替换为 `Executors.newVirtualThreadPerTaskExecutor` |
| **MQ 消费者** | `MessageListenerContainer` | 同上 |
| **定时任务** | Quartz 线程池 | 不适合（任务少且非阻塞） |
| **Netty / Redis 客户端** | 独立的事件循环 | 不适合（已经是异步） |
| **ThreadLocal（TTL）** | TransmittableThreadLocal | 虚拟线程场景下仍是 TTL，因为 TTL 是框架无关的 |

> ⚠️ ruoyi-vue-pro 的 `TransmittableThreadLocal` 在虚拟线程下仍有效，但需要 JDK 21+ 的 `-Djdk.tracePinnedThreads=full` 排查 `synchronized` 阻塞导致的 pinning 问题。

## 4. 关键要点总结

- **虚拟线程**是 Java 21 引入的轻量级线程，M:N 调度，栈在堆上分配
- **核心价值**：用同步代码风格写出高并发 I/O 应用，免去回调地狱
- **适用场景**：HTTP 请求、DB 查询、MQ 消费等 I/O 密集任务
- **不适用**：CPU 密集任务、`synchronized` + native、JNI 阻塞
- **创建成本极低**：~1μs（vs 平台线程 ~1ms），可百万级并发
- **ruoyi-vue-pro 当前 main 分支是 JDK 8**，需升级到 `jdk21` 分支或自行升级才能享受虚拟线程

## 5. 练习题

### 练习 1：基础（必做）

写一个 HTTP 客户端，并发请求 1000 个 URL：
- 用 `Executors.newFixedThreadPool(100)` 实现
- 用 `Executors.newVirtualThreadPerTaskExecutor()` 实现（需 JDK 21+）
- 对比两者的吞吐量和内存占用

### 练习 2：进阶

阅读 Spring Boot 3.2 的 `spring.threads.virtual.enabled` 实现原理（源码 `org.springframework.boot.autoconfigure.task.TaskExecutionAutoConfiguration`），画出请求从 Tomcat 进入虚拟线程池的完整链路。

### 练习 3：挑战（选做）

在 ruoyi-vue-pro 上做一次"虚拟线程改造 POC"：
1. 把 JDK 升级到 21
2. 启用 `spring.threads.virtual.enabled=true`
3. 把 `@Async` 执行器改为虚拟线程池
4. 用 wrk/JMeter 压测，对比改造前后的 QPS 和 P99 延迟

## 6. 参考资料

- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)（JDK 21）
- [JEP 453: Structured Concurrency (Preview)](https://openjdk.org/jeps/453)
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491)（JDK 24）
- [Spring Boot 3.2 虚拟线程支持](https://spring.io/blog/2023/09/09/spring-boot-3-2-0-available-now)
- 《Java 21 虚拟线程官方教程》：[https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)
- ruoyi-vue-pro jdk21 分支（社区维护）

---

**文档版本**：v1.0
**最后更新**：2026-07-13