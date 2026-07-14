# 1.4.7 ThreadLocal 与 InheritableThreadLocal

> 掌握 ThreadLocal 的内存模型与常见陷阱，理解 ruoyi-vue-pro 为什么用 TransmittableThreadLocal 解决 @Async 跨线程传递问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ThreadLocal 的内部实现（ThreadLocalMap、Entry、弱引用 Key）
- 知道 InheritableThreadLocal 的局限（线程池下失效）
- 理解 ruoyi-vue-pro 选用 TransmittableThreadLocal（Alibaba TTL）的原因
- 写出无内存泄漏的 ThreadLocal 代码（try-finally clear）

## 📚 前置知识

- [21-thread.md](./21-thread.md)：线程基础
- [22-thread-pool.md](./22-thread-pool.md)：线程池
- [26-concurrent-collections.md](./26-concurrent-collections.md)：并发集合

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

ruoyi-vue-pro 在 **租户上下文、安全上下文、数据权限上下文** 三大场景统一使用 `TransmittableThreadLocal`，保证跨 `@Async` / MQ 消费者 / 定时任务时上下文不丢失。

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 租户上下文：TransmittableThreadLocal

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
**核心代码**（行 11-48）：

```java
11  public class TenantContextHolder {
12
13      /**
14       * 当前租户编号
15       */
16      private static final ThreadLocal<Long> TENANT_ID = new TransmittableThreadLocal<>();
17
18      /**
19       * 是否忽略租户
20       */
21      private static final ThreadLocal<Boolean> IGNORE = new TransmittableThreadLocal<>();
22
23      /**
24       * 获得租户编号。如果不存在，则抛出 NullPointerException 异常
25       */
26      public static Long getRequiredTenantId() {
27          Long tenantId = getTenantId();
28          if (tenantId == null) {
29              throw new NullPointerException("TenantContextHolder 不存在租户编号！可参考文档："
30                  + DocumentEnum.TENANT.getUrl());
31          }
32          return tenantId;
33      }
34
35      public static void setTenantId(Long tenantId) {
36          TENANT_ID.set(tenantId);
37      }
38
39      // ... getTenantId / isIgnore / setIgnore / clear 略
40
41      public static void clear() {
42          TENANT_ID.remove();    // 必须 remove！
43          IGNORE.remove();
44      }
45  }
```

**解读**：
- **第 16、21 行**：声明类型是 `ThreadLocal<T>`（接口），实际创建用 `TransmittableThreadLocal<>`（实现）
- **这种"声明为接口、创建为实现"的写法**：业务代码只知道是 ThreadLocal，不知道有 TTL 依赖，便于测试和替换
- **第 30 行**：错误信息附带文档链接，引导开发者自助排查
- **第 42-43 行**：clear() 同时清理多个 ThreadLocal，防止内存泄漏
- **真实调用链**：HTTP 请求 → `TenantContextWebFilter` 读取 `tenant-id` header → `setTenantId()` → MyBatis 拦截器读 `getRequiredTenantId()` 拼接 SQL

