# 06 pytest Fixture：`@pytest.fixture` 与作用域

> 掌握 pytest fixture 的定义、作用域与复用，能在 dify 测试中用 fixture 隔离副作用。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@pytest.fixture` 的基本用法和参数化
- 理解 fixture 的 4 种作用域（function / class / module / session）
- 知道 fixture 的 `autouse`、`yield` 清理机制
- 应用：能在 dify 测试中编写自定义 fixture 隔离副作用

## 📚 前置知识

- 09-testing/05-pytest-basics.md
- Python 装饰器、上下文管理器

## 1. 核心概念

### 1.1 Fixture 是什么

**Fixture** 是 pytest 用于**准备和清理测试资源**的机制。它通过 `@pytest.fixture` 装饰器定义，通过**同名参数**自动注入到测试函数。

```python
@pytest.fixture
def sample_data():
    return {"name": "alice", "age": 30}

def test_user(sample_data):  # pytest 自动注入
    assert sample_data["name"] == "alice"
```

### 1.2 Fixture 的 4 种作用域

| 作用域 | 范围 | 适用场景 |
|--------|------|----------|
| `function`（默认） | 每个测试函数执行一次 | 大多数情况 |
| `class` | 每个测试类执行一次 | 跨测试共享但只与该类相关 |
| `module` | 每个 .py 文件执行一次 | 文件内共享 |
| `session` | 整个 pytest 运行执行一次 | 昂贵资源（如数据库连接池） |

```python
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("postgresql://...")
    yield engine
    engine.dispose()  # 测试结束后清理
```

### 1.3 Fixture 的清理机制

用 `yield` 而不是 `return`，yield 之后的代码在测试**结束后**执行：

```python
@pytest.fixture
def temp_file():
    f = open("/tmp/test.txt", "w")
    yield f          # 测试开始
    f.close()        # 测试结束（即使失败也执行）
```

等价于 unittest 的 `setUp` / `tearDown`，但更灵活。

## 2. 代码示例

### 2.1 基础 fixture

```python
import pytest

@pytest.fixture
def user():
    """准备一个测试用户。"""
    return {"id": 1, "name": "alice", "email": "alice@x.com"}

def test_user_name(user):
    assert user["name"] == "alice"

def test_user_email(user):
    assert user["email"] == "alice@x.com"
```

### 2.2 带清理的 fixture（yield）

```python
@pytest.fixture
def temp_database():
    """创建临时 SQLite 数据库，测试结束自动清理。"""
    import sqlite3
    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)

    yield conn  # 把连接交给测试

    # 测试结束后的清理
    conn.close()
    os.unlink(path)

def test_insert_user(temp_database):
    temp_database.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    temp_database.execute("INSERT INTO users VALUES (1, 'alice')")
    cursor = temp_database.execute("SELECT name FROM users WHERE id = 1")
    assert cursor.fetchone()[0] == "alice"
```

### 2.3 autouse fixture（自动应用）

```python
@pytest.fixture(autouse=True)
def reset_settings():
    """每个测试前自动重置配置。"""
    print("\n[setup] reset settings")
    yield
    print("[teardown] cleanup")

def test_x():
    print("test x")
    # reset_settings 自动执行，无需在参数中声明

def test_y():
    print("test y")
```

### 2.4 fixture 嵌套（依赖其他 fixture）

```python
@pytest.fixture
def db():
    return {"conn": "fake_db"}

@pytest.fixture
def user_repo(db):  # 依赖 db fixture
    from services.user_repo import UserRepo
    return UserRepo(connection=db["conn"])

def test_find_user(user_repo):
    user = user_repo.find_by_email("alice@x.com")
    assert user is not None
```

## 3. dify 仓库源码解读

### 3.1 dify 的 session 级 fixture

**文件位置**：`/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`
**核心代码**（行 58-66）：

```python
@pytest.fixture(scope="session")
def dify_config() -> DifyConfig:
    config = DifyConfig()  # type: ignore
    return config


@pytest.fixture
def flask_app() -> Flask:
    return _CACHED_APP
