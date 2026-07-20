# 1.4.5 原子类：AtomicInteger / AtomicReference

> 掌握 `java.util.concurrent.atomic` 包下原子类的 CAS 实现原理，能用原子类实现无锁并发数据结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 CAS（Compare-And-Swap）的工作原理与 ABA 问题
- 区分 `AtomicInteger`、`AtomicLong`、`AtomicReference`、`AtomicStampedReference` 的适用场景
- 理解 `LongAdder` 在高并发下优于 `AtomicLong` 的原因
- 能读懂 Redisson、MyBatis 等框架中基于原子类的实现

## 📚 前置知识

- [25-thread.md](./25-thread.md)：线程基础
- [33-lock.md](./33-lock.md)：锁机制（对比学习）
- 硬件基础：CPU 缓存一致性协议 MESI

## 1. 核心概念

### 1.1 为什么需要原子类？

```java
// ❌ 经典线程安全问题
class Counter {
    private int count = 0;
    public void increment() {
        count++;  // 实际是 3 步：读、加、写 → 非原子
    }
}

// ✅ 用 AtomicInteger 替代
class AtomicCounter {
    private AtomicInteger count = new AtomicInteger(0);
    public void increment() {
        count.incrementAndGet();  // 单条 CPU 指令完成，无锁
    }
}
```

### 1.2 CAS（Compare-And-Swap）

**硬件级原子指令**，是所有原子类的基石：

```
CAS(V, E, N):
  if V == E:
      V = N
      return true
  else:
      return false
```

- **V（Value）**：内存地址中的当前值
- **E（Expected）**：期望值
- **N（New）**：要设置的新值

**翻译成 x86 指令**：`CMPXCHG`（compare-and-exchange）

**乐观 vs 悲观**：
- 悲观锁（synchronized/ReentrantLock，详见 [27-lock](./33-lock.md)）：先加锁，再操作
- 乐观锁（CAS）：无锁操作，失败就重试

### 1.3 CAS 的三大问题

| 问题 | 描述 | 解决方案 |
|------|------|---------|
| **ABA 问题** | V 从 A 变 B 又变回 A，CAS 误判未变 | `AtomicStampedReference` 加版本号 |
| **CPU 开销** | 高并发下大量重试，浪费 CPU | 退化为锁；或用 `LongAdder` 分散热点 |
| **只能保证一个变量原子** | 多变量组合操作需要其他机制 | 锁、或把多变量封装为对象 |

### 1.4 AtomicInteger / AtomicLong / AtomicBoolean

```java
AtomicInteger count = new AtomicInteger(0);

count.incrementAndGet();      // ++count，返回新值
count.getAndIncrement();      // count++，返回旧值
count.addAndGet(10);          // count += 10
count.compareAndSet(5, 10);   // CAS
count.updateAndGet(x -> x * 2);  // JDK 8+ 函数式更新
```

### 1.5 AtomicReference / AtomicStampedReference

```java
// 原子引用：用于无锁更新对象
AtomicReference<User> ref = new AtomicReference<>(initialUser);
ref.compareAndSet(oldUser, newUser);

// ABA 问题演示
User oldRef = new User("Alice", 1);
User newRef = new User("Alice", 2);  // 看似"等价"，但 version 不同

// 解决：AtomicStampedReference 加版本戳
AtomicStampedReference<User> stampedRef = new AtomicStampedReference<>(oldRef, 0);
int[] stampHolder = new int[1];
stampedRef.compareAndSet(oldRef, newRef, stampHolder[0], stampHolder[0] + 1);
```

### 1.6 LongAdder：高并发计数器之王

**AtomicLong 的瓶颈**：所有线程竞争同一个 `value` 字段的 CAS。

**LongAdder 的优化**：把热点分散到多个 Cell（类似分段）：

```
AtomicLong:  [value]  ← 所有线程 CAS 同一个槽位 → 高并发下重试严重

LongAdder:   [Cell[0]] [Cell[1]] [Cell[2]] ... [Cell[n]]
              ↑         ↑         ↑              ↑
           线程0~3   线程4~7   线程8~11      ...
           每个 Cell 独立 CAS → 大幅降低冲突
```

**代价**：`sum()` 不是强一致性的（可能漏加正在 Cell 中累加的值）。

**使用建议**：
- **写多读少**（计数）→ `LongAdder`
- **读多写少 / 要求强一致** → `AtomicLong`

### 1.7 原子数组与字段更新器

```java
// 原子数组：每个元素独立 CAS
AtomicIntegerArray array = new AtomicIntegerArray(10);
array.compareAndSet(0, 0, 100);

// 字段更新器：让普通类的 volatile 字段也支持原子更新
AtomicIntegerFieldUpdater<User> updater =
        AtomicIntegerFieldUpdater.newUpdater(User.class, "age");
updater.compareAndSet(user, 18, 19);

// 累加器：JDK 8+ 提供，扩展 LongAdder 思想
LongAccumulator accumulator = new LongAccumulator(Long::sum, 0);
accumulator.accumulate(10);  // 任意二元操作
```

