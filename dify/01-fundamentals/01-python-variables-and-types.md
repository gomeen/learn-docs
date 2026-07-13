# 0.1 Python 变量与数据类型

> 入门 Python 的第一步：变量命名、赋值、动态类型、内置数据类型。这是后续所有 Python 类型系统学习的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Python 变量的本质（标签而非盒子）
- 掌握 Python 动态类型的工作机制
- 熟练使用内置数据类型：int / float / str / bool / None
- 能在 dify 仓库代码中识别各种基本类型

## 📚 前置知识

- 无（Python 入门第一篇）

## 1. 核心概念

### 1.1 变量：贴标签而非装盒子

很多人学过 C/Java，以为变量是"装数据的盒子"。Python 不一样：

```
传统理解：盒子 = 变量，里面装的是数据
Python 理解：标签 = 变量，贴在数据对象上
```

```python
a = [1, 2, 3]   # [1,2,3] 是数据对象，a 是贴在它身上的标签
b = a           # b 是另一个标签，也贴在同一个对象上
b.append(4)     # 通过 b 修改对象
print(a)        # [1, 2, 3, 4] —— a 和 b 指向同一对象！
```

### 1.2 动态类型：运行时才确定类型

```python
x = 10          # x 是 int
x = "hello"     # 现在 x 是 str（同一个变量可以指向不同类型）
x = [1, 2, 3]   # 现在 x 是 list
```

类型在**赋值时**确定，运行期间可以改变。这与 Java/C 等静态类型语言截然不同。

### 1.3 内置类型速览

| 类型 | 例子 | 说明 |
|------|------|------|
| `int` | `42`, `-7` | 整数（任意精度，不溢出） |
| `float` | `3.14`, `1e-3` | 浮点数 |
| `str` | `"hello"`, `'world'` | 字符串（不可变） |
| `bool` | `True`, `False` | 布尔值（实际是 int 的子类） |
| `NoneType` | `None` | 空值（唯一实例是 None） |
| `list` | `[1, 2, 3]` | 有序可变序列 |
| `dict` | `{"a": 1}` | 键值对映射 |
| `tuple` | `(1, 2)` | 有序不可变序列 |
| `set` | `{1, 2, 3}` | 无序不重复集合 |

### 1.4 字符串基础

```python
s = "hello"

# 索引（下标从 0 开始）
print(s[0])      # 'h'
print(s[-1])     # 'o'（倒数第一个）

# 切片 [start:end:step]
print(s[0:3])    # 'hel'（不包含 end）
print(s[::2])    # 'hlo'（步长 2）
print(s[::-1])   # 'olleh'（反转）

# 字符串是不可变的
s[0] = 'H'       # ❌ TypeError
new_s = 'H' + s[1:]  # ✅ 正确做法：创建新字符串
```

### 1.5 布尔与 None

```python
# 布尔值本质是整数
print(True == 1)   # True
print(False == 0)  # True
print(True + True) # 2

# None 表示"空"或"不存在"
result = None
if result is None:
    print("没有结果")

# ⚠️ 用 is 判断 None，不要用 ==
if result is None:  # ✅ 推荐
    ...
if result == None:  # ❌ 不推荐（PEP 8）
    ...
```

## 2. 代码示例

### 2.1 变量赋值的多重形式

```python
# 基本赋值
name = "dify"
version = 1.0

# 多重赋值
a, b, c = 1, 2, 3
print(a, b, c)  # 1 2 3

# 链式赋值
x = y = z = 0   # x、y、z 都指向同一个 int 对象 0

# 解包（unpacking）
first, *middle, last = [1, 2, 3, 4, 5]
print(first, middle, last)  # 1 [2, 3, 4] 5

# 交换变量（无需临时变量）
a, b = 10, 20
a, b = b, a
print(a, b)  # 20 10
```

### 2.2 类型转换

```python
# 字符串 ↔ 数字
s = "42"
n = int(s)        # str → int
f = float("3.14") # str → float

# 数字 → 字符串
s = str(42)       # int → str

# 集合之间转换
items = [1, 2, 2, 3, 3, 3]
unique = set(items)      # {1, 2, 3}
back_to_list = list(unique)  # [1, 2, 3]（顺序不保证）

# ⚠️ 失败的转换会抛异常
int("abc")  # ValueError: invalid literal for int()
```

