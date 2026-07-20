# 1.4.7 ThreadLocal 与 InheritableThreadLocal

> 掌握 ThreadLocal 的内存模型与常见陷阱，理解 ruoyi-vue-pro 为什么用 TransmittableThreadLocal 解决 @Async 跨线程传递问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ThreadLocal 的内部实现（ThreadLocalMap、Entry、弱引用 Key）
- 知道 InheritableThreadLocal 的局限（线程池下失效）
- 理解 ruoyi-vue-pro 选用 TransmittableThreadLocal（Alibaba TTL）的原因
- 写出无内存泄漏的 ThreadLocal 代码（try-finally clear）

## 📚 前置知识

- [25-thread.md](./25-thread.md)：线程基础
- [26-thread-pool.md](./26-thread-pool.md)：线程池
- [31-concurrent-collections.md](./31-concurrent-collections.md)：并发集合

## 1. 核心概念

### 1.1 ThreadLocal 的作用

**让每个线程持有自己独立的变量副本**，避免共享变量带来的同步问题。

```java
ThreadLocal<User> currentUser = new ThreadLocal<>();

// 在线程 A 中设置
currentUser.set(userA);  // 只有线程 A 能看到 userA

// 在线程 B 中设置
currentUser.set(userB);  // 只有线程 B 能看到 userB，互不影响
```

**典型使用场景**：
- **请求上下文**：当前用户、租户 ID、TraceID
- **事务上下文**：Spring `@Transactional` 用 ThreadLocal 存 Connection
- **SimpleDateFormat**：每个线程一个实例，避免 synchronized

### 1.2 内部实现：ThreadLocalMap

```
Thread (线程对象)
├── threadLocals: ThreadLocalMap
│     ├── Entry[] table
│     │     ├── Entry[0]: key=ThreadLocal#1, value=UserA
│     │     ├── Entry[1]: key=ThreadLocal#2, value=OrderId
│     │     └── ...
│     └── ...
└── ...
```

**Entry 的 Key 是弱引用**：
```java
static class Entry extends WeakReference<ThreadLocal<?>> {
    Object value;
    Entry(ThreadLocal<?> k, Object v) {
        super(k);  // Key 是弱引用
        value = v; // Value 是强引用！
    }
}
```

**为什么 Key 弱引用？**
- 防止 ThreadLocal 对象本身无法 GC（如果 ThreadLocal 没有外部强引用）
- **但 Value 仍是强引用**，必须手动 `remove()`，否则即使 ThreadLocal 被 GC，value 还在

### 1.3 内存泄漏与正确清理

```
ThreadLocal tl = new ThreadLocal();
tl.set(new byte[10 * 1024 * 1024]);  // 10MB

tl = null;  // tl 失去强引用 → 下次 GC 时 Entry 的弱引用 Key 被回收
            // 但 value(byte[10MB]) 仍被 Thread → ThreadLocalMap → Entry.value 强引用！
            // 若线程存活（如线程池核心线程），value 永远不释放 → 内存泄漏
```

**正确做法**：
```java
try {
    tl.set(value);
    // 业务逻辑
} finally {
    tl.remove();  // 必须 remove！
}
```

### 1.4 InheritableThreadLocal：父子线程传递

```java
InheritableThreadLocal<String> itl = new InheritableThreadLocal<>();

// 主线程
itl.set("parent-value");

// 子线程会自动继承
new Thread(() -> {
    System.out.println(itl.get());  // "parent-value"
}).start();
```

**实现原理**：子线程创建时，`Thread.init()` 会把父线程的 `inheritableThreadLocals` 复制到子线程。

**致命缺陷**：**线程池下失效**！
```java
ExecutorService pool = Executors.newFixedThreadPool(2);

// 主线程设置
itl.set("parent-value");

// 提交任务（线程池复用 worker-1，可能已经跑过别的任务）
pool.submit(() -> {
    System.out.println(itl.get());  // 可能是 null（旧任务残留）或别的值
});
```

### 1.5 TransmittableThreadLocal（Alibaba TTL）

**解决线程池下 ThreadLocal 传递问题**：
- 任务提交时：捕获当前线程的 TTL 值
- 任务执行前：把值恢复到执行线程
- 任务执行后：清空

**使用方法**：
```xml
<!-- 1. 引入依赖 -->
<dependency>
    <groupId>com.alibaba.ttl</groupId>
    <artifactId>transmittable-thread-local</artifactId>
</dependency>
```

```bash
# 2. 启动时加 -javaagent 参数
java -javaagent:transmittable-thread-local-agent.jar -jar app.jar
```

