# 11 集成测试：数据库与外部服务

> 理解集成测试的目标和挑战，能在 dify 中编写依赖真实数据库的集成测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解集成测试与单元测试的本质区别
- 掌握集成测试中数据库和外部服务的处理方式
- 能用 session 级 fixture 复用昂贵资源
- 应用：能为 dify 的新模块编写集成测试

## 📚 前置知识

- 09-testing/01-testing-pyramid.md
- 09-testing/06-pytest-fixture.md
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

## 3. dify 仓库源码解读

### 3.1 dify 的集成测试入口

**文件位置**：`/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`
**核心代码**（行 55-67）：

```python
_SIO_APP, _CACHED_APP = create_app()


@pytest.fixture(scope="session")
def dify_config() -> DifyConfig:
    config = DifyConfig()  # type: ignore
    return config


@pytest.fixture
def flask_app() -> Flask:
    return _CACHED_APP
```

**解读**：
- 第 55 行：在 conftest 加载时就调用 `create_app()` 启动 Flask app，整个 pytest 会话期间复用
- 第 59 行：`scope="session"` —— 整个测试会话只读一次配置
- 第 64 行：`flask_app` 用 function 作用域（默认），但返回的 `_CACHED_APP` 是同一份
- **设计意图**：通过 `_CACHED_APP` 全局变量 + session 级 fixture，让集成测试启动一次 Flask，复用于所有测试

### 3.2 dify 的测试账号 fixture

**文件位置**：`/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`
**核心代码**（行 69-101）：

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

    # Teardown
    with _CACHED_APP.test_request_context():
        db.session.execute(delete(DifySetup))
        db.session.execute(delete(TenantAccountJoin))
        db.session.execute(delete(Account))
        db.session.execute(delete(Tenant))
        db.session.commit()
```

**解读**：
- 第 78 行：用随机后缀生成测试账号，避免冲突
- 第 81-88 行：调用真正的 `RegisterService.setup()` 走完注册流程
- 第 90-92 行：从数据库查回账号并 yield
- 第 96-101 行：测试结束后清理 `DifySetup` / `TenantAccountJoin` / `Account` / `Tenant` 四张表
- **设计意图**：用真实注册流程准备测试数据，确保账号状态真实有效；teardown 严格清理保证测试可重复运行

### 3.3 dify 的 test_client fixture

**文件位置**：`/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`
**核心代码**（行 116-119）：

```python
@pytest.fixture
def test_client() -> Generator[FlaskClient, None, None]:
    with _CACHED_APP.test_client() as client:
        yield client
```

**解读**：
- `Flask.test_client()` 返回一个可以在内存中模拟 HTTP 请求的客户端
- 这是 Flask 的官方集成测试工具，**不经过真正的 HTTP socket**
- 测试结束后 `with` 自动关闭 client

## 4. 关键要点总结

- 集成测试关注**模块协作**，需要真实数据库和外部服务
- session 级 fixture 复用昂贵资源（Flask app、配置、测试账号）
- 测试结束后**严格清理数据库**，保证可重复运行
- `Flask.test_client()` 提供内存 HTTP 模拟，不走真实 socket
- dify 的 `integration_tests/` 必须先启动 Docker middleware

## 5. 练习题

### 练习 1：基础（必做）

阅读 `api/tests/integration_tests/conftest.py` 的 `_load_env()` 函数（行 27-49），理解 dify 如何加载测试环境变量，回答：为什么这里用 `override=True`？

### 练习 2：进阶

为 `services/user_service.py` 写一个集成测试 `test_user_signup_creates_account_and_tenant`，要求：
- 使用 `setup_account` fixture 或自己创建账号
- 验证账号创建后自动创建 tenant
- 测试结束后清理

### 练习 3：挑战（选做）

阅读 `api/tests/integration_tests/services/test_workflow_draft_variable_service.py`，理解 dify 的 service 集成测试如何用真实数据库验证 Workflow 草稿变量，找出它使用的 fixture 链。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/integration_tests/conftest.py`（集成测试 fixture）
- `/Users/xu/code/github/dify/api/tests/integration_tests/workflow/test_sync_workflow.py`（集成测试范例）
- Flask 测试文档：https://flask.palletsprojects.com/en/stable/testing/

---

**文档版本**：v1.0
**最后更新**：2026-07-13