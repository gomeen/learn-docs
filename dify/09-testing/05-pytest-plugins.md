# 09 pytest 插件：`pytest-cov` / `pytest-asyncio`

> 掌握 pytest 生态的核心插件，能在 dify 测试中使用覆盖率、异步测试、并行执行等增强能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `pytest-cov` 配置覆盖率和报告
- 理解 `pytest-asyncio` 的 async 测试模式
- 知道 `pytest-xdist` 的并行执行原理
- 应用：能在 dify 测试中配置和使用这些插件

## 📚 前置知识

- ../../_common/18-testing/03-coverage.md
- Python 异步编程（详见 [async/await 与 asyncio](../01-fundamentals/14-async-asyncio.md)）
- 09-testing/01-pytest-basics.md

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

# 模式 1：装饰器写法（推荐；装饰器原理详见 [装饰器](../01-fundamentals/11-decorator.md)）
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

## 3. 关键要点总结

- `pytest-cov` 通过 `--cov` 选项启用，自动生成覆盖率报告
- `pytest-asyncio` 用 `@pytest.mark.asyncio` 装饰器标记 async 测试
- `pytest-xdist` 的 `-n auto` 让测试并行执行，大幅加快 CI
- `pytest-timeout` 防止测试卡死拖慢 CI
- `pytest-env` 在 pytest.ini 中统一管理测试环境变量
- dify 用 `-p no:benchmark --timeout 20 -n auto` 三件套保证 CI 速度

---

**文档版本**：v1.0
**最后更新**：2026-07-13
