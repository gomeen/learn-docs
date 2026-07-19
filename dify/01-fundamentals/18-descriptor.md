# 1.1.18 描述符（Descriptor）协议

> 理解 Python 描述符的工作机制，能识别 `@property`、方法绑定、`__set_name__` 等高级特性的实现原理。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释描述符协议 `__get__` / `__set__` / `__delete__` 的作用
- 区分数据描述符与非数据描述符的优先级
- 理解 `@property`、方法绑定、`cached_property` 的底层原理
- 能看懂 dify 的 Pydantic / SQLAlchemy 中描述符的应用

## 📚 前置知识

- Python 基础：`@property` 装饰器
- 01-fundamentals/10-decorator.md（装饰器原理）
- 01-fundamentals/16-dunder-methods.md（魔术方法）

## 1. 核心概念

### 1.1 什么是描述符

**描述符（Descriptor）是实现了 `__get__` / `__set__` / `__delete__` 中任意一个方法的对象**。当一个描述符被定义为另一个类（owner）的**类属性**时，访问 owner 的实例属性时会自动触发描述符协议。

```python
class Validator:
    """一个简单的非数据描述符（只实现 __get__）。"""
    def __get__(self, instance, owner):
        if instance is None:
            return self  # 通过类访问时返回描述符自身
        return instance.__dict__.get('_value', None)

class Foo:
    attr = Validator()

foo = Foo()
foo.attr = 42
print(foo.attr)  # 42（不走 __get__，因为实例字典已有值）
```

### 1.2 三种描述符类型

| 类型 | 实现方法 | 优先级 |
| --- | --- | --- |
| **数据描述符** | 同时实现 `__get__` 和 `__set__`（或 `__delete__`） | 最高（覆盖实例字典） |
| **非数据描述符** | 只实现 `__get__` | 最低（实例字典优先） |
| **方法** | 函数对象本身是描述符 | —— |

> **关键规则**：访问实例属性时，数据描述符 > 实例字典 > 非数据描述符。

### 1.3 `__get__` 三个参数的含义

```python
class MyDescriptor:
    def __get__(self, instance, owner):
        # self:     描述符实例本身
        # instance: 访问它的实例（通过类访问时为 None）
        # owner:    描述符所在类
        ...
```

```python
class D:
    def __get__(self, instance, owner):
        print(f"instance={instance}, owner={owner}")

class A:
    d = D()

A.d           # instance=None, owner=<class 'A'>
A().d         # instance=<A object>, owner=<class 'A'>
```

### 1.4 方法就是描述符

```python
class Foo:
    def hello(self):
        return "hi"

foo = Foo()
print(foo.hello)   # <bound method Foo.hello of ...>
print(Foo.hello)   # <function Foo.hello at ...>
```

`foo.hello` 是绑定方法（bound method），它是怎么实现的？因为函数（function）是一个**非数据描述符**，`__get__` 在传入实例时返回 `functools.partial(func, instance)`。

### 1.5 `@property` 的本质

`@property` 装饰器返回一个实现了 `__get__` / `__set__` 的描述符对象：

```python
class Circle:
    def __init__(self, r):
        self._r = r

    @property
    def radius(self):
        return self._r

    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("radius must be non-negative")
        self._r = value
```

等价于：
```python
class Circle:
    def __init__(self, r):
        self._r = r

    def _get_radius(self):
        return self._r

    def _set_radius(self, value):
        if value < 0:
            raise ValueError("radius must be non-negative")
        self._r = value

    radius = property(_get_radius, _set_radius)  # property 本身是描述符
```

### 1.6 `__set_name__`（Python 3.6+）

描述符可以感知自己被绑定到哪个类以及什么名字：

```python
class Field:
    def __init__(self, type_):
        self.type = type_

    def __set_name__(self, owner, name):
        self.name = name  # 自动捕获属性名

class User:
    name = Field(str)
    age = Field(int)

print(User.name.name)  # 'name'
print(User.age.name)   # 'age'
```

`__set_name__` 在类创建时被元类自动调用，省去了显式传入字段名的麻烦。

## 2. 代码示例

### 2.1 自定义类型校验描述符

```python
class TypedField:
    """数据描述符：自动校验赋值类型。"""
    def __init__(self, type_, name=None):
        self.type = type_
        self.name = name

    def __set_name__(self, owner, name):
        # 元类创建类时自动调用
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance, value):
        if not isinstance(value, self.type):
            raise TypeError(f"{self.name} must be {self.type.__name__}")
        instance.__dict__[self.name] = value

class User:
    name: TypedField = TypedField(str)
    age: TypedField = TypedField(int)

u = User()
u.name = "Alice"   # OK
u.age = "30"       # TypeError: age must be int
```

### 2.2 常见错误：把描述符当实例属性存

```python
# ❌ 错误：把描述符存到实例字典，会让它失去描述符行为
class Foo:
    attr = Validator()

foo = Foo()
foo.attr = 42        # 触发 __set__（如果实现了），正常
foo.__dict__['attr'] = 42  # ❌ 绕过描述符
```

```python
# ✅ 正确：在 __set__ 中始终写到 instance.__dict__
def __set__(self, instance, value):
    instance.__dict__[self.name] = value  # OK
```

