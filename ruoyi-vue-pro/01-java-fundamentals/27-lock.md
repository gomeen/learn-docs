# 1.4.4 锁机制：synchronized / ReentrantLock / ReadWriteLock

> 掌握 Java 三类核心锁的原理与差异，能在 ruoyi-vue-pro 中识别 synchronized、ReentrantLock 和分布式锁（Redisson RLock）的使用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `synchronized`、`ReentrantLock`、`ReentrantReadWriteLock` 的底层实现
- 区分"对象监视器锁"、"API 级显式锁"、"读写分离锁"三种粒度
- 在 ruoyi-vue-pro 中识别锁的使用：synchronized（DCL）、ReentrantLock（tryLock + 超时）、Redisson RLock（分布式）
- 知道什么时候必须用分布式锁而不是单机锁

## 📚 前置知识

- [21-thread.md](./21-thread.md)：线程基础
- [22-thread-pool.md](./22-thread-pool.md)：线程池
- [23-juc.md](./23-juc.md)：JUC 工具类

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 多租户表过滤的 DCL（synchronized 块）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
**核心代码**（行 40-66）：

```java
40  @Override
41  public boolean ignoreTable(String tableName) {
42      // 情况一，全局忽略多租户
43      if (TenantContextHolder.isIgnore()) {
44          return true;
45      }
46      // 情况二，忽略多租户的表
47      tableName = SqlParserUtils.removeWrapperSymbol(tableName);
48      Boolean ignore = ignoreTables.get(tableName.toLowerCase());
49      if (ignore == null) {
50          ignore = computeIgnoreTable(tableName);
51          synchronized (ignoreTables) {                    // ← 锁 ignoreTables，不是 this
52              addIgnoreTable(tableName, ignore);
53          }
54      }
55      return ignore;
56  }
```

**解读**：
- **第 48 行**：第一次检查（无锁）—— 大多数情况下 `ignore` 已存在，直接返回
- **第 51 行**：`synchronized (ignoreTables)` 锁的是 `HashMap` 对象本身，而不是 `this`（`TenantDatabaseInterceptor` 实例），缩小锁的粒度，其他线程可以并发调用 `ignoreTable` 的同步块之外的方法
- **关键设计**：这是个典型的 **DCL 懒加载模式**——只有第一次访问某张表时才计算，后续直接命中缓存
- **可改进**：第 50 行的 `computeIgnoreTable` 在锁外执行，若计算昂贵可优化为 `ConcurrentHashMap.computeIfAbsent`

