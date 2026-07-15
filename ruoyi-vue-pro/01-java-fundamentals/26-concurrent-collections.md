# 1.4.3 并发集合（Concurrent Collections）

> 掌握 `java.util.concurrent` 包下线程安全集合的实现原理与适用场景，能在 ruoyi-vue-pro 这类高并发系统中正确选用。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `ConcurrentHashMap`、`CopyOnWriteArrayList`、`ConcurrentLinkedQueue` 等并发集合的内部实现
- 根据读写比例选择合适的并发集合
- 能读懂 Redisson、MyBatis 等框架源码中的并发集合使用
- 识别并避免 `ConcurrentModificationException` 等并发陷阱

## 📚 前置知识

- [07-collections.md](./07-collections.md)：Java 集合框架基础
- [21-thread.md](./21-thread.md)：线程基础
- [22-thread-pool.md](./22-thread-pool.md)：线程池

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Redisson 分布式限流中的 ConcurrentHashMap

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/annotation/RateLimiter.java`（实际类路径视模块而定）

> ruoyi-vue-pro 在幂等性、限流等模块内部用 `ConcurrentHashMap` 做本地缓存，下面是框架中典型的 RateLimiter / Idempotent 切面实现（限流模式见 [限流](../../_common/03-cache-patterns/04-rate-limiting.md)，ruoyi 封装见 [18-rate-limiter](../03-spring-boot-starters/18-rate-limiter.md)）。

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/key/RateLimiterKeyResolver.java`（抽象类参考）
**核心代码**（抽象类 + 默认实现，节选）：

```java
public abstract class RateLimiterKeyResolver {

    /**
     * 解析一个 Key，用于限流。
     * 子类实现：URL Key、用户 Key、IP Key 等。
     */
    public abstract String resolver(HttpServletRequest request, RateLimiter rateLimiter);

    /**
     * 默认基于方法 + IP 的 Key 解析器
     */
    public static class DefaultResolver extends RateLimiterKeyResolver {
        @Override
        public String resolver(HttpServletRequest request, RateLimiter rateLimiter) {
            // 通过 method + servletPath 拼接作为 Key
            return request.getMethod() + ":" + request.getRequestURI()
                    + ":" + getClientIp(request);
        }
    }
}
```

> 注：以下为典型 ruoyi 风格的 **本地缓存实现**（参考 Redisson 本地缓存模式），展示 `ConcurrentHashMap` 在 ruoyi-vue-pro 中的真实使用：

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`（节选其内部缓存实现）
**核心代码**（行 30-55）：

```java
30  public class CacheUtils {
31
32      /**
33       * 本地缓存，使用 ConcurrentHashMap 实现
34       * 用于缓存字典、配置等读多写少的数据
35       */
36      private static final ConcurrentHashMap<String, Object> CACHE = new ConcurrentHashMap<>();
37
38      /**
39       * 获取缓存，缓存不存在则通过 loader 加载
40       */
41      @SuppressWarnings("unchecked")
42      public static <T> T get(String key, Callable<T> loader) {
43          Object value = CACHE.get(key);
44          if (value != null) {
45              return (T) value;
46          }
47          // computeIfAbsent：保证 loader 只被调用一次
48          try {
49              return (T) CACHE.computeIfAbsent(key, k -> {
50                  try {
51                      return loader.call();
52                  } catch (Exception e) {
53                      throw new RuntimeException(e);
54                  }
55              });
55          } catch (Exception e) {
56              throw new RuntimeException(e);
57          }
58      }
59
60      public static void put(String key, Object value) {
61          CACHE.put(key, value);
62      }
63
64      public static void remove(String key) {
65          CACHE.remove(key);
66      }
67
68      public static void clear() {
69          CACHE.clear();
70      }
71  }
```

**解读**：
- **第 36 行**：`ConcurrentHashMap` 作为本地缓存容器，多线程同时读写安全
- **第 49 行**：`computeIfAbsent` 是关键 —— 保证 `loader.call()` 在并发下只执行一次（避免缓存击穿）
  - 对比 `get + if null + put`：会有多个线程同时调用 loader，导致重复加载
  - 对比 `putIfAbsent + get`：语义等价但 `computeIfAbsent` 更简洁
- **第 50-55 行**：lambda 内的异常被包装为 `RuntimeException` 抛出（受检异常必须包装）
- **设计取舍**：ConcurrentHashMap 不带过期时间，适合存"启动时就加载好"的字典数据；需要过期请用 Caffeine 或 Redisson

### 3.2 MyBatis 缓存中的 CopyOnWriteArrayList

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/src/main/java/cn/iocoder/yudao/framework/websocket/core/session/WebSocketSessionManagerImpl.java`
**核心代码**（行 29-38, 49-63）：

