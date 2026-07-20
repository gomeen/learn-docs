# 1.1.17 元类（Metaclass）与类创建过程

> 理解 Python 中「类也是对象」的元编程思想，能识别 dify 第三方库中的元类用法（如 SQLAlchemy Declarative Base）。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释「类也是对象」以及元类在类创建中的作用
- 编写一个自定义元类并理解 `__new__` 与 `__init__` 的调用时机
- 区分 type、`__init_subclass__`、元类三种拦截类创建的方式
- 能看懂 dify 依赖的 SQLAlchemy、Pydantic 等库中的元类机制

## 📚 前置知识

- Python 基础：`class` / `type()` / `isinstance`
- [装饰器](./11-decorator.md)（装饰器原理）
- [魔术方法](./19-dunder-methods.md)

## 1. 核心概念

### 1.1 类也是对象

在 Python 中，`class Foo: ...` 并不仅仅是「定义了一个类」，它实际上是**创建了一个名为 `Foo` 的对象**。而这个对象的类型（type）是 `type`，或某个 `type` 的子类。

```python
class Foo:
    pass

print(type(Foo))   # <class 'type'>
print(isinstance(Foo, type))  # True
```

我们平时说 `Foo` 是一个类，更准确地说 `Foo` 是一个 `type` 的实例——它的「类型」就是 `type`。

### 1.2 元类的定义

**元类（Metaclass）是「类的类」**，即用来创建类的类。默认情况下，Python 使用 `type` 作为元类：

- `type(obj)` → 返回 `obj` 的类型
- `type(name, bases, dict)` → 用三参数形式**动态创建一个新类**

```python
# 用 type 动态创建一个类（等价于 class Foo: x = 1）
Foo = type('Foo', (), {'x': 1})
print(Foo().x)  # 1
```

### 1.3 自定义元类

自定义元类需要继承 `type`，并实现 `__new__` 或 `__init__`：

```python
class MyMeta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        # 在类对象被创建之前/之时进行修改
        namespace['created_by'] = 'MyMeta'
        return super().__new__(mcs, name, bases, namespace)

# 使用：metaclass=MyMeta
class Foo(metaclass=MyMeta):
    pass

print(Foo.created_by)  # 'MyMeta'
```

`__new__` 接收的四个参数：
- `mcs`：元类本身（对应 `MyMeta`）
- `name`：类名（字符串 `'Foo'`）
- `bases`：父类的元组
- `namespace`：类的属性字典（包含方法、属性、`__init__` 等）

### 1.4 三种拦截类创建的方式

| 方式 | 触发时机 | 用途 |
| --- | --- | --- |
| `__init_subclass__` | 子类创建时（仅对直接子类生效） | 给子类自动注册 |
| `classmethod` + `__set_name__` | 描述符绑定到类时 | 描述符元数据 |
| **元类（metaclass）** | 类对象创建时 | 全局拦截、修改类结构 |

> 99% 的场景用 `__init_subclass__` 就够了，只有需要**修改类结构本身**（如 SQLAlchemy ORM、Pydantic 数据模型）时才需要元类。

## 2. 代码示例

### 2.1 自动注册所有子类

```python
class PluginRegistry:
    """记录所有继承 Plugin 的子类。"""
    _registry: dict[str, type] = {}

    class Plugin:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            PluginRegistry._registry[cls.__name__] = cls

    class TextPlugin(Plugin):
        def run(self): return "text"

    class ImagePlugin(Plugin):
        def run(self): return "image"

print(PluginRegistry._registry)
# {'TextPlugin': <class '__main__.TextPlugin'>, 'ImagePlugin': <class '__main__.ImagePlugin'>}
```

### 2.2 元类示例：把所有方法名转为大写

```python
class UpperAttrMeta(type):
    """把类中所有非魔术方法的属性名都改成大写。"""
    def __new__(mcs, name, bases, namespace):
        upper = {}
        for key, val in namespace.items():
            if not key.startswith('__'):
                upper[key.upper()] = val
            else:
                upper[key] = val
        return super().__new__(mcs, name, bases, upper)

class MyClass(metaclass=UpperAttrMeta):
    foo = 1
    bar = 2

    def hello(self): return "hi"

print(dir(MyClass))
# [..., 'BAR', 'FOO', 'HELLO', ...]
print(MyClass().HELLO())  # 'hi'
```

### 2.3 常见错误：忘记调用 `super().__new__`

```python
# ❌ 错误：忘记返回类对象，会导致类创建失败
class BrokenMeta(type):
    def __new__(mcs, name, bases, namespace):
        # 修改了 namespace 但忘了调用 super
        return None  # 永远不会创建出这个类

class Foo(metaclass=BrokenMeta):
    pass  # TypeError: type.__new__() returned None
```

```python
# ✅ 正确：必须返回 super().__new__ 的结果
class GoodMeta(type):
    def __new__(mcs, name, bases, namespace):
        namespace['meta_marker'] = True
        return super().__new__(mcs, name, bases, namespace)
```

## 3. 关键要点总结

- **类也是对象**，它的类型是 `type` 或 `type` 的子类（元类）
- 元类通过 `metaclass=MyMeta` 声明，Python 在 `class` 语句执行时调用元类的 `__new__` / `__init__`
- 99% 的需求用 `__init_subclass__` 就够了，只有 SQLAlchemy / Pydantic 这种框架才需要真元类
- dify 大量依赖 SQLAlchemy 和 Pydantic 的元类来生成 ORM 模型和数据校验类
- **别轻易自定义元类**：会增加调试难度，让代码「魔法化」

---

**文档版本**：v1.0
**最后更新**：2026-07-13
