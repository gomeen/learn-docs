# 11.08 SOLID 原则

> 用五条设计原则管理变化、替换和依赖，让代码更容易扩展与验证。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释 SOLID 五项原则分别解决什么设计问题
- 用变化原因判断类是否符合单一职责原则
- 使用组合、Protocol 和依赖注入构建可替换组件
- 识别违反 LSP 与 ISP 的接口设计
- 看懂 dify controller → service → core/domain 分层中的依赖方向

## 📚 前置知识

- Python 类、继承、组合与类型注解
- `typing.Protocol` 的基本概念（详见 [Protocol 与 Generic](../01-fundamentals/09-protocol-generic.md)）
- 依赖注入和单元测试基础
- 已阅读 `06-refactor-basics.md` 与 `07-code-smells.md`
- 设计模式总览中的 SOLID 对照（可选，详见 [SOLID 原则（模式篇）](../../_fundamentals/06-design-patterns/24-solid.md)）

## 🧱 核心概念

### SOLID 是决策工具，不是类数量目标

SOLID 由五项面向对象设计原则组成：

| 缩写 | 原则 | 关注问题 |
|---|---|---|
| S | Single Responsibility Principle | 谁因什么原因变化 |
| O | Open/Closed Principle | 如何扩展而不反复修改稳定逻辑 |
| L | Liskov Substitution Principle | 实现能否安全替换抽象 |
| I | Interface Segregation Principle | 调用者是否被迫依赖无关能力 |
| D | Dependency Inversion Principle | 业务策略是否依赖稳定抽象 |

这些原则不是要求每个函数都变成类，也不要求为每个实现创建接口。
它们帮助开发者识别变化轴，建立恰到好处的边界。

### S：单一职责原则

Single Responsibility Principle（SRP）常被概括为：
一个模块应该只有一个引起它变化的原因。
“职责”不是“一件小事”，而是对某一类参与者或业务变化负责。

例如 API endpoint 通常涉及：

- 请求 DTO 和输入校验
- 业务用例协调
- 领域规则
- 持久化
- HTTP 响应序列化

把全部细节写进 controller，会让接口协议变化与领域规则变化互相影响。
更合理的边界是：controller 负责 HTTP，service 负责用例协调，
core/domain 负责可复用的领域能力。

判断 SRP 时可问：这个模块的修改请求来自同一个角色吗？
若 API 设计者、计费负责人和数据库管理员都经常修改同一个类，职责可能过多。

### O：开放封闭原则

Open/Closed Principle（OCP）要求软件实体对扩展开放、对修改封闭。
含义不是“旧代码永远不能改”，而是当一个变化轴已经稳定出现时，
新增变体应主要通过添加实现完成，避免反复修改中央条件分支。

例如通知服务已经有 email、webhook、短信多个渠道，
可以定义 `Notifier` 契约并注入不同实现；新增渠道不必修改订单用例。

但只有一个实现、没有真实变化证据时，先写简单函数通常更好。
OCP 不应成为 Speculative Generality 的借口。

### L：里氏替换原则

Liskov Substitution Principle（LSP）要求：若 `S` 是 `T` 的子类型，
程序中使用 `T` 的位置应能换成 `S`，且正确性不被破坏。

可操作的契约规则包括：

- 子类型不能加强前置条件
- 子类型不能削弱后置条件
- 子类型应保持异常与副作用语义
- 子类型应维护抽象声明的不变量

典型违反是抽象接口承诺 `send()` 可发送消息，某个子类却对合法输入抛出
`NotImplementedError`。这说明继承层次并不真实，应拆分接口或使用组合。

Python 的鸭子类型不会自动保证 LSP。Protocol、类型检查和契约测试结合，
才能验证不同实现是否具有一致行为。

### I：接口隔离原则

Interface Segregation Principle（ISP）要求调用者不应被迫依赖它不使用的方法。
宽接口会带来两个问题：

- 实现类被迫写空方法或抛出 `NotImplementedError`
- 调用者获得不必要能力，依赖面扩大

