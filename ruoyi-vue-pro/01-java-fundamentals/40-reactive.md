# 1.4.10 Reactor / RxJava 响应式编程

> 理解响应式编程的核心思想，能读懂 Spring WebFlux、Reactor、RxJava 的源码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解响应式编程的四大核心：发布者 / 订阅者 / 订阅 / 信号
- 区分 Reactor 的 `Mono`（0..1）和 `Flux`（0..N）
- 掌握响应式编程的常用操作符（map、flatMap、filter 等）
- 在 ruoyi-vue-pro 中识别响应式编程的间接使用

## 📚 前置知识

- [09-stream-lambda.md](./09-stream-lambda.md)：Stream API 与 Lambda
- [25-thread.md](./25-thread.md)：线程基础
- [26-thread-pool.md](./26-thread-pool.md)：线程池
- [39-netty.md](./39-netty.md)：Netty（响应式常基于 Netty）

> **重要**：ruoyi-vue-pro 当前 `master` 分支是 **JDK 8 / Spring Boot 2.7 / Spring MVC**，但 `yudao-module-ai` 模块**重度使用 Reactor**（3 个 SSE Controller 返回 `Flux`，多个 AI 厂商适配器用 `Flux<ChatResponse>`）。本节结合 ruoyi 真实 AI 流式响应代码讲解。

## 1. 核心概念

### 1.1 什么是响应式编程？

**响应式编程（Reactive Programming）** 是一种**基于数据流和变化传播**的编程范式。

**核心思想**：把数据看作"流"，从上游到下游传播，**异步非阻塞**地处理。

**对比传统命令式**：

```java
// ❌ 命令式：阻塞、单线程
User user = userService.getById(1L);            // 阻塞等 DB 返回
List<Order> orders = orderService.listByUserId(user.getId());  // 再阻塞
return new UserDetailVO(user, orders);

// ✅ 响应式：非阻塞、链式
Mono<User> userMono = userService.getById(1L);
Mono<List<Order>> ordersMono = userMono.flatMap(user ->
    orderService.listByUserId(user.getId()));
return Mono.zip(userMono, ordersMono, UserDetailVO::new);
```

### 1.2 响应式宣言（Reactive Manifesto）

四大原则：
1. **响应（Responsive）**：快速响应用户
2. **回弹（Resilient）**：故障隔离，不级联
3. **弹性（Elastic）**：根据负载动态扩缩
4. **消息驱动（Message Driven）**：异步消息传递

### 1.3 四大核心接口

```
                  Publisher（发布者）
                  ┌────────────────┐
                  │  subscribe(s)  │
                  └────────┬───────┘
                           │ subscribe
                           ↓
                  Subscriber（订阅者）
                  ┌─────────────────────────┐
                  │  onSubscribe(s)         │
                  │  onNext(t)              │ ← 数据信号
                  │  onError(e)             │ ← 错误信号
                  │  onComplete()           │ ← 完成信号
                  └─────────────────────────┘
                           ↑
                  Subscription（订阅关系）
                  ┌─────────────────────────┐
                  │  request(n)             │ ← 反压（Backpressure）
                  │  cancel()               │
                  └─────────────────────────┘
```

**Java 9+ `java.util.concurrent.Flow`**：JDK 官方响应式标准接口，Reactor 3 / RxJava 3 都遵循。

### 1.4 Reactor 的 Mono 与 Flux

**Project Reactor**（Spring 官方响应式库）：

| 类型 | 元素数 | 典型场景 |
|------|--------|---------|
| **Mono<T>** | 0..1 | 单个用户、单个订单 |
| **Flux<T>** | 0..N | 用户列表、消息流 |

```java
// Mono 示例
Mono<User> monoUser = userRepository.findById(1L);
Mono<User> monoEmpty = Mono.empty();
Mono<User> monoError = Mono.error(new RuntimeException("not found"));

// Flux 示例
Flux<User> fluxUsers = userRepository.findAll();
Flux<Integer> fluxRange = Flux.range(1, 10);  // 1..10
Flux<Long> fluxInterval = Flux.interval(Duration.ofSeconds(1));  // 每秒发射一个
```

