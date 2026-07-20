# 2.1.1 DDD 核心概念：实体、值对象、聚合根

> 理解 DDD（领域驱动设计）的三大核心概念，能识别 dify 后端代码中的领域对象。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分实体（Entity）、值对象（Value Object）、聚合根（Aggregate Root）的差异
- 理解领域模型的设计原则：不变性、身份标识、边界封装
- 在 dify 仓库中找到对应的领域对象（如 `WorkflowExecution`、`Message`、`Account`）
- 应用 DDD 概念设计清晰的领域边界

## 📚 前置知识

- Python 基础语法（[`dataclass`](../../dify/01-fundamentals/22-dataclasses.md)、[Pydantic BaseModel](../../dify/02-backend/09-pydantic-basics.md)）
- [TypedDict](../../dify/01-fundamentals/08-typeddict.md)（与 Pydantic 的区别）
- 了解面向对象设计基础（封装、继承）

## 1. 核心概念

### 1.1 为什么需要 DDD？

传统三层架构（Controller → Service → DAO）容易导致业务逻辑散落在 Service 层，模型层变成贫血模型（只有 getter/setter 没有行为）。DDD 把业务逻辑**收敛到领域模型**内部，让代码结构贴近业务语义。

**贫血模型 vs 充血模型**：

```python
# ❌ 贫血模型：数据和行为分离
class UserData:
    name: str
    balance: int

class UserService:
    def deposit(self, user: UserData, amount: int):
        user.balance += amount  # 业务逻辑在 Service

# ✅ 充血模型：数据 + 行为封装
class User:
    def __init__(self, name: str, balance: int):
        self.name = name
        self.balance = balance

    def deposit(self, amount: int):
        if amount <= 0:
            raise ValueError("金额必须大于 0")
        self.balance += amount  # 业务逻辑在领域对象内部
```

### 1.2 实体（Entity）

实体有**唯一身份标识**（ID），生命周期内状态可变。两个实体即使所有属性相同，只要 ID 不同就是不同的实体。

**特点**：
- 有 `id` 或 `uuid` 标识
- 可变性：通过方法改变状态而非直接修改属性
- 持久化：通常映射到数据库表

**dify 示例**：`WorkflowRun`、`App`、`Account`、`Message` 都属于实体。

### 1.3 值对象（Value Object）

值对象**没有身份**，只关心属性值。两个值对象属性相同就视为相等。值对象应该是**不可变的**。

**特点**：
- 用 `frozen=True` 或不提供 setter
- 通过 `__eq__` 比较值
- 不独立持久化，作为实体的一部分存储

**dify 示例**：`FileReference`、`RetrievalSourceMetadata`、`ModelConfigWithCredentialsEntity` 都是值对象。

### 1.4 聚合根（Aggregate Root）

聚合根是聚合的**唯一入口**，外部对象只能通过聚合根修改聚合内的对象。聚合根负责**一致性边界**：一个事务只修改一个聚合。

**设计原则**：
- 聚合根有全局唯一 ID
- 聚合内部对象通过聚合根访问
- 跨聚合访问通过 ID 引用而非对象引用
- 事务边界 = 聚合边界

**dify 示例**：`WorkflowExecution` 是聚合根，`WorkflowNodeExecution` 是聚合内部的实体。

### 1.5 三者对比

| 维度 | 实体 | 值对象 | 聚合根 |
|------|------|--------|--------|
| 身份标识 | 有 | 无 | 有 |
| 可变性 | 可变 | 不可变 | 可变 |
| 相等性 | 按 ID | 按值 | 按 ID |
| 持久化 | 独立 | 嵌入实体 | 独立 |
| 例子 | `User` | `Address` | `Order` |

## 2. 代码示例

### 2.1 实体 vs 值对象

`@dataclass` 用于快速定义领域对象（机制见前置 [dataclass](../../dify/01-fundamentals/22-dataclasses.md)），此处只把它当作「带默认构造与可选不可变」的数据类。

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

# 实体：有身份 ID
@dataclass
class Account:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def rename(self, new_name: str):
        self.name = new_name  # 实体可变

    def __eq__(self, other):
        if not isinstance(other, Account):
            return False
        return self.id == other.id  # 按 ID 比较

    def __hash__(self):
        return hash(self.id)


# 值对象：无身份、不可变、按值相等
@dataclass(frozen=True)  # frozen=True 强制不可变
class Money:
    amount: int
    currency: str = "CNY"

    def __eq__(self, other):
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self):
        return hash((self.amount, self.currency))


# 使用
a1 = Account(name="Alice")
a2 = Account(name="Alice")
print(a1 == a2)  # False（不同 ID）

m1 = Money(100, "USD")
m2 = Money(100, "USD")
print(m1 == m2)  # True（值相同）
```

### 2.2 聚合根：保证一致性边界

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from typing import List

@dataclass(frozen=True)
class LineItem:  # 值对象：订单项
    product_id: str
    quantity: int
    price: int

@dataclass
class Order:  # 聚合根
    id: UUID = field(default_factory=uuid4)
    items: List[LineItem] = field(default_factory=list)
    status: str = "pending"

    def add_item(self, item: LineItem):
        """只能通过聚合根修改聚合内对象"""
        self.items.append(item)

    def total(self) -> int:
        return sum(item.price * item.quantity for item in self.items)

    def pay(self):
        if self.total() == 0:
            raise ValueError("空订单不能支付")
        self.status = "paid"


# 使用
order = Order()
order.add_item(LineItem("P001", 2, 50))
order.add_item(LineItem("P002", 1, 30))
order.pay()
print(f"订单 {order.id} 总额 {order.total()}，状态 {order.status}")
```