例如把 `send`、`history`、`retry`、`delete` 都放进一个 `MessagingPlatform`，
只会发送消息的 webhook 实现就必须伪装支持其他能力。
可以拆成 `MessageSender`、`MessageHistoryReader` 等小型 Protocol。

接口大小没有固定数字。应根据调用者角色拆分，而不是机械地“一方法一接口”。

### D：依赖倒置原则

Dependency Inversion Principle（DIP）包含两层含义：

- 高层策略不依赖低层实现，两者依赖抽象
- 抽象不依赖细节，细节依赖抽象

例如订单用例不应在内部直接构造 SMTP 客户端。
它只依赖 `Notifier` 契约，应用装配位置决定注入 Email 或 Fake 实现。
这样业务规则无需了解网络协议，测试也不需要真实外部服务。

“依赖注入”是实现 DIP 的手段之一，不等于 DIP 本身。
若注入的是一个巨大具体对象，高层仍然可能依赖低层细节。

### 五项原则如何协作

一个设计往往同时使用多项原则：

- SRP 找到通知与订单计算两个变化原因
- ISP 提取订单用例真正需要的 `send` 能力
- DIP 让用例依赖 `Notifier` Protocol
- OCP 允许通过新增实现扩展通知渠道
- LSP 要求 Fake、Email、Webhook 实现保持同一契约

实施时仍然遵循 Red-Green-Refactor：先用需求和测试证明变化轴，
再提取最小边界，不一次搭建完整框架。

## 💻 代码示例

### 使用 Protocol 与构造器注入通知能力

**示例文件**：`examples/solid_notifications.py`  
**示例代码**（行 1-49，独立可运行示例）：

```python
from dataclasses import dataclass
from typing import Protocol


class Notifier(Protocol):
    def send(self, recipient: str, message: str) -> None: ...


@dataclass(frozen=True)
class Order:
    customer_email: str
    total: int


class CheckoutService:
    def __init__(self, notifier: Notifier) -> None:
        self._notifier = notifier

    def checkout(self, order: Order) -> str:
        if order.total <= 0:
            raise ValueError("total must be positive")
        confirmation = f"paid:{order.total}"
        self._notifier.send(order.customer_email, confirmation)
        return confirmation


class EmailNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"email to {recipient}: {message}")


class RecordingNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))


def test_checkout_uses_notifier_contract() -> None:
    notifier = RecordingNotifier()
    service = CheckoutService(notifier)
    order = Order("user@example.com", 1200)

    result = service.checkout(order)

    assert result == "paid:1200"
    assert notifier.messages == [
        ("user@example.com", "paid:1200")
    ]
```

`CheckoutService` 只负责结账用例协调，符合 SRP；它只依赖 `Notifier.send`，
体现 ISP 与 DIP。新增 `WebhookNotifier` 时无需修改结账逻辑，体现 OCP。
只要新实现接受相同合法输入并完成发送契约，就能满足 LSP。

示例中的 `print` 仅表示外部发送动作；生产代码应使用真正的 adapter 和日志设施。

## 🔍 dify 仓库源码解读

### Controller 请求模型的单一职责

**文件位置**：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`  
**核心代码**（行 13-25）：

```markdown

## Naming

- Request body models: use a `Payload` suffix.
  - Example: `WorkflowRunPayload`, `DatasourceVariablesPayload`.
- Query parameter models: use a `Query` suffix.
  - Example: `WorkflowRunListQuery`, `MessageListQuery`.
- Response models: use a `Response` suffix and inherit from `ResponseModel`.
  - Example: `WorkflowRunDetailResponse`, `WorkflowRunNodeExecutionListResponse`.
- Use `ListResponse` or `PaginationResponse` for wrapper responses.
  - Example: `WorkflowRunNodeExecutionListResponse`, `WorkflowRunPaginationResponse`.
