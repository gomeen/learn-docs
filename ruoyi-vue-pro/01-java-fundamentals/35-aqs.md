# 1.4.6 AQS 抽象队列同步器原理

> 理解 AQS（AbstractQueuedSynchronizer）的设计思想，能看懂 ReentrantLock、CountDownLatch、Semaphore 等 JUC 工具的源码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 AQS 的核心三要素：state、CAS、CLH 队列
- 理解 ReentrantLock、CountDownLatch、Semaphore 等 JUC 工具都基于 AQS
- 能基于 AQS 自定义一个简单的同步器
- 在 ruoyi-vue-pro 中识别基于 AQS 的工具使用

## 📚 前置知识

- [27-juc.md](./27-juc.md)：JUC 工具类基础
- [33-lock.md](./33-lock.md)：锁机制
- [34-atomic.md](./34-atomic.md)：原子类与 CAS

## 1. 核心概念

### 1.1 AQS 是什么？

`AbstractQueuedSynchronizer`（抽象队列同步器）是 **JUC（java.util.concurrent）包的核心**，是构建锁和同步器的框架：

```
┌────────────────────────────────────────────┐
│             ReentrantLock                   │  ← 基于 AQS
│             CountDownLatch                  │  ← 基于 AQS
│             Semaphore                       │  ← 基于 AQS
│             ReentrantReadWriteLock          │  ← 基于 AQS
│             ThreadPoolExecutor.Worker       │  ← 基于 AQS
└─────────────────┬──────────────────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │  AbstractQueued     │
        │  Synchronizer (AQS) │
        └─────────────────────┘
```

**设计思想**：AQS 把 **"同步状态管理"** 和 **"阻塞/唤醒线程"** 这两件事抽象出来，子类只需通过 CAS 修改 state + 实现 `tryAcquire/tryRelease`，即可获得完整同步能力。

### 1.2 AQS 的三大核心

#### 1.2.1 state（同步状态）

```java
private volatile int state;  // 0=未锁定，1=已锁定，n=重入次数
```

- 通过 **CAS** 修改
- 不同子类用 state 表示不同含义：
  - `ReentrantLock`：重入次数（0=未占用，n=占用且重入 n-1 次）
  - `CountDownLatch`：倒计数（n=还需 countDown 几次）
  - `Semaphore`：剩余许可数（n=可用许可）

#### 1.2.2 CLH 队列（双向链表）

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ Thread │ ←→ │ Thread │ ←→ │ Thread │ ←→ │ Thread │
│  (T1)  │    │  (T2)  │    │  (T3)  │    │  (T4)  │
└────────┘    └────────┘    └────────┘    └────────┘
   ↑
 head                                           ↑
                                              tail
```

- **Node.waitStatus**：CANCELLED（取消）/ SIGNAL（唤醒后继）/ CONDITION（条件队列）/ PROPAGATE
- 等待获取锁失败的线程会被包装为 Node 加入队尾
- 持锁线程释放时唤醒 head 的后继节点

#### 1.2.3 CAS 操作

- **修改 state**：`compareAndSetState(0, 1)`
- **修改 Node.prev/next/nextWaiter**：用 CAS 保证并发安全

### 1.3 AQS 的模板方法

> 📌 **Sighting**：模板方法模式完整讲解见 [模板方法](../../_fundamentals/06-design-patterns/14-template-method.md)。AQS 用「父类骨架 + 子类 tryAcquire」实现同步器扩展。

AQS 定义了独占/共享两类模板方法：

```java
// 独占模式（互斥锁）
protected boolean tryAcquire(int arg);     // 尝试获取锁，子类实现
protected boolean tryRelease(int arg);     // 尝试释放锁，子类实现

// 共享模式（共享资源，如 Semaphore）
protected int tryAcquireShared(int arg);
protected boolean tryReleaseShared(int arg);

