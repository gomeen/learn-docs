# 1.1.19 抽象基类（abc 模块）

> 理解 Python 抽象基类（ABC）的用法，能看懂 dify 中所有继承 `ABC` 的接口设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 `ABC` 与 `ABCMeta` 的关系
- 用 `@abstractmethod` 定义抽象方法，强制子类实现
- 理解 `register` 虚子类的用法（适配类型检查）
- 在 dify 中识别所有 ABC 接口（如 `Tool`、`DatasourcePlugin`、`BaseVector`）

## 📚 前置知识

- Python 基础：类的继承、方法重写
- [类与对象基础](./03-python-classes-basics.md)
- [元类](./23-metaclass.md)（推荐了解）

## 1. 核心概念

### 1.1 为什么需要抽象基类

普通继承约定「子类必须实现父类的方法」是**文档层面的**——Python 不会强制检查。抽象基类（Abstract Base Class，ABC）通过 `@abstractmethod` 装饰器**强制**子类实现这些方法，否则实例化时直接报错。

**举例**：你想定义 `Tool` 接口规范，让所有工具（Google 搜索、天气查询、HTTP 请求）都必须实现 `invoke` 方法。

```python
# 没有 ABC：约定俗成，不强制
class Tool:
    def invoke(self):
        raise NotImplementedError
```

```python
# 有 ABC：强制子类必须实现
from abc import ABC, abstractmethod

class Tool(ABC):
    @abstractmethod
    def invoke(self):
        ...

class GoogleSearchTool(Tool):
    pass  # 没有实现 invoke

GoogleSearchTool()  # TypeError: Can't instantiate abstract class GoogleSearchTool
```

### 1.2 `ABC` 的本质

`ABC` 是一个**辅助类**，它的元类是 `ABCMeta`（元类原理见 [21-metaclass](./23-metaclass.md)）：

```python
from abc import ABC, ABCMeta

# 这两种写法等价
class Foo(ABC): pass
class Foo(metaclass=ABCMeta): pass
```

`ABCMeta` 的作用：在类创建时扫描所有 `@abstractmethod` 标记的方法。如果一个类含有未实现的抽象方法，调用 `cls(...)` 实例化时会抛出 `TypeError`。

### 1.3 `@abstractmethod` 的特性

被 `@abstractmethod` 装饰的方法可以**有实现**（提供默认行为），子类可以选择性重写。但只要有一个抽象方法没实现，类就不能实例化。

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self):
        return "..."  # 默认实现，子类可覆盖

    @abstractmethod
    def move(self):
        ...

class Dog(Animal):
    # 实现了 move，但 speak 用了父类的默认实现
    def move(self):
        return "running"

Dog()  # 可以实例化（所有抽象方法都被实现了）
```

### 1.4 抽象属性

```python
from abc import ABC, abstractmethod

class Config(ABC):
    @property
    @abstractmethod
    def api_key(self) -> str:
        ...

class MyConfig(Config):
    @property
    def api_key(self) -> str:
        return "sk-xxx"

MyConfig()  # OK
```

> `@abstractmethod` 必须放在 `@property` **下面**才能正确地标记为抽象属性（`@property` 见 [10-decorator](./11-decorator.md) / [22-descriptor](./24-descriptor.md)）。

### 1.5 虚子类（Virtual Subclass）

有时两个类没有继承关系，但在语义上是「同类」，可以用 `register` 让它们互相兼容 `isinstance` 检查：

```python
from abc import ABC

class Drawable(ABC):
    pass

class MyClass:
    pass

Drawable.register(MyClass)
print(isinstance(MyClass(), Drawable))  # True（但没有真正的继承关系）
```

> dify 中较少使用 `register`，但 Pydantic / SQLAlchemy 内部用得很多。

## 2. 代码示例

### 2.1 基础 ABC 接口

```python
from abc import ABC, abstractmethod

class Storage(ABC):
    """统一的存储接口，dify 的 FileService 也有类似设计。"""
    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

class S3Storage(Storage):
    def save(self, key, data):
        print(f"upload to S3: {key}")

    def load(self, key):
        return b"data"

    def delete(self, key):
        print(f"delete from S3: {key}")

s = S3Storage()
s.save("test.txt", b"hello")
```

### 2.2 抽象方法 + 默认实现

```python
from abc import ABC, abstractmethod

class BaseRetriever(ABC):
    def retrieve(self, query: str) -> list[str]:
        """模板方法：固定流程，子类只关心 query → docs 的核心逻辑。"""
        docs = self._fetch(query)             # 抽象
        return self._post_process(docs)        # 默认实现

    @abstractmethod
    def _fetch(self, query: str) -> list[str]:
        ...

    def _post_process(self, docs):
        return [d.strip() for d in docs]       # 默认实现

class KeywordRetriever(BaseRetriever):
    def _fetch(self, query):
        return ["doc about " + query]
```

### 2.3 常见错误：抽象方法顺序写错

```python
from abc import ABC, abstractmethod

# ❌ 错误：abstractmethod 在 property 上方
class Foo(ABC):
    @abstractmethod
    @property
    def x(self): ...     # 实际只标记 x 为 property，不是抽象属性
```

```python
# ✅ 正确：property 在外层，abstractmethod 在内层
class Foo(ABC):
    @property
    @abstractmethod
    def x(self): ...
```

## 3. 关键要点总结

- `ABC` 是 `ABCMeta` 元类的辅助类，用于声明抽象基类
- `@abstractmethod` 装饰的方法**必须**被子类实现，否则 `cls()` 实例化报错
- 抽象方法可以提供默认实现，子类选择性重写
- `@property` + `@abstractmethod` 组合声明抽象属性（property 在外层）
- `register()` 用于虚子类（`isinstance` 通过，但无实际继承关系）
- **dify 大量使用 ABC**：Tool、DatasourcePlugin、BaseVector、IndexProcessorBase 等

---

**文档版本**：v1.0
**最后更新**：2026-07-13
