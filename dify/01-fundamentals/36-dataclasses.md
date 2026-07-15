# 1.1.20 `dataclass` 数据类

> 掌握 Python 3.7+ 的 `@dataclass`，理解 `frozen` / `slots` / `field` 等高级选项，能看懂 dify 中所有 DTO / 缓存实体的写法。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `@dataclass` 替代手写 `__init__` / `__repr__` / `__eq__`
- 理解 `frozen=True`（不可变）和 `slots=True`（内存优化）的作用
- 使用 `field(default_factory=...)` 处理可变默认值
- 在 dify 中识别所有 `@dataclass` 用法（DTO、缓存条目、配置）

## 📚 前置知识

- Python 基础：类、类型注解
- 01-fundamentals/07-python-typing-basics.md
- 01-fundamentals/16-dunder-methods.md

## 1. 核心概念

### 1.1 为什么需要 dataclass

写一个普通类，需要手动写 `__init__`、`__repr__`、`__eq__` 等样板代码：

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y
```

`@dataclass` 是装饰器写法（装饰器原理见 [10-decorator](./10-decorator.md)），帮你**自动生成**这些方法：

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

# 自动获得 __init__、__repr__、__eq__
p = Point(1, 2)
print(p)            # Point(x=1, y=2)
print(Point(1, 2) == Point(1, 2))  # True
```

### 1.2 `frozen=True`：不可变数据类

```python
@dataclass(frozen=True)
class Vector:
    x: float
    y: float

v = Vector(1.0, 2.0)
v.x = 3.0  # FrozenInstanceError: cannot assign to field 'x'
```

**优点**：
- 不可变 → 可哈希（默认 `frozen` dataclass 自动获得 `__hash__`）
- 线程安全
- 防止意外修改

**注意**：浅冻结，深层嵌套对象仍可修改。

### 1.3 `slots=True`：内存优化（Python 3.10+）

```python
@dataclass(slots=True)
class User:
    id: int
    name: str
```

`slots=True` 等价于手动 `__slots__ = ('id', 'name')`（内存管理见 [41-memory-management](./41-memory-management.md)）：
- 节省内存（每个实例不再有 `__dict__`）
- 加快属性访问
- 不能再添加新属性

### 1.4 `field()`：处理可变默认值

Python 的可变默认值陷阱：

```python
# ❌ 经典陷阱
class A:
    items: list = []  # 所有实例共享同一个 list！
```

`@dataclass` 强制用 `default_factory`：

```python
from dataclasses import dataclass, field

@dataclass
class Order:
    items: list[str] = field(default_factory=list)  # ✅ 每个实例独立的 list
    tags: dict[str, int] = field(default_factory=dict)
```

`field()` 还可以：
- 排除字段（`field(compare=False)` 不参与 `__eq__`）
- 设置别名、metadata 等

### 1.5 继承

```python
@dataclass
class Animal:
    name: str

@dataclass
class Dog(Animal):
    breed: str
```

子类会继承父类的字段。

### 1.6 `asdict` / `astuple` 转换

```python
from dataclasses import dataclass, asdict

@dataclass
class User:
    id: int
    name: str

u = User(1, "Alice")
print(asdict(u))  # {'id': 1, 'name': 'Alice'}
```

## 2. 代码示例

### 2.1 基础 dataclass

```python
from dataclasses import dataclass

@dataclass
class Transaction:
    id: str
    amount: float
    currency: str = "USD"      # 有默认值
    timestamp: float = 0.0     # 有默认值

t = Transaction("tx-001", 99.9)
print(t)  # Transaction(id='tx-001', amount=99.9, currency='USD', timestamp=0.0)
```

### 2.2 不可变 + slots

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Config:
    api_key: str
    timeout: int

c = Config("sk-xxx", 30)
# c.api_key = "sk-yyy"  # FrozenInstanceError
# c.new_attr = 1        # AttributeError: 'Config' object has no attribute 'new_attr'
print(hash(c))  # 可以哈希
```

### 2.3 常见错误：可变默认值

```python
from dataclasses import dataclass, field

# ❌ 错误
@dataclass
class Cache:
    items: list = []  # ValueError: mutable default <class 'list'> is not allowed

# ✅ 正确
@dataclass
class Cache:
    items: list = field(default_factory=list)
```

## 3. dify 仓库源码解读

### 3.1 `frozen + slots` 缓存条目

**文件位置**：`/Users/xu/code/github/dify/api/core/provider_manager.py`
**核心代码**（行 95-141）：

```python
@dataclass(frozen=True, slots=True)
class _ProviderConfigurationCacheSourceSpec[T: _CacheEntry]:
    name: ProviderConfigurationCacheSource
    entry_cls: type[T]
    load_records: Callable[[str], list[T]]


