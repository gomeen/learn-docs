# 10 dify 的测试目录结构与规范

> 全面了解 dify 后端的测试目录布局、命名规范和组织原则。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟悉 dify 后端的 `api/tests/` 目录结构
- 理解 dify 测试的命名和组织规范
- 能在 dify 中找到对应模块的测试位置
- 应用：能在 dify 中新增符合规范的测试文件

## 📚 前置知识

- ../../_common/18-testing/01-testing-pyramid.md
- 09-testing/01-pytest-basics.md
- 02-backend/01-ddd-layout.md

## 1. 核心概念

### 1.1 dify 测试目录总览

```
api/tests/
├── conftest.py                          # 全局 fixture（绑 workflow file runtime）
├── pytest_dify.py                       # Docker 中间件管理工具（Compose 详见 [Docker Compose](../../_common/09-containerization/04-compose.md)）
├── workflow_test_utils.py               # 工作流测试工具
├── unit_tests/                          # 单元测试（默认 make test 跑）
│   ├── conftest.py                      # 单元测试 fixture（Redis mock、SQLite）
│   ├── commands/                        # CLI 命令测试
│   ├── controllers/                     # Controller 测试（需要 Flask app）
│   ├── core/                            # core/ 业务逻辑测试
│   ├── extensions/                      # extensions/ 测试
│   ├── services/                        # services/ 测试
│   └── tools/ utils/ fields/ ...         # 工具类测试
├── integration_tests/                   # 集成测试（需要 Docker middleware）
│   ├── conftest.py                      # 真实账号、tenant、JWT（详见 [JWT](../../_common/07-authentication/03-jwt.md)）
│   ├── workflow/                        # 工作流集成测试
│   └── ...
└── test_containers_integration_tests/   # testcontainers 动态容器测试
```

### 1.2 测试目录与源码目录的镜像

dify 测试目录**镜像源码目录**结构：

| 源码路径 | 测试路径 |
|----------|----------|
| `api/services/billing_service.py` | `api/tests/unit_tests/services/test_billing_service.py` |
| `api/core/rag/embedding/embedding_base.py` | `api/tests/unit_tests/core/rag/embedding/test_embedding_base.py` |
| `api/controllers/console/...` | `api/tests/unit_tests/controllers/console/...` |
| `api/commands/upgrade_db.py` | `api/tests/unit_tests/commands/test_upgrade_db.py` |

这种"镜像布局"让找测试 = 找源码 + 替换目录前缀。

### 1.3 dify 测试命名规范

| 元素 | 命名规则 | 示例 |
|------|----------|------|
| 测试文件 | `test_{source_file}.py` | `test_billing_service.py` |
| 测试类 | `Test{ClassName}` | `TestBillingService` |
| 测试方法 | `test_{method_name}_{scenario}` | `test_get_request_success` |
| fixture | `mock_{dependency}` 或 `{entity}_{scope}` | `mock_httpx_request` |

## 2. 代码示例

### 2.1 镜像目录示例

```
api/
├── services/
│   └── billing_service.py
├── controllers/
│   └── console/
│       └── workspace/
│           └── billing.py
└── core/
    └── rag/
        └── embedding/
            └── embedding_base.py

api/tests/
├── unit_tests/
│   ├── services/
│   │   └── test_billing_service.py        # 测 billing_service.py
│   ├── controllers/
│   │   └── console/
│   │       └── workspace/
│   │           └── test_billing.py        # 测 billing.py
│   └── core/
│       └── rag/
│           └── embedding/
│               └── test_embedding_base.py  # 测 embedding_base.py
```

### 2.2 命名规范示例

```python
# 文件：test_billing_service.py

# 测试类：Test + 被测类名
class TestBillingServiceSendRequest:
    pass

class TestBillingServiceGetSubscription:
    pass

# 测试方法：test_ + 被测方法名 + _ + 场景
def test_get_request_success(self):
    pass

def test_get_request_raises_on_500(self):
    pass

def test_get_request_with_params(self):
    pass

# fixture：mock_ + 被 mock 的对象
@pytest.fixture
def mock_httpx_request(self):
    pass

@pytest.fixture
def mock_db_session(self):
    pass
```

## 3. 关键要点总结

- dify 测试目录**镜像源码目录**：`api/services/foo.py` → `api/tests/unit_tests/services/test_foo.py`
- 三层 conftest：根（CLI 选项）→ tests/（跨层 fixture）→ unit_tests/（单元测试专属）
- `make test` 默认跑单元测试，controller 测试单独跑
- 命名规范：`test_{file}.py`、`Test{Class}`、`test_{method}_{scenario}`
- 顶层测试文件（`test_makefile_backend_tests.py`）用于跨模块验证

---

**文档版本**：v1.0
**最后更新**：2026-07-13
