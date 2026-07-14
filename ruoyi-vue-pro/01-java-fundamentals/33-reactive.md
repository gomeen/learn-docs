# 1.4.10 Reactor / RxJava 响应式编程

> 理解响应式编程的核心思想，能读懂 Spring WebFlux、Reactor、RxJava 的源码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解响应式编程的四大核心：发布者 / 订阅者 / 订阅 / 信号
- 区分 Reactor 的 `Mono`（0..1）和 `Flux`（0..N）
- 掌握响应式编程的常用操作符（map、flatMap、filter 等）
- 在 ruoyi-vue-pro 中识别响应式编程的间接使用

## 📚 前置知识

- [08-stream-lambda.md](./08-stream-lambda.md)：Stream API 与 Lambda
- [21-thread.md](./21-thread.md)：线程基础
- [22-thread-pool.md](./22-thread-pool.md)：线程池
- [32-netty.md](./32-netty.md)：Netty（响应式常基于 Netty）

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

## 3. ruoyi-vue-pro 仓库源码解读

> ruoyi-vue-pro 主框架是 **Spring MVC**，但 `yudao-module-ai` 模块**重度使用 Reactor**：3 个 SSE Controller 返回 `Flux`，多个 Chat Model 适配器用 `Flux<ChatResponse>` 流式推送，WebClient 用 `bodyToMono.block()` 实现"伪异步"。这是学习 Reactor 在生产项目中如何落地的最佳教材。

