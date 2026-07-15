# 2.1.4 领域服务与应用服务的边界

> 理解领域服务（Domain Service）和应用服务（Application Service）的差异，能正确放置业务逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分领域服务和应用服务的职责
- 识别何时应该用领域服务（跨聚合的业务规则）
- 识别何时应该用应用服务（编排、事务、跨领域协调）
- 在 dify 仓库中找到两类服务的对应实现

## 📚 前置知识

- [聚合根、领域对象](./01-ddd-concepts.md)
- [分层架构](./02-layered-architecture.md)
- [仓储模式](./03-repository-pattern.md)

## 1. 核心概念

### 1.1 两类服务的定位

```
┌──────────────────────────────────────────────┐
│ Application Service（应用服务）                  │  Service 层
│ - 编排业务流程                                   │  api/services/
│ - 管理事务                                       │
│ - 协调多个聚合                                   │
├──────────────────────────────────────────────┤
│ Domain Service（领域服务）                        │  Domain 层
│ - 跨聚合的业务规则                                │  api/core/
│ - 纯领域逻辑（无技术依赖）                         │
└──────────────────────────────────────────────┘
```

| 维度 | 应用服务 | 领域服务 |
|------|---------|---------|
| 层级 | Service 层 | Domain 层 |
| 职责 | 编排、事务控制 | 业务规则 |
| 依赖 | Repository、外部服务 | 只依赖领域对象 |
| 命名 | `AppService`、`WorkflowService` | `TokenBufferMemory`、`InputModeration` |
| 是否无状态 | 是 | 通常是 |

### 1.2 何时用领域服务？

**场景**：业务规则涉及多个聚合，无法放在单个聚合根方法内。

```python
# ❌ 把跨聚合规则放在聚合根内（违反单一职责）
class Order:
    def apply_discount(self, user: User):  # Order 不应该知道 User
        if user.is_vip:
            self.total *= 0.8

# ✅ 用领域服务
class DiscountPolicy:
    """纯领域逻辑：VIP 用户订单打 8 折"""
    def calculate(self, order: Order, user: User) -> int:
        if user.is_vip:
            return int(order.total * 0.8)
        return order.total
```

**领域服务的特征**：
- 操作多个聚合
- 无状态（不持有可变状态）
- 不依赖任何基础设施（DB、HTTP、消息队列）
- 可以被多个应用服务复用

### 1.3 何时用应用服务？

**场景**：编排多个步骤、管理事务、与外部系统交互。

```python
class OrderApplicationService:
    def place_order(self, user_id: str, items: list[LineItem]) -> str:
        """编排下单流程：加载用户、计算价格、扣库存、发邮件。

        `with self.uow` 是上下文管理器写法（详见 [上下文管理器](../01-fundamentals/11-context-manager.md)），
        此处只把它当作「进入事务 / 退出时提交或回滚」来理解。
        """
        with self.uow:  # 事务边界
            user = self.user_repo.find_by_id(user_id)
            order = Order.create(items)
            final_price = self.discount_policy.calculate(order, user)  # 调用领域服务
            order.confirm(final_price)
            self.inventory_service.reserve(items)  # 调用外部服务
            self.order_repo.save(order)
            self.email_service.send_confirmation(user.email)  # 副作用
        return order.id
```

**应用服务的特征**：
- 一个方法对应一个用例（use case）
- 管理事务（`commit`/`rollback`；SQL 事务语义详见 [事务与隔离级别](../03-database/04-sql-transaction.md)）
- 协调多个聚合、外部服务
- 命名通常是动词 + 名词（`place_order`、`create_app`）

### 1.4 dify 中的命名约定

dify 仓库中：
- **应用服务**：`api/services/*.py`（如 `app_service.py`、`workflow_service.py`）
- **领域服务/纯业务逻辑**：`api/core/*.py`（如 `core/moderation/`、`core/prompt/`）

特别注意：
- `core/moderation/` 下的 `InputModeration`、`OutputModeration` 是**领域服务**（内容审核规则）
- `core/prompt/simple_prompt_transform.py`、`core/prompt/advanced_prompt_transform.py` 是**领域服务**（提示词模板转换）
- `core/rag/retrieval/` 是**领域服务**（RAG 检索算法）

## 2. 代码示例

### 2.1 领域服务：纯业务规则