### 2.3 可变 vs 不可变

```python
# 不可变类型：int, float, str, tuple, frozenset
# 修改时实际上是创建新对象
a = "hello"
b = a
a = a + " world"  # a 现在指向新字符串 "hello world"
print(b)          # "hello"（b 不受影响）

# 可变类型：list, dict, set
# 修改时原地操作
a = [1, 2, 3]
b = a
a.append(4)
print(b)          # [1, 2, 3, 4]（b 也变了！）
```

## 3. dify 仓库源码解读

### 3.1 配置文件中的常量赋值

**文件位置**：`/Users/xu/code/github/dify/api/configs/app_config.py`
**核心代码**（行 1-30）：

```python
from typing import ClassVar

class DifyConfig:
    """Dify 全局配置类，所有配置项的单一来源。"""

    # 类变量（用 ClassVar 标注，区别于实例变量）
    DEBUG: ClassVar[bool] = False
    EDITION: ClassVar[str] = "SELF_HOSTED"
    DEPLOY_ENV: ClassVar[str] = "PRODUCTION"

    # 实例变量（在 __init__ 中赋值）
    def __init__(self) -> None:
        self.SECRET_KEY: str = ""
        self.CONSOLE_API_URL: str = ""
        self.DB_USERNAME: str = "postgres"
        self.DB_PORT: int = 5432
        self.DB_ENABLE_CHEVRON: bool = False
```

**解读**：
- 第 7 行：`ClassVar[bool]` 表示这是类变量，所有实例共享
- 第 14-19 行：实例变量用 `self.xxx` 赋值，每个实例独立
- 第 17 行：`int = 5432` 是 PostgreSQL 默认端口
- **整体设计意图**：用类型注解让配置项的"契约"清晰，IDE 可以自动补全和检查

### 3.2 字符串与字典的常见用法

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1-30）：

```python
import json
import re

EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
MIN_PASSWORD_LENGTH = 8


class AccountService:
    """账户服务：处理用户注册、登录、密码重置等。"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """校验邮箱格式。"""
        return bool(EMAIL_PATTERN.match(email))

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成随机 token。"""
        import secrets
        return secrets.token_urlsafe(length)
```

**解读**：
- 第 5 行：模块级常量 `EMAIL_PATTERN` 是编译好的正则（提高性能）
- 第 6 行：`MIN_PASSWORD_LENGTH = 8` 是密码最小长度常量
- 第 16 行：`bool()` 将正则匹配结果（Match 对象或 None）转为 True/False
- 第 21 行：`secrets.token_urlsafe()` 生成加密安全的随机字符串
- **关键模式**：dify 中大量使用「模块级常量 + 静态方法」的简洁风格

## 4. 关键要点总结

- Python 变量是**标签**，不是盒子；多个变量可以指向同一个对象
- Python 是**动态类型**，运行时才确定类型
- 字符串、tuple、int 是**不可变**；list、dict、set 是**可变**
- 比较 `None` 用 `is`，不要用 `==`
- dify 中常用 `ClassVar` 标注类变量，模块级常量全大写命名

## 5. 练习题

### 练习 1：基础（必做）

预测以下代码的输出，并实际运行验证：

```python
a = [1, 2, 3]
b = a
c = a.copy()
a.append(4)
print(a, b, c)

x = 10
y = x
x = 20
print(x, y)
```

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/configs/app_config.py`，列出：
1. 哪些是类变量（`ClassVar`），哪些是实例变量？
2. dify 用什么命名风格（蛇形/驼峰）？

### 练习 3：挑战（选做）

写一个函数 `normalize_config(raw: dict) -> dict`，把不规范的配置字典（值为字符串 "true"/"false"/"null"/数字字符串）转换为正确类型：

```python
input = {"debug": "true", "port": "5432", "name": "dify"}
output = normalize_config(input)
# {"debug": True, "port": 5432, "name": "dify"}
```

## 6. 参考资料

- `/Users/xu/code/github/dify/api/configs/app_config.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`
- Python 官方文档：https://docs.python.org/3/tutorial/introduction.html
- Real Python 变量与内存：https://realpython.com/python-variables/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
