# 1.4.4 锁机制：synchronized / ReentrantLock / ReadWriteLock

> 掌握 Java 三类核心锁的原理与差异，能在 ruoyi-vue-pro 中识别 synchronized、ReentrantLock 和分布式锁（Redisson RLock）的使用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `synchronized`、`ReentrantLock`、`ReentrantReadWriteLock` 的底层实现
- 区分"对象监视器锁"、"API 级显式锁"、"读写分离锁"三种粒度
- 在 ruoyi-vue-pro 中识别锁的使用：synchronized（DCL）、ReentrantLock（tryLock + 超时）、Redisson RLock（分布式）
- 知道什么时候必须用分布式锁而不是单机锁

## 📚 前置知识

- [25-thread.md](./25-thread.md)：线程基础
- [26-thread-pool.md](./26-thread-pool.md)：线程池
- [27-juc.md](./27-juc.md)：JUC 工具类

## 1. 核心概念

### 1.1 三类锁速览

| 锁 | 范围 | 粒度 | 特性 | JDK 版本 |
|----|------|------|------|---------|
| **synchronized** | JVM 内置 | 对象/Monitor | 自动释放、不可中断、不可超时 | 1.0 |
| **ReentrantLock** | java.util.concurrent | API | 可中断、可超时、公平锁、Condition | 5.0 |
| **ReentrantReadWriteLock** | java.util.concurrent | 读锁/写锁 | 读读不互斥、读写/写写互斥 | 5.0 |
| **StampedLock** | java.util.concurrent | 邮戳 | 乐观读，性能更优 | 8.0 |
| **Redisson RLock** | Redisson | Redis 分布式 | 跨 JVM 互斥、超时续期 | 第三方 |

### 1.2 synchronized 的演进

- **JDK 1.0**：重量级 Monitor 锁，每次加锁都要 OS mutex → 用户态/内核态切换
- **JDK 1.6+**：引入**偏向锁 → 轻量级锁 → 重量级锁**的锁升级机制
  - **偏向锁**：单线程反复进入同步块，几乎无开销（无 CAS、无 Monitor enter）—— JDK 15 默认禁用
  - **轻量级锁**：CAS 自旋，多线程交替进入
  - **重量级锁**：高并发争用，OS mutex 阻塞

**锁升级路径**：
```
无锁 → 偏向锁（单线程）→ 轻量级锁（CAS 自旋）→ 重量级锁（OS 阻塞）
```

**对象头**（64 位 JVM 示例）：
```
[unused(25)] | hash(31) | age(4) | biased_lock(1) | lock(2)
                                                       ↑
                                                00=轻量 10=重量 01=无锁/偏向
```

### 1.3 synchronized 的两种写法

```java
// 写法 1：同步方法（锁 this）
public synchronized void increment() { count++; }

// 写法 2：同步代码块（锁任意对象）—— 推荐，粒度更细
public void increment() {
    synchronized (this) {
        count++;
    }
}

// 写法 3：锁特定对象（推荐）
private final Object lock = new Object();
public void increment() {
    synchronized (lock) {
        count++;
    }
}
```

### 1.4 ReentrantLock 的核心 API

```java
ReentrantLock lock = new ReentrantLock();        // 非公平锁（默认，吞吐高）
ReentrantLock fairLock = new ReentrantLock(true); // 公平锁（FIFO）

lock.lock();                    // 阻塞获取
lock.tryLock();                 // 非阻塞尝试，立刻返回 boolean
lock.tryLock(1, TimeUnit.SECONDS); // 带超时尝试
lock.lockInterruptibly();       // 可中断等待

lock.unlock();                  // 必须手动释放（通常在 finally）

// 多个 Condition（synchronized 只有 1 个）
Condition notFull = lock.newCondition();
Condition notEmpty = lock.newCondition();
```

**何时选 ReentrantLock 而不是 synchronized**：
1. 需要 **tryLock / 超时** 能力
2. 需要 **可中断** 的等待
3. 需要 **公平锁**
4. 需要 **多个 Condition**（生产者-消费者细分）
5. 需要 **try { ... } catch (...) { ... } finally { unlock() }** 的精细控制

### 1.5 ReadWriteLock 读写分离

**核心思想**：读-读不互斥，读-写、写-写互斥。

```java
ReadWriteLock rwLock = new ReentrantReadWriteLock();
Lock readLock = rwLock.readLock();
Lock writeLock = rwLock.writeLock();

// 多个线程可同时持有读锁
readLock.lock();
try {
    return cache.get(key);
} finally {
    readLock.unlock();
}

// 写锁独占
writeLock.lock();
try {
    cache.put(key, value);
} finally {
    writeLock.unlock();
}
```

**适用场景**：缓存配置、字典数据、白名单等**读多写少**的场景。

### 1.6 锁升级 / 降级

- **升级**：读锁 → 写锁？**不允许**！会导致死锁（A 持读锁想拿写锁，B 也想拿写锁 → 阻塞）
- **降级**：写锁 → 读锁？**允许**（释放写锁前先获取读锁）
- **StampedLock 优化**：用 `tryConvertToReadLock()` 实现乐观读→读锁的"软"升级

