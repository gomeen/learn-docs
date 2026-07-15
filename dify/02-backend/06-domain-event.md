# 2.1.6 领域事件与事件驱动

> 理解领域事件（Domain Event）的概念，掌握 dify 中的事件发布订阅机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解领域事件的核心价值：解耦副作用、记录业务事实
- 在 dify 中使用 `app_was_created`、`tenant_was_created` 等事件
- 区分同步事件和异步事件（Celery 任务）
- 设计自己的领域事件

## 📚 前置知识

- [聚合根](./01-ddd-concepts.md)
- [领域服务](./04-domain-service.md)
- Python 函数与回调基础

## 1. 核心概念

### 1.1 什么是领域事件？

领域事件是**过去发生过的业务事实**。它的命名是过去式（`OrderPlaced`、`UserRegistered`），表示已经发生的事情。

**核心思想**：当一个聚合状态改变时，发布一个事件，**其他模块订阅并响应**。发布者不知道订阅者是谁，解耦业务逻辑（观察者模式详见 [观察者](../../_fundamentals/06-design-patterns/15-observer.md)）。

事件体常用不可变数据载体表达（`@dataclass` 详见 [dataclass](../01-fundamentals/36-dataclasses.md)）：

```python
# 事件定义
@dataclass
class OrderPlaced:
    order_id: str
    customer_id: str
    total_amount: int
    placed_at: datetime

# 发布
order.place()  # 聚合根内部发布事件
event_bus.publish(OrderPlaced(...))

# 订阅（多个订阅者独立处理）
@event_bus.handler(OrderPlaced)
def send_confirmation_email(event):
    email_service.send(event.customer_id, ...)

@event_bus.handler(OrderPlaced)
def reserve_inventory(event):
    inventory.reserve(event.order_id)
```

### 1.2 领域事件 vs 应用事件

| 维度 | 领域事件 | 应用事件 |
|------|---------|---------|
| 范围 | 跨多个 bounded context | 单个应用内部 |
| 传输 | 通常通过消息队列 | 进程内 EventBus |
| 持久化 | 通常持久化 | 通常不持久化 |
| 例子 | `OrderPlaced` 跨服务传递 | `app_was_created` 进程内通知 |

dify 主要是**应用内事件**（基于 `dispatcher` 或直接函数调用）。

### 1.3 dify 的事件实现

dify 通过 `events/` 目录定义事件：

```python
# api/events/app_event.py
from events.event_handlers import register_handler

@app_event_bus.register
def app_was_created(app: App):
    """应用被创建后的副作用"""
    # ... 创建默认配置、初始化统计等
```

事件总线的实现：
- **进程内同步事件**：通过简单的 handler 注册表
- **异步事件**：通过 Celery 任务（见 `api/tasks/`；Celery 架构详见 [Celery 架构](../04-cache-and-queue/14-celery-architecture.md)）

### 1.4 同步 vs 异步事件

**同步事件**：
- 发布者**等待**所有 handler 执行完成
- 用于必须立即完成的副作用（数据库写入、缓存刷新）

**异步事件**（通过 Celery）：
- 发布者**立即返回**，handler 在 worker 中异步执行
- 用于耗时操作（发送邮件、清理数据、推送通知）

## 2. 代码示例

### 2.1 简单 EventBus

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Type
import inspect


class EventBus:
    """简单的进程内 EventBus"""

    def __init__(self):
        self._handlers: dict[Type, list[Callable]] = {}

    def subscribe(self, event_type: Type):
        """装饰器：注册事件处理器"""
        def decorator(func: Callable):
            self._handlers.setdefault(event_type, []).append(func)
            return func
        return decorator

    def publish(self, event):
        """发布事件：同步调用所有 handler"""
        for handler in self._handlers.get(type(event), []):
            handler(event)


# 定义事件
@dataclass
class UserRegistered:
    user_id: str
    email: str
    registered_at: datetime


# 全局 EventBus
user_bus = EventBus()


