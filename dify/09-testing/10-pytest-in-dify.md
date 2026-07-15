# 10 dify 的测试目录结构与规范

> 全面了解 dify 后端的测试目录布局、命名规范和组织原则。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟悉 dify 后端的 `api/tests/` 目录结构
- 理解 dify 测试的命名和组织规范
- 能在 dify 中找到对应模块的测试位置
- 应用：能在 dify 中新增符合规范的测试文件

## 📚 前置知识

- 09-testing/01-testing-pyramid.md
- 09-testing/05-pytest-basics.md
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

## 3. dify 仓库源码解读

### 3.1 dify 的测试目录结构（详细）

**文件位置**：`/Users/xu/code/github/dify/api/tests/`

```python
# unit_tests/ 子目录镜像 api/ 的源码结构
api/tests/unit_tests/
├── commands/                          # 测 api/commands/
├── controllers/                       # 测 api/controllers/
├── core/                              # 测 api/core/
├── enterprise/                        # 测 api/enterprise/
├── enums/                             # 测 api/enums/
├── events/                            # 测 api/events/
├── extensions/                        # 测 api/extensions/
├── factories/                         # 测 api/factories/
├── fields/                            # 测 api/fields/
├── libs/                              # 测 api/libs/
├── migrations/                        # 测 api/migrations/
├── models/                            # 测 api/models/
├── oss/                               # 测 api/oss/
├── repositories/                      # 测 api/repositories/
├── services/                          # 测 api/services/
├── tasks/                             # 测 api/tasks/
├── tools/                             # 测 api/tools/
├── utils/                             # 测 api/utils/
├── test_makefile_backend_tests.py     # 顶层测试：Makefile 引用一致性
└── test_pytest_dify.py                # 顶层测试：Docker 中间件管理
```

**解读**：
- **镜像布局**：`unit_tests/<module>/test_<file>.py` 一一对应 `api/<module>/<file>.py`
- **顶层测试**：`test_makefile_backend_tests.py` 和 `test_pytest_dify.py` 是跨模块的全局测试
- **缺失的子目录**：如果 `api/commands/` 没有对应的 `unit_tests/commands/`，意味着该模块没有单元测试

### 3.2 dify 的 conftest.py 分层

**文件位置**：`/Users/xu/code/github/dify/api/conftest.py` 和 `api/tests/conftest.py` 和 `api/tests/unit_tests/conftest.py`

```python
# 文件：api/conftest.py（根 conftest）
"""Global pytest hooks for Dify backend tests."""
from tests.pytest_dify import (
    DEFAULT_MIDDLEWARE_SERVICES,
    DEFAULT_VDB_SERVICES,
    DockerComposeStack,
    build_middleware_stack,
    build_vdb_stack,
    ensure_backend_test_environment,
    ensure_compose_env_files,
    parse_services,
)

def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --start-middleware / --start-vdb CLI options."""
    ...

# 文件：api/tests/conftest.py（tests 层 conftest）
import pytest
from core.app.workflow.file_runtime import bind_dify_workflow_file_runtime

@pytest.fixture(autouse=True)
def _bind_workflow_file_runtime() -> None:
    bind_dify_workflow_file_runtime()

# 文件：api/tests/unit_tests/conftest.py（unit_tests 层 conftest）
# 提供 Redis mock、SQLite engine、App context 等
```

**解读**：
- **三层 conftest**：根 `api/conftest.py` 定义 CLI 选项；`tests/conftest.py` 提供跨所有测试的 fixture；`unit_tests/conftest.py` 提供单元测试专属 fixture
- **就近原则**：越靠近测试代码的 conftest 越具体
- pytest 自动按目录层级加载所有 conftest.py（从根到测试文件）

### 3.3 dify 的 Makefile 测试入口

**文件位置**：`/Users/xu/code/github/dify/Makefile`
**核心代码**（行 92-110）：

```makefile
test:
	@echo "🧪 Running backend unit tests..."
	@if [ -n "$(TARGET_TESTS)" ]; then \
		echo "Target: $(TARGET_TESTS)"; \
		uv run --project api --dev pytest $(TARGET_TESTS); \
	else \
		echo "Running backend unit tests"; \
		uv run --project api --dev pytest -p no:benchmark --timeout "$${PYTEST_TIMEOUT:-20}" -n auto \
			api/tests/unit_tests \
			api/providers/vdb/*/tests/unit_tests \
			api/providers/trace/*/tests/unit_tests \
			--ignore=api/tests/unit_tests/controllers; \
		uv run --project api --dev pytest --timeout "$${PYTEST_TIMEOUT:-20}" --cov-append \
			api/tests/unit_tests/controllers; \
	fi
	@echo "✅ Unit tests complete"
```

**解读**：
- 第 92 行：`make test` 入口
- 第 95-97 行：如果指定了 `TARGET_TESTS=path/to/test_file.py`，只跑指定测试
- 第 100-104 行：默认跑 `unit_tests` + `vdb/*/tests/unit_tests` + `trace/*/tests/unit_tests`
- 第 105 行：`--ignore=...controllers` 把 controller 测试排除（它们注册 Flask 路由，与 xdist 冲突）
- 第 106-107 行：**单独**再跑 controller 测试（不加 `-n auto`）
- **设计意图**：通过分层执行避免 xdist 的副作用

## 4. 关键要点总结

- dify 测试目录**镜像源码目录**：`api/services/foo.py` → `api/tests/unit_tests/services/test_foo.py`
- 三层 conftest：根（CLI 选项）→ tests/（跨层 fixture）→ unit_tests/（单元测试专属）
- `make test` 默认跑单元测试，controller 测试单独跑
- 命名规范：`test_{file}.py`、`Test{Class}`、`test_{method}_{scenario}`
- 顶层测试文件（`test_makefile_backend_tests.py`）用于跨模块验证

## 5. 练习题

### 练习 1：基础（必做）

在 `api/tests/unit_tests/services/` 下找一个测试文件，对照 `api/services/` 下的同名源文件，理解镜像布局。

### 练习 2：进阶

阅读 `api/tests/unit_tests/conftest.py` 的完整内容，列出所有的 `autouse=True` fixture，并解释它们各自的作用。

### 练习 3：挑战（选做）

阅读 `api/tests/unit_tests/test_makefile_backend_tests.py`，理解它如何验证 Makefile 的一致性，并尝试为 `api/services/` 下新建的 `agent_service.py` 写一个类似的"Makefile 验证测试"。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tests/`（测试目录）
- `/Users/xu/code/github/dify/api/conftest.py`（根 conftest）
- `/Users/xu/code/github/dify/Makefile`（`make test` 入口）
- `/Users/xu/code/github/dify/api/AGENTS.md`（dify 后端开发规范）

---

**文档版本**：v1.0
**最后更新**：2026-07-13