### 1.7 分布式锁（Redisson RLock）

**为什么需要分布式锁**：
```
Java 单机锁只对当前 JVM 进程内的线程互斥。
多实例部署时（K8s 3 副本），3 个进程同时跑定时任务，单机锁无效 → 必须用 Redis/Zookeeper 分布式锁
```

**Redisson RLock 特性**：
- 基于 Redis 的 SET NX PX 命令 + Lua 脚本保证原子性
- 自动续期（Watch Dog，默认 30s 续期到 30s）
- 可重入（Hash 结构记录重入次数）
- 阻塞/tryLock/tryLock(time) 三种等待方式

```java
RLock lock = redissonClient.getLock("order:create:" + orderId);
try {
    boolean acquired = lock.tryLock(3, 15, TimeUnit.SECONDS);  // 等待 3s，锁 15s
    if (!acquired) {
        throw new ServiceException("系统繁忙，请重试");
    }
    // 业务逻辑
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

## 2. 代码示例

### 2.1 DCL 单例（synchronized 经典案例）

> 📌 **Sighting**：完整单例模式变体（饿汉/懒汉/枚举/静态内部类）见 [单例](../../_fundamentals/06-design-patterns/01-singleton.md)。此处只演示 `synchronized` + `volatile` 的 DCL 写法。

```java
// 文件：DclSingleton.java
public class DclSingleton {
    // volatile 防止指令重排序：保证 new 操作的三步（分配内存、初始化、引用赋值）有序
    private static volatile DclSingleton instance;

    private DclSingleton() {}

    public static DclSingleton getInstance() {
        if (instance == null) {                       // 第一次检查（无锁，快速失败）
            synchronized (DclSingleton.class) {       // 类对象加锁
                if (instance == null) {                // 第二次检查（持锁后再判一次）
                    instance = new DclSingleton();     // volatile 保证可见性
                }
            }
        }
        return instance;
    }
}
```

**为什么需要两次检查**：
- 不加第一次检查：每次 getInstance 都要排队等锁（即使实例已存在）
- 不加第二次检查：线程 A 进入同步块还没创建实例，线程 B 抢到锁会再创建一个

### 2.2 ReentrantLock 实现生产者-消费者

```java
// 文件：ProducerConsumer.java
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

public class ProducerConsumer {
    private final BlockingQueue<Integer> queue = new LinkedBlockingQueue<>(10);

    public void produce() throws InterruptedException {
        // 简洁做法：直接用 BlockingQueue
        queue.put(1);
    }

    // ReentrantLock + Condition 实现版本（学习用）
    static class AdvancedPC {
        private final ReentrantLock lock = new ReentrantLock();
        private final Condition notFull = lock.newCondition();
        private final Condition notEmpty = lock.newCondition();
        private final int[] buffer = new int[10];
        private int count = 0, putIdx = 0, takeIdx = 0;

        public void put(int item) throws InterruptedException {
            lock.lock();
            try {
                while (count == buffer.length) notFull.await();  // 循环检查防虚假唤醒
                buffer[putIdx] = item;
                putIdx = (putIdx + 1) % buffer.length;
                count++;
                notEmpty.signal();  // 唤醒消费者
            } finally {
                lock.unlock();
            }
        }

        public int take() throws InterruptedException {
            lock.lock();
            try {
                while (count == 0) notEmpty.await();
                int item = buffer[takeIdx];
                takeIdx = (takeIdx + 1) % buffer.length;
                count--;
                notFull.signal();   // 唤醒生产者
                return item;
            } finally {
                lock.unlock();
            }
        }
    }
}
```

### 2.3 ReadWriteLock 缓存

```java
// 文件：ReadWriteCache.java
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.locks.*;

public class ReadWriteCache<K, V> {
    private final Map<K, V> map = new HashMap<>();
    private final ReadWriteLock rwLock = new ReentrantReadWriteLock();

    public V get(K key) {
        rwLock.readLock().lock();          // 多线程可同时读
        try {
            return map.get(key);
        } finally {
            rwLock.readLock().unlock();
        }
    }

    public void put(K key, V value) {
        rwLock.writeLock().lock();         // 写独占
        try {
            map.put(key, value);
        } finally {
            rwLock.writeLock().unlock();
        }
    }
}
```

## 3. 关键要点总结

- **synchronized**：JVM 内置，自动释放，适合简单同步；JDK 6+ 已优化（偏向锁/轻量级锁/重量级锁升级）
- **ReentrantLock**：API 级显式锁，支持 tryLock/超时/中断/公平/多 Condition
- **ReadWriteLock**：读写分离，读多写少场景性能提升 5~10 倍
- **选择原则**：简单场景用 synchronized；需要超时/中断/公平 → ReentrantLock；读多写少 → ReadWriteLock
- **多实例部署必须用分布式锁**（Redisson RLock），单机锁无效
- **tryLock(time) 后必须 `isHeldByCurrentThread()` 再 unlock**，防止误释放

---

**文档版本**：v1.0
**最后更新**：2026-07-13
