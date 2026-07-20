# 1.4.3 并发集合（Concurrent Collections）

> 掌握 `java.util.concurrent` 包下线程安全集合的实现原理与适用场景，能在 ruoyi-vue-pro 这类高并发系统中正确选用。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `ConcurrentHashMap`、`CopyOnWriteArrayList`、`ConcurrentLinkedQueue` 等并发集合的内部实现
- 根据读写比例选择合适的并发集合
- 能读懂 Redisson、MyBatis 等框架源码中的并发集合使用
- 识别并避免 `ConcurrentModificationException` 等并发陷阱

## 📚 前置知识

- [08-collections.md](./08-collections.md)：Java 集合框架基础
- [25-thread.md](./25-thread.md)：线程基础
- [26-thread-pool.md](./26-thread-pool.md)：线程池

## 1. 核心概念

### 1.1 为什么需要并发集合？

```java
// ❌ HashMap 在多线程下会死循环（JDK 8 前）或数据丢失（JDK 8+）
Map<String, Integer> map = new HashMap<>();
// 多线程同时 put → 链表/红黑树结构损坏

// ❌ Collections.synchronizedMap 性能差（全表锁）
Map<String, Integer> syncMap = Collections.synchronizedMap(new HashMap<>());
// 读多写少场景：每次 get 也要加锁

// ✅ 选择合适的并发集合
Map<String, Integer> concurrentMap = new ConcurrentHashMap<>();  // 分段锁 / CAS
```

### 1.2 并发集合全景图

```
java.util.concurrent
├── ConcurrentMap
│   ├── ConcurrentHashMap           ← 分段锁（JDK7）/ CAS+synchronized（JDK8+）
│   ├── ConcurrentSkipListMap      ← 跳表实现，有序
│   └── ConcurrentNavigableMap     ← 接口
├── List
│   └── CopyOnWriteArrayList       ← 写时复制，适合读多写极少
├── Queue
│   ├── ConcurrentLinkedQueue      ← 无锁单向链表
│   ├── ConcurrentLinkedDeque      ← 无锁双向链表
│   └── BlockingQueue
│       ├── ArrayBlockingQueue     ← 有界，数组
│       ├── LinkedBlockingQueue    ← 可选有界，链表
│       ├── PriorityBlockingQueue  ← 优先级
│       ├── DelayQueue             ← 延时
│       └── SynchronousQueue       ← 零容量
└── Set
    ├── CopyOnWriteArraySet        ← 写时复制
    └── ConcurrentSkipListSet      ← 跳表，有序
```

### 1.3 ConcurrentHashMap 演进

| JDK 版本 | 数据结构 | 并发机制 |
|---------|---------|---------|
| 5~7 | Segment[] + HashEntry[] | 分段锁（16 个 Segment） |
| 8+ | Node[] + 红黑树 | CAS + synchronized（锁桶头节点） |

**JDK 8+ 关键设计**：
- **put**：
  1. 桶为空 → CAS 设置新 Node
  2. 桶非空 → synchronized 锁住桶头节点，插入链表/红黑树
- **get**：完全无锁（volatile 读 Node.val）
- **扩容**：多线程协作式扩容（ForwardingNode + transfer），每个线程领取一段桶区间

### 1.4 CopyOnWriteArrayList（COW）

**写时复制**：每次 `add/set/remove` 都复制一份底层数组，修改后替换引用。

```
[读线程] ─→ 旧数组 [A, B, C]      ─── 无锁读，无阻塞
[写线程] ─→ 复制 → 新数组 [A, B, C, D] ─→ 替换引用
                                      旧数组等所有读线程结束后 GC
```

**代价**：
- **写操作 O(n)**：每次都要复制整个数组
- **内存占用翻倍**：写时新旧数组同时存在
- **弱一致性迭代器**：迭代时看到的是创建迭代器时的快照

**适用场景**：
- **读远多于写**（监听器列表、配置项、白名单）
- **写极少但不能容忍读阻塞**

### 1.5 BlockingQueue：生产者-消费者模型核心

```java
// 经典生产者-消费者
BlockingQueue<Task> queue = new LinkedBlockingQueue<>(1000);

// 生产者
new Thread(() -> {
    queue.put(new Task());  // 队列满时阻塞
}).start();

// 消费者
new Thread(() -> {
    Task t = queue.take();  // 队列空时阻塞
    process(t);
}).start();
```

**实现对比**：

