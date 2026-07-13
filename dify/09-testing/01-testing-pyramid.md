# 01 测试金字塔：单元 / 集成 / E2E

> 理解测试分层思想，能根据 dify 的测试目录结构判断测试类型。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解测试金字塔的三层结构及其权衡
- 区分单元测试、集成测试、E2E 测试的适用场景
- 能根据 `api/tests/` 目录结构识别 dify 的测试类型
- 应用：能看懂 dify 后端测试的分层策略与执行优先级

## 📚 前置知识

- Python 基础语法
- 了解 Web 应用的基本架构
- 01-fundamentals/02-typeddict.md

## 1. 核心概念

### 1.1 什么是测试金字塔

测试金字塔（Test Pyramid）是 Mike Cohn 提出的分层测试模型。它把测试按 **粒度从细到粗**、**执行速度从快到慢**、**覆盖范围从窄到广** 分成三层：

```
        /\
       /  \        E2E（端到端测试）
      /----\       - 慢、脆弱、贴近用户
     /      \
    /--------\     集成测试
   /          \    - 中等速度，测试模块协作
  /------------\
 /              \  单元测试
/________________\ - 快速、精确、覆盖率高
```

**关键原则**：
- **越往下越多**：单元测试数量应远大于集成测试，集成测试远大于 E2E
- **越往下越快**：单元测试毫秒级，E2E 可能需要几秒甚至几分钟
- **越往下越稳定**：单元测试不应依赖外部服务

### 1.2 三层测试对比

| 维度 | 单元测试 | 集成测试 | E2E 测试 |
|------|----------|----------|----------|
| 测试对象 | 单个函数/类 | 多个模块协作 | 完整用户流程 |
| 执行速度 | < 100ms | 100ms - 1s | 秒级 ~ 分钟级 |
| 是否需要数据库 | 否（用 mock） | 是（真实 DB） | 是 |
| 是否需要网络 | 否 | 部分（依赖外部） | 是 |
| 维护成本 | 低 | 中 | 高 |
| 反馈精确度 | 高（指出具体函数） | 中（指出模块） | 低（指出流程） |

### 1.3 倒金字塔反模式

一种常见的反模式是 **冰淇淋锥型**（Ice Cream Cone）：E2E 测试占比最大，单元测试很少。

```
   ___________
  /  E2E 多   \    ← 慢、脆弱、维护噩梦
 /------------\
/  集成测试少  \
|  单元测试极少 |    ← 反馈慢，难以定位 bug
```

dify 通过 `make test` 把单元测试和集成测试分离执行，避免了这个问题。

## 2. 代码示例

### 2.1 三层测试对比示例

```python
# 文件：example_pyramid.py

# ===== 1. 单元测试：测试纯函数 =====
def calculate_tax(price: float, rate: float) -> float:
    """纯函数：没有副作用，单元测试的最佳目标。"""
    return price * rate


def test_calculate_tax_unit():
    # 单元测试：直接调用，不依赖任何外部资源
    assert calculate_tax(100, 0.1) == 10.0
    assert calculate_tax(0, 0.1) == 0.0


# ===== 2. 集成测试：测试数据库交互 =====
def test_user_service_create_user(db_session):
    """集成测试：需要真实数据库 session。"""
    from services.user_service import UserService
    user = UserService.create(session=db_session, email="test@example.com")
    assert user.id is not None
    # 清理
    db_session.delete(user)
    db_session.commit()


# ===== 3. E2E 测试：测试完整 HTTP 流程 =====
def test_register_flow_e2e(test_client):
    """E2E 测试：模拟用户从浏览器发起的完整请求。"""
    response = test_client.post(
        "/api/register",
        json={"email": "new@example.com", "password": "secret123"},
    )
    assert response.status_code == 201
    assert "token" in response.json
```

### 2.2 单元测试的反例：依赖外部服务

