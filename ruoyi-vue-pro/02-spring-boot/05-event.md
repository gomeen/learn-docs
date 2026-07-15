# 05 Spring 事件机制：ApplicationEvent

> 理解 Spring 事件发布/订阅模式，掌握 `ApplicationEventPublisher` 与 `@EventListener` 的使用，能在 ruoyi-vue-pro 中解耦业务逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解观察者模式在 Spring 中的实现（ApplicationEvent）
- 掌握同步事件（`ApplicationEvent`）和异步事件（`@Async` + `@EventListener`）的差异
- 区分 `ApplicationListener` 接口和 `@EventListener` 注解
- 能在 ruoyi-vue-pro 中用事件解耦业务逻辑（如登录后发送审计日志）

## 📚 前置知识

- [01-ioc.md](./01-ioc.md)
- 观察者模式基础（详见 [观察者](../../_fundamentals/06-design-patterns/15-observer.md)）

## 1. 核心概念

### 1.1 什么是 Spring 事件？

Spring 事件是**应用内部的消息传递机制**，基于观察者模式：
- **发布者**：`ApplicationEventPublisher`（通常是 Service）
- **订阅者**：`@EventListener` 标注的方法
- **事件**：继承 `ApplicationEvent` 的对象

**优势**：解耦业务逻辑（如"用户注册"→ 发送短信、发放优惠券、记录日志、发送邮件……）

### 1.2 三种使用方式

```java
// 方式 1：继承 ApplicationEvent（传统）
public class UserRegisteredEvent extends ApplicationEvent { ... }

// 方式 2：普通 POJO（Spring 4.2+ 推荐）
public class UserRegisteredEvent { }  // 不需要继承

// 方式 3：使用 ApplicationEventPublisher
applicationEventPublisher.publishEvent(new UserRegisteredEvent(user));
```

### 1.3 同步 vs 异步

- **同步事件**（默认）：发布者线程同步执行所有监听器，监听器慢会阻塞发布者
- **异步事件**：监听器上加 `@Async`，需要 `@EnableAsync`（`@Async` 详见 [22-async](./22-async.md)）

## 2. 代码示例

### 2.1 基础事件发布订阅

```java
// 文件：UserEvent.java —— 事件对象（普通 POJO）
public class UserRegisteredEvent {
    private final Long userId;
    private final String email;
    public UserRegisteredEvent(Long userId, String email) {
        this.userId = userId;
        this.email = email;
    }
    // 省略 getter
}

// 文件：UserService.java —— 发布者
@Service
@RequiredArgsConstructor
public class UserService {
    private final ApplicationEventPublisher publisher;

    public void register(UserDTO dto) {
        // 1. 保存用户
        userDao.insert(dto);
        // 2. 发布事件（不关心谁处理）
        publisher.publishEvent(new UserRegisteredEvent(dto.getId(), dto.getEmail()));
    }
}

// 文件：UserEventListener.java —— 订阅者
@Component
public class UserEventListener {

    @EventListener
    public void onUserRegistered(UserRegisteredEvent event) {
        // 发送欢迎邮件
        emailService.sendWelcome(event.getEmail());
    }

    @EventListener
    @Async  // 异步执行
    public void onUserRegisteredAsync(UserRegisteredEvent event) {
        // 记录审计日志
        auditService.log(event.getUserId(), "用户注册");
    }
}
```

### 2.2 条件监听

```java
@EventListener(condition = "#event.userId > 0")
public void handleEvent(SomeEvent event) { ... }
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 启动 Banner 事件监听

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
**核心代码**（行 28-50）：

```java
@Slf4j
@Order(0)  // 越小越靠前
public class BannerApplicationRunner implements ApplicationRunner {

    @Override
    public void run(ApplicationArguments args) throws Exception {
        log.info("""
                
                ----------------------------------------------------------
                \t项目启动成功！
                \t项目名称：{}
                \t启动时间：{}
                ----------------------------------------------------------
                """,
                applicationName, LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
    }
}
```

**解读**：
- 第 8 行：实现 `ApplicationRunner` 接口，这是 Spring 事件机制的一种（Spring Boot 启动事件）
- **事件原理**：Spring Boot 启动时发布 `ApplicationStartedEvent`、`ApplicationReadyEvent`，这些 Runner 监听器按 `@Order` 顺序执行
- **设计意图**：在项目启动完成后输出美化 Banner，方便运维快速确认启动状态

### 3.2 Web 配置中的工具类注册

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 94-99）：

```java
@Bean
@SuppressWarnings("InstantiationOfUtilityClass")
public WebFrameworkUtils webFrameworkUtils(WebProperties webProperties) {
    // 由于 WebFrameworkUtils 需要使用到 webProperties 属性，所以注册为一个 Bean
    return new WebFrameworkUtils(webProperties);
}
```

**解读**：
- 第 4 行：`WebFrameworkUtils` 工具类用 `@Bean` 注册，使其在 Spring 容器中被管理
- **应用场景**：当 web 配置（如 API 前缀）变化时，工具类可以通过监听 `EnvironmentChangeEvent` 实时更新
- **事件设计**：这种"配置中心 + 事件广播"的模式，是 ruoyi 支持 Nacos 配置热更新的基础

### 3.3 异常日志的事件驱动记录

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 130-160，推测 `createExceptionLog`）：

```java
/**
 * 处理系统异常
 */
@ExceptionHandler(value = Exception.class)
public CommonResult<?> exceptionHandler(HttpServletRequest request, Throwable ex) {
    log.error("[exceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, WebFrameworkUtils.getLoginUserId());
    // 返回 ERROR CommonResult
    return CommonResult.error(INTERNAL_SERVER_ERROR.getCode(), INTERNAL_SERVER_ERROR.getMsg());
}
```

**解读**：
- `createExceptionLog` 通过 RPC（`ApiErrorLogCommonApi`）异步写入错误日志
- **事件解耦思想**：异常处理只负责返回错误响应，日志记录通过 RPC / 事件异步处理，不影响响应速度
- ruoyi-vue-pro 中通过 `ApiErrorLogCommonApi` + MQ 实现"异常发生时异步持久化日志"

## 4. 关键要点总结

- **Spring 事件 = 观察者模式** 的 Spring 实现
- **发布者**：`ApplicationEventPublisher.publishEvent(event)`
- **订阅者**：`@EventListener` 标注的方法
- **事件对象**：可以是任意 POJO（Spring 4.2+），不必继承 `ApplicationEvent`
- **异步事件**：订阅者方法加 `@Async` + 启动类加 `@EnableAsync`
- ruoyi-vue-pro 通过 `ApplicationRunner` / `CommandLineRunner` 实现启动后钩子
- ruoyi 通过 RPC + MQ 实现跨服务的"事件驱动"

## 5. 练习题

### 练习 1：基础（必做）

定义 `OrderCreatedEvent` 事件，发布者 `OrderService.createOrder()` 发布事件，订阅者发送邮件 + 扣减库存（用 `@EventListener`）。

### 练习 2：进阶

在 ruoyi-vue-pro 中搜索 `ApplicationEventPublisher` / `@EventListener`，看哪些模块用了事件机制？分析为什么这些场景适合用事件。

### 练习 3：挑战（选做）

实现一个"配置热更新"功能：监听 `EnvironmentChangeEvent`，当 `yudao.web.admin-api.prefix` 改变时，自动更新 `WebFrameworkUtils` 中的 API 前缀。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- Spring 事件官方文档：https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html#context-functionality-events
- 芋道 Spring 事件教程：https://doc.iocoder.cn/spring-boot-event/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