| 类型 | 容量 | 锁 | 公平性 | 适用 |
|------|------|------|--------|------|
| ArrayBlockingQueue | 必须有界 | 单锁 | 可选 | 固定容量严格限流 |
| LinkedBlockingQueue | 可选有界 | 双锁（take/put） | 默认非公平 | 通用场景，吞吐高 |
| SynchronousQueue | 0 | CAS | 可选 | 线程间直接交付（线程池 Executors.newCachedThreadPool 用它） |
| PriorityBlockingQueue | 无界 | 单锁 | 非公平 | 任务有优先级 |
| DelayQueue | 无界 | 单锁 | 非公平 | 定时任务 |

## 2. 代码示例

### 2.1 ConcurrentHashMap 原子操作

```java
// 文件：ConcurrentMapDemo.java
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public class ConcurrentMapDemo {
    // 统计每个 URL 的访问次数（替代 ConcurrentHashMap<String, AtomicInteger>）
    private final ConcurrentHashMap<String, AtomicInteger> counter = new ConcurrentHashMap<>();

    public void visit(String url) {
        // computeIfAbsent：原子地"若不存在则创建"
        counter.computeIfAbsent(url, k -> new AtomicInteger(0)).incrementAndGet();
    }

    // JDK 8+ 新增方法：merge、compute、computeIfPresent
    public int totalVisits() {
        return counter.reduceValuesToInt(1, AtomicInteger::get, 0, Integer::sum);
    }

    public static void main(String[] args) throws InterruptedException {
        ConcurrentMapDemo demo = new ConcurrentMapDemo();
        // 10 个线程各访问 1000 次
        Thread[] threads = new Thread[10];
        for (int i = 0; i < 10; i++) {
            threads[i] = new Thread(() -> {
                for (int j = 0; j < 1000; j++) {
                    demo.visit("/api/user/" + (j % 5));
                }
            });
            threads[i].start();
        }
        for (Thread t : threads) t.join();
        System.out.println("Total: " + demo.totalVisits());  // 10000
        System.out.println("Per URL: " + demo.counter);
    }
}
```

### 2.2 CopyOnWriteArrayList 监听器模式

```java
// 文件：EventBusDemo.java
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

public class EventBusDemo {
    public interface Listener {
        void onEvent(String event);
    }

    // 监听器列表：注册多、写少、读多 → CopyOnWriteArrayList 完美匹配
    private final List<Listener> listeners = new CopyOnWriteArrayList<>();

    public void register(Listener l) { listeners.add(l); }       // 写：复制整个数组
    public void unregister(Listener l) { listeners.remove(l); }   // 写：复制整个数组

    // 读：完全无锁，迭代过程中数组不会被修改（弱一致性）
    public void publish(String event) {
        for (Listener l : listeners) {  // 安全迭代，不会 ConcurrentModificationException
            l.onEvent(event);
        }
    }
}
```

### 2.3 BlockingQueue 实现简易线程池

```java
// 文件：SimpleThreadPool.java
import java.util.concurrent.*;

public class SimpleThreadPool {
    private final BlockingQueue<Runnable> taskQueue = new LinkedBlockingQueue<>(100);
    private final Thread[] workers;
    private volatile boolean running = true;

    public SimpleThreadPool(int nWorkers) {
        workers = new Thread[nWorkers];
        for (int i = 0; i < nWorkers; i++) {
            workers[i] = new Thread(() -> {
                while (running) {
                    try {
                        Runnable task = taskQueue.poll(1, TimeUnit.SECONDS);  // 1 秒超时
                        if (task != null) task.run();
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }, "worker-" + i);
            workers[i].start();
        }
    }

    public void submit(Runnable task) throws InterruptedException {
        taskQueue.put(task);  // 队列满时阻塞
    }

    public void shutdown() {
        running = false;
        for (Thread w : workers) {
            w.interrupt();
        }
    }
}
```

## 3. 关键要点总结

- **ConcurrentHashMap**：默认并发集合首选，JDK 8+ 用 CAS + synchronized，读完全无锁
- **CopyOnWriteArrayList**：**读多写极少**（监听器、白名单），写时复制整数组
- **ConcurrentLinkedQueue**：无锁单向链表，性能极佳，适合 MPSC 场景
- **BlockingQueue**：生产者-消费者模型，记住 ArrayBlockingQueue 必须有界，LinkedBlockingQueue 可选
- **computeIfAbsent**：替代 `get + if null + put`，避免缓存击穿
- ruoyi-vue-pro 用 ConcurrentHashMap 做本地字典缓存、CopyOnWriteArrayList 防御性返回

---

**文档版本**：v1.0
**最后更新**：2026-07-13
