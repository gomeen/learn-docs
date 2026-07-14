# 3.3 观察者模式（Observer）

> 观察者模式定义对象间一对多的依赖关系，当一个对象状态变化时，所有依赖者都收到通知。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解观察者模式的核心（发布-订阅）
- 区分观察者 vs 责任链
- 识别 ruoyi 的 Spring ApplicationEvent
- 知道观察者模式的优缺点

## 📚 前置知识

- 接口与回调
- 异步编程基础

## 1. 核心概念

### 1.1 观察者模式的核心思想

**主题（Subject）** 维护一组 **观察者（Observer）**，状态变化时**自动通知**所有观察者。

### 1.2 经典比喻

公众号订阅：你关注公众号（订阅），公众号发文时所有订阅者收到推送。

### 1.3 观察者 vs 发布订阅

| 维度 | 观察者 | 发布订阅（Pub/Sub） |
|------|--------|--------------------|
| 耦合 | 主题知道观察者 | 通过 broker 解耦 |
| 通信 | 直接调用 | 异步消息 |
| 实现 | 简单 | 复杂（Redis/Kafka） |

## 2. 代码示例

### 2.1 经典观察者

```python
from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod
    def update(self, message: str) -> None:
        ...

class Subject:
    def __init__(self):
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)

    def notify(self, message: str) -> None:
        for obs in self._observers:
            obs.update(message)


class EmailNotifier(Observer):
    def update(self, message: str) -> None:
        print(f"Email: {message}")

class SMSNotifier(Observer):
    def update(self, message: str) -> None:
        print(f"SMS: {message}")


# 使用
publisher = Subject()
publisher.attach(EmailNotifier())
publisher.attach(SMSNotifier())
publisher.notify("New order!")  # 两个观察者都收到
```

### 2.2 Python 内置观察者（简单的）

```python
class EventEmitter:
    """Node.js 风格的 EventEmitter"""

    def __init__(self):
        self._listeners: dict[str, list] = {}

    def on(self, event: str, callback):
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, *args, **kwargs):
        for cb in self._listeners.get(event, []):
            cb(*args, **kwargs)


emitter = EventEmitter()
emitter.on("user.created", lambda user: print(f"Send welcome to {user}"))
emitter.on("user.created", lambda user: print(f"Log user {user}"))
emitter.emit("user.created", "Alice")
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 ruoyi 的 Spring ApplicationEvent

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
**核心代码**：

```java
@Service
public class AdminUserServiceImpl implements AdminUserService {

    @Resource
    private ApplicationEventPublisher eventPublisher;  // 事件发布者

    @Override
    @Transactional
    public Long createUser(UserSaveReqVO reqVO) {
        // 1. 插入用户
        AdminUserDO user = ...;
        userMapper.insert(user);

        // 2. 发布事件——通知所有订阅者
        eventPublisher.publishEvent(new UserCreatedEvent(user.getId()));
        return user.getId();
    }
}

// 订阅者 1：发送欢迎邮件
@EventListener
public void onUserCreated(UserCreatedEvent event) {
    emailService.sendWelcome(event.getUserId());
}

// 订阅者 2：记录审计日志
@EventListener
public void onUserCreated(UserCreatedEvent event) {
    auditLogService.record("USER_CREATED", event.getUserId());
}
```

**解读**：
- `ApplicationEventPublisher` 发布事件
- `@EventListener` 监听事件——观察者
- 业务代码只管发事件，无需知道谁订阅——解耦
- **整体设计**：Spring 事件机制实现模块间解耦

### 3.2 dify 的 Celery 任务队列（异步观察者）

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 1-30）：

```python
from tasks.workflow import run_workflow_task

def trigger_workflow(workflow_id: str, inputs: dict) -> str:
    """触发工作流——发布任务到 Celery"""
    # 1. 同步落库
    with Session(db.engine) as session:
        run = WorkflowRun(workflow_id=workflow_id, status="pending")
        session.add(run)

    # 2. 发布异步任务（订阅者：Celery Worker）
    run_workflow_task.delay(workflow_id=workflow_id, inputs=inputs)
    return run.id
```

**解读**：
- API 发布任务（事件）
- Celery Worker 异步消费（订阅者）
- **整体设计**：用消息队列实现异步观察者

## 4. 关键要点总结

- 观察者 = 发布-订阅
- 主题状态变化自动通知观察者
- ruoyi 用 Spring ApplicationEvent（同步观察者）
- dify 用 Celery（异步观察者）
- 优点：解耦、支持广播
- 缺点：通知顺序难保证、可能循环依赖

## 5. 练习题

### 练习 1：基础
实现一个用户注册系统，注册成功后通知邮件、短信、日志 3 个观察者。

### 练习 2：进阶
阅读 ruoyi 的 `AdminUserServiceImpl`，找出所有 `publishEvent` 的位置。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- Spring Events：https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html
- 《设计模式》第 5 章：观察者模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13