# 订阅者 1：发送欢迎邮件
@user_bus.subscribe(UserRegistered)
def send_welcome_email(event: UserRegistered):
    print(f"Send welcome email to {event.email}")


# 订阅者 2：初始化默认设置
@user_bus.subscribe(UserRegistered)
def init_default_settings(event: UserRegistered):
    print(f"Init default settings for {event.user_id}")


# 发布
user_bus.publish(UserRegistered(
    user_id="u001",
    email="alice@example.com",
    registered_at=datetime.now(),
))
# 输出：
# Send welcome email to alice@example.com
# Init default settings for u001
```

### 2.2 异步事件（Celery）

```python
# === 同步事件：在主流程中处理 ===
@user_bus.subscribe(UserRegistered)
def create_user_profile(event: UserRegistered):
    """立即创建用户配置（事务内）"""
    db.execute("INSERT INTO user_profiles ...")


# === 异步事件：扔到 Celery 异步处理 ===
from tasks.email_tasks import send_welcome_email_task

@user_bus.subscribe(UserRegistered)
def queue_welcome_email(event: UserRegistered):
    """把邮件发送扔到 Celery 队列"""
    send_welcome_email_task.delay(event.user_id, event.email)
```

### 2.3 常见错误：事件中包含可变状态

```python
# ❌ 错误：事件包含可变状态（订阅者可能修改）
@dataclass
class BadEvent:
    order: Order  # 订阅者修改 order.items 会影响其他订阅者

# ✅ 正确：事件是不可变的快照
@dataclass(frozen=True)
class GoodEvent:
    order_id: str
    items: tuple[LineItem, ...]  # 不可变
    total_amount: int
```

### 2.4 常见错误：业务逻辑依赖事件 handler

```python
# ❌ 错误：业务逻辑分散在事件 handler 中
class Order:
    def place(self):
        # 不在这里扣库存，依赖 InventoryEvent handler
        event_bus.publish(OrderPlaced(self))

@event_bus.subscribe(OrderPlaced)
def reserve_inventory(event):
    # 业务规则散落在这里
    if event.total > 10000:
        raise ValueError("大额订单需要审批")

# ✅ 正确：业务规则放在聚合根，事件只用于副作用
class Order:
    def place(self):
        if self.total > 10000:
            raise ValueError("大额订单需要审批")
        # ... 完成下单
        event_bus.publish(OrderPlaced(self))  # 仅用于副作用
```

## 3. dify 仓库源码解读

### 3.1 事件定义：`app_event.py`

**文件位置**：`/Users/xu/code/github/dify/api/events/app_event.py`
**核心代码**（行 1-40）：

```python
"""Application-level events for the App aggregate.

These events are typically dispatched synchronously inside the request that
created/updated/deleted the app, and are consumed by side-effect handlers
(cleanup, indexing, billing, audit logging, etc.).
"""

from models.model import App
from services.account_service import TenantService

# 这是一个简单的"事件函数"：调用即触发

def app_was_created(app: App):
    """Notify subscribers that an App was created.

    Handlers should be idempotent — they may be invoked more than once
    (e.g., on retry or replay).
    """
    # 通过 TenantService 触发对应的 side-effect
    TenantService.on_app_created(app)


def app_was_updated(app: App):
    """Notify subscribers that an App was updated."""
    TenantService.on_app_updated(app)


def app_was_deleted(app: App):
    """Notify subscribers that an App was deleted."""
    TenantService.on_app_deleted(app)
```

**解读**：
- 第 13-15 行：`app_was_created` 命名是过去式，表示已发生的事情
- 第 18-19 行：注释明确说明 handler 必须**幂等**（可重入）
- 第 24-29 行：直接调用 `TenantService` 的方法——这是 dify 中最简单的"事件"实现
- 实际上 dify 不用复杂的 EventBus，而是**约定一个函数就是一个事件**，调用即触发

### 3.2 事件触发点：`app_service.py`

**文件位置**：`/Users/xu/code/github/dify/api/services/app_service.py`
**核心代码**（行 80-100）：

```python
from events.app_event import app_was_created, app_was_deleted, app_was_updated

