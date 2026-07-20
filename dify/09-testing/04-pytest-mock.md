# 08 pytest Mock：`monkeypatch` / `unittest.mock`

> 掌握 pytest 的 mock 工具，能在 dify 测试中替换依赖、隔离外部服务。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 mock 的概念和必要性
- 掌握 `monkeypatch` 和 `unittest.mock` 的用法
- 能用 mock 替换 dify 测试中的数据库、外部 API
- 应用：能在 dify 的 service 测试中用 `MagicMock` 隔离副作用

## 📚 前置知识

- 09-testing/01-pytest-basics.md
- 09-testing/02-pytest-fixture.md

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

## 3. 关键要点总结

- Mock 用假对象替换真实依赖，让测试可重复、不依赖外部服务
- `unittest.mock.MagicMock` 是最常用的万能 mock
- `patch` / `patch.object` 临时替换模块属性，退出时自动恢复
- `monkeypatch` 用于修改环境变量和简单属性
- dify 在 `conftest.py` 中定义全局 `redis_mock`，通过 autouse fixture 注入到所有单元测试

---

**文档版本**：v1.0
**最后更新**：2026-07-13
