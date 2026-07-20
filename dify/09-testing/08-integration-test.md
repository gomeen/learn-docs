# 11 集成测试：数据库与外部服务

> 理解集成测试的目标和挑战，能在 dify 中编写依赖真实数据库的集成测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解集成测试与单元测试的本质区别
- 掌握集成测试中数据库和外部服务的处理方式
- 能用 session 级 fixture 复用昂贵资源
- 应用：能为 dify 的新模块编写集成测试

## 📚 前置知识

- ../../_common/18-testing/01-testing-pyramid.md
- 09-testing/02-pytest-fixture.md
- 02-backend/04-repository.md

## 1. 核心概念

### 1.1 集成测试的目标

集成测试关注**模块之间的协作**，验证：
- 多个 service 一起工作时是否正确
- 数据库操作是否符合预期
- 外部 API 调用是否正确组装请求

**与单元测试的区别**：

| 维度 | 单元测试 | 集成测试 |
|------|----------|----------|
| 范围 | 单个函数/类 | 多个模块协作 |
| 外部依赖 | 用 mock 替换 | 真实数据库/服务 |
| 速度 | < 100ms | 100ms - 数秒 |
| 失败定位 | 精确（具体函数） | 中等（模块边界） |

### 1.2 集成测试的常见挑战

- **数据库准备**：每次测试前要建表、插入测试数据
- **测试隔离**：测试之间不能互相影响
- **环境依赖**：CI 需要启动 PostgreSQL、Redis 等
- **速度**：真实 I/O 比 mock 慢得多

### 1.3 dify 的集成测试策略

dify 通过**显式分层**解决这些挑战：
- `integration_tests/`：需要 Docker middleware（PG、Redis；容器编排详见 [Docker Compose](../../_common/09-containerization/04-compose.md)）
- `test_containers_integration_tests/`：用 testcontainers 动态启动
- `unit_tests/`：不依赖任何外部服务（默认跑）

## 2. 代码示例

### 2.1 简单集成测试示例

```python
# 文件：test_user_repo_integration.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Base
from repositories.user_repo import UserRepository


@pytest.fixture(scope="module")
def engine():
    """模块级共享的 SQLite 引擎。"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """每个测试一个干净 session。"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_create_and_find_user(session):
    # Arrange & Act
    repo = UserRepository(session)
    user = repo.create(email="alice@x.com", name="alice")
    found = repo.find_by_email("alice@x.com")

    # Assert
    assert found.id == user.id
    assert found.email == "alice@x.com"
```

### 2.2 跨多个 service 的集成测试

```python
def test_user_signup_creates_tenant(session):
    """集成测试：UserService + TenantService 一起工作。"""
    from services.user_service import UserService
    from services.tenant_service import TenantService

    # Arrange
    email = "bob@x.com"
    password = "secret"

    # Act
    user = UserService.create(session=session, email=email, password=password)
    tenant = TenantService.create_for_user(session=session, user=user)

    # Assert
    assert tenant.owner_id == user.id
    assert tenant.name == user.name + "'s workspace"
```

### 2.3 用真实 Redis（不用 mock）

```python
def test_redis_cache_set_get(redis_client):
    """集成测试：真实 Redis。"""
    redis_client.set("key", "value", ex=10)
    assert redis_client.get("key") == "value"
```

## 3. 关键要点总结

- 集成测试关注**模块协作**，需要真实数据库和外部服务
- session 级 fixture 复用昂贵资源（Flask app、配置、测试账号）
- 测试结束后**严格清理数据库**，保证可重复运行
- `Flask.test_client()` 提供内存 HTTP 模拟，不走真实 socket
- dify 的 `integration_tests/` 必须先启动 Docker middleware

---

**文档版本**：v1.0
**最后更新**：2026-07-13