### 1.5 RxJava 对比

**RxJava**（Netflix 出品，Android 圈广泛使用）：

| Reactor | RxJava 3 |
|---------|----------|
| `Mono` | `Single` / `Maybe` / `Completable` |
| `Flux` | `Observable` / `Flowable` |
| `subscribe()` | `subscribe()` |
| `map()` | `map()` |
| `flatMap()` | `flatMap()` |
| Scheduler 切换 | Scheduler 切换 |

**主要区别**：
- RxJava 历史更久（2014），生态更广
- Reactor 与 Spring 集成更好（Spring WebFlux 默认）
- Reactor 实现遵循 `org.reactivestreams` 标准

### 1.6 常用操作符

#### 转换类

```java
// map：一对一转换
Flux<User> flux = Flux.just(user1, user2);
Flux<String> names = flux.map(User::getName);

// flatMap：一对多异步转换（合并结果）
Flux<Order> orders = userFlux.flatMap(user -> orderService.findByUserId(user.getId()));

// concatMap：保持顺序的 flatMap
Flux<Order> orders = userFlux.concatMap(user -> orderService.findByUserId(user.getId()));

// switchIfEmpty：空值时切换到另一个 Publisher
Mono<User> user = userRepository.findById(id)
        .switchIfEmpty(Mono.error(new NotFoundException("user not found")));
```

#### 过滤类

```java
Flux<Integer> nums = Flux.range(1, 10);
nums.filter(n -> n % 2 == 0)        // 取偶数
    .distinct()                     // 去重
    .take(3)                        // 取前 3 个
    .skipLast(2)                    // 跳过最后 2 个
    .subscribe(System.out::println);
```

#### 组合类

```java
// zip：多 Publisher 合并（按位配对）
Mono<User> userMono = userService.findById(id);
Mono<Order> orderMono = orderService.findByUserId(id);
Mono<UserDetail> detail = Mono.zip(userMono, orderMono,
        (user, order) -> new UserDetail(user, order));

// merge：合并多个 Flux
Flux<User> admin = userService.findAdmins();
Flux<User> vip = userService.findVips();
Flux<User> all = Flux.merge(admin, vip);
```

#### 错误处理

```java
// onErrorReturn：出错时返回默认值
Mono<User> user = userService.findById(id)
        .onErrorReturn(defaultUser);

// onErrorResume：出错时切换到另一个 Publisher
Mono<User> user = userService.findById(id)
        .onErrorResume(e -> Mono.just(defaultUser));

// retry：失败重试
Mono<User> user = userService.findById(id)
        .retry(3);  // 最多重试 3 次
```

### 1.7 背压（Backpressure）

**背压** = 订阅者告诉发布者"我处理能力有限，别发太快"。

```java
Flux.range(1, 1000)
    .log()                          // 打印日志看信号
    .subscribe(new BaseSubscriber<Integer>() {
        @Override
        protected void hookOnSubscribe(Subscription subscription) {
            request(10);  // 订阅时只请求 10 个
        }

        @Override
        protected void hookOnNext(Integer value) {
            System.out.println("Got: " + value);
            if (value % 10 == 0) {
                request(10);  // 处理完一批再请求 10 个
            }
        }
    });
```

### 1.8 调度器（Scheduler）

**切换执行线程**：

```java
Flux.just(1, 2, 3)
    .subscribeOn(Schedulers.boundedElastic())   // 订阅发生在弹性线程池
    .publishOn(Schedulers.parallel())           // 后续操作在并行线程池
    .map(i -> i * 2)
    .subscribeOn(Schedulers.single())           // 不影响：subscribeOn 只生效第一个
    .subscribe();
```

**常用 Scheduler**：
- `Schedulers.boundedElastic()`：I/O 密集（DB、HTTP），有界
- `Schedulers.parallel()`：CPU 密集
- `Schedulers.single()`：单线程顺序
- `Schedulers.immediate()`：当前线程

### 1.9 阻塞的代价

**响应式编程最致命的陷阱**：**在响应式链中调用阻塞 API 会破坏整个链**。

