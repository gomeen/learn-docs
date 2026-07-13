# 22 dify 的 lint / type-check / test 三件套

> 全面理解 dify 的质量保障三件套：`make test` / `make lint` / `make type-check`，掌握三者的协作与权衡。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 dify 三个核心质量命令的用法
- 理解三者在 CI 中的协作流程
- 能根据失败信息定位问题根源
- 应用：能独立完成 dify 的"提交前 + 提交后"质量门禁

## 📚 前置知识

- 09-testing/19-lint-tools.md
- 09-testing/20-type-check.md
- 09-testing/10-pytest-in-dify.md

## 1. 核心概念

### 1.1 dify 质量保障三件套

```
                ┌─────────────────┐
                │   git commit    │
                └────────┬────────┘
                         ↓
              ┌──────────────────────┐
              │   pre-commit hook    │
              │   (Ruff auto-fix)    │
              └──────────┬───────────┘
                         ↓
                ┌─────────────────┐
                │   git push       │
                └────────┬────────┘
                         ↓
       ┌─────────────────────────────────────┐
       │             CI Pipeline             │
       │                                     │
       │   1. make lint     ← 风格 / 错误    │
       │   2. make type-check ← 类型一致性   │
       │   3. make test      ← 行为正确性    │
       │                                     │
       └─────────────────────────────────────┘
                         ↓
                ┌─────────────────┐
                │   全部通过？     │
                │  ✓ 合并 PR      │
                │  ✗ 阻止合并     │
                └─────────────────┘
```

### 1.2 三个命令的层次关系

| 命令 | 检查内容 | 速度 | 严格度 | 失败代价 |
|------|----------|------|--------|----------|
| `make lint` | 风格、语法、潜在 bug | 快（秒级） | 中 | 低（可自动修复） |
| `make type-check` | 类型一致性 | 中（10秒级） | 高 | 中（需手动修复） |
| `make test` | 行为正确性 | 慢（分钟级） | 极高 | 高（需调试） |

### 1.3 三个命令的协作

```
                   ┌─────────────────┐
                   │  dev/reformat   │  ← 开发本地（自动修复）
                   └────────┬────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │                                       │
        │  提交前：pre-commit 自动跑 ruff        │
        │                                       │
        └───────────────────┬───────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │                                       │
        │  提交后：CI 跑 三件套                 │
        │                                       │
        │  lint → type-check → test             │
        │   ↓          ↓           ↓            │
        │  风格       类型        行为          │
        │                                       │
        └───────────────────────────────────────┘
```

## 2. 代码示例

### 2.1 本地开发的标准流程

```bash
# 1. 开发代码
$ vim api/services/billing_service.py

# 2. 本地自动修复 lint
$ dev/reformat
# 或者手动
$ uv run --project api --dev ruff format ./api
$ uv run --project api --dev ruff check --fix ./api

# 3. 运行测试
$ cd api && uv run --project api --dev pytest api/tests/unit_tests/services/test_billing_service.py -v

# 4. 类型检查
$ make type-check

# 5. 完整 lint 检查
$ make lint

# 6. 提交（pre-commit hook 自动触发）
$ git commit -m "feat: add billing refund"
```

### 2.2 CI 流程（伪代码）

```yaml
# CI 中按顺序执行
steps:
  - name: Lint
    run: make lint
    # 失败 → 直接拒绝，节省后续步骤时间

  - name: Type Check
    run: make type-check
    # 失败 → 拒绝，类型不一致的代码不应进入测试

  - name: Unit Tests
    run: make test
    # 失败 → 拒绝，行为不正确不能合并

  - name: Integration Tests
    run: make test-integration
    # 失败 → 警告（不阻塞合并），但应在合并后修复
```

### 2.3 三个命令的输出风格对比

**lint 输出**（人类友好，带代码位置）：

```
api/services/billing_service.py:42:5: E501 Line too long (135 > 120)
api/services/billing_service.py:55:1: F401 `os` imported but unused
Found 2 errors.
```

**type-check 输出**（类型错误，含类型签名）：

```
api/services/billing_service.py:42: error: Argument 1 to "send_request" has incompatible type "str"; expected "int"  [arg-type]
    def send_request(user_id: int, ...) -> Response:
                        ^
api/services/billing_service.py:55: error: "os" is unbound  [used-before-def]
```

**test 输出**（详细的断言和回溯）：

```
======================== FAILURES ========================
_______ test_billing_service_refund _______
api/tests/unit_tests/services/test_billing_service.py:88: in test_billing_service_refund
    result = BillingService.refund(user_id=42)
api/services/billing_service.py:120: in refund
    raise ValueError("user not found")
E   ValueError: user not found
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Makefile 三件套

**文件位置**：`/Users/xu/code/github/dify/Makefile`
**核心代码**（行 65-90）：

```makefile
lint:
	@echo "🔧 Running ruff format, check with fixes, response contract lint, import linter, and dotenv-linter..."
	@uv run --project api --dev ruff format ./api
	@uv run --project api --dev ruff check --fix ./api
	@$(MAKE) api-contract-lint
	@uv run --directory api --dev lint-imports
	@uv run --project api --dev dotenv-linter ./api/.env.example ./web/.env.example
	@echo "✅ Linting complete"

