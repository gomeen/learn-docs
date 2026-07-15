# 08 pytest Mock：`monkeypatch` / `unittest.mock`

> 掌握 pytest 的 mock 工具，能在 dify 测试中替换依赖、隔离外部服务。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 mock 的概念和必要性
- 掌握 `monkeypatch` 和 `unittest.mock` 的用法
- 能用 mock 替换 dify 测试中的数据库、外部 API
- 应用：能在 dify 的 service 测试中用 `MagicMock` 隔离副作用

## 📚 前置知识

- 09-testing/05-pytest-basics.md
- 09-testing/06-pytest-fixture.md

## 1. 核心概念

### 1.1 Mock 是什么

**Mock** 是用一个"假对象"替换真实的依赖项，让测试：
- 不依赖外部服务（数据库、Redis（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）、第三方 API）
- 精确控制返回值和异常
- 验证被测代码是否正确调用了依赖

### 1.2 pytest 提供的 mock 工具

| 工具 | 用途 | 特点 |
|------|------|------|
| `monkeypatch` | pytest 内置，临时修改属性/环境变量 | 自动清理 |
| `unittest.mock.MagicMock` | 创建万能 mock 对象 | 标准库 |
| `unittest.mock.patch` | 临时替换模块/类的属性 | 函数级 |
| `pytest-mock` | pytest 的 mock 插件 | fixture 形式 |

dify 主要使用 `unittest.mock.MagicMock` 和 `patch`，配合 fixture 使用。

### 1.3 Mock 的三种核心操作

```python
mock = MagicMock()

# 1. 配置返回值
mock.return_value = 42
mock.some_method.return_value = "hello"

# 2. 配置异常
mock.some_method.side_effect = ValueError("oops")

# 3. 验证调用
mock.some_method.assert_called_once_with("alice")
mock.some_method.assert_not_called()
```

## 2. 代码示例

### 2.1 MagicMock 基础用法

```python
from unittest.mock import MagicMock

# ===== 创建一个万能 mock =====
mock_service = MagicMock()

# 配置返回值
mock_service.get_user.return_value = {"id": 1, "name": "alice"}
user = mock_service.get_user(1)
print(user)  # {"id": 1, "name": "alice"}

# 配置调用时抛出异常
mock_service.delete.side_effect = ValueError("not found")
try:
    mock_service.delete(99)
except ValueError as e:
    print(e)  # "not found"

# 验证调用
mock_service.get_user.assert_called_once_with(1)
mock_service.get_user.assert_called_once()
```

### 2.2 patch 装饰器替换真实函数

```python
from unittest.mock import patch

# 临时把 requests.get 替换成 mock
@patch("services.user_service.requests.get")
def test_fetch_user(mock_get):
    # Arrange
    mock_get.return_value.json.return_value = {"id": 1, "name": "alice"}
    mock_get.return_value.status_code = 200

    # Act
    from services.user_service import UserService
    user = UserService.fetch_from_api("https://api.example.com/users/1")

    # Assert
    assert user["name"] == "alice"
    mock_get.assert_called_once_with("https://api.example.com/users/1")
```

### 2.3 monkeypatch 修改环境变量

```python
import os
import pytest


def test_uses_custom_db_url(monkeypatch):
    # Arrange
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test_db")

    # Act
    from services.config import get_db_url
    url = get_db_url()

    # Assert
    assert url == "postgresql://test:test@localhost/test_db"
    # monkeypatch 在测试结束后自动恢复环境变量
```

### 2.4 patch 作为 fixture（pytest-mock 风格）

```python
@pytest.fixture
def mock_billing_api():
    with patch("services.billing_service._http_client.request") as mock_request:
        mock_request.return_value.json.return_value = {"result": "success"}
        mock_request.return_value.status_code = 200
        yield mock_request


def test_get_balance(mock_billing_api):
    from services.billing_service import BillingService
    balance = BillingService.get_balance(user_id=1)
    assert balance == {"result": "success"}
    mock_billing_api.assert_called_once()
```

## 3. dify 仓库源码解读

### 3.1 dify 用 patch 替换 httpx 调用

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`
**核心代码**（行 39-52）：

```python
@pytest.fixture
def mock_httpx_request(self):
    """Mock httpx.request for testing."""
    with patch("services.billing_service._http_client.request") as mock_request:
        yield mock_request

@pytest.fixture
def mock_billing_config(self):
    """Mock BillingService configuration."""
    with (
        patch.object(BillingService, "base_url", "https://billing-api.example.com"),
        patch.object(BillingService, "secret_key", "test-secret-key"),
    ):
        yield