```java
// ❌ 灾难：在 Mono.map 里调用阻塞 JDBC
Mono<User> user = userRepository.findById(id)
    .map(id -> jdbcTemplate.queryForObject(...));  // 阻塞！阻塞整个事件循环！

// ✅ 正确：用响应式 Repository
Mono<User> user = reactiveUserRepository.findById(id);

// 或把阻塞调用包到 boundedElastic
Mono<User> user = Mono.fromCallable(() ->
        jdbcTemplate.queryForObject(...))
    .subscribeOn(Schedulers.boundedElastic());
```

## 2. 代码示例

### 2.1 Mono 基础

```java
// 文件：MonoDemo.java
import reactor.core.publisher.Mono;

public class MonoDemo {
    public static void main(String[] args) {
        // 1. 创建 Mono
        Mono<String> hello = Mono.just("Hello World");
        Mono<String> empty = Mono.empty();
        Mono<String> error = Mono.error(new RuntimeException("oops"));

        // 2. 订阅
        hello.subscribe(
                value -> System.out.println("Got: " + value),
                err -> System.err.println("Error: " + err),
                () -> System.out.println("Completed"));

        // 3. 链式操作
        Mono<String> upper = hello.map(String::toUpperCase);
        upper.subscribe(System.out::println);  // "HELLO WORLD"

        // 4. 阻塞等待（仅用于测试）
        String result = upper.block();  // "HELLO WORLD"
    }
}
```

### 2.2 Flux 流处理

```java
// 文件：FluxDemo.java
import reactor.core.publisher.Flux;

public class FluxDemo {
    public static void main(String[] args) {
        // 1. 创建 Flux
        Flux<Integer> nums = Flux.just(1, 2, 3, 4, 5);
        Flux<Integer> range = Flux.range(1, 100);
        Flux<Long> timer = Flux.interval(Duration.ofSeconds(1)).take(5);  // 0,1,2,3,4

        // 2. 操作链
        Flux<Integer> processed = nums
                .filter(n -> n % 2 == 0)   // 偶数: 2, 4
                .map(n -> n * n)           // 平方: 4, 16
                .take(3);                  // 取前 3 个

        processed.subscribe(System.out::println);

        // 3. 转换为 List（阻塞）
        List<Integer> list = processed.collectList().block();
    }
}
```

### 2.3 Spring WebFlux Controller

```java
// 文件：UserController.java
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/users")
public class UserController {
    @Autowired
    private UserRepository userRepository;  // 响应式 Repository（R2DBC）

    @GetMapping("/{id}")
    public Mono<User> getById(@PathVariable Long id) {
        return userRepository.findById(id);
    }

    @GetMapping
    public Flux<User> list() {
        return userRepository.findAll();
    }

    @PostMapping
    public Mono<User> create(@RequestBody Mono<User> userMono) {
        return userMono.flatMap(userRepository::save);
    }

    // SSE（Server-Sent Events）：服务端推送
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<User> stream() {
        return Flux.interval(Duration.ofSeconds(1))
                .flatMap(i -> userRepository.findById((long) (i % 10 + 1)));
    }
}
```

## 3. 关键要点总结

- **响应式编程** = 数据流 + 异步非阻塞 + 背压
- **Reactor** = Spring 官方响应式库，`Mono`（0..1）+ `Flux`（0..N）
- **四大接口**：Publisher / Subscriber / Subscription / Processor（Java 9+ `Flow`）
- **操作符**：map / flatMap / filter / zip / merge / concatMap 等
- **三大生命周期钩子**：`doOnNext` / `doOnComplete` / `doOnError` —— ruoyi-vue-pro 的 AI 流式 Service 是教科书用法
- **背压**：订阅者通过 `request(n)` 控制上游速率
- **调度器**：Schedulers.boundedElastic() / parallel() / single()
- **致命陷阱**：响应式链中调用阻塞 API 会破坏整个链；ThreadLocal 在 Flux 内**不生效**（ruoyi 注释明确说明）
- **混搭模式**：ruoyi-vue-pro 用 **Spring MVC + Flux SSE Controller + WebClient.block()**，是渐进式响应式改造的典型案例

---

**文档版本**：v1.0
**最后更新**：2026-07-13
