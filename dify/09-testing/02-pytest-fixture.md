# 06 pytest Fixture：`@pytest.fixture` 与作用域

> 掌握 pytest fixture 的定义、作用域与复用，能在 dify 测试中用 fixture 隔离副作用。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@pytest.fixture` 的基本用法和参数化
- 理解 fixture 的 4 种作用域（function / class / module / session）
- 知道 fixture 的 `autouse`、`yield` 清理机制
- 应用：能在 dify 测试中编写自定义 fixture 隔离副作用

## 📚 前置知识

- 09-testing/01-pytest-basics.md
- Python 装饰器（详见 [装饰器](../01-fundamentals/11-decorator.md)）
- 上下文管理器（详见 [上下文管理器](../01-fundamentals/12-context-manager.md)）——fixture 的 `yield` 清理与之类似

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

## 3. 关键要点总结

- Fixture 是 pytest 替代 `setUp/tearDown` 的更优雅方式
- 4 种作用域：function / class / module / session，按"昂贵程度"递增
- 用 `yield` 替代 `return`，实现自动清理
- `autouse=True` 让 fixture 自动对所有测试生效
- dify 用 session 级 fixture 复用 Flask app 和测试账号，用 autouse 隔离全局配置

---

**文档版本**：v1.0
**最后更新**：2026-07-13
