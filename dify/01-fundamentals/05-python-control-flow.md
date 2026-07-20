# 0.5 Python 控制流

> 掌握 if/for/while/with 等流程控制语法，能读懂 dify 后端的所有业务逻辑分支。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用条件语句（if/elif/else）、三元表达式、match-case
- 熟练使用循环（for/while）、推导式、enumerate/zip
- 掌握 `with` 语句的用法（资源管理；自定义上下文管理器见专题）
- 能读懂 dify 中的复杂业务分支

## 📚 前置知识

- [00-python-variables-and-types.md](./01-python-variables-and-types.md)

## 1. 核心概念

### 1.1 条件语句：if / elif / else

```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"     # ← 进入这里
elif score >= 70:
    grade = "C"
else:
    grade = "D"

print(grade)  # "B"
```

要点：
- 条件判断用 `==`、`!=`、`<`、`>`、`<=`、`>=`
- 逻辑组合用 `and`、`or`、`not`
- `elif` 是 `else if` 的缩写，Python 特有

### 1.2 真值判断（Truthiness）

```python
# 以下都视为 False
bool(False)    # False
bool(None)     # False
bool(0)        # False
bool("")       # False（空字符串）
bool([])       # False（空列表）
bool({})       # False（空字典）
bool(set())    # False（空集合）

# 其他都视为 True
bool(1)        # True
bool("hello")  # True
bool([0])      # True（含一个元素的列表）

# 因此可以直接写：
items = []
if not items:   # 比 if len(items) == 0 更 Pythonic
    print("列表为空")
```

### 1.3 三元表达式

```python
# 语法：value_if_true if condition else value_if_false
age = 20
status = "成年" if age >= 18 else "未成年"

# 等价于：
if age >= 18:
    status = "成年"
else:
    status = "未成年"
```

### 1.4 match-case（Python 3.10+）

```python
def http_status(code):
    match code:
        case 200:
            return "OK"
        case 301 | 302:        # 多个值用 |
            return "Redirect"
        case 404:
            return "Not Found"
        case 500 if code == 500:  # 守卫（不推荐，这里是示例）
            return "Server Error"
        case _:                # 默认分支
            return "Unknown"
```

### 1.5 循环：for / while

```python
# for 循环：遍历可迭代对象
for item in [1, 2, 3]:
    print(item)

# range 生成数字序列
for i in range(5):          # 0, 1, 2, 3, 4
    print(i)

for i in range(2, 10, 2):   # 2, 4, 6, 8（start, stop, step）
    print(i)

# while 循环：条件循环
count = 0
while count < 3:
    print(count)
    count += 1

# break 跳出循环，continue 跳过本次
for i in range(10):
    if i == 3:
        continue  # 跳过 3
    if i == 7:
        break     # 在 7 处退出
    print(i)      # 输出 0, 1, 2, 4, 5, 6
```

### 1.6 enumerate / zip

```python
# enumerate：同时获取索引和值
fruits = ["apple", "banana", "cherry"]
for i, fruit in enumerate(fruits):
    print(f"{i}: {fruit}")
# 0: apple
# 1: banana
# 2: cherry

# zip：并行遍历多个列表
names = ["Alice", "Bob"]
ages = [30, 25]
for name, age in zip(names, ages):
    print(f"{name} is {age}")
# Alice is 30
# Bob is 25
```

## 2. 代码示例

### 2.1 列表/字典/集合推导式

```python
# 列表推导式
squares = [x * x for x in range(5)]           # [0, 1, 4, 9, 16]
evens = [x for x in range(10) if x % 2 == 0]  # [0, 2, 4, 6, 8]

# 字典推导式
word_lengths = {word: len(word) for word in ["hi", "hello", "hey"]}
# {"hi": 2, "hello": 5, "hey": 3}

# 集合推导式
unique_lengths = {len(word) for word in ["hi", "hello", "hey"]}
# {2, 3, 5}

# 生成器表达式（节省内存）
sum_of_squares = sum(x * x for x in range(1000000))  # 不创建中间列表
```

### 2.2 上下文管理器：with 语句

本文只掌握 **`with` 的用法**（自动释放资源）。自定义上下文管理器、`@contextmanager`、`__enter__` / `__exit__` 见 [11-context-manager](./12-context-manager.md)。

```python
# 文件操作（自动关闭）
with open("data.txt", "r") as f:
    content = f.read()
# 文件自动关闭，即使发生异常

# 数据库连接（事务自动提交/回滚）
with Session(engine) as session:
    session.execute(...)
    session.commit()
# 异常时自动回滚，正常时自动提交

# 锁（自动释放）
import threading
lock = threading.Lock()
with lock:
    # 临界区代码
    ...
# 锁自动释放
```

**为什么用 `with`？**
- **资源安全**：即使发生异常也能正确释放资源
- **代码简洁**：不需要写 `try/finally`
- **可读性强**：清楚表达"作用域"

### 2.3 循环中的 else 子句（Python 特有）

```python
# else 在循环正常完成时执行（break 不会触发）
for n in range(2, 10):
    for x in range(2, n):
        if n % x == 0:
            break
    else:
        # 没有找到因子，n 是质数
        print(f"{n} 是质数")
```

## 3. 关键要点总结

- Python 真值判断：`0`、`""`、`[]`、`{}`、`None` 都是 False
- 三元表达式：`value_if_true if cond else value_if_false`
- 推导式比循环更 Pythonic，但不要嵌套太深（>2 层可读性差）
- `with` 语句是资源管理的最佳实践（文件、数据库、锁）；自定义实现见上下文管理器专题
- dify 风格：能用字典映射就不用 if/elif 链
- 数据库操作必须用 `with session_scope()` 上下文管理器

---

**文档版本**：v1.0
**最后更新**：2026-07-13