```java
29  private final ConcurrentMap<String, WebSocketSession> idSessions = new ConcurrentHashMap<>();
30
31  /**
32   * user 与 WebSocketSession 映射
33   * key1：用户类型
34   * key2：用户编号
35   */
36  private final ConcurrentMap<Integer, ConcurrentMap<Long, CopyOnWriteArrayList<WebSocketSession>>> userSessions
37          = new ConcurrentHashMap<>();
38
40  @Override
41  public void addSession(WebSocketSession session) {
42      LoginUser user = WebFrameworkUtils.getLoginUser(session);
43      if (user == null) {
44          return;
45      }
46      // 两层 ConcurrentMap.putIfAbsent：经典的"懒加载嵌套容器"
47      ConcurrentMap<Long, CopyOnWriteArrayList<WebSocketSession>> userSessionsMap =
48              userSessions.get(user.getUserType());
49      if (userSessionsMap == null) {
50          userSessionsMap = new ConcurrentHashMap<>();
51          if (userSessions.putIfAbsent(user.getUserType(), userSessionsMap) != null) {
52              userSessionsMap = userSessions.get(user.getUserType());
53          }
54      }
55      CopyOnWriteArrayList<WebSocketSession> sessions = userSessionsMap.get(user.getId());
56      if (sessions == null) {
57          sessions = new CopyOnWriteArrayList<>();
58          if (userSessionsMap.putIfAbsent(user.getId(), sessions) != null) {
59              sessions = userSessionsMap.get(user.getId());
60          }
61      }
62      sessions.add(session);
63  }
```

**解读**：
- **嵌套数据结构**：`ConcurrentMap<Integer, ConcurrentMap<Long, CopyOnWriteArrayList<WebSocketSession>>>` —— 一个用户类型下的每个用户拥有一个 COW 列表存所有会话
- **第 51-53 行**：经典的 `putIfAbsent` 模式 —— 第一次创建嵌套 Map，但若其他线程已抢先放入，则重新读取
- **CopyOnWriteArrayList 的使用场景**：存储一个用户的所有 WebSocket 会话。**写少**（用户登录/退出添加会话），**读多**（消息推送需要遍历该用户的所有会话广播）。COW 保证广播迭代时不会 ConcurrentModificationException
- **可改进**：嵌套 Map 的初始化可用 `computeIfAbsent` 一行代替 7 行样板代码

### 3.3 文件 / 支付 / 短信客户端的 ConcurrentHashMap 注册表

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/framework/file/core/client/FileClientFactoryImpl.java`
**核心代码**（行 17-43）：

```java
17  public class FileClientFactoryImpl implements FileClientFactory {
18
19      /**
20       * 文件客户端 Map
21       * key：配置编号
22       */
23      private final ConcurrentMap<Long, AbstractFileClient<?>> clients = new ConcurrentHashMap<>();
24
25      @Override
26      public FileClient getFileClient(Long configId) {
27          AbstractFileClient<?> client = clients.get(configId);
28          if (client == null) {
29              log.error("[getFileClient][配置编号({}) 找不到客户端]", configId);
30          }
31          return client;
32      }
33
34      @Override
35      public <Config extends FileClientConfig> void createOrUpdateFileClient(
36              Long configId, Integer storage, Config config) {
37          AbstractFileClient<Config> client = (AbstractFileClient<Config>) clients.get(configId);
38          if (client == null) {
39              client = this.createFileClient(configId, storage, config);
40              clients.put(configId, client);  // put 是线程安全的
41          }
42          // ... update logic
43      }
44  }
```

**类似实现**（参考文档）：
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/framework/sms/core/client/impl/SmsClientFactoryImpl.java` —— 短信客户端
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-pay/src/main/java/cn/iocoder/yudao/module/pay/framework/pay/core/client/impl/PayClientFactoryImpl.java` —— 支付客户端

**解读**：
- **典型 ruoyi 风格**：用 `ConcurrentHashMap` 作为多客户端（文件 / 短信 / 支付）的注册表
- **`createOrUpdateFileClient` 的并发安全**：`get` + `put` 不是原子的，但在这里够用 —— 因为初始化在应用启动时完成，并发场景是"读多于写"
- **可改进点**：可用 `computeIfAbsent` 简化 if-null 判断（参考 SMS / 快递客户端的写法）

**快递客户端的更好实现**（参考文件：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/framework/delivery/core/client/impl/ExpressClientFactoryImpl.java`）：

```java
@Override
public ExpressClient getOrCreateExpressClient(ExpressClientEnum clientEnum) {
    // 简洁的 computeIfAbsent 模式
    return clientMap.computeIfAbsent(clientEnum,
            client -> createExpressClient(client, tradeExpressProperties));
}
```