### 3.2 安全上下文：Spring Security 策略替换

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/context/TransmittableThreadLocalSecurityContextHolderStrategy.java`
**核心代码**（行 1-46）：

```java
1   package cn.iocoder.yudao.framework.security.core.context;
2
3   import com.alibaba.ttl.TransmittableThreadLocal;
4   import org.springframework.security.core.context.SecurityContext;
5   import org.springframework.security.core.context.SecurityContextHolderStrategy;
6   import org.springframework.security.core.context.SecurityContextImpl;
7   import org.springframework.util.Assert;
8
9   /**
10   * 基于 TransmittableThreadLocal 实现的 Security Context 持有者策略
11   * 目的是，避免 @Async 等异步执行时，原生 ThreadLocal 的丢失问题
12   */
13  public class TransmittableThreadLocalSecurityContextHolderStrategy
14          implements SecurityContextHolderStrategy {
15
16      /**
17       * 使用 TransmittableThreadLocal 作为上下文
18       */
19      private static final ThreadLocal<SecurityContext> CONTEXT_HOLDER =
20              new TransmittableThreadLocal<>();
21
22      @Override
23      public void clearContext() {
24          CONTEXT_HOLDER.remove();
25      }
26
27      @Override
28      public SecurityContext getContext() {
29          SecurityContext ctx = CONTEXT_HOLDER.get();
30          if (ctx == null) {
31              ctx = createEmptyContext();
32              CONTEXT_HOLDER.set(ctx);
33          }
34          return ctx;
35      }
36
37      @Override
38      public void setContext(SecurityContext context) {
39          Assert.notNull(context, "Only non-null SecurityContext instances are permitted");
40          CONTEXT_HOLDER.set(context);
41      }
42
43      @Override
44      public SecurityContext createEmptyContext() {
45          return new SecurityContextImpl();
46      }
47  }
```

**解读**：
- **第 11 行（注释）**：直接说明设计动机 —— "避免 @Async 等异步执行时，原生 ThreadLocal 的丢失问题"
- **第 19-20 行**：实现 `SecurityContextHolderStrategy` 接口，把 Spring Security 默认的 ThreadLocal 策略替换为 TTL 策略
- **第 29-34 行**：经典的 `get → if null → set` 模式，每次请求初始化一次空 context
- **配套配置**（`YudaoSecurityAutoConfiguration.securityContextHolderMethodInvokingFactoryBean()`）：通过反射调用 `SecurityContextHolder.setStrategyName(...)` 切换策略
- **业务影响**：用户在 `@Async` 异步方法中也能通过 `SecurityContextHolder.getContext().getAuthentication()` 拿到登录用户，否则拿到 null

### 3.3 数据权限上下文：嵌套注解栈

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`
**核心代码**（行 1-53）：

```java
1   package cn.iocoder.yudao.framework.datapermission.core.aop;
2
3   import cn.iocoder.yudao.framework.datapermission.core.annotation.DataPermission;
4   import com.alibaba.ttl.TransmittableThreadLocal;
5
6   import java.util.LinkedList;
7   import java.util.List;
8
9   /**
10   * {@link DataPermission} 注解的 Context 上下文
11   */
12  public class DataPermissionContextHolder {
13
14      /**
15       * 使用 List 的原因，可能存在方法的嵌套调用
16       */
17      private static final ThreadLocal<LinkedList<DataPermission>> DATA_PERMISSIONS =
18              TransmittableThreadLocal.withInitial(LinkedList::new);
19
20      public static DataPermission get() {
21          return DATA_PERMISSIONS.get().peekLast();
22      }
23
24      public static void add(DataPermission dataPermission) {
25          DATA_PERMISSIONS.get().addLast(dataPermission);
26      }
27
28      public static DataPermission remove() {
29          DataPermission dataPermission = DATA_PERMISSIONS.get().removeLast();
30          // 无元素时，清空 ThreadLocal
31          if (DATA_PERMISSIONS.get().isEmpty()) {
32              DATA_PERMISSIONS.remove();
33          }
34          return dataPermission;
35      }
36  }
```

**解读**：
- **第 17-18 行**：`TransmittableThreadLocal.withInitial(LinkedList::new)` —— 使用工厂方法，第一次访问时自动初始化为空的 LinkedList
- **LinkedList 作为栈**：支持嵌套的 `@DataPermission` 注解（如 A 方法有，B 方法也有，A 调 B 时 A 的 annotation 仍保留）
- **第 29-33 行**：pop 时若栈空，调用 `remove()` 清理 ThreadLocal，防止内存泄漏（重要细节！）
- **TTL 的关键作用**：AOP 拦截器解析 SQL 时若进入 `@Async`，仍能取到正确的权限注解