### 2.3 复用 `functools.cached_property`

```python
from functools import cached_property

class DataLoader:
    def __init__(self, path):
        self.path = path

    @cached_property
    def content(self):
        # 只在第一次访问时计算，后续访问直接返回缓存
        print("loading...")
        with open(self.path) as f:
            return f.read()

d = DataLoader("big.txt")
print(d.content)  # loading... <contents>
print(d.content)  # <contents>（不再 loading）
```

`cached_property` 是一个**数据描述符**，缓存存在实例字典里，所以会拦截后续的赋值。

## 3. dify 仓库源码解读

### 3.1 `cached_property` 的工程考量

**文件位置**：`/Users/xu/code/github/dify/api/models/workflow.py`
**核心代码**（行 300-314）：

```python
    @property
    def graph_dict(self) -> Mapping[str, Any]:
        # TODO(QuantumGhost): Consider caching `graph_dict` to avoid repeated JSON decoding.
        #
        # Using `functools.cached_property` could help, but some code in the codebase may
        # modify the returned dict, which can cause issues elsewhere.
        #
        # For example, changing this property to a cached property led to errors like the
        # following when single stepping an `Iteration` node:
        #
        #     Root node id 1748401971780start not found in the graph
        #
```

**解读**：
- 第 1 行：定义 `graph_dict` 属性，每次访问都执行一次 JSON 反序列化
- 第 3-12 行：开发者想用 `functools.cached_property` 缓存结果，但**遇到了 bug**——某些调用方修改了返回的 dict，导致后续节点查找失败
- **描述符机制的隐患**：`cached_property` 把结果存在 `instance.__dict__` 中，导致任何「修改返回 dict」的代码都会污染缓存
- **教训**：缓存是有副作用的，写描述符时要考虑下游调用方是否安全

### 3.2 Pydantic Field 的描述符应用

**文件位置**：`/Users/xu/code/github/dify/api/clients/agent_backend/session_cleanup.py`
**核心代码**（行 17-33）：

```python
from pydantic import BaseModel, ConfigDict, Field, JsonValue


class AgentBackendSessionCleanupPayload(BaseModel):
    """Serialized cleanup inputs preserved across API and Celery boundaries."""

    session_snapshot: CompositorSessionSnapshot | None = None
    runtime_layer_specs: list[RuntimeLayerSpec] = Field(default_factory=list)
    idempotency_key: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    timeout_seconds: float = 30.0

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
```

**解读**：
- 第 6-10 行：每个 `Field(...)` 实际上返回的是一个 Pydantic `FieldInfo` 对象，它**不是普通描述符**，但 Pydantic 用 `ModelMetaclass` 在类创建时把这些 `FieldInfo` 收集起来，生成对应的描述符逻辑
- 第 6 行：`session_snapshot: ... = None` 这类带默认值的字段，Pydantic 通过 `__set_name__` 捕获名字 `session_snapshot`，再实现 `__get__` / `__set__` 来做类型校验
- **为什么 dify 大量用 Pydantic**：因为 Pydantic 的描述符 + 元类组合，让开发者只要写类型注解就自动得到类型校验、JSON 序列化、文档生成等能力

## 4. 关键要点总结

- **描述符**：实现了 `__get__` / `__set__` / `__delete__` 的对象，控制其他类的属性访问
- **数据描述符 vs 非数据描述符**：前者优先级高于实例字典，后者反之
- 函数、property、classmethod、staticmethod、`cached_property` 都是描述符
- `__set_name__`（3.6+）让描述符自动知道自己的属性名
- **dify 工程经验**：缓存属性（`cached_property`）有副作用，下游若修改返回值会导致 bug

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `LazyField` 描述符：第一次访问时计算值（接受一个 `compute` 工厂函数），之后直接返回缓存。提示：使用 `__set_name__` 和实例字典。

```python
class LazyField:
    def __init__(self, compute):
        self.compute = compute

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        # TODO: 计算并缓存到 instance.__dict__
        ...

class Data:
    big = LazyField(lambda self: sum(range(1_000_000)))

d = Data()
print(d.big)  # 计算
print(d.big)  # 用缓存
```

### 练习 2：进阶

阅读 Python 源码 `Lib/functools.py` 中 `cached_property` 的实现（约 1100 行），理解它是如何用 `__set_name__` + `__get__` + `__set__` 实现缓存的，并解释它为什么是**数据描述符**。

### 练习 3：挑战（选做）

实现一个 `ValidatedTypedDict` 描述符：当赋值时检查类型并自动序列化（`datetime` 转 ISO 字符串）。结合 dify 的 `session_cleanup.py` 风格，思考这个能力其实等同于手写 Pydantic 模型。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/workflow.py`（第 300-314 行）
- `/Users/xu/code/github/dify/api/clients/agent_backend/session_cleanup.py`
- Python 官方文档 Descriptor Protocol：https://docs.python.org/3/howto/descriptor.html
- Python `functools.cached_property` 源码：https://github.com/python/cpython/blob/main/Lib/functools.py
- Real Python 描述符教程：https://realpython.com/python-descriptors/

---

**文档版本**：v1.0
**最后更新**：2026-07-13