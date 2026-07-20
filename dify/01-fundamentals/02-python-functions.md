# 0.2 Python 函数基础

> 理解函数定义、参数、返回值与作用域。这是阅读 dify 后端代码的基础——几乎每个业务逻辑都是一个函数。

## 🎯 学习目标

完成本文档后，你将能够：

- 熟练定义函数（def、参数、返回值、文档字符串）
- 掌握各种参数形式：位置参数、关键字参数、默认参数、`*args` / `**kwargs`
- 理解变量作用域（LEGB 规则）
- 能看懂 dify 中所有 service 方法与 controller 函数

## 📚 前置知识

- [00-python-variables-and-types.md](./01-python-variables-and-types.md)

## 1. 核心概念

### 1.1 函数定义基础

```python
def greet(name: str) -> str:
    """向用户问好。"""
    return f"Hello, {name}"

# 调用
message = greet("dify")
print(message)  # "Hello, dify"
```

三要素：

- **def 关键字**：定义函数
- **参数列表**：`name: str`
- **返回值**：`-> str` + `return`

### 1.2 四种参数形式

```python
def func(
    a,              # 1. 位置参数（必传）
    b=10,           # 2. 关键字参数（有默认值）
    *args,          # 3. 可变位置参数（元组）
    c=20,           # 4. 关键字-only 参数（* 之后必须用关键字传）
    **kwargs,       # 5. 可变关键字参数（字典）
):
    print(a, b, args, c, kwargs)

# 调用示例
func(1)                          # a=1, b=10, args=(), c=20, kwargs={}
func(1, 2, 3, 4, 5)              # a=1, b=2, args=(3,4,5), c=20, kwargs={}
func(1, 2, 3, c=99, x=100)       # a=1, b=2, args=(3,), c=99, kwargs={'x':100}
```

### 1.3 返回值：单值、多值、None

```python
# 单值返回
def square(x): return x * x

# 多值返回（实际是 tuple）
def divide(a, b):
    return a // b, a % b  # 返回 (商, 余数)
q, r = divide(10, 3)      # q=3, r=1

# 没有 return 或 return 后无值 → 返回 None
def log(msg):
    print(msg)
    # 隐式 return None

result = log("hi")
print(result)  # None
```

### 1.4 作用域：LEGB 规则

Python 查找变量时按 **L → E → G → B** 顺序：

| 层级 | 名称           | 示例               |
| ---- | -------------- | ------------------ |
| L    | Local 函数内部 | 函数内定义的变量   |
| E    | Enclosing 闭包 | 外层函数（嵌套时） |
| G    | Global 全局    | 模块级变量         |
| B    | Built-in 内建  | `print`、`len` 等  |

```python
x = "global"          # G

def outer():
    x = "enclosing"   # E
    def inner():
        x = "local"   # L
        print(x)      # "local"（优先用最近的）
    inner()
    print(x)          # "enclosing"

outer()
print(x)              # "global"
```

## 2. 代码示例

### 2.1 默认参数陷阱

```python
# ❌ 经典坑：默认参数是可变对象时
def add_item(item, lst=[]):  # lst 在函数定义时只创建一次！
    lst.append(item)
    return lst

print(add_item("a"))  # ["a"]
print(add_item("b"))  # ["a", "b"] ← 累加了！
print(add_item("c"))  # ["a", "b", "c"]

# ✅ 正确做法：用 None 占位
def add_item(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

### 2.2 `*args` 与 `**kwargs` 的实战用法

```python
# *args：收集多余的位置参数为元组
def log(level, *messages):
    for msg in messages:
        print(f"[{level}] {msg}")

log("INFO", "服务启动", "端口 8080", "环境 prod")
# [INFO] 服务启动
# [INFO] 端口 8080
# [INFO] 环境 prod

# **kwargs：收集多余的关键字参数为字典
def make_user(name, **extras):
    return {"name": name, **extras}

user = make_user("Alice", age=30, role="admin")
# {"name": "Alice", "age": 30, "role": "admin"}
```

### 2.3 解包调用（`*` 和 `**` 在调用时使用）

```python
def calc(a, b, c):
    return a + b * c

# 调用时 * 解包列表/元组为位置参数
args = [1, 2, 3]
print(calc(*args))  # 1 + 2 * 3 = 7

# 调用时 ** 解包字典为关键字参数
kwargs = {"a": 1, "b": 2, "c": 3}
print(calc(**kwargs))  # 7
```

## 3. 关键要点总结

- 函数四要素：def + 名字 + 参数列表 + 函数体
- 参数顺序：位置 → 默认 → `*args` → 关键字-only → `**kwargs`
- 默认参数**绝不能用可变对象**（用 None 占位）
- `*args` 收集元组，`**kwargs` 收集字典；调用时反过来用
- dify 风格：关键字-only 参数用于"可选配置"，`**kwargs` 用于"扩展字段"
- 阅读代码时会遇到装饰器写法；实现与原理见装饰器专题（上文 Sighting）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
