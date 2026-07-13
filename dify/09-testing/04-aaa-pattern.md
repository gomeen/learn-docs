# 04 Arrange-Act-Assert 测试结构

> 掌握 AAA（Arrange-Act-Assert）测试结构，写出清晰、易维护的 dify 测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 AAA 三段式结构的目的和好处
- 在 dify 测试中正确应用 AAA
- 区分 AAA 与其他结构（如 BDD 的 Given-When-Then）
- 应用：能用 AAA 改写混乱的测试用例

## 📚 前置知识

- 09-testing/01-testing-pyramid.md
- pytest 基本用法

## 1. 核心概念

### 1.1 AAA 是什么

**Arrange-Act-Assert** 是测试代码的标准三段式组织方式：

```python
def test_xxx():
    # ===== Arrange（准备）=====
    # 准备测试数据、mock、fixture

    # ===== Act（执行）=====
    # 调用被测代码（通常只有一行）

    # ===== Assert（断言）=====
    # 验证结果
```

每段各司其职，**Act 段通常只有一行**——这是判断测试结构是否合理的关键指标。

### 1.2 为什么需要 AAA

- **可读性**：阅读测试时一眼看出"做了什么、验证什么"
- **可维护性**：重构代码时容易找到需要更新的地方
- **减少 bug**：明确的结构让你不会漏掉边界条件
- **促进 TDD**：先写 Arrange → 思考 Act → 明确 Assert，是自然的设计流程

### 1.3 AAA vs Given-When-Then

| 维度 | AAA | Given-When-Then (BDD) |
|------|-----|----------------------|
| 起源 | xUnit 测试社区 | 行为驱动开发（BDD） |
| 语法 | 注释或空行 | `given()` / `when()` / `then()` 函数 |
| 适用 | 单元测试、集成测试 | 业务规则、E2E |
| 工具 | pytest 原生 | pytest-bdd、behave |

两者本质相同，只是表述风格不同。dify 主要用 AAA。

## 2. 代码示例

### 2.1 标准 AAA 结构

```python
# 文件：test_user_service.py
from services.user_service import UserService


def test_create_user_success():
    # ===== Arrange =====
    email = "alice@example.com"
    password = "secret123"
    mock_db = MagicMock()

    # ===== Act =====
    user = UserService.create(session=mock_db, email=email, password=password)

    # ===== Assert =====
    assert user.email == email
    mock_db.add.assert_called_once()
```

### 2.2 反例：混乱的测试

```python
# ❌ 错误：没有分段、Act 多行、断言散落
def test_user():
    user1 = UserService.create("a@x.com", "pwd")
    assert user1 is not None
    UserService.delete(user1.id)
    user2 = UserService.create("b@x.com", "pwd2")
    mock_db.commit.assert_called()
    assert user2.email == "b@x.com"
    # Act/Assert 混杂，无法一眼看出测的是什么
```

```python
# ✅ 正确：拆分成两个独立测试
def test_create_user_a():
    # Arrange
    email = "a@x.com"
    # Act
    user = UserService.create(session=mock_db, email=email, password="pwd")
    # Assert
    assert user is not None

def test_create_user_b():
    # Arrange
    email = "b@x.com"
    # Act
    user = UserService.create(session=mock_db, email=email, password="pwd2")
    # Assert
    assert user.email == email
```

### 2.3 异常测试的 AAA

```python
def test_create_user_duplicate_email_raises():
    # ===== Arrange =====
    existing_user = User(email="alice@example.com")
    mock_db.query.return_value.filter_by.return_value.first.return_value = existing_user

    # ===== Act & Assert =====
    # 当 Act 和 Assert 紧密耦合时（如断言异常），可以合并
    with pytest.raises(DuplicateEmailError):
        UserService.create(session=mock_db, email="alice@example.com", password="x")
```

## 3. dify 仓库源码解读

### 3.1 dify 测试中的 AAA 典范

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`
**核心代码**（行 54-74）：

```python
def test_get_request_success(self, mock_httpx_request, mock_billing_config):
    """Test successful GET request."""
    # Arrange
    expected_response = {"result": "success", "data": {"info": "test"}}
    mock_response = MagicMock()
    mock_response.status_code = httpx.codes.OK
    mock_response.json.return_value = expected_response
    mock_httpx_request.return_value = mock_response

    # Act
    result = BillingService._send_request("GET", "/test", params={"key": "value"})

    # Assert
    assert result == expected_response
    mock_httpx_request.assert_called_once()
    call_args = mock_httpx_request.call_args
    assert call_args[0][0] == "GET"
    assert call_args[0][1] == "https://billing-api.example.com/test"
    assert call_args[1]["params"] == {"key": "value"}
    assert call_args[1]["headers"]["Billing-Api-Secret-Key"] == "test-secret-key"
    assert call_args[1]["headers"]["Content-Type"] == "application/json"
```

**解读**：
- 第 56-62 行（Arrange）：用 `MagicMock` 构造 mock 对象，`patch` 替换底层 httpx 调用
- 第 65 行（Act）：**只有一行**，调用被测方法
- 第 68-74 行（Assert）：不仅验证返回值，还验证 mock 的调用参数
- **关键设计**：Arrange 用 fixture（`mock_httpx_request` / `mock_billing_config`）提取公共设置，让每个测试方法的 AAA 更聚焦

### 3.2 用 fixture 提升 AAA 的复用性

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
- 把"准备 mock"放进 fixture，测试方法本身的 Arrange 段只剩下"测试数据"
- 这种"Arrange in fixture + Assert in test"模式让测试更像"声明意图"
- **整体设计意图**：dify 的 service 测试追求**一个测试方法只测一件事**，AAA 各段都极简

## 4. 关键要点总结

- AAA 三段：**Arrange（准备）→ Act（执行一行）→ Assert（验证）**
- Act 段应只有一行，复杂逻辑说明需要拆分测试
- 用 fixture 提取重复的 Arrange 代码
- 异常测试可以把 Act & Assert 合并（用 `with pytest.raises`）
- dify 测试默认采用 AAA，并通过 fixture 让结构更清晰

## 5. 练习题

### 练习 1：基础（必做）

把下面这个没有 AAA 结构的测试改写成标准 AAA 格式：

```python
def test_x():
    UserService.delete("u1")
    u = UserService.create("test@x.com", "pwd")
    assert u.id == 99
    UserService.delete(u.id)
```

### 练习 2：进阶

阅读 `api/tests/unit_tests/services/test_billing_service.py` 的 `test_get_request_non_200_status_code`（约第 93-107 行），找出它的 Arrange / Act / Assert 分段，并解释为什么这里可以没有 Act 行。

### 练习 3：挑战（选做）

为 `api/services/billing_service.py` 写一个新方法 `validate_email(email: str) -> bool`（要求：邮箱格式正确返回 True，否则 False），先写 3 个 AAA 测试用例，再实现方法。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`（AAA 范例）
- `/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`（fixture 设计）
- xUnit Test Patterns（Meszaros 2007）—— AAA 概念起源

---

**文档版本**：v1.0
**最后更新**：2026-07-13