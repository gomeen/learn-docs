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
- 25-thread.md、26-thread-pool.md

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

## 3. 关键要点总结

- `CountDownLatch`：一次性，主线程等子线程
- `CyclicBarrier`：可重用，N 线程彼此等
- `Semaphore`：限流，控制同时执行的线程数
- `Phaser` / `Exchanger`：更复杂的协作场景
- 分布式场景用 Redisson 的同类工具

---

**文档版本**：v1.0
**最后更新**：2026-07-13
