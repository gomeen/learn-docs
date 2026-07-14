# 1.3.5 线程池：ExecutorService

> 掌握 Java 线程池的核心参数、工作原理与拒绝策略，能在 Spring Boot 中合理配置 `@Async` 的线程池。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 `ThreadPoolExecutor` 的 7 大核心参数
- 描述线程池工作流程（任务提交 → 核心线程 → 队列 → 最大线程 → 拒绝策略）
- 区分 4 种内置线程池（Fixed / Cached / Single / Scheduled）的使用场景
- 能在 Spring Boot 项目中配置自定义线程池

## 📚 前置知识

- Thread / Runnable / Callable 基础
- 21-thread.md

## 1. 核心概念

### 1.1 为什么需要线程池？

直接 `new Thread()` 的问题：
- 创建 / 销毁线程开销大
- 大量线程竞争 CPU / 内存，可能 OOM
- 无法限制并发数

线程池的价值：**资源复用 + 控制并发 + 统一异常处理**。

### 1.2 `ThreadPoolExecutor` 7 大参数

```java
new ThreadPoolExecutor(
    corePoolSize,          // 核心线程数（即使空闲也不回收）
    maximumPoolSize,       // 最大线程数（包含 core）
    keepAliveTime,         // 非核心线程的空闲存活时间
    unit,                  // 时间单位
    workQueue,             // 任务队列
    threadFactory,         // 线程创建工厂（通常 NamedThreadFactory）
    rejectedExecutionHandler // 拒绝策略
);
```

### 1.3 工作流程

```
提交任务
   ↓
核心线程数未满 → 新建 core 线程执行
   ↓ 满了
进入队列等待
   ↓ 队列也满了
未达 max 线程 → 新建非 core 线程执行
   ↓ 达到 max
触发拒绝策略
```

**关键点**：
- 核心线程先填满 → 队列再缓冲 → 最后才扩到 max
- 许多面试题错误地把顺序说成"先扩到 max 再用队列"

### 1.4 4 种内置拒绝策略

| 策略                          | 行为                       |
|-----------------------------|--------------------------|
| `AbortPolicy` (默认)          | 抛 `RejectedExecutionException` |
| `CallerRunsPolicy`          | 谁提交谁执行（让调用方同步执行）        |
| `DiscardPolicy`             | 直接丢弃（不抛异常）              |
| `DiscardOldestPolicy`       | 抛弃队列最老的任务，重新提交          |

**生产推荐**：`CallerRunsPolicy`，至少让调用方感知到过载。

### 1.5 4 种内置线程池（`Executors`）

| 工厂方法                    | 队列类型     | 适用场景                |
|-------------------------|----------|---------------------|
| `newFixedThreadPool(n)`  | 无界 LinkedBlockingQueue | 固定并发                |
| `newCachedThreadPool()`  | 同步队列      | 短期异步任务              |
| `newSingleThreadExecutor` | 无界队列     | 顺序执行                |
| `newScheduledThreadPool` | DelayedWorkQueue | 定时任务                |

**警告**：阿里规范禁止用 `Executors` 创建线程池，因为它会用无界队列，导致 OOM！

### 1.6 合理配置线程数

> CPU 密集型：`corePoolSize = CPU 核数 + 1`
> I/O 密集型：`corePoolSize = CPU 核数 * 2`

更精确：先压测，看 CPU 利用率、上下文切换次数。

## 2. 代码示例

### 2.1 自定义 ThreadPoolExecutor

```java
// 文件：ThreadPoolDemo.java
import java.util.concurrent.*;

public class ThreadPoolDemo {

    public static void main(String[] args) {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(
            2,                          // corePoolSize
            4,                          // maximumPoolSize
            60, TimeUnit.SECONDS,       // keepAliveTime / unit
            new ArrayBlockingQueue<>(100),   // 有界队列防 OOM
            new ThreadPoolExecutor.CallerRunsPolicy()  // 谁提交谁执行
        );

        for (int i = 0; i < 10; i++) {
            final int taskId = i;
            pool.submit(() -> {
                System.out.println("执行任务 " + taskId +
                    " | 线程: " + Thread.currentThread().getName());
                try { Thread.sleep(500); } catch (InterruptedException e) {}
            });
        }

        pool.shutdown();
    }
}
```

### 2.2 `Future` 收集结果

