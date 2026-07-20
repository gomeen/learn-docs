# 1.1.10 装饰器（Decorator）的原理与实践

> 理解 Python 装饰器的本质：函数作为参数和返回值，能写出可复用的横切逻辑。

## 🎯 学习目标

完成本文档后，你将能够：

- 理解装饰器的本质（闭包 + 高阶函数）
- 编写带参数的装饰器
- 使用 `functools.wraps` 保留元信息
- 看懂 dify 中所有 `@login_required` / `@retry` 等装饰器

## 📚 前置知识

- Python 基础：函数、闭包
- 01-fundamentals/01-python-typing-basics.md

## 1. 核心概念

### 1.1 装饰器是什么？

装饰器是**接受函数、返回函数**的可调用对象，用于在不修改原函数代码的情况下增加功能。

```python
# 最简单的装饰器
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result
    return wrapper

@my_decorator
def greet(name):
    return f"Hello, {name}"

greet("Alice")
# Before call
# Hello, Alice
# After call
```

**等价于**：`greet = my_decorator(greet)`，`greet` 现在指向 `wrapper`。

### 1.2 保留原函数元信息：`functools.wraps`

装饰器会"覆盖"原函数的 `__name__`、`__doc__`：

```python
# ❌ 不保留元信息
def bad_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@bad_decorator
def hello():
    """Say hello."""
    pass

print(hello.__name__)  # "wrapper"（丢失了 hello）
print(hello.__doc__)   # None

# ✅ 使用 functools.wraps
from functools import wraps

def good_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@good_decorator
def hello():
    """Say hello."""
    pass

print(hello.__name__)  # "hello"（保留）
print(hello.__doc__)   # "Say hello."
```

### 1.3 带参数的装饰器

三層嵌套：外层接收参数、中层接收函数、内层是 wrapper：

```python
from functools import wraps

def repeat(times):
    """重复执行函数 times 次。"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            results = []
            for _ in range(times):
                results.append(func(*args, **kwargs))
            return results
        return wrapper
    return decorator

@repeat(3)
def greet(name):
    return f"Hello, {name}"

print(greet("Alice"))
# ['Hello, Alice', 'Hello, Alice', 'Hello, Alice']
```

### 1.4 类装饰器

装饰器也可以是类，只要实现 `__call__`（魔术方法见 [16-dunder-methods](./19-dunder-methods.md)）：

```python
from functools import wraps

class CountCalls:
    def __init__(self, func):
        wraps(func)(self)  # 手动保留元信息
        self.func = func
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"Call {self.count} of {self.func.__name__}")
        return self.func(*args, **kwargs)

@CountCalls
def hello():
    print("hello")

hello()  # Call 1 of hello
hello()  # Call 2 of hello
```

## 2. 代码示例

### 2.1 计时装饰器

```python
import time
from functools import wraps

def timer(func):
    """记录函数执行耗时。"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} 耗时 {elapsed:.4f}s")
        return result
    return wrapper

@timer
def slow_func():
    time.sleep(0.5)
    return "done"

slow_func()
# slow_func 耗时 0.5001s
```

### 2.2 重试装饰器（带参数）

```python
import time
from functools import wraps

def retry(max_attempts=3, delay=1.0):
    """失败时自动重试。"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        print(f"Attempt {attempt} failed: {e}, retry in {delay}s")
                        time.sleep(delay)
            raise last_error  # type: ignore[misc]
        return wrapper
    return decorator

@retry(max_attempts=3, delay=0.5)
def flaky_api_call():
    import random
    if random.random() < 0.7:
        raise ConnectionError("network error")
    return "success"
```

### 2.3 常见错误：忘记 `functools.wraps`

```python
# ❌ 错误：丢失原函数信息
def my_logger(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@my_logger
def calculate(x, y):
    """加法函数"""
    return x + y

print(calculate.__name__)  # "wrapper"（应该是 "calculate"）
print(calculate.__doc__)   # None

# ✅ 正确：使用 @wraps(func)
from functools import wraps

def my_logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

## 3. 关键要点总结

- 装饰器本质是**接受函数、返回函数**的可调用对象
- 必须用 `@functools.wraps(func)` 保留原函数元信息
- 带参数装饰器是**三层嵌套**：参数 → 装饰器 → wrapper
- 类装饰器通过实现 `__call__` 工作
- dify 中常见装饰器：`@login_required`、`@retry`、Celery `@task`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
