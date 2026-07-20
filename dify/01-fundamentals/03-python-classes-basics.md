# 0.3 Python 类与对象基础

> 理解面向对象在 Python 中的实现，能看懂 dify 中的 Service 类、Model 类、Controller 类的基本结构。

## 🎯 学习目标

完成本文档后，你将能够：

- 定义类、创建实例、理解 `self` 的含义
- 掌握实例方法、类方法、静态方法的区别
- 理解继承与 `super()` 的用法
- 能在 dify 代码中识别类的职责

## 📚 前置知识

- [00-python-variables-and-types.md](./01-python-variables-and-types.md)
- [00-python-functions.md](./02-python-functions.md)

## 1. 核心概念

### 1.1 类与实例

```python
class User:
    """用户类。"""

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def greet(self) -> str:
        return f"Hello, I'm {self.name}"

# 创建实例
user = User("Alice", "alice@example.com")
print(user.greet())  # "Hello, I'm Alice"
```

要点：

- `__init__` 是**构造方法**，创建实例时自动调用
- `self` 指代**当前实例**，必须作为第一个参数
- 属性通过 `self.xxx` 访问

### 1.2 三种方法类型

`@classmethod` / `@staticmethod` 是装饰器写法（详见 [装饰器](./11-decorator.md)），此处只把它们当作「挂在类上的方法标记」来理解。

```python
class Counter:
    total = 0  # 类变量（所有实例共享）

    def __init__(self):
        self.count = 0  # 实例变量

    # 1. 实例方法：操作实例，第一个参数必须是 self
    def increment(self):
        self.count += 1

    # 2. 类方法：操作类，第一个参数是 cls（类本身）
    @classmethod
    def get_total(cls):
        return cls.total

    # 3. 静态方法：不依赖实例也不依赖类，普通函数挂到类上
    @staticmethod
    def is_valid_count(n):
        return 0 <= n < 1000
```

| 类型     | 第一个参数 | 访问               | 何时用                         |
| -------- | ---------- | ------------------ | ------------------------------ |
| 实例方法 | `self`     | 实例 + 类          | 需要操作实例状态               |
| 类方法   | `cls`      | 类（不能访问实例） | 工厂方法、备选构造             |
| 静态方法 | 无         | 无                 | 与类相关但不依赖状态的工具函数 |

### 1.3 继承与 `super()`

```python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        raise NotImplementedError("子类必须实现")

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)  # 调用父类 __init__
        self.breed = breed

    def speak(self):
        return f"{self.name} 说：汪汪"

dog = Dog("旺财", "柴犬")
print(dog.speak())  # "旺财 说：汪汪"
```

### 1.4 私有属性（约定）

Python 没有真正的 private，但有**命名约定**：

```python
class Account:
    def __init__(self):
        self.name = "public"      # 公有
        self._internal = "weak"   # 单下划线：内部用，外部不应访问
        self.__secret = "strong"  # 双下划线：名称会被改写（name mangling）

a = Account()
print(a.name)            # ✅
print(a._internal)       # ⚠️ 可以但不推荐
print(a._Account__secret) # ✅ 通过改写后的名字访问（不推荐这样做）
```

## 2. 代码示例

### 2.1 完整的类定义示例

```python
from typing import ClassVar


class ApiKey:
    """API Key 模型示例（简化版）。"""

    # 类变量
    PREFIX: ClassVar[str] = "dify_"

    def __init__(
        self,
        tenant_id: str,
        key: str,
        created_by: str,
    ) -> None:
        # 实例变量（dify 风格：在 __init__ 之前显式声明）
        self.tenant_id: str = tenant_id
        self.key: str = key
        self.created_by: str = created_by
        self.is_active: bool = True

    def revoke(self) -> None:
        """撤销 API Key。"""
        self.is_active = False

    @classmethod
    def generate(cls, tenant_id: str, created_by: str) -> "ApiKey":
        """工厂方法：生成新的 API Key。"""
        import secrets
        raw_key = secrets.token_urlsafe(32)
        return cls(
            tenant_id=tenant_id,
            key=cls.PREFIX + raw_key,
            created_by=created_by,
        )

    def __repr__(self) -> str:
        return f"<ApiKey tenant={self.tenant_id} active={self.is_active}>"
```

**说明**：

- 第 13-17 行：dify 风格——实例变量在 `__init__` 前显式声明类型
- 第 24 行：`@classmethod` 作为工厂方法，cls 自动指向 `ApiKey` 类
- 第 32 行：`__repr__` 让调试时输出更有意义（`<ApiKey tenant=...>`）

### 2.2 属性装饰器 `@property`

`@property` 同样是装饰器写法（原理见上文链接的装饰器篇）；底层描述符机制见 [22-descriptor](./24-descriptor.md)。此处只掌握「方法当属性用」。

```python
class Temperature:
    def __init__(self, celsius: float):
        self._celsius = celsius

    @property
    def fahrenheit(self) -> float:
        """华氏度（只读属性）。"""
        return self._celsius * 9 / 5 + 32

    @property
    def kelvin(self) -> float:
        """开尔文温度（只读属性）。"""
        return self._celsius + 273.15

t = Temperature(25)
print(t.fahrenheit)  # 77.0（像访问属性一样）
print(t.kelvin)      # 298.15
```

`@property` 把方法**伪装成属性**：调用时不需要加括号，但内部执行计算逻辑。

## 3. 关键要点总结

- `__init__` 是构造方法，`self` 指代当前实例
- 三种方法：实例方法（self）、类方法（cls）、静态方法（无）
- 继承用 `super().__init__()` 调用父类构造
- `_` 单下划线是约定私有，`__` 双下划线触发名称改写
- dify 的 Model 继承 `TypeBase`（SQLAlchemy 基类）
- dify 的 Service 通常是**静态方法集合**，不依赖实例状态

---

**文档版本**：v1.0
**最后更新**：2026-07-13