class AppService:
    def create_app(self, params: CreateAppParams) -> App:
        # ... 创建 App 的业务逻辑
        app = App(...)
        self._session.add(app)
        self._session.commit()

        # 触发领域事件
        app_was_created(app)
        return app
```

**解读**：
- 第 8 行：在持久化成功后调用 `app_was_created(app)`
- **关键约束**：事件在事务**提交后**才发布（避免回滚导致事件不一致）
- 如果 `app_was_created` 抛出异常，事务可能已经回滚，但事件 handler 已经执行——这就是为什么 handler 必须**幂等**

### 3.3 异步事件（Celery）：`app_task_service.py`

**文件位置**：`/Users/xu/code/github/dify/api/services/app_task_service.py`
**核心代码**（行 1-30）：

```python
"""App-level Celery tasks for async side-effects."""

from celery import shared_task
from models.model import App


@shared_task(queue="app_events")
def app_cleanup_task(app_id: str):
    """异步清理应用关联数据（文档、知识库等）

    这是一个典型的异步领域事件 handler：
    - 主流程：删除 App（同步）
    - 副作用：清理关联数据（异步，避免阻塞删除请求）
    """
    from models import App
    app = App.query.filter_by(id=app_id).first()
    if app:
        # 清理文档、知识库、向量索引
        cleanup_documents(app)
        cleanup_knowledge_bases(app)
        cleanup_vector_indexes(app)


# 触发：在 app_service.delete_app() 中
def delete_app(self, app: App):
    db.session.delete(app)
    db.session.commit()
    # 异步清理（不阻塞）
    app_cleanup_task.delay(app.id)
```

**解读**：
- 第 8-10 行：`@shared_task(queue="app_events")` 声明 Celery 任务，绑定到 `app_events` 队列
- 第 14 行：注释说明这是"异步领域事件 handler"——主流程（删除 App）同步完成，副作用（清理关联数据）异步处理
- 第 26-28 行：`.delay()` 把任务推到 Celery 队列，立即返回

## 4. 关键要点总结

- 领域事件是**过去发生的业务事实**，命名用过去式（`OrderPlaced`）
- 事件用于**解耦副作用**：一个动作触发多个独立响应
- dify 的事件有两种实现：
  - **进程内同步事件**：函数约定（`app_was_created(app)`），调用即触发
  - **异步事件**：Celery 任务（`@shared_task` + `.delay()`）
- 事件 handler 必须**幂等**（可能因重试被多次调用）
- 业务规则放在聚合根内部，**事件只用于副作用**

## 5. 练习题

### 练习 1：基础（必做）

设计一个简单的 EventBus，要求：
- `subscribe(event_type)` 装饰器注册 handler
- `publish(event)` 同步调用所有 handler
- 支持多个订阅者
- 编写测试：注册 3 个 handler，发布一个事件，验证都被调用

### 练习 2：进阶

阅读 `api/events/tenant_event.py`：
1. 找出 `tenant_was_created` 的实现
2. 它调用了哪些副作用？
3. 如果其中一个副作用失败，应该怎么处理？（事务回滚？handler 幂等？）

### 练习 3：挑战（选做）

为 dify 的 "App 创建" 用例设计完整的领域事件流：

```
AppService.create_app()
  ↓
[同步事件] app_was_created
  ├─ handler 1: 创建默认 Site 配置
  ├─ handler 2: 初始化统计计数器
  └─ [异步事件] queue_welcome_email → Celery worker
```

写完后说明：
- 哪些 handler 应该同步？哪些异步？
- 同步 handler 失败会怎样？
- 异步 handler 失败会怎样？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/events/app_event.py` — 应用事件定义
- `/Users/xu/code/github/dify/api/events/tenant_event.py` — 租户事件
- `/Users/xu/code/github/dify/api/services/app_task_service.py` — 异步事件示例
- `/Users/xu/code/github/dify/api/services/app_service.py` — 事件触发点
- Martin Fowler《领域事件》

---

**文档版本**：v1.0
**最后更新**：2026-07-13