- Keep these models near the controller when they are endpoint-specific. Move them to `fields/*_fields.py` only when shared by multiple controllers.
```

**解读**：

- 第 16-22 行分别命名 Payload、Query 与 Response，避免一个 DTO 同时承担输入和输出职责。
- 输入校验变化不会被迫修改响应 DTO，体现按变化原因拆分的 SRP。
- 第 24 行按复用范围决定模块位置：endpoint 专属模型留在 controller 附近。
- 只有被多个 controller 共享时才移动，避免为了假想复用提前创建公共模块。
- 命名本身暴露职责，评审者能快速发现把 Query 当 Response 使用的边界混乱。

### 分层架构与依赖方向

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 105-116）：

```markdown
### Architecture & Boundaries

- Mirror the layered architecture: controller → service → core/domain.
- Reuse existing helpers in `core/`, `services/`, and `libs/` before creating new abstractions.
- Optimise for observability: deterministic control flow, clear logging, actionable errors.

### Logging & Errors

- Never use `print`; use a module-level logger:
  - `logger = logging.getLogger(__name__)`
- Include tenant/app/workflow identifiers in log context when relevant.
- Raise domain-specific exceptions (`services/errors`, `core/errors`) and translate them into HTTP responses in controllers.
```

**解读**：

- 第 107 行规定 controller → service → core/domain 的调用方向，高层 HTTP 入口不应吞并领域实现。
- 分层让协议、用例协调和领域能力各有明确变化原因，首先体现 SRP。
- core/domain 能通过稳定契约承载策略，外围 controller 和 provider 细节围绕边界协作，体现 DIP。
- 第 108 行要求复用现有抽象，避免为同一能力创建竞争接口。
- 第 116 行由领域层抛专用异常、controller 翻译 HTTP 响应，错误职责也遵守分层。

需要注意：仅有目录箭头不自动保证 DIP。还要检查 service 是否直接构造具体客户端、
core 是否反向导入 controller，以及依赖是否能在装配位置替换。

## ✅ 关键要点总结

- SRP 按变化原因拆职责，不是要求每个类只有一个方法。
- OCP 在真实变化轴上建立扩展点，不是禁止修改代码。
- LSP 关注前置条件、后置条件、不变量、异常和副作用的可替换性。
- ISP 按调用者需要拆接口，避免实现无关方法。
- DIP 让业务策略依赖稳定契约，把具体细节放在边界和装配位置。
- Protocol、构造器注入与契约测试是 Python 中常见的组合方式。
- dify 的 controller → service → core/domain 为职责与依赖方向提供了架构基线。

## 🧪 练习题

### 练习：原则配对（基础）

为下列问题选择最主要的 SOLID 原则，并说明其他相关原则：

- 子类对基类允许的输入抛出 `NotImplementedError`
- service 内部直接创建 SMTP 客户端
- controller 同时校验 HTTP 参数和计算计费规则
- 一个实现被迫提供从不使用的 `delete_history()`
- 每新增通知渠道都修改一个中央 `if/elif`

### 练习：扩展示例（进阶）

为独立示例增加 `WebhookNotifier`：

- 不修改 `CheckoutService`
- 使用相同的契约测试验证 `RecordingNotifier` 与新实现
- 说明新实现如何保持 LSP
- 分析是否需要为重试能力扩展现有 Protocol，还是创建新接口

### 练习：审查 dify 依赖方向（挑战）

选择一条 dify 后端调用链，绘制：

```text
Controller → Service → Core/Domain → Infrastructure Adapter
```

记录每层的输入、输出、异常和副作用，并回答：

- 哪些类是高层策略，哪些是实现细节？
- 是否存在反向依赖？
- 哪个接口可以缩小以符合 ISP？
- 如果替换外部 provider，领域行为能否保持不变？

## 📖 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
- Robert C. Martin, *Agile Software Development, Principles, Patterns, and Practices*
- Python `typing.Protocol` 文档：https://docs.python.org/3/library/typing.html#typing.Protocol
- Martin Fowler, Dependency Injection：https://martinfowler.com/articles/injection.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
