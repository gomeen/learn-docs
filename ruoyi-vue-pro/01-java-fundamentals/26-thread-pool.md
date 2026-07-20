# 1.3.5 线程池：ExecutorService

> 掌握 Java 线程池的核心参数、工作原理与拒绝策略，能在 Spring Boot 中合理配置 `@Async` 的线程池（`@Async` 用法详见 [22-async](../02-spring-boot/26-async.md)）。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 `ThreadPoolExecutor` 的 7 大核心参数
- 描述线程池工作流程（任务提交 → 核心线程 → 队列 → 最大线程 → 拒绝策略）
- 区分 4 种内置线程池（Fixed / Cached / Single / Scheduled）的使用场景
- 能在 Spring Boot 项目中配置自定义线程池

## 📚 前置知识

- Thread / Runnable / Callable 基础
- 25-thread.md

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

## 3. 关键要点总结

- 线程池通过"复用线程 + 限制并发"提高性能
- 7 大参数决定线程池行为：核心线程数、最大线程数、队列容量、拒绝策略等
- 阿里规范禁止 `Executors` 创建线程池，要用 `ThreadPoolExecutor` + 有界队列
- Spring Boot 通过 `@EnableAsync + application.yml` 统一管理线程池

---

**文档版本**：v1.0
**最后更新**：2026-07-13