// AQS 提供的公共方法（用模板方法实现）
public final void acquire(int arg) {           // 阻塞获取
    if (!tryAcquire(arg) &&
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        selfInterrupt();
}
public final boolean release(int arg) {        // 释放并唤醒后继
    if (tryRelease(arg)) {
        Node h = head;
        if (h != null && h.waitStatus != 0)
            unparkSuccessor(h);
        return true;
    }
    return false;
}
```

### 1.4 ReentrantLock 的 AQS 实现

```java
class ReentrantLock extends Lock {
    // 内部 Sync 继承 AQS
    abstract static class Sync extends AbstractQueuedSynchronizer {
        abstract void lock();

        // 非公平 lock：直接 CAS 抢锁
        final boolean nonfairTryAcquire(int acquires) {
            final Thread current = Thread.currentThread();
            int c = getState();
            if (c == 0) {
                if (compareAndSetState(0, acquires)) {
                    setExclusiveOwnerThread(current);
                    return true;
                }
            }
            // 重入：state + 1
            else if (current == getExclusiveOwnerThread()) {
                int nextc = c + acquires;
                setState(nextc);
                return true;
            }
            return false;
        }

        protected final boolean tryRelease(int releases) {
            int c = getState() - releases;
            if (Thread.currentThread() != getExclusiveOwnerThread())
                throw new IllegalMonitorStateException();
            boolean free = false;
            if (c == 0) {
                free = true;
                setExclusiveOwnerThread(null);
            }
            setState(c);
            return free;
        }
    }
}
```

### 1.5 CountDownLatch 的 AQS 实现

```java
class CountDownLatch {
    private static final class Sync extends AbstractQueuedSynchronizer {
        Sync(int count) { setState(count); }  // 初始 state = count

        protected int tryAcquireShared(int acquires) {
            // state == 0 时所有等待线程可同时通过
            return (getState() == 0) ? 1 : -1;
        }

        protected boolean tryReleaseShared(int releases) {
            // countDown 时 state - 1，全部归零后唤醒等待线程
            for (;;) {
                int c = getState();
                if (c == 0) return false;
                int nextc = c - 1;
                if (compareAndSetState(c, nextc)) return nextc == 0;
            }
        }
    }
}
```

### 1.6 自定义同步器：基于 AQS 实现互斥锁

```java
// 文件：MyLock.java
import java.util.concurrent.locks.AbstractQueuedSynchronizer;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Lock;

public class MyLock implements Lock {
    private final Sync sync = new Sync();

    // 内部 Sync 继承 AQS
    private static class Sync extends AbstractQueuedSynchronizer {
        @Override
        protected boolean tryAcquire(int arg) {
            if (compareAndSetState(0, arg)) {
                setExclusiveOwnerThread(Thread.currentThread());
                return true;
            }
            return false;
        }

        @Override
        protected boolean tryRelease(int arg) {
            if (getState() == 0) throw new IllegalMonitorStateException();
            setExclusiveOwnerThread(null);
            setState(0);
            return true;
        }

        @Override
        protected boolean isHeldExclusively() {
            return getState() == 1;
        }

        Condition newCondition() {
            return new ConditionObject();
        }
    }

    @Override
    public void lock() { sync.acquire(1); }

    @Override
    public boolean tryLock() { return sync.tryAcquire(1); }

    @Override
    public boolean tryLock(long timeout, TimeUnit unit) throws InterruptedException {
        return sync.tryAcquireNanos(1, unit.toNanos(timeout));
    }

    @Override
    public void unlock() { sync.release(1); }

    @Override
    public Condition newCondition() { return sync.newCondition(); }

    @Override
    public void lockInterruptibly() throws InterruptedException {
        sync.acquireInterruptibly(1);
    }
}
```

## 2. 代码示例

### 2.1 CountDownLatch 等待多任务完成

```java
// 文件：CountDownLatchDemo.java
import java.util.concurrent.*;

public class CountDownLatchDemo {
    public static void main(String[] args) throws InterruptedException {
        int taskCount = 5;
        CountDownLatch latch = new CountDownLatch(taskCount);
        ExecutorService pool = Executors.newFixedThreadPool(3);

        for (int i = 0; i < taskCount; i++) {
            final int id = i;
            pool.submit(() -> {
                try {
                    System.out.println("Task " + id + " 开始");
                    Thread.sleep(1000 + (long) (Math.random() * 2000));
                    System.out.println("Task " + id + " 完成");
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    latch.countDown();  // 必须放在 finally
                }
            });
        }

        System.out.println("主线程等待所有任务...");
        latch.await();  // 阻塞直到 state == 0
        System.out.println("所有任务完成，主线程继续");

        pool.shutdown();
    }
}
```

### 2.2 Semaphore 限流

```java
// 文件：SemaphoreDemo.java
import java.util.concurrent.*;

public class SemaphoreDemo {
    public static void main(String[] args) {
        // 最多 3 个并发
        Semaphore semaphore = new Semaphore(3);
        ExecutorService pool = Executors.newFixedThreadPool(10);

        for (int i = 0; i < 10; i++) {
            final int id = i;
            pool.submit(() -> {
                try {
                    semaphore.acquire();
                    System.out.println("Task " + id + " 获得许可，开始执行");
                    Thread.sleep(2000);
                    System.out.println("Task " + id + " 完成，释放许可");
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    semaphore.release();
                }
            });
        }

        pool.shutdown();
    }
}
```

### 2.3 CyclicBarrier 循环栅栏

```java
// 文件：CyclicBarrierDemo.java
import java.util.concurrent.*;

public class CyclicBarrierDemo {
    public static void main(String[] args) {
        // 3 个线程全部到达 barrier 后才会继续
        CyclicBarrier barrier = new CyclicBarrier(3, () -> {
            System.out.println("所有线程到达 barrier，执行合并任务");
        });

        for (int i = 0; i < 3; i++) {
            final int id = i;
            new Thread(() -> {
                try {
                    System.out.println("Thread " + id + " 准备中...");
                    Thread.sleep(1000 + id * 500);
                    System.out.println("Thread " + id + " 到达 barrier，等待其他线程");
                    barrier.await();  // 阻塞直到 3 个线程都到达
                    System.out.println("Thread " + id + " 继续执行");
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }).start();
        }
    }
}
```

## 3. 关键要点总结

- **AQS 是 JUC 的基石**：ReentrantLock / CountDownLatch / Semaphore / ReentrantReadWriteLock / ThreadPoolExecutor 都基于 AQS
- **三大核心**：`state`（同步状态）+ **CAS**（原子修改）+ **CLH 队列**（阻塞线程排队）
- **两种模式**：独占（ReentrantLock）/ 共享（Semaphore、CountDownLatch）
- **子类只需实现**：tryAcquire / tryRelease（独占）或 tryAcquireShared / tryReleaseShared（共享）
- ruoyi-vue-pro 直接使用 AQS 工具较少，主要通过 Redisson 实现分布式版本
- **典型场景**：CountDownLatch（启动等待）、Semaphore（本地并发限流）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
