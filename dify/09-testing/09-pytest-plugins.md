# 09 pytest 插件：`pytest-cov` / `pytest-asyncio`

> 掌握 pytest 生态的核心插件，能在 dify 测试中使用覆盖率、异步测试、并行执行等增强能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `pytest-cov` 配置覆盖率和报告
- 理解 `pytest-asyncio` 的 async 测试模式
- 知道 `pytest-xdist` 的并行执行原理
- 应用：能在 dify 测试中配置和使用这些插件

## 📚 前置知识

- 09-testing/03-coverage.md
- Python 异步编程（详见 [async/await 与 asyncio](../01-fundamentals/12-async-asyncio.md)）
- 09-testing/05-pytest-basics.md

## 1. 核心概念

### 1.1 pytest 插件生态

pytest 最强大的地方是**插件机制**。核心插件超过 600 个，覆盖各种场景：

| 插件 | 用途 | dify 是否使用 |
|------|------|---------------|
| `pytest-cov` | 覆盖率统计 | ✓ |
| `pytest-mock` | mock 的 fixture 形式封装 | ✓ |
| `pytest-env` | 设置测试环境变量 | ✓ |
| `pytest-asyncio` | 异步测试支持 | 按需 |
| `pytest-xdist` | 并行执行 | ✓ |
| `pytest-timeout` | 测试超时控制 | ✓ |
| `pytest-benchmark` | 性能基准测试 | ✓ |
| `testcontainers` | 容器化集成测试 | ✓ |

### 1.2 pytest-cov 工作原理

`pytest-cov` 包装了 `coverage.py`，在 pytest 启动时自动收集覆盖率数据：

```
pytest 启动
   ↓
pytest-cov 注入覆盖率收集
   ↓
运行测试用例
   ↓
生成 coverage.json / coverage.xml
```

### 1.3 pytest-asyncio 模式

让 pytest 能运行 `async def` 测试函数：

```python
import pytest

# 模式 1：装饰器写法（推荐；装饰器原理详见 [装饰器](../01-fundamentals/10-decorator.md)）
@pytest.mark.asyncio
async def test_async_func():
    result = await async_operation()
    assert result == 42

# 模式 2：自动模式（在 pytest.ini 配置）
# asyncio_mode = auto 后，无需装饰器
async def test_async_func():  # 自动识别
    ...
```

## 2. 代码示例

### 2.1 pytest-cov 配置

```ini
# 文件：pytest.ini
[pytest]
addopts =
    --cov=./src
    --cov-report=term
    --cov-report=html:htmlcov
    --cov-branch
    --cov-fail-under=80
```

```bash
# 常用命令
$ pytest --cov=./api                    # 收集 api 目录覆盖率
$ pytest --cov-report=term-missing      # 显示未覆盖的行号
$ pytest --cov-report=html:htmlcov      # 生成 HTML 报告
$ pytest --cov-fail-under=80            # 低于 80% 时失败
```

### 2.2 pytest-asyncio 异步测试

```python
import pytest
import asyncio


async def async_add(a, b):
    await asyncio.sleep(0.01)  # 模拟异步操作
    return a + b


@pytest.mark.asyncio
async def test_async_add():
    result = await async_add(2, 3)
    assert result == 5


# 同时跑多组数据
@pytest.mark.asyncio
@pytest.mark.parametrize("a,b,expected", [(1, 2, 3), (0, 0, 0), (-1, -1, -2)])
async def test_async_add_param(a, b, expected):
    result = await async_add(a, b)
    assert result == expected
```

### 2.3 pytest-xdist 并行执行

```bash
# 自动检测 CPU 数量并行
$ pytest -n auto

# 指定 4 个 worker
$ pytest -n 4

# 按文件分布（dify 默认模式）
$ pytest -n auto --dist=loadfile
```

### 2.4 pytest-timeout 防止卡死

```python
import pytest


@pytest.mark.timeout(5)  # 5 秒未完成就失败
def test_slow_operation():
    import time
    time.sleep(3)  # OK，5 秒内完成


def test_no_timeout_marker():
    # 没有 marker，按全局 --timeout 设置
    pytest.skip("long running")
```

```bash
# 全局设置 20 秒超时（dify 的配置）
$ pytest --timeout=20
```

## 3. dify 仓库源码解读

### 3.1 dify 的 pytest 插件依赖

**文件位置**：`/Users/xu/code/github/dify/api/pyproject.toml`
**核心代码**（行 130-135）：

