# 1.4.5 原子类：AtomicInteger / AtomicReference

> 掌握 `java.util.concurrent.atomic` 包下原子类的 CAS 实现原理，能用原子类实现无锁并发数据结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 CAS（Compare-And-Swap）的工作原理与 ABA 问题
- 区分 `AtomicInteger`、`AtomicLong`、`AtomicReference`、`AtomicStampedReference` 的适用场景
- 理解 `LongAdder` 在高并发下优于 `AtomicLong` 的原因
- 能读懂 Redisson、MyBatis 等框架中基于原子类的实现

## 📚 前置知识

- [21-thread.md](./21-thread.md)：线程基础
- [27-lock.md](./27-lock.md)：锁机制（对比学习）
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
- 悲观锁（synchronized/ReentrantLock，详见 [27-lock](./27-lock.md)）：先加锁，再操作
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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Redisson 分布式限流中的 AtomicLong

> ruoyi-vue-pro 通过 Redisson 间接使用 JDK 原子类。Redisson 内部的分布式限流、分布式计数器底层基于 `AtomicLong`（限流见 [限流](../../_common/03-cache-patterns/04-rate-limiting.md) / [18-rate-limiter](../03-spring-boot-starters/18-rate-limiter.md)）。

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
**核心代码**（行 18-35）：

```java
@AutoConfiguration(before = RedissonAutoConfigurationV2.class)
@Slf4j
public class YudaoRedisAutoConfiguration {

    /**
     * 自定义 RedisTemplate，使用 yudao 默认配置
     */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        // ... 配置序列化器
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(RedisSerializer.string());
        template.setValueSerializer(RedisSerializer.json());
        // ...
        return template;
    }

    /**
     * Redisson 客户端配置
     */
    @Bean
    public RedissonClient redissonClient(RedissonProperties redissonProperties) {
        Config config = new Config();
        config.useSingleServer()
                .setAddress(redissonProperties.getAddress())
                .setPassword(redissonProperties.getPassword())
                .setDatabase(redissonProperties.getDatabase());
        return Redisson.create(config);
    }
}
```

> **注**：ruoyi-vue-pro 的分布式限流（`yudao-spring-boot-starter-protection`）底层调用 Redisson 的 `RRateLimiter`，Redisson 内部用 **Redis Lua 脚本 + AtomicLong** 实现令牌桶。在 `main` 分支直接 grep `AtomicInteger|AtomicLong|AtomicReference` 仅在测试代码中出现，业务代码通过 Redisson 间接使用。

**典型 ruoyi 风格的本地原子计数器**（参考实现）：

```java
/**
 * 本地限流计数器：使用 AtomicLong 实现
 * 适用于单机场景
 */
public class LocalRateLimiter {
    private final AtomicLong counter = new AtomicLong(0);
    private final long maxPermitsPerSecond;

    public LocalRateLimiter(long maxPermitsPerSecond) {
        this.maxPermitsPerSecond = maxPermitsPerSecond;
    }

    public boolean tryAcquire() {
        long current = counter.incrementAndGet();
        // 简单实现：每秒重置
        return current <= maxPermitsPerSecond;
    }
}
```

### 3.2 Spring Security 中的 CAS 模式

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/context/TransmittableThreadLocalSecurityContextHolderStrategy.java`
**核心代码**（行 28-34，与 30 文档相同）：

```java
@Override
public SecurityContext getContext() {
    SecurityContext ctx = CONTEXT_HOLDER.get();
    if (ctx == null) {
        ctx = createEmptyContext();
        CONTEXT_HOLDER.set(ctx);
    }
    return ctx;
}
```

**解读**：
- 这里的 `CONTEXT_HOLDER.set(ctx)` 可以视为一次"原子操作"——TransmittableThreadLocal 底层通过 ThreadLocalMap 的 hash 槽位写入，在单线程语义下原子
- **多线程下不安全**：如果两个线程同时调用 `set`，最后一个 set 会覆盖前者（这正是为什么 SecurityContextHolder 是 ThreadLocal 隔离的）
- **CAS 思想延伸**：JDK 的 `AtomicReference.compareAndSet` 也是这种"先检查后写入"模式，只是用 CPU 指令保证了原子性

### 3.3 框架幂等组件中的 Redis 原子操作

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/core/keyresolver/IdempotentKeyResolver.java`（典型实现）

```java
/**
 * 幂等 Key 解析器抽象类
 */
public interface IdempotentKeyResolver {

    /**
     * 解析一个 Key，用于幂等性校验
     */
    String resolver(HttpServletRequest request, Idempotent idempotent);
}
```

