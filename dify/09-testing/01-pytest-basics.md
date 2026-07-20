# 05 pytest 基础：`test_` 函数与断言

> 掌握 pytest 的基本测试函数编写方式，能写出可被 pytest 自动发现和运行的测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 pytest 的自动发现规则（test_ 前缀、test 类）
- 正确使用 `assert` 关键字写测试断言
- 知道 pytest 与 unittest 的区别
- 应用：能在 dify 后端新增测试模块

## 📚 前置知识

- Python 基础语法
- ../../_common/18-testing/04-aaa-pattern.md

## 1. 核心概念

### 1.1 pytest 是什么

`pytest` 是 Python 生态最流行的测试框架，由 Holger Krekel 创建。它的核心理念是：

> 让测试像普通 Python 函数一样简洁，不需要继承任何类。

```python
# 文件：test_example.py
def test_addition():
    assert 1 + 1 == 2
```

只要函数名以 `test_` 开头，pytest 就能自动发现并执行。

### 1.2 自动发现规则

pytest 默认会收集以下模式的测试：

| 元素 | 匹配规则 | 示例 |
|------|----------|------|
| 文件 | `test_*.py` 或 `*_test.py` | `test_user.py` |
| 函数 | `test_*` | `test_create_user()` |
| 类 | `Test*`（且不能有 `__init__`） | `TestUserService` |
| 方法 | 类内 `test_*` 方法 | `TestUserService.test_create()` |

### 1.3 pytest vs unittest

```python
# unittest 风格（啰嗦）
import unittest
class TestUser(unittest.TestCase):
    def test_create(self):
        self.assertEqual(1 + 1, 2)

# pytest 风格（简洁）
def test_create():
    assert 1 + 1 == 2
```

| 维度 | pytest | unittest |
|------|--------|----------|
| 语法 | `assert` 表达式 | `assertEqual` 等方法 |
| 学习曲线 | 平缓 | 较陡 |
| 插件生态 | 丰富（600+） | 较少 |
| 失败信息 | 智能（显示实际值） | 基础 |

dify 完全采用 pytest 风格。

## 2. 代码示例

### 2.1 第一个 pytest 测试

```python
# 文件：test_calculator.py

def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def test_add_positive_numbers():
    """测试两个正数相加。"""
    assert add(1, 2) == 3

def test_add_zero():
    """测试零加任何数。"""
    assert add(0, 100) == 100
    assert add(100, 0) == 100

def test_divide_by_zero_raises():
    """测试除零时抛出 ValueError。"""
    import pytest
    with pytest.raises(ValueError, match="division by zero"):
        divide(10, 0)
```

运行：

```bash
$ pytest test_calculator.py -v
======================== test session starts ========================
test_calculator.py::test_add_positive_numbers PASSED
test_calculator.py::test_add_zero PASSED
test_calculator.py::test_divide_by_zero_raises PASSED
======================== 3 passed in 0.02s ========================
```

### 2.2 测试类

```python
# 文件：test_user_service.py
from services.user_service import UserService


class TestUserService:
    """用户服务测试套件。"""

    def test_create_user_success(self):
        user = UserService.create(email="a@x.com", password="pwd")
        assert user.email == "a@x.com"

    def test_create_user_invalid_email_raises(self):
        import pytest
        with pytest.raises(ValueError):
            UserService.create(email="not-an-email", password="pwd")

    def test_delete_user_removes_from_db(self):
        user = UserService.create(email="b@x.com", password="pwd")
        UserService.delete(user.id)
        assert UserService.get(user.id) is None
```

### 2.3 pytest 的智能失败信息

```python
def test_dict_compare():
    expected = {"name": "alice", "age": 30, "tags": ["admin", "user"]}
    actual = {"name": "alice", "age": 31, "tags": ["admin"]}
    assert expected == actual
```

失败时 pytest 会智能 diff：

```
E   AssertionError: assert {'age': 30, 'name': 'alice', 'tags': ['admin', 'user']} == {'age': 31, 'name': 'alice', 'tags': ['admin']}
E     Differing items:
E     {'age': 30} != {'age': 31}
E     {'tags': ['admin', 'user']} != {'tags': ['admin']}
```

## 3. 关键要点总结

- pytest 用 `assert` 表达式，不用 `assertEqual`
- 自动发现：`test_*.py` 文件 + `test_*` 函数 + `Test*` 类
- 失败信息智能（diff、值对比）
- dify 默认开启覆盖率（`--cov-branch`）和 importlib 模式
- 测试类用 `Test{Class}{Method}` 命名，精确到方法

---

**文档版本**：v1.0
**最后更新**：2026-07-13