```java
// 3. 包装线程池
ExecutorService pool = TtlExecutors.getTtlExecutorService(Executors.newFixedThreadPool(2));

// 或替换 Runnable
Runnable task = TtlRunnable.get(originalRunnable);
```

**TTL Agent 的核心**：`TtlTransformer` 在类加载时改写 `Runnable.run()` 和 `Callable.call()`，在执行前后自动捕获/恢复 ThreadLocal 值。

### 1.6 ruoyi-vue-pro 中的 TTL 实践

ruoyi-vue-pro 在 **租户上下文、安全上下文、数据权限上下文** 三大场景统一使用 `TransmittableThreadLocal`，保证跨 `@Async` / MQ 消费者 / 定时任务时上下文不丢失（多租户理论见 [多租户](../../_common/08-authorization/05-multi-tenant.md)，ruoyi 租户见 [33-tenant](../03-spring-boot-starters/40-tenant.md)；`@Async` 见 [22-async](../02-spring-boot/26-async.md)）。

## 2. 代码示例

### 2.1 基础：用户上下文持有

```java
// 文件：UserContextHolder.java
public class UserContextHolder {
    private static final ThreadLocal<Long> USER_ID = new ThreadLocal<>();

    public static void setUserId(Long userId) {
        USER_ID.set(userId);
    }

    public static Long getUserId() {
        return USER_ID.get();
    }

    public static Long requireUserId() {
        Long userId = USER_ID.get();
        if (userId == null) {
            throw new IllegalStateException("未登录");
        }
        return userId;
    }

    public static void clear() {
        USER_ID.remove();  // 必须 remove！
    }
}

// 在 Spring 拦截器中使用
public class AuthInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        Long userId = parseToken(request.getHeader("Authorization"));
        UserContextHolder.setUserId(userId);
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                 Object handler, Exception ex) {
        UserContextHolder.clear();  // 请求结束后清理，防止线程复用时泄漏
    }
}
```

### 2.2 InheritableThreadLocal 与线程池的陷阱

```java
// 文件：InheritableTLPitfall.java
public class InheritableTLPitfall {
    public static void main(String[] args) throws Exception {
        InheritableThreadLocal<String> itl = new InheritableThreadLocal<>();

        // 主线程设置
        itl.set("MAIN");

        ExecutorService pool = Executors.newFixedThreadPool(2);

        // 第一个任务：在 worker-1 上设置"Task1"
        pool.submit(() -> {
            itl.set("Task1");
            System.out.println("Task1: " + itl.get());  // Task1
        }).get();

        // 第二个任务：worker-1 被复用，但 itl 已经是"Task1"了！
        pool.submit(() -> {
            System.out.println("Task2: " + itl.get());  // Task1（污染！）或 null
        }).get();

        // ✅ 正确做法：用 TransmittableThreadLocal 或手动清理
        pool.shutdown();
    }
}
```

### 2.3 TransmittableThreadLocal 跨线程池传递

```java
// 文件：TTLDemo.java
import com.alibaba.ttl.TransmittableThreadLocal;
import com.alibaba.ttl.threadpool.TtlExecutors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class TTLDemo {
    // 用 TransmittableThreadLocal 替代 ThreadLocal
    private static final ThreadLocal<String> CONTEXT = new TransmittableThreadLocal<>();

    public static void main(String[] args) throws Exception {
        // 包装线程池
        ExecutorService pool = TtlExecutors.getTtlExecutorService(
                Executors.newFixedThreadPool(2));

        // 主线程设置
        CONTEXT.set("MAIN-USER");

        // 提交 5 个任务，worker-1/worker-2 会被复用
        for (int i = 0; i < 5; i++) {
            final int taskId = i;
            pool.submit(() -> {
                System.out.println("Task " + taskId + ": " + CONTEXT.get());
                // 输出全部是 "MAIN-USER"，跨线程保持一致
            }).get();
        }

        pool.shutdown();
    }
}
```

## 3. 关键要点总结

- **ThreadLocal**：线程隔离的变量副本，内部用 ThreadLocalMap 存储
- **内存泄漏**：Entry 的 Key 弱引用但 Value 强引用，必须 `remove()`
- **InheritableThreadLocal**：父子线程传递，但**线程池下失效**（线程复用时已污染）
- **TransmittableThreadLocal**：Alibaba TTL 解决线程池下 ThreadLocal 传递问题，需要 `-javaagent` 启动参数
- **ruoyi-vue-pro** 在租户、安全、数据权限三大上下文用 TTL；AOP 日志切面用普通 ThreadLocal
- **声明为 `ThreadLocal<T>` 接口，创建为 `new TransmittableThreadLocal<>()`**：业务代码与 TTL 解耦

---

**文档版本**：v1.0
**最后更新**：2026-07-13