api-contract-lint:
	@echo "🔎 Linting Flask response contracts..."
	@uv run --project api --dev python api/dev/lint_response_contracts.py
	@echo "✅ Response contract lint complete"

type-check:
	@echo "📝 Running type checks (pyrefly + mypy)..."
	@./dev/pyrefly-check-local $(PATH_TO_CHECK)
	@uv --directory api run mypy --exclude-gitignore --exclude '(^|/)conftest\.py$$' --exclude 'tests/' --exclude 'migrations/' --exclude 'dev/generate_swagger_specs.py' --exclude 'dev/generate_fastopenapi_specs.py' --check-untyped-defs --disable-error-code=import-untyped .
	@echo "✅ Type checks complete"
```

**解读**：
- `make lint` 不只是 Ruff，还包含：
  - `api-contract-lint`：Flask 响应契约检查（自定义工具）
  - `lint-imports`：importlinter 架构守护
  - `dotenv-linter`：环境变量格式
- `make type-check` 是 pyrefly + mypy 双重检查
- 三者都通过 `@echo` 输出 emoji，让输出更友好（🔧📝✅）

### 3.2 dify 的测试入口

**文件位置**：`/Users/xu/code/github/dify/Makefile`
**核心代码**（行 92-130）：

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

test-all:
	@echo "🧪 Running full backend test suite..."
	...
```

**解读**：
- `make test` 默认只跑单元测试（快）
- `make test-all` 跑全部测试（含集成）
- `TARGET_TESTS=path/to/test.py make test` 可指定具体测试
- controller 测试单独跑（与 xdist 冲突）

### 3.3 dify 的 CI workflow

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
**核心代码**（行 19-80）：

```yaml
api-unit:
  name: API Unit Tests
  runs-on: depot-ubuntu-24.04
  env:
    COVERAGE_FILE: coverage-unit
  strategy:
    matrix:
      python-version:
        - "3.12"
  steps:
    - name: Checkout code
      uses: actions/checkout@v9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0
      with:
        fetch-depth: 0
        persist-credentials: false

    - name: Setup UV and Python
      uses: astral-sh/setup-uv@d31148d669074a8d0a63714ba94f3201e7020bc3
      with:
        enable-cache: true
        python-version: ${{ matrix.python-version }}
        cache-dependency-glob: api/uv.lock

    - name: Check UV lockfile
      run: uv lock --project api --check

    - name: Install dependencies
      run: uv sync --project api --dev

    - name: Run dify config tests
      run: uv run --project api pytest api/tests/unit_tests/configs/test_env_consistency.py

    - name: Run Unit Tests
      run: |
        uv run --project api pytest \
          -p no:benchmark \
          --timeout "${PYTEST_TIMEOUT:-20}" \
          -n auto \
          api/tests/unit_tests \
          ...
```

**解读**：
- 第 47 行：`uv lock --project api --check` —— 检查 lock 文件一致性
- 第 50 行：`uv sync --project api --dev` —— 安装开发依赖
- 第 53 行：先跑 config 一致性测试（环境变量）
- 第 56-65 行：跑主测试套件
- **设计意图**：CI 在跑测试前先确保**环境一致**（lock 文件 + dev 依赖），避免环境问题误判为测试失败

### 3.4 dify 的 lint workflow

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/autofix.yml`（摘要）

```yaml
name: Autofix
on:
  pull_request:
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
        with:
          args: "check --fix"
```

**解读**：
- dify 在 CI 中也跑 Ruff（用 `astral-sh/ruff-action`）
- 自动修复 + 自动 commit（`--fix` 模式）
- 这是 "lint 不通过 → 自动修复 → 自动 commit" 的便利工具

## 4. 关键要点总结

- dify 三件套：`make lint`（风格）+ `make type-check`（类型）+ `make test`（行为）
- pre-commit hook 自动跑 Ruff，把质量门禁前置
- CI 顺序：lint → type-check → test（**快速失败在前**）
- `make test` 只跑单元测试，`make test-all` 跑全部
- Controller 测试单独跑，避开 xdist 的路由冲突
- `make lint` 不只是 Ruff，还包含 importlinter、契约检查、dotenv-linter

## 5. 练习题

### 练习 1：基础（必做）

在 dify 仓库根目录依次运行：
```bash
$ make lint
$ make type-check
$ make test
```
观察三者的执行时间和输出风格，记录每一步耗时。

### 练习 2：进阶

故意在 `api/services/` 下新建一个 `services/test_quality.py`，故意写：
- 一个超过 120 字符的行
- 一个未使用的 import
- 一个未注解类型的函数

然后依次跑 `make lint` / `make type-check`，记录哪些被哪些工具捕获。

### 练习 3：挑战（选做）

阅读 `Makefile` 的完整 `test-all` target，理解 dify 集成测试的执行流程，并设计一个 PR Check 脚本：本地依次跑 `lint` → `type-check` → `test`，任何一个失败立即退出，确保本地质量门禁与 CI 一致。

## 6. 参考资料

- `/Users/xu/code/github/dify/Makefile`（三件套入口）
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`（CI 流程）
- `/Users/xu/code/github/dify/.vite-hooks/pre-commit`（pre-commit hook）
- `/Users/xu/code/github/dify/codecov.yml`（覆盖率门禁）

---

**文档版本**：v1.0
**最后更新**：2026-07-13