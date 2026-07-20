# 1.1.11 上下文管理器（Context Manager）与 `with` 语句

> 掌握 `with` 语句的本质：确保资源（文件、锁、连接）一定会被正确释放。

## 🎯 学习目标

完成本文档后，你将能够：

- 理解 `with` 语句解决的"资源泄漏"问题
- 实现自定义上下文管理器（类形式与生成器形式）
- 使用 `contextlib` 简化实现
- 看懂 dify 中所有 `with` 块的实际作用

## 📚 前置知识

- Python 基础：类、`__enter__`/`__exit__` 魔术方法
- 01-fundamentals/01-dunder-methods.md（推荐）

## 1. 核心概念

### 1.1 为什么需要 `with`？

文件、数据库连接、锁等资源必须被**显式释放**。如果中间抛异常，传统写法会泄漏：

```python
# ❌ 危险写法
f = open("/tmp/data.txt")
data = f.read()  # 如果这里抛异常，f 永远不会被关闭
f.close()
```

`with` 语句保证**无论是否抛异常，资源一定会被释放**：

```python
# ✅ 安全写法
with open("/tmp/data.txt") as f:
    data = f.read()  # 即使抛异常，f 也会被关闭
```

### 1.2 协议：`__enter__` / `__exit__`

任何实现了这两个魔术方法的对象都是上下文管理器：

```python
class MyContext:
    def __enter__(self):
        """进入 with 块时调用，返回值赋给 as 后的变量。"""
        print("enter")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """离开 with 块时调用（无论是否异常）。"""
        print("exit")
        return False  # 返回 True 表示吞掉异常

with MyContext() as ctx:
    print("inside")
# enter
# inside
# exit
```

### 1.3 `@contextmanager`：用生成器写上下文管理器

更简洁的写法——用 `contextlib.contextmanager` 把生成器函数"装饰"成上下文管理器（`@contextmanager` 本身是装饰器，详见 [10-decorator](./11-decorator.md)；`yield` / 生成器见 [14-generator](./16-generator.md)）：

```python
from contextlib import contextmanager

@contextmanager
def timer(name):
    start = time.perf_counter()
    print(f"{name} 开始")
    yield  # 这里是 with 块的主体执行点
    elapsed = time.perf_counter() - start
    print(f"{name} 耗时 {elapsed:.4f}s")

with timer("操作"):
    do_something()
```

`yield` **之前**的代码相当于 `__enter__`，**之后**的代码相当于 `__exit__`。

### 1.4 `ExitStack`：组合多个上下文管理器

需要同时管理多个资源时使用：

```python
from contextlib import ExitStack

with ExitStack() as stack:
    f1 = stack.enter_context(open("/tmp/a.txt"))
    f2 = stack.enter_context(open("/tmp/b.txt"))
    # 任何上下文管理器抛异常都会被一起清理
```

## 2. 代码示例

### 2.1 类形式：数据库连接管理

```python
class DatabaseConnection:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None

    def __enter__(self) -> "DatabaseConnection":
        print(f"连接 {self.db_url}")
        self.conn = self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.conn:
            print("关闭连接")
            self.conn.close()
        # 返回 False 让异常继续传播
        return False

    def _connect(self):
        return {"url": self.db_url}

# 使用
with DatabaseConnection("postgresql://...") as db:
    print(db.conn)
# 连接 postgresql://...
# {'url': 'postgresql://...'}
# 关闭连接
```

### 2.2 生成器形式：临时修改全局状态

```python
import os
from contextlib import contextmanager

@contextmanager
def set_env(key: str, value: str):
    """临时设置环境变量，退出时恢复。"""
    old_value = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value

# 使用
with set_env("API_MODE", "test"):
    print(os.environ["API_MODE"])  # "test"
# 退出后 API_MODE 恢复原状
```

### 2.3 常见错误：忘记 `try/finally`

```python
# ❌ 错误：在生成器形式中没有 try/finally
from contextlib import contextmanager

@contextmanager
def bad_timer():
    start = time.perf_counter()
    yield
    print(f"耗时 {time.perf_counter() - start}")  # 如果 yield 抛异常，不会执行

# ✅ 正确：用 try/finally 保证清理
@contextmanager
def good_timer():
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"耗时 {time.perf_counter() - start}")
```

## 3. 关键要点总结

- `with` 语句保证**资源一定会被释放**，无论是否抛异常
- 类形式：实现 `__enter__` 和 `__exit__` 两个魔术方法
- 生成器形式：用 `@contextmanager` + `yield`，更简洁
- 生成器形式中**必须用 try/finally** 保证清理代码执行
- `ExitStack` 可以组合任意数量的上下文管理器
- dify 中常见：`db.session_scope()`、文件操作、临时配置切换

---

**文档版本**：v1.0
**最后更新**：2026-07-13