## 2. 代码示例

### 2.1 AtomicInteger 计数器

```java
// 文件：AtomicCounterDemo.java
import java.util.concurrent.atomic.AtomicInteger;

public class AtomicCounterDemo {
    private final AtomicInteger count = new AtomicInteger(0);

    public int increment() {
        return count.incrementAndGet();
    }

    public int add(int delta) {
        return count.addAndGet(delta);
    }

    // JDK 8+ 函数式更新：原子地"读 → 计算 → 写"
    public int multiply(int factor) {
        return count.updateAndGet(x -> x * factor);
    }

    // CAS 经典用法：自旋更新
    public boolean compareAndSet(int expected, int newValue) {
        return count.compareAndSet(expected, newValue);
    }

    public static void main(String[] args) throws InterruptedException {
        AtomicCounterDemo counter = new AtomicCounterDemo();
        Thread[] threads = new Thread[10];
        for (int i = 0; i < 10; i++) {
            threads[i] = new Thread(() -> {
                for (int j = 0; j < 10000; j++) {
                    counter.increment();
                }
            });
            threads[i].start();
        }
        for (Thread t : threads) t.join();
        System.out.println("Final count: " + counter.count.get());  // 100000
    }
}
```

### 2.2 AtomicReference 实现无锁栈

```java
// 文件：LockFreeStack.java
import java.util.concurrent.atomic.AtomicReference;

public class LockFreeStack<T> {
    private static class Node<T> {
        final T value;
        final Node<T> next;
        Node(T value, Node<T> next) { this.value = value; this.next = next; }
    }

    private final AtomicReference<Node<T>> head = new AtomicReference<>();

    public void push(T value) {
        Node<T> newHead = new Node<>(value, null);
        // CAS：直到把 newHead 放到栈顶
        Node<T> oldHead;
        do {
            oldHead = head.get();
            newHead = new Node<>(value, oldHead);  // 注意：每次都要重新创建！
        } while (!head.compareAndSet(oldHead, newHead));
    }

    public T pop() {
        Node<T> oldHead, newHead;
        do {
            oldHead = head.get();
            if (oldHead == null) return null;
            newHead = oldHead.next;
        } while (!head.compareAndSet(oldHead, newHead));
        return oldHead.value;
    }
}
```

### 2.3 LongAdder vs AtomicLong 性能对比

```java
// 文件：AdderVsAtomicBench.java
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public class AdderVsAtomicBench {
    public static void main(String[] args) throws Exception {
        int threadCount = 16;
        int iterations = 1_000_000;
        ExecutorService pool = Executors.newFixedThreadPool(threadCount);

        // 测试 AtomicLong
        AtomicLong atomicLong = new AtomicLong();
        long start1 = System.nanoTime();
        CountDownLatch latch1 = new CountDownLatch(threadCount);
        for (int i = 0; i < threadCount; i++) {
            pool.submit(() -> {
                for (int j = 0; j < iterations; j++) atomicLong.incrementAndGet();
                latch1.countDown();
            });
        }
        latch1.await();
        long time1 = System.nanoTime() - start1;
        System.out.println("AtomicLong: " + (time1 / 1_000_000) + " ms");

        // 测试 LongAdder
        LongAdder longAdder = new LongAdder();
        long start2 = System.nanoTime();
        CountDownLatch latch2 = new CountDownLatch(threadCount);
        for (int i = 0; i < threadCount; i++) {
            pool.submit(() -> {
                for (int j = 0; j < iterations; j++) longAdder.increment();
                latch2.countDown();
            });
        }
        latch2.await();
        long time2 = System.nanoTime() - start2;
        System.out.println("LongAdder:  " + (time2 / 1_000_000) + " ms");
        System.out.println("LongAdder.sum(): " + longAdder.sum());

        pool.shutdown();
        // 16 线程下 LongAdder 通常快 3~5 倍
    }
}
```

## 3. 关键要点总结

- **CAS（Compare-And-Swap）**：乐观锁的硬件基础，CPU 指令 `CMPXCHG`
- **AtomicInteger/Long/Reference**：单变量无锁原子操作
- **ABA 问题**：用 `AtomicStampedReference` 加版本戳解决
- **LongAdder**：写多读少场景，比 AtomicLong 高 3~5 倍性能（但 sum 非强一致）
- **AtomicIntegerFieldUpdater**：让普通类的 volatile 字段也支持原子更新（更轻量）
- ruoyi-vue-pro 业务代码很少直接用 AtomicXxx，分布式场景通过 Redisson 间接使用，本地限流场景可用 AtomicLong

---

**文档版本**：v1.0
**最后更新**：2026-07-13