### 2.3 常见错误：跨聚合直接修改

```python
# ❌ 错误：绕过聚合根直接修改内部对象
class OrderBad:
    def __init__(self):
        self.items = []  # 暴露内部可变对象

order = OrderBad()
order.items.append(LineItem("P001", 1, 100))  # 没有走业务校验

# ✅ 正确：通过聚合根的方法修改
class OrderGood:
    def __init__(self):
        self._items: List[LineItem] = []  # 私有

    @property
    def items(self) -> List[LineItem]:
        return list(self._items)  # 返回副本

    def add_item(self, item: LineItem):
        if item.quantity <= 0:
            raise ValueError("数量必须大于 0")
        self._items.append(item)
```

## 3. dify 仓库源码解读

### 3.1 实体：`WorkflowRun`

**文件位置**：`/Users/xu/code/github/dify/api/models/workflow.py`
**核心代码**（行 1-50）：

```python
import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID
from models.base import Base

class WorkflowRun(Base):
    """WorkflowRun 是一次工作流执行的聚合根。

    每次用户触发 workflow 都会创建一条 WorkflowRun 记录，
    下属的 WorkflowNodeExecution 通过 workflow_run_id 关联到此聚合根。
    """
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(
        UUID, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(UUID, nullable=False, index=True)
    app_id: Mapped[str] = mapped_column(UUID, nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(UUID, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(255), nullable=False, default="running")
    inputs: Mapped[str] = mapped_column(Text, nullable=True)
    outputs: Mapped[str] = mapped_column(Text, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**解读**：
- `WorkflowRun` 继承 SQLAlchemy `Base` 做表映射（ORM 声明式映射详见 [SQLAlchemy 映射](../../dify/03-database/02-sqlalchemy-mapping.md)，此处不展开）
- 第 14 行：`id` 是 UUID，是实体的身份标识
- 第 18-20 行：外键字段（`tenant_id`、`app_id`、`workflow_id`），都是按 ID 引用其它聚合
- 第 21-22 行：`status` 标识当前执行状态，会随生命周期变化（实体可变性的体现）
- 第 26-27 行：`created_at` / `finished_at` 体现执行的时间维度

### 3.2 值对象：`RetrievalSourceMetadata`

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/entities.py`
**核心代码**（行 1-30）：

```python
from pydantic import BaseModel, ConfigDict

class RetrievalSourceMetadata(BaseModel):
    """检索结果中的元数据值对象。

    表示知识库中某个文档片段的元信息。没有身份 ID，
    仅作为 Message 实体的引用来源存在。
    """
    model_config = ConfigDict(extra="ignore")

    dataset_id: str
    dataset_name: str
    document_id: str
    document_name: str
    segment_id: str
    score: float
    content: str
```

**解读**：
- 第 8 行：继承 `BaseModel`，Pydantic 默认按值相等（值对象特性；机制详见 [Pydantic 基础](../../dify/02-backend/09-pydantic-basics.md)）
- 没有 `id` 字段——值对象不需要自己的身份
- 第 16 行：没有 `frozen=True`，但作为 DTO 应该视作只读快照

## 4. 关键要点总结

- **实体**有 ID 和生命周期，可变性是其核心特征
- **值对象**无 ID、不可变、按值相等，用于描述属性
- **聚合根**是事务一致性的边界，外部只能通过聚合根操作内部对象
- dify 中 `WorkflowRun`、`App` 是聚合根；`RetrievalSourceMetadata` 是值对象
- 跨聚合通过 ID 引用（`workflow_run_id`），避免对象引用导致耦合

## 5. 练习题

### 练习 1：基础（必做）

为 dify 的 `Message` 实体设计一个 `TokenUsage` 值对象，字段包括 `prompt_tokens`、`completion_tokens`、`total_tokens`，要求：
- 不可变（frozen）
- 支持 `+` 操作合并两个 TokenUsage
- 实现 `__str__` 输出 `"{prompt}+{completion}={total}"`

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/models/workflow.py` 中的 `WorkflowNodeExecution`，找出：
1. 它属于哪个聚合根？
2. 它自己有什么字段？它如何引用 `WorkflowRun`？
3. 它为什么不能脱离 `WorkflowRun` 独立操作？

### 练习 3：挑战（选做）

把 dify 的 `Conversation` 设计为聚合根，其中包含 `Message` 实体集合。画出它们的类图（用 mermaid 或文字描述），并说明为什么不能直接通过 `Conversation.messages.append(...)` 修改消息。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/workflow.py` — `WorkflowRun`、`WorkflowNodeExecution` 实体
- `/Users/xu/code/github/dify/api/core/rag/entities.py` — 值对象 `RetrievalSourceMetadata`
- `/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py` — 领域上下文与值对象
- Eric Evans《领域驱动设计》
- Vaughn Vernon《实现领域驱动设计》

---

**文档版本**：v1.0
**最后更新**：2026-07-13