@dataclass(frozen=True, slots=True)
class _ProviderModelCacheEntry:
    id: str
    provider_name: str
    model_name: str
    model_type: ModelType
    credential_id: str | None
    credential_name: str | None
    encrypted_config: str | None

    @classmethod
    def from_record(cls, record: ProviderModel) -> _ProviderModelCacheEntry:
        credential = record.__dict__.get("credential")
        return cls(
            id=record.id,
            provider_name=record.provider_name,
            model_name=record.model_name,
            model_type=record.model_type,
            credential_id=record.credential_id,
            credential_name=credential.credential_name if credential else None,
            encrypted_config=credential.encrypted_config if credential else None,
        )

    @classmethod
    def from_cache_row(cls, row: dict[str, Any]) -> _ProviderModelCacheEntry:
        return cls(
            id=row["id"],
            provider_name=row["provider_name"],
            model_name=row["model_name"],
            model_type=ModelType(row["model_type"]),
            credential_id=row.get("credential_id"),
            credential_name=row.get("credential_name"),
            encrypted_config=row.get("encrypted_config"),
        )
```

**解读**：
- 第 1 行：`@dataclass(frozen=True, slots=True)`——不可变 + 内存优化，**这是 dify 缓存层的最佳实践**
- 第 2-5 行：泛型 `T: _CacheEntry` 让同一个 spec 类支持多种缓存条目类型
- 第 7-16 行：数据类字段全部是基本类型 + `str | None`，可以安全地 `frozen`
- 第 18-28 行：`from_record` 是 `@classmethod` 工厂方法，把 SQLAlchemy ORM 对象转成缓存对象
- **为什么用 `frozen + slots`**：这些缓存条目会被频繁创建（每个 model lookup 一次），不可变保证线程安全，`slots` 节省内存

### 3.2 Session cleanup payload 与 result

**文件位置**：`/Users/xu/code/github/dify/api/clients/agent_backend/session_cleanup.py`
**核心代码**（行 36-54）：

```python
@dataclass(frozen=True, slots=True)
class AgentBackendSessionCleanupResult:
    """Terminal outcome of one backend cleanup attempt."""

    status: Literal["succeeded", "skipped", "failed"]
    reason: str | None = None
    cleanup_run_id: str | None = None

    @classmethod
    def succeeded(cls, cleanup_run_id: str) -> AgentBackendSessionCleanupResult:
        return cls(status="succeeded", cleanup_run_id=cleanup_run_id)

    @classmethod
    def skipped(cls, reason: str) -> AgentBackendSessionCleanupResult:
        return cls(status="skipped", reason=reason)

    @classmethod
    def failed(cls, reason: str, cleanup_run_id: str | None = None) -> AgentBackendSessionCleanupResult:
        return cls(status="failed", reason=reason, cleanup_run_id=cleanup_run_id)
```

**解读**：
- 第 1 行：`frozen=True, slots=True`——表示这个结果是「终态的、不可变的」
- 第 3-6 行：所有字段都是字面量（`Literal["succeeded", "skipped", "failed"]`），类型安全
- 第 8-17 行：三个 `@classmethod` 工厂方法让调用方写出 `Result.succeeded(...)` 这种语义清晰的代码
- **工程价值**：把状态机封装在 dataclass 里，避免到处写 `dict`、`NamedTuple` 或松散的字段

## 4. 关键要点总结

- `@dataclass` 自动生成 `__init__` / `__repr__` / `__eq__`，省去样板代码
- `frozen=True`：不可变、可哈希、线程安全
- `slots=True`：节省内存、禁止加新属性
- `field(default_factory=...)`：可变默认值的**唯一正确**写法
- **dify 的最佳实践**：缓存条目、结果对象都用 `@dataclass(frozen=True, slots=True)`，配合 `@classmethod` 工厂方法

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `Money` 数据类，包含 `amount: float`、`currency: str = "CNY"`，然后实现 `Money(10) + Money(20)` 返回 `Money(30, "CNY")`（用 `__add__` 方法）。

```python
from dataclasses import dataclass, field
from typing import Self

@dataclass(frozen=True, slots=True)
class Money:
    amount: float
    currency: str = "CNY"

    def __add__(self, other: Self) -> Self:
        # TODO: 检查 currency 一致，返回新 Money
        ...

print(Money(10) + Money(20))  # Money(amount=30.0, currency='CNY')
```

### 练习 2：进阶

阅读 `api/core/app/workflow/layers/persistence.py` 第 58-78 行的 `PersistenceWorkflowInfo` 和 `_NodeRuntimeSnapshot`，理解 `slots=True` 在 dify 工作流持久化层的应用。

### 练习 3：挑战（选做）

实现一个 `Event` 数据类层次结构：`BaseEvent` → `WorkflowStarted`、`WorkflowCompleted`、`WorkflowFailed`，用 `@dataclass` + `field(discriminator=...)` 实现 discriminated union（提示：可结合 `typing` 模块）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/provider_manager.py`（第 95-141 行）
- `/Users/xu/code/github/dify/api/clients/agent_backend/session_cleanup.py`
- Python 官方文档 dataclasses：https://docs.python.org/3/library/dataclasses.html
- PEP 557：https://peps.python.org/pep-0557/

---

**文档版本**：v1.0
**最后更新**：2026-07-13