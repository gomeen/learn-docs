# 1.3.6 JUC 工具类：CountDownLatch / CyclicBarrier

> 掌握 `java.util.concurrent` 包的常用同步工具，理解 `CountDownLatch` 与 `CyclicBarrier` 的差别。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 `CountDownLatch` 等待多个线程完成
- 使用 `CyclicBarrier` 让多个线程相互等待同一点
- 区分两者的适用场景（一次性 vs 循环复用）
- 用 `Semaphore` 实现简单的并发限流

## 📚 前置知识

- Thread / Runnable 基础
- 线程池基础
- 21-thread.md、22-thread-pool.md

## 1. 核心概念

### 1.1 JUC 工具类一览

`java.util.concurrent` 包提供了多种**高级同步工具**，让多线程协作更简单：

| 工具              | 用途                          |
|-----------------|-----------------------------|
| `CountDownLatch`| 一次性等待 N 个线程完成             |
| `CyclicBarrier` | N 个线程相互等待，到齐后再一起放行      |
| `Semaphore`     | 限制同时运行的线程数（信号量）          |
| `Phaser`        | 更强大的 CyclicBarrier，按阶段同步 |
| `Exchanger`     | 两线程间数据交换                  |
| `Future`        | 一个线程等另一个线程的结果            |

### 1.2 CountDownLatch vs CyclicBarrier

| 维度               | CountDownLatch             | CyclicBarrier                   |
|------------------|----------------------------|---------------------------------|
| 计数方式            | `countDown()` 把计数减到 0      | `await()` 等所有线程都到达 barrier |
| 重用              | 一次性                        | 可重用（reset 或自动 reset）         |
| 参与方             | N 个工作线程 + 1 个等待方         | N 个线程彼此互相等待                  |
| 适用              | "主线程等子线程"                  | "N 个线程互相等到齐"                 |

**形象比喻**：
- CountDownLatch：火箭发射控制台等所有工程师按"准备就绪"按钮
- CyclicBarrier：旅游团 10 个人在集合点彼此等待，谁都不走

### 1.3 Semaphore 信号量

类似"令牌桶"：初始化 N 个令牌，每进入一个线程取一个令牌，N 个用完后其他线程阻塞。用于：
- 连接池限流（数据库连接 / HTTP 连接）
- 接口限流（每秒最多 N 次）

### 1.4 Phaser 与 Exchanger

- `Phaser`：CyclicBarrier 的升级版，可以分阶段 (phase 0 → 1 → 2) 等待，且可动态注册参与方
- `Exchanger`：两线程间数据交换（一手交钱一手交货）

## 2. 代码示例

### 2.1 CountDownLatch：主线程等待 3 个子任务

```java
// 文件：CountDownLatchDemo.java
import java.util.concurrent.*;

public class CountDownLatchDemo {
    public static void main(String[] args) throws InterruptedException {
        CountDownLatch latch = new CountDownLatch(3);

        for (int i = 0; i < 3; i++) {
            final int taskId = i;
            new Thread(() -> {
                System.out.println("任务 " + taskId + " 完成");
                latch.countDown();
            }).start();
        }

        latch.await();   // 阻塞直到计数归 0
        System.out.println("所有任务完成，主线程继续");
    }
}
```

### 2.2 CyclicBarrier：3 个线程相互等待

```java
// 文件：CyclicBarrierDemo.java
import java.util.concurrent.*;

public class CyclicBarrierDemo {

    static class Worker implements Runnable {
        private final CyclicBarrier barrier;
        private final int id;
        Worker(CyclicBarrier b, int id) { this.barrier = b; this.id = id; }

        @Override
        public void run() {
            try {
                System.out.println("Worker " + id + " 到达集合点");
                barrier.await();   // 阻塞等其他人
                System.out.println("Worker " + id + " 继续干活");
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public static void main(String[] args) {
        CyclicBarrier barrier = new CyclicBarrier(3, () -> {
            System.out.println("--- 所有人都到齐了，开始行动 ---");
        });

        for (int i = 1; i <= 3; i++) {
            new Thread(new Worker(barrier, i)).start();
        }
    }
}
```