```toml
[project]
name = "dify-api"

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-benchmark>=5.2.3",
    "pytest-cov>=7.1.0",
    "pytest-env>=1.6.0",
    "pytest-mock>=3.15.1",
]
```

**解读**：
- 第 130 行：`pytest>=9.0.3` —— pytest 核心
- 第 131 行：`pytest-benchmark` —— 性能基准测试
- 第 132 行：`pytest-cov` —— 覆盖率
- 第 133 行：`pytest-env` —— 从 pytest.ini 读取 env 配置
- 第 134 行：`pytest-mock` —— mock 的 fixture 封装

### 3.2 dify 的测试并行与超时配置

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
**核心代码**（行 39-50）：

```yaml
- name: Run Unit Tests
  run: |
    uv run --project api pytest \
      -p no:benchmark \
      --timeout "${PYTEST_TIMEOUT:-20}" \
      -n auto \
      api/tests/unit_tests \
      api/providers/vdb/*/tests/unit_tests \
      api/providers/trace/*/tests/unit_tests \
      --ignore=api/tests/unit_tests/controllers
```

**解读**：
- 第 42 行：`-p no:benchmark` —— 关闭 benchmark 插件（CI 中不跑性能测试）
- 第 43 行：`--timeout "${PYTEST_TIMEOUT:-20}"` —— 全局 20 秒超时（环境变量可覆盖）
- 第 44 行：`-n auto` —— pytest-xdist 自动并行（CPU 多少核就用多少 worker）
- 第 48 行：`--ignore=...controllers` —— Controller 测试注册 Flask 路由，会与 xdist 冲突，单独跑

### 3.3 dify 的 pytest-env 配置

**文件位置**：`/Users/xu/code/github/dify/api/pytest.ini`
**核心代码**（行 4-6）：

```ini
[pytest]
pythonpath = .
addopts = --cov=./api --cov-report=json --import-mode=importlib --cov-branch --cov-report=xml
env =
    OPENAI_API_KEY = sk-IamNotARealKeyJustForMockTestKawaiiiiiiiiii
    MOCK_SWITCH = true
    ANTHROPIC_API_KEY = sk-ant-api11-IamNotARealKeyJustForMockTestKawaiiiiiiiiii-NotBaka-ASkksz
```

**解读**：
- 第 4 行：`env =` 配置由 `pytest-env` 插件读取，在测试启动时自动设置环境变量
- 这些 mock 用的 API key 都是测试专用（值故意是假名），防止误用真实密钥
- `MOCK_SWITCH = true` 是 dify 的全局 mock 开关

## 4. 关键要点总结

- `pytest-cov` 通过 `--cov` 选项启用，自动生成覆盖率报告
- `pytest-asyncio` 用 `@pytest.mark.asyncio` 装饰器标记 async 测试
- `pytest-xdist` 的 `-n auto` 让测试并行执行，大幅加快 CI
- `pytest-timeout` 防止测试卡死拖慢 CI
- `pytest-env` 在 pytest.ini 中统一管理测试环境变量
- dify 用 `-p no:benchmark --timeout 20 -n auto` 三件套保证 CI 速度

## 5. 练习题

### 练习 1：基础（必做）

本地运行 `cd api && uv run --project api --dev pytest api/tests/unit_tests/core/rag/embedding/ --cov=api.core.rag.embedding --cov-report=term-missing`，观察 `--cov-report=term-missing` 显示的未覆盖行。

### 练习 2：进阶

为下面 async 函数写测试：

```python
import asyncio

async def fetch_with_retry(url: str, max_retries: int = 3) -> str:
    for i in range(max_retries):
        try:
            # 假设的异步请求
            await asyncio.sleep(0.1)
            return f"ok from {url}"
        except Exception:
            if i == max_retries - 1:
                raise
    return ""
```

要求使用 `@pytest.mark.asyncio` 和 `@pytest.mark.parametrize` 覆盖 1/2/3 次重试。

### 练习 3：挑战（选做）

阅读 `api/Makefile`（或根目录的 `Makefile`），理解 dify 的测试入口（`make test`），并尝试在本地用 `-n 2` 替换 `-n auto`，观察执行时间差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pyproject.toml`（依赖声明）
- `/Users/xu/code/github/dify/api/pytest.ini`（pytest-env 配置）
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`（CI 中的并行与超时）
- pytest-cov 文档：https://pytest-cov.readthedocs.io/
- pytest-asyncio 文档：https://pytest-asyncio.readthedocs.io/
- pytest-xdist 文档：https://pytest-xdist.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13