```python
# === 领域对象 ===
@dataclass(frozen=True)
class Money:
    amount: int  # 单位：分
    currency: str = "CNY"

@dataclass(frozen=True)
class User:
    id: str
    is_vip: bool
    total_spent: int

@dataclass
class OrderItem:
    product_id: str
    price: Money
    quantity: int


# === 领域服务：跨聚合的业务规则 ===
class PricingPolicy:
    """定价策略：VIP 8 折，满 1000 减 100"""

    def calculate(self, user: User, items: list[OrderItem]) -> Money:
        subtotal = sum(
            (item.price.amount * item.quantity for item in items),
            start=0,
        )

        # VIP 折扣
        if user.is_vip:
            subtotal = int(subtotal * 0.8)

        # 满减
        if subtotal >= 100_000:  # 1000 元 = 100000 分
            subtotal -= 10_000

        return Money(subtotal, items[0].price.currency)


# === 应用服务：编排 ===
class OrderApplicationService:
    def __init__(self, pricing: PricingPolicy, order_repo, payment_service):
        self._pricing = pricing
        self._order_repo = order_repo
        self._payment_service = payment_service

    def place_order(self, user: User, items: list[OrderItem]) -> str:
        # 1. 调用领域服务计算价格
        total = self._pricing.calculate(user, items)

        # 2. 调用外部服务（payment）
        payment_id = self._payment_service.charge(user, total)

        # 3. 持久化订单
        order = Order.create(items=items, total=total, payment_id=payment_id)
        self._order_repo.save(order)

        return order.id
```

### 2.2 常见错误：领域服务依赖基础设施

```python
# ❌ 错误：领域服务依赖数据库
class BadDiscountPolicy:
    def __init__(self, db_session):  # 依赖泄漏
        self._db = db_session

    def calculate(self, order, user):
        # 直接查数据库——领域服务不应依赖 DB
        history = self._db.query(OrderHistory).filter_by(user_id=user.id).all()
        ...

# ✅ 正确：领域服务只接收领域对象
class GoodDiscountPolicy:
    def calculate(self, order: Order, user: User, history: list[OrderHistory]) -> int:
        # 数据由应用服务加载好后传入
        total_spent = sum(h.amount for h in history)
        ...
```

### 2.3 常见错误：应用服务包含业务规则

```python
# ❌ 错误：应用服务自己写业务规则
class BadOrderService:
    def place_order(self, user, items):
        total = sum(item.price for item in items)
        if user.is_vip:
            total = int(total * 0.8)  # 业务规则散落在 Service
        if total > 1000:
            total -= 100  # 又一个业务规则
        order = Order(items, total)
        self.order_repo.save(order)

# ✅ 正确：业务规则收敛到领域服务
class GoodOrderService:
    def place_order(self, user, items):
        total = self.pricing_policy.calculate(user, items)  # 委托给领域服务
        order = Order(items, total)
        self.order_repo.save(order)
```

## 3. dify 仓库源码解读

### 3.1 领域服务：`InputModeration`

**文件位置**：`/Users/xu/code/github/dify/api/core/moderation/input_moderation.py`
**核心代码**（行 1-40）：

```python
from configs import dify_config
from core.moderation.base import ModerationException, ModerationAction


class InputModeration:
    """输入内容审核：检测用户输入是否违规（领域服务）

    作为领域服务，它实现了"内容审核规则"这一跨多个聚合的业务规则：
    - 不修改 Workflow、Conversation 等具体聚合
    - 只根据输入文本判断是否违规
    - 输出结构化的 ModerationAction（flagged / replaced / blocked）
    """

    def __init__(
        self,
        tenant_id: str,
        app_id: str,
        user_id: str,
        inputs: dict,
        message_id: str | None = None,
    ):
        self.tenant_id = tenant_id
        self.app_id = app_id
        self.user_id = user_id
        self.inputs = inputs
        self.message_id = message_id

    def check(self) -> tuple[bool, dict]:
        """执行内容审核规则

        Returns:
            (flagged, replaced_inputs)：是否违规，以及替换后的输入
        """
        # 业务规则：调用 OpenAI Moderation API
        ...
```

**解读**：
- 第 8-15 行：注释明确说明这是"内容审核规则"——领域规则
- 第 23 行：`check()` 方法是业务规则入口，返回 `(flagged, inputs)`
- 注意：`check()` 内部会调用外部 API（OpenAI Moderation），这是 dify 中**领域服务 + 外部 API 调用**的混合模式（外部 API 调用放在领域服务中，因为它本身就是规则的一部分）

### 3.2 领域服务：`SimplePromptTransform`