输出示例：
```
Worker 3 到达集合点
Worker 1 到达集合点
Worker 2 到达集合点
--- 所有人都到齐了，开始行动 ---
Worker 1 继续干活
Worker 2 继续干活
Worker 3 继续干活
```

### 2.3 Semaphore 信号量（限流）

```java
// 文件：SemaphoreDemo.java
import java.util.concurrent.*;

public class SemaphoreDemo {

    public static void main(String[] args) throws Exception {
        Semaphore semaphore = new Semaphore(3);   // 最多 3 个并发
        ExecutorService pool = Executors.newFixedThreadPool(10);

        for (int i = 1; i <= 10; i++) {
            final int id = i;
            pool.submit(() -> {
                try {
                    semaphore.acquire();           // 取令牌
                    System.out.println("任务 " + id + " 获得许可，开始执行");
                    Thread.sleep(1000);
                    System.out.println("任务 " + id + " 完成");
                } catch (InterruptedException e) {
                    e.printStackTrace();
                } finally {
                    semaphore.release();           // 还令牌
                }
            });
        }

        pool.shutdown();
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 中无直接示例（同步工具分散在各 starter）

> ruoyi 仓库中 `CountDownLatch` 等同步工具主要在以下场景使用：
- `yudao-spring-boot-starter-test`：单元测试等待异步任务
- `yudao-spring-boot-starter-job`：Quartz 调度器内部使用
- `yudao-spring-boot-starter-redis`：分布式场景用 Redisson 的 `RCountDownLatch`、`RSemaphore`

### 3.2 Redisson 的 `RSemaphore`：分布式信号量

典型 ruoyi 场景：分布式限流（防止 N 个实例同时访问同一资源）：

```java
// 伪代码：在 ruoyi 中通过 Redisson 客户端获取分布式信号量
RSemaphore semaphore = redissonClient.getSemaphore("order_create_limit");
semaphore.trySetPermits(100);        // 最多 100 个并发
boolean ok = semaphore.tryAcquire(5, SECONDS);   // 拿令牌
try {
    if (ok) {
        // 执行业务
    }
} finally {
    if (ok) semaphore.release();
}
```

与 JDK `Semaphore` 区别：
- `Semaphore` 在**单个 JVM 进程内**生效
- `RSemaphore` 是**分布式**的，跨进程生效

### 3.3 ruoyi 操作日志的异步批量提交

间接应用——通过 `CountDownLatch` 等多个异步任务最后同步：

```java
public void asyncBatchLog(List<OperateLog> logs) {
    CountDownLatch latch = new CountDownLatch(logs.size() / 100);
    // 分批异步提交
    Lists.partition(logs, 100).forEach(batch -> {
        logExecutor.submit(() -> {
            logMapper.insertBatch(batch);
            latch.countDown();
        });
    });
    latch.await();   // 等所有批次完成
}
```

## 4. 关键要点总结

- `CountDownLatch`：一次性，主线程等子线程
- `CyclicBarrier`：可重用，N 线程彼此等
- `Semaphore`：限流，控制同时执行的线程数
- `Phaser` / `Exchanger`：更复杂的协作场景
- 分布式场景用 Redisson 的同类工具

## 5. 练习题

### 练习 1：基础（必做）

写一个"赛跑"模拟器：4 个选手（线程）同时起跑，所有选手到达终点后主线程打印"比赛结束"。用 `CountDownLatch` 实现。

### 练习 2：进阶

解释为什么 `CyclicBarrier` 适合"组团旅游互相等待"，而 `CountDownLatch` 适合"主线程等所有 worker"。画时序图说明。

### 练习 3：挑战（选做）

实现一个简单的"分布式锁"（伪分布式）：用 Redis 的 `SETNX` 命令 + 过期时间，加上 `Semaphore` 的 tryAcquire 模拟并发限流。

## 6. 参考资料

- 《Java 并发编程实战》第 5 章：构建块
- JUC 官方文档：https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html
- Redisson 分布式工具：https://github.com/redisson/redisson/wiki

---

**文档版本**：v1.0
**最后更新**：2026-07-13