```

**解读**：
- 第 39-43 行：用 `with patch(...)` 临时替换 `services.billing_service._http_client.request`，让测试不真正发 HTTP 请求
- 第 47-52 行：用 `patch.object` 替换类属性 `base_url` 和 `secret_key`，让被测代码读取测试值
- `yield mock_request` 把 mock 暴露给测试函数使用
- **设计意图**：把 mock 提取为 fixture，避免每个测试函数重复 patch 代码

### 3.2 dify 的全局 Redis mock

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`
**核心代码**（行 1-30）：

```python
import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# set global mock for Redis client
redis_mock = MagicMock()
redis_mock.get = MagicMock(return_value=None)
redis_mock.setex = MagicMock()
redis_mock.setnx = MagicMock()
redis_mock.delete = MagicMock()
redis_mock.lock = MagicMock()
redis_mock.exists = MagicMock(return_value=False)
redis_mock.set = MagicMock()
redis_mock.expire = MagicMock()
redis_mock.hgetall = MagicMock(return_value={})
redis_mock.hdel = MagicMock()
redis_mock.incr = MagicMock(return_value=1)


def _patch_redis_clients_on_loaded_modules():
    """Ensure any module-level redis_client references point to the shared redis_mock."""
    import sys
    for module in list(sys.modules.values()):
        if module is None:
            continue
        if hasattr(module, "redis_client"):
            module.redis_client = redis_mock
```

**解读**：
- 第 12-25 行：在文件加载时创建**全局 redis_mock**，预设所有方法的返回值
- 第 28-37 行：`_patch_redis_clients_on_loaded_modules()` 遍历 `sys.modules`，把所有模块级别的 `redis_client` 都指向 mock
- **关键设计**：模块级别的全局 mock 让任何 import 了 redis 客户端的代码都不会真正连接 Redis
- 这就是 dify 单元测试**不需要 Redis 服务**的原因

### 3.3 dify 的 autouse patch

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`
**核心代码**（行 53-66）：

```python
@pytest.fixture(autouse=True)
def _patch_redis_clients():
    """Patch redis_client to MagicMock only for unit test executions."""

    with (
        patch.object(ext_redis, "redis_client", redis_mock),
        patch.object(ext_redis, "_pubsub_redis_client", redis_mock),
    ):
        _patch_redis_clients_on_loaded_modules()
        yield
```

**解读**：
- `autouse=True` 让所有单元测试自动获得 Redis mock
- `patch.object(ext_redis, "redis_client", redis_mock)` 替换 `extensions.ext_redis` 模块的全局变量
- yield 后自动恢复原值
- **设计意图**：单元测试不应该假设 Redis 可用，autouse mock 是最简洁的隔离手段

## 4. 关键要点总结

- Mock 用假对象替换真实依赖，让测试可重复、不依赖外部服务
- `unittest.mock.MagicMock` 是最常用的万能 mock
- `patch` / `patch.object` 临时替换模块属性，退出时自动恢复
- `monkeypatch` 用于修改环境变量和简单属性
- dify 在 `conftest.py` 中定义全局 `redis_mock`，通过 autouse fixture 注入到所有单元测试

## 5. 练习题

### 练习 1：基础（必做）

用 `patch` 替换下面函数中的 `requests.get`，写一个测试：

```python
import requests

def fetch_user_name(user_id: int) -> str:
    resp = requests.get(f"https://api.example.com/users/{user_id}")
    return resp.json()["name"]
```

要求：mock 返回 `{"name": "alice"}`，断言函数返回 `"alice"`。

### 练习 2：进阶

阅读 `api/tests/unit_tests/services/test_billing_service.py` 的 `mock_billing_config` fixture（约第 45-52 行），理解 `patch.object` 与 `with` 块的关系，并回答：为什么这里用 `with` 而不是装饰器？

### 练习 3：挑战（选做）

为 `services/email_service.py` 写一个 `mock_smtp` fixture，要求：
- 用 `patch` 替换 `smtplib.SMTP`
- mock 发送邮件时不真正建立连接
- 提供 `sent_messages` 属性用于断言发送了几封邮件

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`（patch 范例）
- `/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`（全局 Redis mock）
- pytest monkeypatch 文档：https://docs.pytest.org/en/stable/monkeypatch.html
- unittest.mock 文档：https://docs.python.org/3/library/unittest.mock.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13