```java
// 文件：FutureBatchDemo.java
import java.util.*;
import java.util.concurrent.*;

public class FutureBatchDemo {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(3);

        List<Future<Integer>> futures = new ArrayList<>();
        for (int i = 0; i < 5; i++) {
            final int taskId = i;
            futures.add(pool.submit(() -> {
                Thread.sleep(1000);
                return taskId * 10;
            }));
        }

        int sum = 0;
        for (Future<Integer> f : futures) {
            sum += f.get();      // 阻塞，每秒等一个
        }

        System.out.println("总和: " + sum);   // 0+10+20+30+40 = 100
        pool.shutdown();
    }
}
```

### 2.3 常见错误：无界队列导致 OOM

```java
// 文件：BadPoolDemo.java
public class BadPoolDemo {

    public static void main(String[] args) {
        // ❌ FixedThreadPool 默认用无界 LinkedBlockingQueue
        ExecutorService bad = Executors.newFixedThreadPool(2);
        for (int i = 0; i < 1_000_000; i++) {
            bad.submit(() -> {
                try { Thread.sleep(1000); } catch (InterruptedException e) {}
            });
        }
        // 队列会累积 100 万个任务，最终 OOM
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 中无直接线程池示例

> ruoyi 不在 common 模块直接写线程池，而是放在 Spring Boot starter 中配置。常见位置：
- `yudao-spring-boot-starter-job`（Quartz 定时任务）
- `yudao-spring-boot-starter-mq`（Redis Stream / RabbitMQ 消息消费线程池）
- `yudao-server` 的 `application.yaml`（业务线程池）

### 3.2 推荐配置（基于 Spring Boot）

`application.yml` 中：

```yaml
spring:
  task:
    execution:
      pool:
        core-size: 8
        max-size: 32
        queue-capacity: 200
        keep-alive: 60s
        thread-name-prefix: yudao-async-
        rejected-execution-handler-class: java.util.concurrent.ThreadPoolExecutor.CallerRunsPolicy
```

加上 `@EnableAsync` 在主类上：

```java
@EnableAsync
@SpringBootApplication
public class YudaoServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(YudaoServerApplication.class, args);
    }
}
```

业务代码：

```java
@Async
public CompletableFuture<X> asyncProcess(X req) {
    return CompletableFuture.completedFuture(doWork(req));
}
```

### 3.3 Async 类的设计逻辑

源自 ruoyi 中常见的"日志注解 + 异步执行"：

```java
@Slf4j
@Async("taskExecutor")
public void logOperation(OperateLog log) {
    logMapper.insert(log);
}
```

设计意图：
- 高频接口（如登录）需要快速响应，操作日志不必即时写库
- `@Async` 提交到线程池异步执行

## 4. 关键要点总结

- 线程池通过"复用线程 + 限制并发"提高性能
- 7 大参数决定线程池行为：核心线程数、最大线程数、队列容量、拒绝策略等
- 阿里规范禁止 `Executors` 创建线程池，要用 `ThreadPoolExecutor` + 有界队列
- Spring Boot 通过 `@EnableAsync + application.yml` 统一管理线程池

## 5. 练习题

### 练习 1：基础（必做）

手写一个 `ThreadPoolExecutor`，参数 `core=2, max=4, queue=10, 拒绝=CALLER_RUNS`。提交 20 个任务观察行为（核心线程处理 → 队列缓冲 → 非核心线程 → 拒绝时主线程执行）。

### 练习 2：进阶

解释为什么 `CachedThreadPool` 适合"短期异步任务"而 `FixedThreadPool` 适合"长期稳定负载"。

### 练习 3：挑战（选做）

实现一个"任务超时淘汰"线程池：每个任务有 timeout，超过时间被丢弃且记录日志。提示：用 `Future.get(timeout, MILLISECONDS)`。

## 6. 参考资料

- 《Java 并发编程实战》第 6、8 章：线程池
- Alibaba Java 开发手册：线程池章节
- ThreadPoolExecutor 源码：`/Users/xu/code/JDK-17/java.base/java/util/concurrent/ThreadPoolExecutor.java`
- Spring Async 文档：https://docs.spring.io/spring-framework/docs/current/reference/html/integration.html#scheduling-annotation-support

---

**文档版本**：v1.0
**最后更新**：2026-07-13
