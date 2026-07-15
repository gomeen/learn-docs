# 22 异步任务：@Async

> 掌握 Spring `@Async` 异步任务的使用，能在 ruoyi-vue-pro 中把耗时操作异步化。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@Async` 的工作原理
- 掌握 `@EnableAsync` + `@Async` 的使用
- 区分同步 vs 异步、@Async vs MQ
- 能在 ruoyi-vue-pro 中用 `@Async` 实现"非阻塞"业务

## 📚 前置知识

- [03-aop.md](./03-aop.md)（AOP 基础，`@Async` 本质是 AOP）
- 线程池（详见 [22-thread-pool](../01-java-fundamentals/22-thread-pool.md)）
- 04-transaction.md

## 1. 核心概念

### 1.1 什么是 `@Async`？

`@Async` 是 Spring 提供的**方法级异步执行**注解：
- 把方法调用从同步改为异步（提交到线程池）
- 调用方立即返回，不等待方法执行完成
- 本质是 AOP：方法被代理后，调用 `TaskExecutor.execute()`

### 1.2 启用方式

```java
@SpringBootApplication
@EnableAsync  // 启用 @Async 支持
public class MyApplication { ... }
```

### 1.3 `@Async` vs MQ

| 特性 | `@Async` | MQ (Redis/RabbitMQ/Kafka，详见 [MQ 概念](../../_common/02-mq/01-concepts.md)) |
|------|---------|--------------------------|
| 作用范围 | 单 JVM | 跨 JVM |
| 可靠性 | 应用重启任务丢失 | 持久化、可靠投递 |
| 性能 | 高（内存） | 中（网络 IO） |
| 适用 | 短任务、日志、通知 | 耗时任务、分布式 |

## 2. 代码示例

### 2.1 基础异步方法

```java
// 文件：EmailService.java
@Service
public class EmailService {

    @Async  // 异步执行
    public void sendWelcome(String email) {
        // 模拟耗时操作
        try { Thread.sleep(3000); } catch (InterruptedException e) {}
        log.info("发送欢迎邮件到 {}", email);
    }
}

// 调用方
@RestController
public class UserController {

    @Autowired
    private EmailService emailService;

    @PostMapping("/register")
    public CommonResult<Long> register(@RequestBody UserCreateReqVO req) {
        userService.createUser(req);
        // 异步发送邮件，立即返回
        emailService.sendWelcome(req.getEmail());
        return CommonResult.success(true);
    }
}
```

### 2.2 自定义线程池

```java
@Configuration
public class AsyncConfig {

    @Bean("myTaskExecutor")
    public TaskExecutor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("my-async-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        return executor;
    }
}

// 使用
@Async("myTaskExecutor")
public void process() { ... }
```

### 2.3 异步返回值（CompletableFuture）

```java
@Async
public CompletableFuture<UserVO> getUserAsync(Long id) {
    UserDO user = userDao.selectById(id);
    return CompletableFuture.completedFuture(UserVO.from(user));
}

// 调用方
public void batchGet() {
    CompletableFuture<UserVO> f1 = userService.getUserAsync(1L);
    CompletableFuture<UserVO> f2 = userService.getUserAsync(2L);
    CompletableFuture.allOf(f1, f2).join();  // 等待完成
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 中使用 @Async 的位置

通过文件搜索发现，ruoyi-vue-pro 在以下位置使用了 `@Async`：

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/context/TransmittableThreadLocalSecurityContextHolderStrategy.java`

（推测）`LogRecordServiceImpl` 也使用 `@Async` 异步记录操作日志。

**关键设计**：
- API 访问日志、错误日志都通过 **MQ 异步** 持久化
- 不直接用 `@Async`，因为：
  - `@Async` 只能单 JVM，集群部署会重复执行
  - MQ 支持分布式、高可靠、自动重试

### 3.2 YudaoCacheAutoConfiguration 缓存配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 27-31）：

```java
@AutoConfiguration
@EnableConfigurationProperties({CacheProperties.class, YudaoCacheProperties.class})
@EnableCaching
public class YudaoCacheAutoConfiguration {
```

**解读**：
- 第 4 行：`@EnableCaching` 开启 Spring Cache 注解支持
- **关联**：`@Cacheable` 注解的方法第一次调用是同步的（执行方法 → 写缓存）
- 后续调用是同步读缓存（快）
- **ruoyi 设计选择**：用 Redis 缓存而不是 `@Async`，因为缓存是高频读操作，异步反而慢

### 3.3 异常日志的异步处理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 130-160）：

```java
/**
 * 处理 ServiceException 业务异常
 */
@ExceptionHandler(value = ServiceException.class)
public CommonResult<?> serviceExceptionHandler(ServiceException ex) {
    log.warn("[serviceExceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, null);
    return CommonResult.error(ex.getCode(), ex.getMessage());
}
```

**解读**：
- 第 5 行：`createExceptionLog(ex, null)` 是 RPC 调用，**跨服务异步记录异常日志**
- 这里没有用 `@Async`，而是用 **MQ + RPC** 实现分布式异步
- **设计原因**：
  - 异常日志写入 `infra` 服务（独立部署）
  - 用 MQ 异步推送，不影响主业务响应
  - 支持日志聚合分析（ELK）

## 4. 关键要点总结

- **`@EnableAsync` 启用异步支持**
- **`@Async` 把方法提交到线程池异步执行**
- **`@Async` 失效场景**：
  - 自调用（`this.asyncMethod()`）
  - 方法不是 public
  - 没有 `@EnableAsync`
- **`@Async` vs MQ**：
  - `@Async`：单 JVM，简单
  - MQ：跨 JVM，可靠
- ruoyi-vue-pro 优先用 **MQ** 实现分布式异步（API 日志、错误日志）
- 单 JVM 简单场景可以用 `@Async`（如操作日志）

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `EmailService` 用 `@Async` 异步发送邮件，启动类加 `@EnableAsync`，Controller 调用后立即返回。

### 练习 2：进阶

解释为什么 ruoyi-vue-pro 的 API 访问日志用 MQ 而不是 `@Async`？从"集群部署"和"可靠性"两个角度分析。

### 练习 3：挑战（选做）

实现一个自定义 `TaskDecorator`（任务装饰器），把当前请求的 traceId 透传到异步线程的 MDC 中，实现分布式追踪。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- Spring `@Async` 文档：https://docs.spring.io/spring-framework/reference/integration/async.html
- 芋道异步任务：https://doc.iocoder.cn/spring-boot-async/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