### 3.1 AI 流式对话 Controller：Flux + text/event-stream

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/controller/admin/chat/AiChatMessageController.java`
**核心代码**（行 59-69）：

```java
59  @Operation(summary = "发送消息（段式）", description = "一次性返回，响应较慢")
60  @PostMapping("/send")
61  public CommonResult<AiChatMessageSendRespVO> sendMessage(@Valid @RequestBody AiChatMessageSendReqVO sendReqVO) {
62      return success(chatMessageService.sendMessage(sendReqVO, getLoginUserId()));
63  }
64
65  @Operation(summary = "发送消息（流式）", description = "流式返回，响应较快")
66  @PostMapping(value = "/send-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
67  public Flux<CommonResult<AiChatMessageSendRespVO>> sendChatMessageStream(
68          @Valid @RequestBody AiChatMessageSendReqVO sendReqVO) {
69      return chatMessageService.sendChatMessageStream(sendReqVO, getLoginUserId());
70  }
```

**解读**：
- **第 61 行 vs 第 67 行**：同一 Controller 同时提供阻塞版（`/send`，返回 `CommonResult`）和流式版（`/send-stream`，返回 `Flux<CommonResult>`）
- **`produces = MediaType.TEXT_EVENT_STREAM_VALUE`**：声明 SSE 协议（Content-Type: text/event-stream），浏览器 EventSource / fetch API 可消费
- **`@PostMapping` 而非 `@GetMapping`**：因为 AI 对话需要 body 传消息内容
- **混搭的精妙之处**：项目主体是 Spring MVC，但 Controller 方法签名可以是 `Flux<T>`——Spring MVC 3.2+ 支持响应式返回值（自动用 ReactiveAdapterRegistry 处理）
- **3 个类似 Controller**：
  - `/ai/chat/send-stream`（聊天）
  - `/ai/write/generate-stream`（写作）
  - `/ai/mind-map/generate-stream`（思维导图）

### 3.2 AI 流式 Service：Flux.map + doOnComplete + onErrorResume

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/service/write/AiWriteServiceImpl.java`
**核心代码**（行 83-105）：

```java
83  // 3.1 构建 Prompt，并进行调用
84  Prompt prompt = buildPrompt(generateReqVO, model, systemMessage);
85  Flux<ChatResponse> streamResponse = chatModel.stream(prompt);
86
87  // 3.2 流式返回
88  StringBuffer contentBuffer = new StringBuffer();
89  return streamResponse.map(chunk -> {
90      String newContent = chunk.getResult() != null
91              ? chunk.getResult().getOutput().getText() : null;
92      newContent = StrUtil.nullToDefault(newContent, "");
93      contentBuffer.append(newContent);
94      return success(newContent);
95  }).doOnComplete(() -> {
96      // 忽略租户，因为 Flux 异步无法透传租户
97      TenantUtils.executeIgnore(() ->
98              writeMapper.updateById(new AiWriteDO().setId(writeDO.getId())
99                      .setGeneratedContent(contentBuffer.toString())));
100 }).doOnError(throwable -> {
101     log.error("[generateWriteContent][generateReqVO({}) 发生异常]", generateReqVO, throwable);
102     TenantUtils.executeIgnore(() ->
103             writeMapper.updateById(new AiWriteDO().setId(writeDO.getId())
104                     .setErrorMessage(throwable.getMessage())));
105 }).onErrorResume(error -> Flux.just(error(ErrorCodeConstants.WRITE_STREAM_ERROR)));
```

**解读**：
- **第 85 行**：`Flux<ChatResponse>` —— Spring AI 的 ChatModel 接口原生返回 Flux（每个 chunk 是一个 ChatResponse）
- **第 89 行 `.map(chunk -> ...)`**：把每个 ChatResponse 转换为 VO。注意 `contentBuffer.append` 在 map 内执行 —— **map 是同步的、无副作用的语义被打破**（用 StringBuffer 累积内容是为了 doOnComplete 时落库）
- **第 95-99 行 `.doOnComplete(...)`**：流结束时把累积内容写入 DB。**关键注释**："忽略租户，因为 Flux 异步无法透传租户" —— 这就是 ThreadLocal 在响应式上下文失效的经典问题（参考 [30-threadlocal.md](./30-threadlocal.md)）
- **第 100-104 行 `.doOnError(...)`**：流异常时记录错误信息
- **第 105 行 `.onErrorResume(...)`**：最终兜底，返回一个包含错误信息的 `Flux.just(...)`，避免异常传播到客户端
- **响应式三大操作符的经典组合**：`map`（转换）+ `doOnComplete`（副作用）+ `doOnError`（副作用）+ `onErrorResume`（恢复）—— 完整覆盖流生命周期的所有事件

### 3.3 AI 流式 Service（聊天版）：AtomicBoolean + AtomicReference 确保知识库只查一次

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/service/chat/AiChatMessageServiceImpl.java`
**核心代码**（行 229-254）：

```java
229 // 4.2 构建 Prompt，并进行调用
230 Prompt prompt = buildPrompt(conversation, historyMessages, knowledgeSegments,
231         webSearchResponse, model, sendReqVO);
232 Flux<ChatResponse> streamResponse = chatModel.stream(prompt);
233
234 // 4.3 流式返回
235 StringBuffer contentBuffer = new StringBuffer();
236 StringBuffer reasoningContentBuffer = new StringBuffer();
237
238 AtomicBoolean firstExecuteFlag = new AtomicBoolean(true);
239 AtomicReference<List<AiChatMessageRespVO.KnowledgeSegment>> cacheSegments = new AtomicReference<>();
240 AtomicReference<List<AiWebSearchResponse.WebPage>> cacheWebSearchPages = new AtomicReference<>();
241 return streamResponse.map(chunk -> {
242     // 仅首次：返回知识库、联网搜索
243     if (StrUtil.isEmpty(contentBuffer)) {
244         if (firstExecuteFlag.compareAndSet(true, false)) { // CAS 操作，确保仅执行一次
245             Map<Long, AiKnowledgeDocumentDO> documentMap =
246                     TenantUtils.executeIgnore(() -> knowledgeDocumentService.getKnowledgeDocumentMap(
247                             convertSet(knowledgeSegments,
248                                     AiKnowledgeSegmentSearchRespBO::getDocumentId)));
249             cacheSegments.set(BeanUtils.toBean(knowledgeSegments,
250                     AiChatMessageRespVO.KnowledgeSegment.class));
```

**解读**：
- **第 241-244 行**：与文档 28 中的 `AtomicBoolean` + `compareAndSet` 模式完全一致 —— 保证知识库检索只在第一个 chunk 执行一次
- **第 232 行 → 第 241 行**：响应式编程中"一次性副作用"的经典问题（每个 chunk 都触发 map，需要 CAS 保证只执行一次）
- **第 235-236 行**：两个 StringBuffer 分别累积"思考过程"和"最终答案"，对应 DeepSeek-R1 等推理模型的输出格式
- **第 238-240 行**：3 个原子变量（flag + 2 个结果缓存），都是 stream 上下文的可变状态。在传统多线程模型下需要锁，在 Flux.map 内由于 Reactor 保证**单线程串行执行 map**，普通变量也安全 —— 但作者选择 AtomicBoolean/AtomicReference 是**防御性编程**

### 3.4 Chat Model 适配器：Stream → Flux 桥接

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/framework/ai/core/model/gemini/GeminiChatModel.java`
**核心代码**（行 31-44）：

```java
31  @Override
32  public ChatResponse call(Prompt prompt) {
33      return openAiChatModel.call(prompt);
34  }
35
36  @Override
37  public Flux<ChatResponse> stream(Prompt prompt) {
38      return openAiChatModel.stream(prompt);
39  }
```

**解读**：
- **第 37 行 `Flux<ChatResponse>`**：适配器模式 —— 把 Spring AI 底层的响应式 API 直接转发给上层
- **7 个 AI 厂商适配器**（Gemini、SiliconFlow、XingHuo、DouBao、Grok、HunYuan、BaiChuan）都用相同模式
- **核心价值**：上层 Service 只依赖抽象 `ChatModel`，不用关心具体厂商；新增厂商只需写一个 30 行的适配器
- **设计哲学**：ruoyi-vue-pro 在 AI 模块采用**响应式优先**设计，但混搭 Spring MVC 框架，是渐进式响应式改造的典型案例

### 3.5 WebClient 异步 HTTP + .block() 伪同步

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/framework/ai/core/webserch/bocha/AiBoChaWebSearchClient.java`
**核心代码**（行 66-73）：

```java
66 // 调用博查 API
67 CommonResult<WebSearchResponse> response = this.webClient.post()
68         .uri("/v1/web-search")
69         .bodyValue(webSearchRequest)
70         .retrieve()
71         .onStatus(STATUS_PREDICATE, EXCEPTION_FUNCTION.apply(webSearchRequest))
72         .bodyToMono(new ParameterizedTypeReference<CommonResult<WebSearchResponse>>() {})
73         .block();
```

**解读**：
- **第 67-72 行**：标准的 WebClient 链式调用，**完全响应式 API**（post/uri/bodyValue/retrieve/bodyToMono 都是 Mono/Mono 的链）
- **第 73 行 `.block()`**：在链末尾调用 block，把异步 Mono 转为同步阻塞 —— 这是**反模式**（把响应式的优势全浪费了）
- **为什么这么写**：项目的 Service 层都是同步阻塞的（Spring MVC 风格），为了让响应式 WebClient 能被同步代码调用，不得不用 `.block()` 桥接
- **更好的写法**：
  ```java
  // 方法返回 Mono<WebSearchResponse>，调用方继续链式
  public Mono<WebSearchResponse> search(WebSearchRequest req) {
      return webClient.post().uri("/v1/web-search").bodyValue(req)
              .retrieve().bodyToMono(new ParameterizedTypeReference<...>() {});
  }
  ```
- **5 个类似客户端**：AiBoChaWebSearchClient、XunFeiPptApi、WenDuoDuoPptApi、MidjourneyApi、SunoApi 都用这个模式

### 3.6 AI 模块的 POM 注释：明确不用 WebFlux

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/pom.xml`
**核心代码**（行 197-213）：

```xml
197 <!-- MCP 相关 -->
198 <!--
199     特殊说明：不能使用 spring-ai-starter-mcp-server-webflux
200     或 spring-ai-starter-mcp-client-webflux ！！！
201     原因：项目使用了 SpringMVC，而不是 WebFlux。
202     引入上述 2 个，会导致 SSE Server 失效。
203 -->
204 <dependency>
205     <!-- 服务端 -->
206     <groupId>org.springframework.ai</groupId>
207     <artifactId>spring-ai-starter-mcp-server-webmvc</artifactId>
208     <version>${spring-ai.version}</version>
```

**解读**：
- **原作者明确警告**：不能切换到 WebFlux，因为 Spring MVC 的 SSE Controller（`produces = TEXT_EVENT_STREAM_VALUE`）依赖 MVC 的异步 Servlet 机制
- **官方推荐**：`spring-ai-starter-mcp-server-webmvc`（基于 MVC 的 SSE）
- **启示**：响应式编程不一定要全栈 WebFlux，可以"**局部响应式 + 全局阻塞**"——这是渐进式改造的现实选择

### 3.7 Netty BOM：响应式底座的间接依赖

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-dependencies/pom.xml`
**核心代码**（行 97-103）：

```xml
97   <dependency>
98       <groupId>io.netty</groupId>
99       <artifactId>netty-bom</artifactId>
100      <version>${netty.version}</version>
101      <type>pom</type>
102      <scope>import</scope>
103  </dependency>
```

**第 73 行**：`netty.version = 4.2.15.Final`（来自 properties）

**解读**：
- Reactor Core 底层基于 Netty（`reactor-netty` 模块），所以 BOM 中统一管理 Netty 版本
- Spring WebClient 也走 Netty HTTP Client
- AI 模块的所有 WebClient 调用底层都是 Netty，但**业务代码完全感知不到 Netty 存在**（详见 [32-netty.md](./32-netty.md)）

## 4. 关键要点总结

- **响应式编程** = 数据流 + 异步非阻塞 + 背压
- **Reactor** = Spring 官方响应式库，`Mono`（0..1）+ `Flux`（0..N）
- **四大接口**：Publisher / Subscriber / Subscription / Processor（Java 9+ `Flow`）
- **操作符**：map / flatMap / filter / zip / merge / concatMap 等
- **三大生命周期钩子**：`doOnNext` / `doOnComplete` / `doOnError` —— ruoyi-vue-pro 的 AI 流式 Service 是教科书用法
- **背压**：订阅者通过 `request(n)` 控制上游速率
- **调度器**：Schedulers.boundedElastic() / parallel() / single()
- **致命陷阱**：响应式链中调用阻塞 API 会破坏整个链；ThreadLocal 在 Flux 内**不生效**（ruoyi 注释明确说明）
- **混搭模式**：ruoyi-vue-pro 用 **Spring MVC + Flux SSE Controller + WebClient.block()**，是渐进式响应式改造的典型案例

## 5. 练习题

### 练习 1：基础（必做）

用 Reactor 写一个**响应式斐波那契数列**：
- 创建一个 `Flux<Long>`，逐个发射 0, 1, 1, 2, 3, 5, 8, 13, ...
- 取前 10 个元素并打印

### 练习 2：进阶

阅读 Spring Boot 的 `WebMvcAutoConfiguration` 源码（GitHub），找出 Spring MVC 在哪些地方用了响应式技术（SSE、异步 Servlet）。

### 练习 3：挑战（选做）

把 ruoyi 的 `AdminUserServiceImpl.getUserDetail()` 改造为响应式版本：
1. 引入 `spring-boot-starter-webflux` 和 `spring-boot-starter-data-r2dbc`
2. 改写 Mapper 为响应式
3. 用 `Mono.zip` 并行执行 3 个查询
4. 对比改造前后的吞吐量（用 JMH 或 wrk）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/controller/admin/chat/AiChatMessageController.java`（Flux SSE Controller）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/service/write/AiWriteServiceImpl.java`（Flux + doOnComplete + onErrorResume）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/module/ai/service/chat/AiChatMessageServiceImpl.java`（AtomicBoolean CAS + Flux.map）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/framework/ai/core/model/gemini/GeminiChatModel.java`（AI 模型适配器）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/src/main/java/cn/iocoder/yudao/framework/ai/core/webserch/bocha/AiBoChaWebSearchClient.java`（WebClient + .block()）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-ai/pom.xml`（明确不用 WebFlux 的注释）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-dependencies/pom.xml`（Netty BOM）
- 《Spring 响应式编程》（Spring 官方文档）
- [Project Reactor 官方文档](https://projectreactor.io/docs/core/release/reference/)
- [响应式宣言](https://www.reactivemanifesto.org/zh-CN)
- [Reactive Streams 标准](https://www.reactive-streams.org/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13