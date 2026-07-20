# 12 测试数据库：事务回滚与 fixture

> 掌握测试数据库的核心模式：事务回滚、夹具（fixture，详见 [pytest Fixture](./02-pytest-fixture.md)）复用、隔离策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握测试数据库的隔离策略（事务回滚 vs 重建数据库）
- 理解 dify 单元测试为何用内存 SQLite 而非真实 PostgreSQL
- 能在 dify 测试中为不同模块选择合适的数据库策略
- 应用：能在 dify 的 service 测试中使用 `_unit_test_engine` fixture

## 📚 前置知识

- 09-testing/02-pytest-fixture.md
- 09-testing/08-integration-test.md
- 02-backend/04-repository.md

## 1. 核心概念

### 1.1 测试数据库的 3 种策略

| 策略 | 速度 | 隔离性 | 适用场景 |
|------|------|--------|----------|
| **事务回滚** | 最快 | 中（同一连接） | 单元测试、CI 集成测试 |
| **重建数据库** | 慢 | 高 | 跨连接测试 |
| **独立 Schema/Database** | 中 | 高 | 并行测试 |

### 1.2 事务回滚模式

```python
@pytest.fixture
def db_session(engine):
    """用事务包裹每个测试，测试结束后回滚。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()  # 测试产生的修改全部撤销
    connection.close()
```

**优点**：
- 每个测试结束后自动清理，无需手动 `delete`
- 比 truncate/drop 快 10-100 倍

**缺点**：
- 不能测试**跨连接事务**行为（如 Celery 任务）
- 不能测试 `COMMIT` 后的真实持久化

### 1.3 dify 的内存 SQLite 策略

dify 单元测试使用 `sqlite:///:memory:` 内存数据库：

```python
@pytest.fixture(scope="session")
def _unit_test_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()
```

**为什么用 SQLite？**
- **零配置**：不需要启动 PostgreSQL 容器
- **极快**：内存操作，比真实 DB 快一个数量级
- **SQL 兼容性**：大多数 ORM 操作 SQLite 都支持
- **session 级**：整个 pytest 运行期间只创建一次引擎

## 2. 代码示例

### 2.1 事务回滚模式

```python
# 文件：test_with_rollback.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("postgresql://test:test@localhost/test_db")
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Session:
    """事务回滚 fixture。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()  # 所有修改撤销
    connection.close()


def test_create_user(db_session):
    from models import User
    user = User(email="test@x.com", name="alice")
    db_session.add(user)
    db_session.commit()

    found = db_session.query(User).filter_by(email="test@x.com").first()
    assert found is not None
    # 测试结束后 rollback，user 不再存在
```

### 2.2 每个测试重建数据库

```python
@pytest.fixture
def fresh_db():
    """每个测试都重建数据库（慢但完全隔离）。"""
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
```

### 2.3 用内存 SQLite 跑 SQLAlchemy 测试

```python
@pytest.fixture
def sqlite_session(request, sqlite_engine):
    """动态建表，根据 param 传入的 models 创建对应表。"""
    models = request.param
    tables = [m.metadata.tables[m.__tablename__] for m in models]
    TypeBase.metadata.create_all(sqlite_engine, tables=tables)
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
```

## 3. 关键要点总结

- 测试数据库的三大策略：事务回滚（最快）、重建（最慢但最安全）、独立 Schema
- dify 单元测试用 `sqlite:///:memory:` 内存数据库，session 级复用
- `sqlite_session` fixture 通过 `request.param` 按需建表，避免创建全部模型
- autouse fixture 全局替换 `session_factory`，让任何测试代码自动使用 SQLite
- 集成测试用真实 PostgreSQL（通过 Docker），单元测试用内存 SQLite，分层清晰

---

**文档版本**：v1.0
**最后更新**：2026-07-13