### 3.4 AOP 日志切面：简单 ThreadLocal

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/framework/order/core/aop/TradeOrderLogAspect.java`
**核心代码**（行 32-60）：

```java
32  public class TradeOrderLogAspect {
33
34      /**
35       * 用户编号
36       * 目前的使用场景：支付回调时，需要强制设置下用户编号
37       */
38      private static final ThreadLocal<Long> USER_ID = new ThreadLocal<>();
39      /**
40       * 用户类型
41       */
42      private static final ThreadLocal<Integer> USER_TYPE = new ThreadLocal<>();
43      /**
44       * 订单编号
45       */
46      private static final ThreadLocal<Long> ORDER_ID = new ThreadLocal<>();
47      /**
48       * 操作前的状态
49       */
50      private static final ThreadLocal<Integer> BEFORE_STATUS = new ThreadLocal<>();
51      /**
52       * 操作后的状态
53       */
54      private static final ThreadLocal<Integer> AFTER_STATUS = new ThreadLocal<>();
55      /**
56       * 拓展参数 Map，用于格式化操作内容
57       */
58      private static final ThreadLocal<Map<String, Object>> EXTS = new ThreadLocal<>();
59
60      // ... setter 在 Around 前置阶段填充，@AfterReturning 读取，finally clear()
61  }
```

**解读**：
- 这里用**普通 ThreadLocal 而非 TransmittableThreadLocal**，原因是：
  - 切面方法本身是同步的（不是 @Async）
  - 切面方法不会跨越线程边界
  - 简单 ThreadLocal 性能略好（无 TTL 包装开销）
- **6 个 ThreadLocal**：每个保存订单状态流转的一个字段，最终拼接成"用户 X 把订单 Y 从状态 A 改为状态 B"的日志
- **最佳实践**：每个 ThreadLocal 字段都有清晰注释 + setter/getter + try-finally clear，避免内存泄漏

## 4. 关键要点总结

- **ThreadLocal**：线程隔离的变量副本，内部用 ThreadLocalMap 存储
- **内存泄漏**：Entry 的 Key 弱引用但 Value 强引用，必须 `remove()`
- **InheritableThreadLocal**：父子线程传递，但**线程池下失效**（线程复用时已污染）
- **TransmittableThreadLocal**：Alibaba TTL 解决线程池下 ThreadLocal 传递问题，需要 `-javaagent` 启动参数
- **ruoyi-vue-pro** 在租户、安全、数据权限三大上下文用 TTL；AOP 日志切面用普通 ThreadLocal
- **声明为 `ThreadLocal<T>` 接口，创建为 `new TransmittableThreadLocal<>()`**：业务代码与 TTL 解耦

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `RequestContextHolder`：
- 提供 `setRequestId(String)` / `getRequestId()` / `clear()`
- 在 Spring 拦截器中 preHandle 设置，afterCompletion 清理
- 故意在 clear() 中不调用 remove()，模拟内存泄漏，并用 VisualVM 观察线程的 ThreadLocalMap 残留

### 练习 2：进阶

阅读 `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`，为什么用 `LinkedList` 而不是单个 `DataPermission`？用伪代码写出嵌套调用场景。

### 练习 3：挑战（选做）

实现一个**简易 TransmittableThreadLocal**（不依赖 Alibaba TTL）：
- 用 `WeakHashMap<Thread, Object>` 存储
- 提供 `set(value)` / `get()` / 跨线程的 capture/restore 方法
- 提示：参考 TTL 源码 100 行可实现最小可用版本

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/context/TransmittableThreadLocalSecurityContextHolderStrategy.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/framework/order/core/aop/TradeOrderLogAspect.java`
- [Alibaba TTL GitHub](https://github.com/alibaba/transmittable-thread-local)
- 《Java 并发编程实战》第 3 章，Brian Goetz 等

---

**文档版本**：v1.0
**最后更新**：2026-07-13