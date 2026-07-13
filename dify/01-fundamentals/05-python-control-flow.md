# 0.5 Python 控制流

> 掌握 if/for/while/with 等流程控制语法，能读懂 dify 后端的所有业务逻辑分支。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用条件语句（if/elif/else）、三元表达式、match-case
- 熟练使用循环（for/while）、推导式、enumerate/zip
- 理解 `with` 语句与上下文管理器（资源管理）
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

## 3. dify 仓库源码解读

### 3.1 复杂的权限判断

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 150-185）：

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.account import Account


def _is_account_initialized(account: "Account") -> bool:
    """检查账户是否已完成初始化。"""
    if account.status == "uninitialized":
        return False
    if account.status == "pending" and not account.password:
        # pending 状态但没有密码：未完成
        return False
    if account.status == "active":
        return True
    # 其他未知状态：保守返回 False
    return False


def get_account_status(account: "Account") -> str:
    """返回账户状态的友好描述。"""
    status_map = {
        "uninitialized": "未初始化",
        "pending": "待完善",
        "active": "活跃",
        "banned": "已封禁",
    }
    return status_map.get(account.status, "未知状态")
```

**解读**：
- 第 4-5 行：`TYPE_CHECKING` 是类型检查时为 True，运行时为 False——避免循环导入
- 第 10-17 行：多重 `if` 判断账户状态，dify 中常见模式
- 第 25-31 行：用字典替代 if/elif 链，更易扩展
- **Pythonic 风格**：能用字典就不要用 if 链

### 3.2 循环遍历 dify 数据

**文件位置**：`/Users/xu/code/github/dify/api/services/feature_service.py`
**核心代码**（行 30-55）：

```python
def calculate_token_usage(tenant_id: str, runs: list[dict]) -> dict[str, int]:
    """统计租户的 token 用量。

    Args:
        tenant_id: 租户 ID
        runs: 工作流执行记录列表，每条包含 token_usage 字段

    Returns:
        按模型分组的 token 统计
    """
    usage: dict[str, int] = {}
    for run in runs:
        if run.get("tenant_id") != tenant_id:
            continue  # 跳过不属于该租户的记录

        for model, count in run.get("token_usage", {}).items():
            usage[model] = usage.get(model, 0) + count

    return usage
```

**解读**：
- 第 13 行：`usage: dict[str, int] = {}` 先初始化空字典
- 第 15 行：`if run.get(...) != tenant_id: continue` 用 `continue` 过滤无关数据
- 第 18 行：`for model, count in dict.items()` 解包键值对
- 第 19 行：`dict.get(key, default)` 安全获取，默认值 0
- **典型模式**：用 `continue` 跳过 + `dict.get(key, default)` 累加

### 3.3 上下文管理器管理数据库事务

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 50-80）：

```python
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker


SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """提供事务安全的数据库 session。

    用法：
        with session_scope() as session:
            session.add(obj)
            # 退出 with 块时自动 commit/rollback
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**解读**：
- 第 14 行：`@contextmanager` 装饰器把生成器函数转为上下文管理器
- 第 22-29 行：try/except/finally 保证异常时回滚 + 关闭连接
- 第 21 行：`yield session` 是关键——`with` 块内 `as` 拿到的就是这个 session
- **dify 强制规范**：所有数据库操作必须用 `with session_scope()`，避免连接泄漏

## 4. 关键要点总结

- Python 真值判断：`0`、`""`、`[]`、`{}`、`None` 都是 False
- 三元表达式：`value_if_true if cond else value_if_false`
- 推导式比循环更 Pythonic，但不要嵌套太深（>2 层可读性差）
- `with` 语句是资源管理的最佳实践（文件、数据库、锁）
- dify 风格：能用字典映射就不用 if/elif 链
- 数据库操作必须用 `with session_scope()` 上下文管理器

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `classify_score(scores: list[int]) -> dict` 函数，统计分数段：
- 优秀（>= 90）
- 良好（>= 80）
- 及格（>= 60）
- 不及格（< 60）

```python
input = [95, 87, 65, 42, 73, 100]
output = classify_score(input)
# {"优秀": 2, "良好": 1, "及格": 2, "不及格": 1}
```

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/services/feature_service.py`：
1. dify 在统计时为什么要过滤 `tenant_id`？
2. 为什么用 `dict.get(key, 0)` 而不是 `dict[key]`？

### 练习 3：挑战（选做）

实现一个自定义上下文管理器 `timer()`，记录代码块执行耗时：

```python
with timer() as t:
    time.sleep(0.5)

print(f"耗时: {t.elapsed:.2f}秒")
```

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/dify/api/services/feature_service.py`
- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- Python 官方文档：https://docs.python.org/3/tutorial/controlflow.html
- PEP 634（match-case）：https://peps.python.org/pep-0634/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