**文件位置**：`/Users/xu/code/github/dify/api/core/prompt/simple_prompt_transform.py`
**核心代码**（行 1-40）：

```python
class ModelMode(StrEnum):
    CHAT = "chat"
    COMPLETION = "completion"


class SimplePromptTransform:
    """简单提示词转换：根据模型模式拼装 prompt messages。

    这是典型的领域服务：
    - 输入：原始 prompt 模板 + 模型模式
    - 输出：模型可消费的 PromptMessage 列表
    - 不依赖 DB、HTTP（纯计算）
    """

    def __init__(
        self,
        with_variable_tmpl: str,
        prompt_template: list,
        inputs: dict,
        query: str,
        system_message: str | None = None,
    ):
        self.with_variable_tmpl = with_variable_tmpl
        # ...

    def get_prompt(self) -> list:
        """根据 ModelMode 选择不同的 prompt 拼装策略"""
        if self.model_mode == ModelMode.CHAT:
            return self._get_chat_prompt()
        elif self.model_mode == ModelMode.COMPLETION:
            return self._get_completion_prompt()
```

**解读**：
- 第 14-16 行：领域服务只接收领域对象（PromptTemplate、inputs、query）
- 第 27 行：`get_prompt()` 是业务规则的入口
- 第 29-32 行：根据 `ModelMode` 走不同分支——**业务规则**，不是流程编排

### 3.3 应用服务：`AppService.get_app()`

**文件位置**：`/Users/xu/code/github/dify/api/services/app_service.py`
**核心代码**（行 60-90）：

```python
class AppService:
    """应用服务：编排 App 相关的用例。

    与领域服务的区别：
    - 关注点：业务用例（如 create_app、update_app、get_app）
    - 依赖：可调用 Repository、外部服务、领域服务
    - 事务：管理跨多个聚合的事务边界
    """

    def get_app(self, app: App) -> App:
        """用例：获取 App 详情（控制器已校验租户）"""
        # 1. 业务校验（应用服务层做权限检查）
        if app.tenant_id != current_user.current_tenant_id:
            raise UnauthorizedAndForceLogout("无权访问该应用")

        # 2. 编排：填充关联数据（site、model_config）
        if not app.site:
            app.site = self._ensure_site(app)
        if app.mode in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            app.app_model_config = self._load_model_config(app)

        return app
```

**解读**：
- 第 9-11 行：业务校验——租户权限（编排性检查）
- 第 14-18 行：编排——调用内部方法（`_ensure_site`、`_load_model_config`）填充关联数据
- **没有业务规则**：折扣计算、状态流转等应该在领域服务或聚合根内部

## 4. 关键要点总结

- **领域服务**：纯业务规则，可被多个应用服务复用，不依赖基础设施
- **应用服务**：编排业务用例，管理事务，调用领域服务 + Repository
- dify 中领域服务集中在 `api/core/`（`moderation/`、`prompt/`、`rag/`）
- dify 中应用服务集中在 `api/services/`
- **业务规则收敛**：把跨聚合规则放到领域服务，避免散落在多个 Service

## 5. 练习题

### 练习 1：基础（必做）

为 dify 设计一个 `WorkflowVersionPolicy` 领域服务：
- 输入：`Workflow` 和目标版本号
- 规则：版本号必须单调递增；不允许直接跳过中间版本
- 输出：是否允许发布，错误原因

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/prompt/advanced_prompt_transform.py`：
1. 它和 `SimplePromptTransform` 的区别是什么？
2. 它调用了哪些其他模块？（看 import 语句）
3. 它是否依赖数据库或 HTTP 框架？

### 练习 3：挑战（选做）

把 dify 中"创建工作流"用例拆分为：
1. `WorkflowApplicationService.create_workflow()`（应用服务，编排）
2. `WorkflowValidationPolicy.validate()`（领域服务，校验规则）
3. `Workflow` 聚合根的 `create()` 方法（工厂方法；工厂模式详见 [策略与工厂](./23-strategy-factory.md)，学完后再对照实现）

说明每一部分的职责和它们之间的调用顺序。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/moderation/input_moderation.py` — 领域服务示例
- `/Users/xu/code/github/dify/api/core/prompt/simple_prompt_transform.py` — 领域服务示例
- `/Users/xu/code/github/dify/api/services/app_service.py` — 应用服务示例
- `/Users/xu/code/github/dify/api/services/workflow_service.py` — 应用服务示例
- Vaughn Vernon《实现领域驱动设计》第 7 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13