```

**解读**：
- 第 58 行：`scope="session"` 表示整个 pytest 运行期间只创建一次 `DifyConfig`
- 第 64 行：`flask_app` 用默认的 function 作用域，每个测试函数拿到的 Flask app 是同一份（`_CACHED_APP`）但隔离清晰
- **设计意图**：昂贵的资源（Flask app、配置对象）用 session 级 fixture 复用，避免每次测试都重新构造

### 3.2 dify 的 setup_account fixture

**文件位置**：`/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`
**核心代码**（行 70-101）：

```python
@pytest.fixture(scope="session")
def setup_account(request) -> Generator[Account, None, None]:
    """`dify_setup` completes the setup process for the Dify application.

    It creates `Account` and `Tenant`, and inserts a `DifySetup` record into the database.

    Most tests in the `controllers` package may require dify has been successfully setup.
    """
    with _CACHED_APP.test_request_context():
        rand_suffix = random.randint(int(1e6), int(1e7))  # noqa
        name = f"test-user-{rand_suffix}"
        email = f"{name}@example.com"
        RegisterService.setup(
            email=email,
            name=name,
            password=secrets.token_hex(16),
            ip_address="localhost",
            language="en-US",
            session=db.session(),
        )

    with _CACHED_APP.test_request_context():
        with Session(bind=db.engine, expire_on_commit=False) as session:
            account = session.scalars(select(Account).filter_by(email=email)).one()

    yield account

    # teardown：清理数据库
    with _CACHED_APP.test_request_context():
        db.session.execute(delete(DifySetup))
        db.session.execute(delete(TenantAccountJoin))
        db.session.execute(delete(Account))
        db.session.execute(delete(Tenant))
        db.session.commit()
```

**解读**：
- 第 70 行：`scope="session"` —— 整个测试会话只创建一个测试账号，避免每个测试都重复 register
- 第 81-88 行：用 `RegisterService.setup` 真正走一遍注册流程（端到端）
- 第 96-101 行：测试结束后用 `delete()` SQL 清理数据，保证测试可重复运行
- **关键设计**：session 级 fixture + teardown 是 dify 集成测试的核心模式

### 3.3 dify 的 autouse fixture 隔离副作用

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`
**核心代码**（行 99-110）：

```python
@pytest.fixture(autouse=True)
def reset_secret_key():
    """Ensure SECRET_KEY-dependent logic sees an empty config value by default."""

    from configs import dify_config

    original = dify_config.SECRET_KEY
    dify_config.SECRET_KEY = ""
    try:
        yield
    finally:
        dify_config.SECRET_KEY = original
```

**解读**：
- `autouse=True` 让 fixture 自动对所有单元测试生效，无需在测试函数签名中声明
- `try/finally` 保证即使测试失败也能恢复 `SECRET_KEY`
- **设计意图**：单元测试应该完全无副作用，`autouse` fixture 是隔离全局配置的利器

## 4. 关键要点总结

- Fixture 是 pytest 替代 `setUp/tearDown` 的更优雅方式
- 4 种作用域：function / class / module / session，按"昂贵程度"递增
- 用 `yield` 替代 `return`，实现自动清理
- `autouse=True` 让 fixture 自动对所有测试生效
- dify 用 session 级 fixture 复用 Flask app 和测试账号，用 autouse 隔离全局配置

## 5. 练习题

### 练习 1：基础（必做）

写一个 `temp_directory` fixture，自动创建临时目录，测试结束后删除。要求：
- 用 `tempfile.mkdtemp()` 创建目录
- 用 `yield` 暴露目录路径
- 用 `shutil.rmtree()` 清理

### 练习 2：进阶

阅读 `api/tests/unit_tests/conftest.py` 第 113-128 行，理解 `_unit_test_engine`（session 级）和 `sqlite_engine`（function 级）的区别，并回答：为什么 dify 在单元测试中要创建内存 SQLite 而不是用真实数据库？

### 练习 3：挑战（选做）

为 `services/user_service.py` 写一个 `mock_user_db` fixture，使其返回 3 个预置用户，并在测试结束后清理。fixture 应支持 `autouse=True` 模式。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`（autouse fixture 范例）
- `/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`（session 级 fixture）
- pytest fixture 官方文档：https://docs.pytest.org/en/stable/fixture.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13