```python
# ❌ 错误：单元测试不应该真正调用数据库
def test_user_count():
    # 这其实不是单元测试，而是集成测试！
    from models import User
    count = db.session.query(User).count()
    assert count > 0

# ✅ 正确：用 mock 替换数据库
def test_user_count_with_mock():
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    mock_session.query.return_value.count.return_value = 42
    count = mock_session.query(User).count()
    assert count == 42
```

## 3. dify 仓库源码解读

### 3.1 dify 测试目录结构

**文件位置**：`/Users/xu/code/github/dify/api/tests/`
**核心代码**（目录结构）：

```
api/tests/
├── conftest.py                          # 全局 fixture（绑定 workflow file runtime）
├── unit_tests/                          # 单元测试（不依赖真实外部服务）
│   ├── conftest.py                      # 单元测试 fixtures（mock Redis, sqlite, app context）
│   ├── commands/                        # CLI 命令测试
│   ├── controllers/                     # Controller 单元测试（需 Flask app）
│   ├── core/                            # 核心业务逻辑测试
│   └── services/                        # Service 层测试
├── integration_tests/                   # 集成测试（需要 Docker middleware）
│   ├── conftest.py                      # 集成测试 fixtures（真实账号、tenant、client）
│   └── workflow/                        # 工作流集成测试
└── test_containers_integration_tests/   # testcontainers 集成测试
```

**解读**：
- **第 1 层（unit_tests）**：默认 `make test` 跑这一层，使用 SQLite 内存数据库 + mock Redis，速度极快
- **第 2 层（integration_tests）**：需要先启动 Docker middleware（PostgreSQL、Redis），通过 `--start-middleware` 选项控制
- **第 3 层（test_containers_integration_tests）**：用 testcontainers 库动态启动容器，最贴近生产环境
- **设计意图**：dify 把测试分成 3 个目录，明确每层的依赖边界，避免单元测试意外触发外部服务调用

### 3.2 conftest.py 的三层差异化设计

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`
**核心代码**（行 80-110）：

```python
@pytest.fixture(autouse=True)
def reset_redis_mock():
    """reset the Redis mock before each test"""
    redis_mock.reset_mock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = None
    # ... 重置所有 mock 行为

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
- `reset_redis_mock` 是 `autouse=True` 的 fixture：**每个单元测试运行前**都会自动重置 Redis mock，保证测试之间互不干扰
- `reset_secret_key` 把 `SECRET_KEY` 暂时清空，避免单元测试意外依赖真实加密逻辑
- **整体设计意图**：单元测试应该"无外部依赖"——任何来自配置中心、缓存、加密的副作用都要在 fixture 层隔离掉

## 4. 关键要点总结

- 测试金字塔自下而上：**数量递减、速度递减、覆盖范围递增**
- 单元测试用 mock 隔离依赖，集成测试用真实 DB / 容器，E2E 跑完整 HTTP 流
- dify 通过 `unit_tests/`、`integration_tests/`、`test_containers_integration_tests/` 三个目录明确分层
- `make test` 默认只跑单元测试，需要 `--start-middleware` 才跑集成测试
- 单元测试的 `autouse=True` fixture 是隔离副作用的关键武器

## 5. 练习题

### 练习 1：基础（必做）

阅读 `api/tests/unit_tests/conftest.py`，列出所有 `autouse=True` 的 fixture，并说明每个 fixture 解决了什么副作用问题。

### 练习 2：进阶

打开 `api/tests/unit_tests/services/test_billing_service.py`，逐个判断里面的测试是单元测试还是集成测试，并说明依据（是否使用 mock、是否访问真实网络等）。

### 练习 3：挑战（选做）

设计一个新的 `services/agent_service.py` 模块，并为它规划至少 3 个单元测试 + 2 个集成测试用例，写出测试函数签名和测试意图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/`（测试目录结构）
- `/Users/xu/code/github/dify/api/tests/unit_tests/conftest.py`（单元测试 fixture）
- `/Users/xu/code/github/dify/Makefile`（`make test` / `make test-all`）
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`（CI 分层执行）
- Martin Fowler《Test Pyramid》：https://martinfowler.com/bliki/TestPyramid.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13