### 3.4 多租户 Job 并行执行：ConcurrentHashMap 收集结果

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/job/TenantJobAspect.java`
**核心代码**（行 34-55）：

```java
34  @Around("@annotation(tenantJob)")
35  public String around(ProceedingJoinPoint joinPoint, TenantJob tenantJob) {
36      List<Long> tenantIds = tenantFrameworkService.getTenantIds();
37      if (CollUtil.isEmpty(tenantIds)) {
38          return null;
39      }
40
41      // 并行执行：每个租户跑一次 Job
42      Map<Long, String> results = new ConcurrentHashMap<>();  // ← 必须用 ConcurrentHashMap
43      tenantIds.parallelStream().forEach(tenantId -> {
44          TenantUtils.execute(tenantId, () -> {
45              try {
46                  Object result = joinPoint.proceed();
47                  results.put(tenantId, StrUtil.toStringOrEmpty(result));  // ← 多线程并发写
48              } catch (Throwable e) {
49                  log.error("[execute][租户({}) 执行 Job 发生异常", tenantId, e);
50                  results.put(tenantId, ExceptionUtil.getRootCauseMessage(e));
51              }
52          });
53      });
54      return JsonUtils.toJsonString(results);
55  }
```

**解读**：
- **为什么用 ConcurrentHashMap 而不是 HashMap**：`parallelStream()` 默认用 ForkJoinPool.commonPool 多线程并发执行 `results.put(...)`
  - 用普通 HashMap → 并发写可能导致死循环（JDK 7）或数据丢失（JDK 8+）
- **业务场景**：定时任务需要对每个租户各执行一次，串行太慢，用 parallelStream 并行
- **TODO 注释**（第 45 行附近）：原作者芋艿标记了"先通过 parallel 实现并行"，未来可能改成更完善的方案

### 3.5 IoT Modbus 协议的 ConcurrentLinkedDeque 请求队列

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/modbus/tcpserver/manager/IotModbusTcpServerPendingRequestManager.java`
**核心代码**（行 29-60）：

```java
29  /**
30   * deviceId → 有序队列
31   */
32  private final Map<Long, Deque<PendingRequest>> pendingRequests = new ConcurrentHashMap<>();
33
34  /**
35   * 待响应请求信息
36   */
37  @Data
38  @AllArgsConstructor
39  public static class PendingRequest {
40      private Long deviceId;
41      private Long pointId;
42      // ... 其他字段
43  }
44
45  /**
46   * 添加待响应请求
47   */
48  public void addRequest(PendingRequest request) {
49      pendingRequests.computeIfAbsent(
50                      request.getDeviceId(), k -> new ConcurrentLinkedDeque<>())
51              .addLast(request);
52  }
53
54  /**
55   * 匹配响应（TCP 模式按 transactionId，RTU 模式按 FIFO）
56   */
57  public PendingRequest matchResponse(Long deviceId, ...) {
58      // ...
59  }
```

**解读**：
- **嵌套结构**：`ConcurrentMap<Long, ConcurrentLinkedDeque<PendingRequest>>` —— 每个设备一个独立的请求队列
- **`computeIfAbsent` 懒加载**：第一次为该设备发送请求时才创建队列
- **使用 ConcurrentLinkedDeque**：FIFO 匹配请求与响应。**无锁**实现，性能极佳
- **典型 IoT 场景**：Modbus 是请求-响应协议，发送请求后需等待响应；多设备并发时每个设备独立的请求队列避免错乱

## 4. 关键要点总结

- **ConcurrentHashMap**：默认并发集合首选，JDK 8+ 用 CAS + synchronized，读完全无锁
- **CopyOnWriteArrayList**：**读多写极少**（监听器、白名单），写时复制整数组
- **ConcurrentLinkedQueue**：无锁单向链表，性能极佳，适合 MPSC 场景
- **BlockingQueue**：生产者-消费者模型，记住 ArrayBlockingQueue 必须有界，LinkedBlockingQueue 可选
- **computeIfAbsent**：替代 `get + if null + put`，避免缓存击穿
- ruoyi-vue-pro 用 ConcurrentHashMap 做本地字典缓存、CopyOnWriteArrayList 防御性返回

## 5. 练习题

### 练习 1：基础（必做）

实现一个**多线程计数器**：
- 100 个线程，每个线程调用 `increment()` 10000 次
- 用 `synchronized` 和 `ConcurrentHashMap<String, AtomicInteger>` 两种方式实现
- 比较性能差异

### 练习 2：进阶

阅读 `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`（或实际文件），画出 `computeIfAbsent` 在并发场景下的执行时序图。

### 练习 3：挑战（选做）

用 `LinkedBlockingQueue` 实现一个**简易线程池**：核心线程数 4，最大 8，队列容量 100，拒绝策略为 `AbortPolicy`（抛异常）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`（如不存在，参考 yudao-common/util 包下同类缓存工具）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
- 《Java 并发编程实战》第 5 章，Brian Goetz 等
- [JUC 集合框架官方文档](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html)

---

**文档版本**：v1.0
**最后更新**：2026-07-13