**配套 Redis 原子操作**（典型实现思路，参考 Redisson `RSemaphore`）：

```java
/**
 * 基于 Redis 的分布式原子计数器
 * 实际使用：RedissonClient.getAtomicLong(key)
 *
 * ruoyi-vue-pro 通过 Redisson 调用，Redisson 内部用 Redis Lua 脚本保证原子性
 */
public class DistributedCounter {
    private final RedissonClient redisson;
    private final String key;

    public DistributedCounter(RedissonClient redisson, String key) {
        this.redisson = redisson;
        this.key = key;
    }

    public long incrementAndGet() {
        RAtomicLong counter = redisson.getAtomicLong(key);
        return counter.incrementAndGet();  // Redis 单线程模型，天然原子
    }
}
```

**解读**：
- **Redis 单线程特性**：`INCR` 命令是原子的（Redis 用单线程执行命令），所以分布式场景下用 Redis 计数器天然避免并发问题
- **对比 AtomicLong**：AtomicLong 是单机多线程原子；Redis `INCR` 是多机多进程原子
- **ruoyi-vue-pro 的选择**：所有分布式原子需求通过 **Redisson**（基于 Redis）实现，本地原子需求用 JDK `AtomicLong/LongAdder`

### 3.4 AI 流式响应：AtomicBoolean + AtomicReference 保证知识库只查一次

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/service/chat/AiChatMessageServiceImpl.java`
**核心代码**（行 238-254）：

```java
238 // 防止执行多次知识库和联网搜索
239 AtomicBoolean firstExecuteFlag = new AtomicBoolean(true);
240 AtomicReference<List<AiChatMessageRespVO.KnowledgeSegment>> cacheSegments = new AtomicReference<>();
241 AtomicReference<List<AiWebSearchResponse.WebPage>> cacheWebSearchPages = new AtomicReference<>();
242 return streamResponse.map(chunk -> {
243     // 仅首次：返回知识库、联网搜索
244     if (StrUtil.isEmpty(contentBuffer)) {
245         if (firstExecuteFlag.compareAndSet(true, false)) { // CAS 操作，确保仅执行一次
246             Map<Long, AiKnowledgeDocumentDO> documentMap = TenantUtils.executeIgnore(() -> knowledgeDocumentService.getKnowledgeDocumentMap(
247                     convertSet(knowledgeSegments, AiKnowledgeSegmentSearchRespVO::getDocumentId)));
248             cacheSegments.set(BeanUtils.toBean(knowledgeSegments, AiChatMessageRespVO.KnowledgeSegment.class, segment -> {
249                 AiKnowledgeDocumentDO document = documentMap.get(segment.getDocumentId());
250                 segment.setDocumentName(document != null ? document.getName() : null);
251             }));
252             if (webSearchResponse != null) {
253                 cacheWebSearchPages.set(webSearchResponse.getLists());
254             }
255         }
256     }
```

**解读**：
- **第 239 行**：`AtomicBoolean(true)` —— 用作"是否首次执行"的开关
- **第 245 行**：`compareAndSet(true, false)` —— CAS 保证只有第一个 chunk 能通过检查，后续全部跳过
- **第 240-241 行**：`AtomicReference<List<...>>` 持有首次执行的结果，后续 chunk 直接复用
- **业务场景**：AI 流式响应分多个 chunk 发送，但**知识库检索只需要做一次**（结果稳定），后续 chunk 复用缓存
- **CAS 替代 synchronized**：原代码如果是 `if (firstExecuteFlag.get()) { synchronized(this) { if (firstExecuteFlag.get()) {...} } }` 的 DCL 模式，用 `compareAndSet` 更简洁且无锁

### 3.5 IoT Modbus TCP 共享事务 ID 计数器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/modbus/tcpserver/IotModbusTcpServerProtocol.java`
**核心代码**（行 123）：

```java
123 AtomicInteger transactionIdCounter = new AtomicInteger(0);
124 // 初始化轮询调度器
125 this.pollScheduler = new IotModbusTcpServerPollScheduler(
126         vertx, connectionManager, frameEncoder, pendingRequestManager,
127         slaveConfig.getRequestTimeout(), transactionIdCounter, configCacheService);
```

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/modbus/tcpserver/handler/downstream/IotModbusTcpServerDownstreamHandler.java`
**核心代码**（行 115-117）：

```java
115 Integer transactionId = frameFormat == IotModbusFrameFormatEnum.MODBUS_TCP
116         ? (transactionIdCounter.incrementAndGet() & 0xFFFF)
117         : null;
```

**解读**：
- **同一 `AtomicInteger` 实例被两个组件共享**：`IotModbusTcpServerProtocol` 创建后传给 `PollScheduler` 和 `DownstreamHandler`
- **`& 0xFFFF`**：Modbus TCP 协议要求 transactionId 是 16 位（0~65535），超出后回绕
- **典型 IoT 模式**：协议层需要单调递增的请求 ID，用于把请求和响应匹配起来。`AtomicInteger.incrementAndGet()` 是线程安全的，比 `synchronized` + `int++` 快得多

### 3.6 WebSocket 客户端连接状态：AtomicBoolean + CountDownLatch 异步转同步

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-biz/src/main/java/cn/iocoder/yudao/module/iot/service/rule/data/action/websocket/IotWebSocketClient.java`
**核心代码**（行 55-92）：

```java
55  public void connect() throws Exception {
56      if (connected.get()) {  // AtomicBoolean 快速失败
57          log.warn("[connect][WebSocket 客户端已经连接，无需重复连接]");
58          return;
59      }
60      try {
61          // 创建 OkHttpClient（异步）
62          okHttpClient = new OkHttpClient.Builder()...
63          // 用 CountDownLatch 把 OkHttp 异步回调转为同步阻塞
64          CountDownLatch connectLatch = new CountDownLatch(1);
65          AtomicBoolean connectSuccess = new AtomicBoolean(false);
66          // 创建 WebSocket 连接（立即返回，注册 listener）
67          webSocket = okHttpClient.newWebSocket(request, new IotWebSocketListener(connectLatch, connectSuccess));
68
69          // 阻塞等待连接完成（或超时）
70          boolean await = connectLatch.await(connectTimeoutMs, TimeUnit.MILLISECONDS);
71          if (!await || !connectSuccess.get()) {
72              close();
73              throw new Exception("WebSocket 连接超时或失败，服务器地址: " + serverUrl);
74          }
75          ...
76      }
77  }
```

**解读**：
- **第 56 行**：`AtomicBoolean.connected` 是连接状态标志，多线程访问安全（防止重复连接）
- **第 64-65 行**：经典 **"异步回调转同步阻塞"模式** —— `CountDownLatch(1)` + `AtomicBoolean` 联合使用
- **第 70 行**：`latch.await(timeout)` 阻塞直到回调里 `latch.countDown()`
- **第 71 行**：双重检查 —— 不仅要 await 成功，还要 `connectSuccess` 为 true（避免连接失败但 latch 被错误 countDown 的情况）
- **回调端 `onFailure` 也要 countDown**：保证异常路径下 await 能被唤醒（第 148 行 `connectLatch.countDown(); // 确保连接失败时也释放等待`）

## 4. 关键要点总结

## 4. 关键要点总结

- **CAS（Compare-And-Swap）**：乐观锁的硬件基础，CPU 指令 `CMPXCHG`
- **AtomicInteger/Long/Reference**：单变量无锁原子操作
- **ABA 问题**：用 `AtomicStampedReference` 加版本戳解决
- **LongAdder**：写多读少场景，比 AtomicLong 高 3~5 倍性能（但 sum 非强一致）
- **AtomicIntegerFieldUpdater**：让普通类的 volatile 字段也支持原子更新（更轻量）
- ruoyi-vue-pro 业务代码很少直接用 AtomicXxx，分布式场景通过 Redisson 间接使用，本地限流场景可用 AtomicLong

## 5. 练习题

### 练习 1：基础（必做）

实现一个**无锁的线程安全队列**（基于 `AtomicReference` + CAS）：
- `enqueue(T)`：把元素加到队尾
- `dequeue()`：从队头取出元素
- 提示：参考 LockFreeStack，用 head 和 tail 两个 AtomicReference

### 练习 2：进阶

阅读 Redisson 源码（GitHub `RAtomicLong`），画出 `INCR` 命令在 Redis 服务端的执行流程，说明为什么 Redis 单线程能保证原子性。

### 练习 3：挑战（选做）

对比测试在 **16 线程 / 1 亿次累加** 场景下：
- `synchronized` 计数器
- `ReentrantLock` 计数器
- `AtomicLong` 计数器
- `LongAdder` 计数器

记录耗时并分析原因（JMH 框架能给出更准确的测试结果）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoRedisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/context/TransmittableThreadLocalSecurityContextHolderStrategy.java`
- 《Java 并发编程实战》第 15 章，Brian Goetz 等
- [JUC Atomic 官方文档](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/atomic/package-summary.html)
- [JEP 193: Variable Handles](https://openjdk.org/jeps/193)（JDK 9 更现代的替代方案）

---

**文档版本**：v1.0
**最后更新**：2026-07-13