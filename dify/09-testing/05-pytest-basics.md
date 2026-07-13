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
- 09-testing/04-aaa-pattern.md

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

## 3. dify 仓库源码解读

### 3.1 dify 的测试命名规范

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`
**核心代码**（行 1-38）：

```python
"""Comprehensive unit tests for BillingService."""

import json
import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest
from werkzeug.exceptions import InternalServerError

from enums.cloud_plan import CloudPlan
from models import Account, TenantAccountJoin, TenantAccountRole
from services.billing_service import BillingService


class TestBillingServiceSendRequest:
    """Unit tests for BillingService._send_request method.

    Tests cover:
    - Successful GET/PUT/POST/DELETE requests
    - Error handling for various HTTP status codes
    - Retry logic on network failures
    - Request header and parameter validation
    """
```

**解读**：
- 第 29 行：测试类 `TestBillingServiceSendRequest` —— `Test` 前缀让 pytest 自动发现，类名明确指出"测什么"
- 第 5-14 行：模块顶部 docstring 列出覆盖范围，等同于测试规约
- **设计意图**：dify 的测试类名采用 `Test{Class}{Method}` 模式，精确到被测方法，便于定位

### 3.2 dify 的 pytest 配置

**文件位置**：`/Users/xu/code/github/dify/api/pytest.ini`
**核心代码**（行 1-3）：

```ini
[pytest]
pythonpath = .
addopts = --cov=./api --cov-report=json --import-mode=importlib --cov-branch --cov-report=xml
```

**解读**：
- `pythonpath = .` —— pytest 会把当前目录加入 sys.path，让 `from services.xxx import` 能直接工作
- `--import-mode=importlib` —— 用 importlib 模式加载测试模块，避免包名冲突
- **整体设计意图**：dify 通过 pytest.ini 把覆盖率、import 模式等"全局约定"集中配置，测试文件本身只关心测试逻辑

## 4. 关键要点总结

- pytest 用 `assert` 表达式，不用 `assertEqual`
- 自动发现：`test_*.py` 文件 + `test_*` 函数 + `Test*` 类
- 失败信息智能（diff、值对比）
- dify 默认开启覆盖率（`--cov-branch`）和 importlib 模式
- 测试类用 `Test{Class}{Method}` 命名，精确到方法

## 5. 练习题

### 练习 1：基础（必做）

为下面函数写至少 3 个 pytest 测试函数：

```python
def validate_password(password: str) -> bool:
    """密码至少 8 位，包含数字和字母。"""
    if len(password) < 8:
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c.isalpha() for c in password):
        return False
    return True
```

要求：
- 至少测 1 个正常情况
- 至少测 2 个边界情况（太短、缺数字、缺字母）

### 练习 2：进阶

运行 `cd api && uv run --project api --dev pytest api/tests/unit_tests/core/rag/embedding/test_embedding_base.py -v`，观察 pytest 输出格式，理解 `-v` 标志的作用。

### 练习 3：挑战（选做）

阅读 `api/tests/unit_tests/core/rag/embedding/test_embedding_base.py` 第 32-60 行，理解 pytest 的 `assert hasattr`、`assert "x" in y` 等高级断言方式。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pytest.ini`（pytest 配置）
- `/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`（测试类范例）
- pytest 官方文档：https://docs.pytest.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13