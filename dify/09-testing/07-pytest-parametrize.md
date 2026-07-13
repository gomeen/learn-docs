# 07 pytest 参数化：`@pytest.mark.parametrize`

> 用 `@pytest.mark.parametrize` 减少重复测试代码，一次性覆盖多个数据组合。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@pytest.mark.parametrize` 的基本用法和高级特性
- 理解参数化与 fixture 的区别和组合用法
- 能用参数化减少 dify 测试的重复代码
- 应用：能在 dify 的 service 测试中使用参数化覆盖多场景

## 📚 前置知识

- 09-testing/05-pytest-basics.md
- 09-testing/06-pytest-fixture.md

## 1. 核心概念

### 1.1 什么是参数化

**参数化**让你用一组数据驱动同一个测试逻辑，避免写重复的测试函数。

```python
# 不参数化：写 3 个函数
def test_add_positive(): assert add(1, 2) == 3
def test_add_negative(): assert add(-1, -2) == -3
def test_add_zero(): assert add(0, 0) == 0

# 参数化：写 1 个函数
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (-1, -2, -3),
    (0, 0, 0),
])
def test_add(a, b, expected):
    assert add(a, b) == expected
```

### 1.2 参数化的好处

- **减少重复**：N 个相似测试合并为 1 个
- **失败定位精确**：报告里清楚显示哪组数据失败
- **易于扩展**：加一个数据点只多一行
- **强制思考**：列出所有测试数据 = 列举所有边界情况

### 1.3 何时不适合参数化

- 每个测试用例的 Arrange 完全不同 → 用 fixture 更合适
- 测试逻辑差异很大 → 拆分成多个函数
- 参数化后函数名太长 → 用 `ids` 参数自定义

## 2. 代码示例

### 2.1 基础参数化

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("World", "WORLD"),
    ("", ""),
    ("123abc", "123ABC"),
])
def test_upper(input, expected):
    assert input.upper() == expected
```

### 2.2 自定义测试 ID

```python
@pytest.mark.parametrize("status_code,expected_error", [
    (400, "Invalid arguments."),
    (401, "Invalid arguments."),
    (404, "Invalid arguments."),
    (500, "Unable to process"),
], ids=["bad_request", "unauthorized", "not_found", "server_error"])
def test_http_error(status_code, expected_error):
    # 用 ids 让失败报告更友好
    ...
```

运行后：

```
test_http_error[bad_request] PASSED
test_http_error[unauthorized] PASSED
test_http_error[not_found] PASSED
test_http_error[server_error] PASSED
```

### 2.3 参数化 + fixture

```python
@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.mark.parametrize("email,is_valid", [
    ("alice@example.com", True),
    ("bob@test.org", True),
    ("not-an-email", False),
    ("@nodomain.com", False),
    ("", False),
])
def test_validate_email(mock_db, email, is_valid):
    # Arrange
    validator = EmailValidator(db=mock_db)

    # Act
    result = validator.validate(email)

    # Assert
    assert result == is_valid
```

### 2.4 多组参数笛卡尔积

```python
@pytest.mark.parametrize("x", [1, 2, 3])
@pytest.mark.parametrize("y", [10, 20])
def test_add(x, y):
    # 3 × 2 = 6 个测试用例
    assert add(x, y) == x + y
```

输出：

```
test_add[10-1] PASSED
test_add[10-2] PASSED
test_add[10-3] PASSED
test_add[20-1] PASSED
test_add[20-2] PASSED
test_add[20-3] PASSED
```

## 3. dify 仓库源码解读

### 3.1 dify 用参数化覆盖 HTTP 状态码

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`
**核心代码**（行 93-106）：

```python
@pytest.mark.parametrize(
    "status_code", [httpx.codes.NOT_FOUND, httpx.codes.INTERNAL_SERVER_ERROR, httpx.codes.BAD_REQUEST]
)
def test_get_request_non_200_status_code(self, mock_httpx_request, mock_billing_config, status_code):
    """Test GET request with non-200 status code raises ValueError."""
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_httpx_request.return_value = mock_response

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        BillingService._send_request("GET", "/test")
    assert "Unable to retrieve billing information" in str(exc_info.value)
```

**解读**：
- 第 93-95 行：传入 `status_code` 参数，3 种状态码生成 3 个独立测试
- 第 102-104 行：`Act & Assert` 合并——因为断言异常时两者紧密耦合
- **设计意图**：用参数化代替 3 个几乎相同的测试函数，把"哪些状态码会抛异常"的知识集中在参数列表里

### 3.2 dify 的多组参数

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`
**核心代码**（行 153-169）：

```python
@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_non_get_non_put_request_success(self, mock_httpx_request, mock_billing_config, method):
    """Test successful POST/DELETE request."""
    # Arrange
    expected_response = {"result": "success"}
    mock_response = MagicMock()
    mock_response.status_code = httpx.codes.OK
    mock_response.json.return_value = expected_response
    mock_httpx_request.return_value = mock_response

    # Act
    result = BillingService._send_request(method, "/test", json={"key": "value"})

    # Assert
    assert result == expected_response
    call_args = mock_httpx_request.call_args
    assert call_args[0][0] == method
```

**解读**：
- 用 `method` 参数覆盖 POST 和 DELETE 两种 HTTP 方法
- 测试函数体不变，只是传入的 `method` 不同
- **关键设计**：当多组数据的差异只是"传入某个值"时，参数化是最优解

## 4. 关键要点总结

- `@pytest.mark.parametrize` 用一组数据驱动同一个测试函数
- 用 `ids` 参数自定义测试 ID，让报告更友好
- 可以叠加多个 `parametrize`，生成笛卡尔积
- 参数化 + fixture 组合使用，处理"公共准备 + 多组数据"的场景
- dify 在 service 测试中大量用参数化覆盖 HTTP 状态码、方法、错误类型

## 5. 练习题

### 练习 1：基础（必做）

把下面 3 个测试合并为一个参数化测试：

```python
def test_is_adult_18(): assert is_adult(18) is True
def test_is_adult_25(): assert is_adult(25) is True
def test_is_adult_17(): assert is_adult(17) is False
```

### 练习 2：进阶

阅读 `api/tests/unit_tests/services/test_billing_service.py` 第 138-152 行的 `test_put_request_non_200_non_500`，找出它参数化的状态码，并解释为什么这些状态码被归为一组。

### 练习 3：挑战（选做）

为 `services/billing_service.py` 的 `_send_request` 方法补充测试，要求用参数化覆盖至少 10 种 HTTP 状态码 × 4 种 HTTP 方法的笛卡尔积（共 40 个测试用例），并合理分组。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`（参数化典范）
- pytest parametrize 官方文档：https://docs.pytest.org/en/stable/parametrize.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13