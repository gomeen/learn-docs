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
- **异步事件**：监听器上加 `@Async`，需要 `@EnableAsync`（`@Async` 详见 [22-async](./26-async.md)）

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

## 3. 关键要点总结

- **Spring 事件 = 观察者模式** 的 Spring 实现
- **发布者**：`ApplicationEventPublisher.publishEvent(event)`
- **订阅者**：`@EventListener` 标注的方法
- **事件对象**：可以是任意 POJO（Spring 4.2+），不必继承 `ApplicationEvent`
- **异步事件**：订阅者方法加 `@Async` + 启动类加 `@EnableAsync`
- ruoyi-vue-pro 通过 `ApplicationRunner` / `CommandLineRunner` 实现启动后钩子
- ruoyi 通过 RPC + MQ 实现跨服务的"事件驱动"

---

**文档版本**：v1.0
**最后更新**：2026-07-13
