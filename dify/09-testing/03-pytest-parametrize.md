# 07 pytest 参数化：`@pytest.mark.parametrize`

> 用 `@pytest.mark.parametrize` 减少重复测试代码，一次性覆盖多个数据组合。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@pytest.mark.parametrize` 的基本用法和高级特性
- 理解参数化与 fixture 的区别和组合用法
- 能用参数化减少 dify 测试的重复代码
- 应用：能在 dify 的 service 测试中使用参数化覆盖多场景

## 📚 前置知识

- 09-testing/01-pytest-basics.md
- 09-testing/02-pytest-fixture.md

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

## 3. 关键要点总结

- `@pytest.mark.parametrize` 用一组数据驱动同一个测试函数
- 用 `ids` 参数自定义测试 ID，让报告更友好
- 可以叠加多个 `parametrize`，生成笛卡尔积
- 参数化 + fixture 组合使用，处理"公共准备 + 多组数据"的场景
- dify 在 service 测试中大量用参数化覆盖 HTTP 状态码、方法、错误类型

---

**文档版本**：v1.0
**最后更新**：2026-07-13