### 3.2 IoT WebSocket 重连的 ReentrantLock + tryLock

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-biz/src/main/java/cn/iocoder/yudao/module/iot/service/rule/data/action/IotWebSocketDataRuleAction.java`
**核心代码**（行 18-39, 100-129）：

```java
18  import java.util.concurrent.ConcurrentHashMap;
19  import java.util.concurrent.TimeUnit;
20  import java.util.concurrent.locks.ReentrantLock;
21
22  /**
23   * WebSocket 的 IotDataRuleAction 实现类
24   */
25  @Component
26  @Slf4j
27  public class IotWebSocketDataRuleAction extends
28          IotDataRuleCacheableAction<IotDataSinkWebSocketConfig, IotWebSocketClient> {
29
30      /** 锁等待超时时间（毫秒） */
31      private static final long LOCK_WAIT_TIME_MS = 5000;
32
33      /** 重连锁，key 为 WebSocket 服务器地址 */
34      private final ConcurrentHashMap<String, ReentrantLock> reconnectLocks = new ConcurrentHashMap<>();
```

```java
100 private void reconnectWithLock(IotWebSocketClient webSocketClient,
101                                IotDataSinkWebSocketConfig config) throws Exception {
102     // 每个 WebSocket 服务器地址一把锁：避免锁粒度太粗
103     ReentrantLock lock = reconnectLocks.computeIfAbsent(
104             config.getServerUrl(), k -> new ReentrantLock());
105     boolean acquired = false;
106     try {
107         // 5 秒超时获取锁——这就是用 ReentrantLock 而不是 synchronized 的原因
108         acquired = lock.tryLock(LOCK_WAIT_TIME_MS, TimeUnit.MILLISECONDS);
109         if (!acquired) {
110             throw new RuntimeException("获取 WebSocket 重连锁超时，服务器: "
111                     + config.getServerUrl());
112         }
113         // 双重检查：获取锁后再次检查连接状态
114         if (!webSocketClient.isConnected()) {
115             log.warn("[reconnectWithLock][WebSocket 连接已断开，尝试重新连接，服务器: {}]",
116                     config.getServerUrl());
117             webSocketClient.connect();
118         }
119     } catch (InterruptedException e) {
120         Thread.currentThread().interrupt();
121         throw new RuntimeException("获取 WebSocket 重连锁被中断，服务器: "
122                 + config.getServerUrl(), e);
123     } finally {
124         // isHeldByCurrentThread 检查防止异常路径下误释放其他线程的锁
125         if (acquired && lock.isHeldByCurrentThread()) {
126             lock.unlock();
127         }
128     }
129 }
```

**解读**：
- **第 31 行**：`5s` 超时是核心需求 —— `synchronized` 不支持超时，必须用 `ReentrantLock.tryLock(time)`
- **第 33-34 行**：`ConcurrentHashMap<String, ReentrantLock>` 按服务器地址分桶加锁，**细粒度**：不同 WebSocket 服务器之间互不阻塞
- **第 108 行**：`tryLock(time, unit)` 返回 boolean —— 超时返回 false，不阻塞
- **第 114 行**：获取锁后**二次检查** `isConnected()` —— 避免其他线程已经重连过，本线程重复 connect
- **第 120 行**：InterruptedException 一定要**重新设置中断标志位** `Thread.currentThread().interrupt()`，否则上层调用方无法感知中断
- **第 125 行**：`isHeldByCurrentThread()` 双重保险 —— 若 tryLock 失败但 acquired 仍为 false，绝不能 unlock

### 3.3 分布式定时任务：Redisson RLock

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
**核心代码**（行 38-62）：

```java
38  @Scheduled(cron = "35 * * * * ?")  // 每分钟第 35 秒执行
39  public void messageResend() {
40      // 获取分布式锁：保证多实例部署时只有一个节点执行本任务
41      RLock lock = redissonClient.getLock(resendLockKey);
42      if (lock.tryLock()) {                                  // 非阻塞尝试
43          try {
44              execute();
45          } catch (Exception ex) {
46              log.error("[messageResend][执行异常][lockKey={}]", resendLockKey, ex);
47          } finally {
48              if (lock.isHeldByCurrentThread()) {           // 防止误释放
49                  lock.unlock();
50              }
51          }
52      } else {
53          log.debug("[messageResend][未获取到锁，跳过本轮][lockKey={}]", resendLockKey);
54      }
55  }
```

**解读**：
- **第 38 行**：`@Scheduled` 是 Spring 的定时任务注解，多实例部署时每个节点都会触发
- **第 41 行**：`RLock` 是 Redisson 的分布式锁接口
- **第 42 行**：`tryLock()` 无参版本默认 **立即返回**，不等 —— 拿不到就跳过本轮（适合"尽力而为"的清理任务）
- **第 48 行**：`isHeldByCurrentThread()` 是防御性编程，防止异常路径下释放了其他线程持有的锁（特别是 `tryLock(time, unit)` 版本容易出现）
- **设计意图**：MQ 消息重发任务不需要严格不丢，**多实例并发重复执行的成本 >> 单实例执行的成本**，所以用分布式锁保证单点执行

### 3.4 Lock4j 注解式分布式锁

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/lock4j/config/YudaoLock4jConfiguration.java`
**核心代码**：

```java
9  @AutoConfiguration(before = LockAutoConfiguration.class)
10 @ConditionalOnClass(name = "com.baomidou.lock.annotation.Lock4j")
11 public class YudaoLock4jConfiguration {
12
13     @Bean
14     public DefaultLockFailureStrategy lockFailureStrategy() {
15         return new DefaultLockFailureStrategy();
16     }
17 }
```

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/lock4j/core/DefaultLockFailureStrategy.java`
**核心代码**：

```java
13 @Slf4j
14 public class DefaultLockFailureStrategy implements LockFailureStrategy {
15
16     @Override
17     public void onLockFailure(String key, Method method, Object[] arguments) {
18         log.debug("[onLockFailure][线程:{} 获取锁失败，key:{} 获取失败:{} ]",
19                 Thread.currentThread().getName(), key, arguments);
20         throw new ServiceException(GlobalErrorCodeConstants.LOCKED);
21     }
22 }
```

**解读**：
- **`@Lock4j`** 是 MyBatis-Plus 生态的注解式分布式锁（基于 Redisson；分布式锁理论见 [分布式锁要求](../../_common/04-distributed-locks/01-requirements.md) / [Redis Redlock](../../_common/04-distributed-locks/02-redis-redlock.md)，ruoyi 封装见 [17-distributed-lock](../03-spring-boot-starters/17-distributed-lock.md)）
- ruoyi-vue-pro 在框架层面提供了**统一失败策略**：获取不到锁时抛出 `ServiceException`（业务异常），转换为统一的 `LOCKED` 错误码返回给前端
- **典型用法**：
  ```java
  @Lock4j(keys = "#orderId", expire = 60000, acquireTimeout = 3000)
  public void createOrder(Long orderId) {
      // 业务逻辑
  }
  ```
- ruoyi-vue-pro **业务代码中目前未直接使用 @Lock4j 注解**，它作为框架能力提供给后续扩展

## 4. 关键要点总结

- **synchronized**：JVM 内置，自动释放，适合简单同步；JDK 6+ 已优化（偏向锁/轻量级锁/重量级锁升级）
- **ReentrantLock**：API 级显式锁，支持 tryLock/超时/中断/公平/多 Condition
- **ReadWriteLock**：读写分离，读多写少场景性能提升 5~10 倍
- **选择原则**：简单场景用 synchronized；需要超时/中断/公平 → ReentrantLock；读多写少 → ReadWriteLock
- **多实例部署必须用分布式锁**（Redisson RLock），单机锁无效
- **tryLock(time) 后必须 `isHeldByCurrentThread()` 再 unlock**，防止误释放

## 5. 练习题

### 练习 1：基础（必做）

实现一个**线程安全的计数器**：
- 用 `synchronized` 实现 `increment()` 和 `get()`
- 用 `ReentrantLock` 实现 `increment()` 和 `get()`
- 用 `AtomicInteger` 实现同样的功能（提示：[28-atomic.md](./28-atomic.md)）
- 比较三者的性能

### 练习 2：进阶

阅读 `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-biz/src/main/java/cn/iocoder/yudao/module/iot/service/rule/data/action/IotWebSocketDataRuleAction.java`，画出 `reconnectWithLock` 的完整时序图，标注锁、超时、二次检查的细节。

### 练习 3：挑战（选做）

实现一个**简易分布式锁**（仅 Redis SET NX PX），要求：
- `tryLock(key, ttl)` 返回 boolean
- `unlock(key)` 只能释放自己加的锁（用 Lua 脚本保证 check-and-delete 原子性）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-biz/src/main/java/cn/iocoder/yudao/module/iot/service/rule/data/action/IotWebSocketDataRuleAction.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/mq/redis/core/job/RedisPendingMessageResendJob.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/lock4j/config/YudaoLock4jConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/lock4j/core/DefaultLockFailureStrategy.java`
- 《Java 并发编程实战》第 13 章
- [Redisson 官方文档](https://redisson.org/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13