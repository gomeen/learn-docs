# 03 测试覆盖率：行覆盖 / 分支覆盖 / 路径覆盖

> 理解测试覆盖率的多种度量方式，以及如何在 dify 中正确使用 `pytest-cov`。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分行覆盖、分支覆盖、路径覆盖的概念
- 解读 `coverage.json` 和 `coverage.xml` 报告
- 能为 dify 模块编写覆盖率合理的测试
- 应用：能通过 `make test` 的覆盖率输出定位未覆盖代码

## 📚 前置知识

- 09-testing/01-testing-pyramid.md
- Python 控制流（if/else、循环、异常处理）

## 1. 核心概念

### 1.1 三种覆盖率度量

**1. 行覆盖（Line Coverage）**

最简单：测试执行时**经过**了多少行代码。

```python
def divide(a, b):
    if b == 0:           # 行 2
        return None      # 行 3
    return a / b         # 行 4

def test_normal():
    assert divide(10, 2) == 5  # 只覆盖行 1, 2, 4
```

覆盖率 = 2/3 行 = 67%。

**2. 分支覆盖（Branch Coverage）**

更严格：测试覆盖了每个 `if/else` 分支的**所有方向**。

```python
def test_branches():
    assert divide(10, 2) == 5  # 走 True 分支
    assert divide(10, 0) is None  # 走 False 分支
```

分支覆盖率 = 100%（两个分支都走到了）。

**3. 路径覆盖（Path Coverage）**

最严格：测试覆盖了所有可能的**执行路径**。当函数有嵌套条件时，路径数量指数级增长，实际工程几乎不可能做到 100%。

### 1.2 覆盖率工具对比

| 工具 | 语言 | 行覆盖 | 分支覆盖 | 速度 |
|------|------|--------|----------|------|
| coverage.py | Python | ✓ | ✓ | 快 |
| pytest-cov | Python | ✓ | ✓ | 快 |
| JaCoCo | Java | ✓ | ✓ | 中 |
| Istanbul | JavaScript | ✓ | ✓ | 中 |

**dify 使用**：`pytest-cov` + `coverage` 组合（见 `pytest.ini` 的 `--cov` 选项）。

### 1.3 覆盖率不是万能的

**反例 1：100% 覆盖率 ≠ 0 bug**

```python
def add(a, b):
    return a - b  # Bug！但所有行都被执行了

def test_add():
    assert add(2, 3) is not None  # 通过
```

**反例 2：高覆盖率 ≠ 高质量测试**

```python
def complex_logic(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    return "zero"

def test_complex_logic():
    complex_logic(1)  # 只覆盖了第一个 if
    # 但 assert 都没写
```

覆盖率只告诉你"代码被执行了"，不告诉你"代码行为被验证了"。

## 2. 代码示例

### 2.1 用 coverage.py 测行覆盖

```python
# 文件：calculator.py
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def divide(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b
```

```python
# 文件：test_calculator.py
from calculator import add, divide

def test_add():
    assert add(1, 2) == 3

def test_divide():
    assert divide(10, 2) == 5
    # 注意：没有测试 divide 的 b==0 分支
```

```bash
# 运行覆盖率
$ coverage run -m pytest test_calculator.py
$ coverage report
Name              Stmts   Miss  Cover
-------------------------------------
calculator.py         7      2    71%
test_calculator.py    4      0   100%
-------------------------------------
TOTAL                11      2    82%
```

### 2.2 启用分支覆盖

```bash
# 启用分支覆盖（dify 的配置）
$ coverage run --branch -m pytest
$ coverage report --show-misses

calculator.py    7      1    85%   15->12
                       ^^^^^
                       分支未覆盖：if b == 0 的 False 分支
```

### 2.3 dify 中的覆盖率配置

`pytest.ini` 中的关键配置：

```ini
[pytest]
addopts = --cov=./api --cov-report=json --import-mode=importlib --cov-branch --cov-report=xml
```

参数解读：
- `--cov=./api`：只统计 `api/` 目录下的代码覆盖率
- `--cov-branch`：启用分支覆盖
- `--cov-report=json`：输出 `coverage.json` 给 Codecov
- `--cov-report=xml`：输出 `coverage.xml` 给 CI（详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)）

## 3. dify 仓库源码解读

### 3.1 dify 的覆盖率收集配置

**文件位置**：`/Users/xu/code/github/dify/api/pytest.ini`
**核心代码**（行 2-3）：

```ini
[pytest]
pythonpath = .
addopts = --cov=./api --cov-report=json --import-mode=importlib --cov-branch --cov-report=xml
```

**解读**：
- 第 2 行：`pythonpath = .` —— 把当前目录加入 Python 路径，方便 import
- 第 3 行：`addopts` 是 pytest 的默认参数集合，每次 `pytest` 命令都会带上
- `--cov-branch` 启用分支覆盖，是 dify 的标准配置（比纯行覆盖严格）
- 输出 `coverage.json` 给 Codecov 上传，可视化展示覆盖率趋势

### 3.2 dify 的覆盖率门禁（间接体现）

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
**核心代码**（行 33-50）：

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

- name: Upload unit coverage data
  uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
  with:
    name: api-coverage-unit
    path: coverage-unit
    retention-days: 1
```

**解读**：
- 第 43 行：`--timeout "${PYTEST_TIMEOUT:-20}"` —— 给每个测试加 20 秒超时，防止卡死拖慢 CI
- 第 44 行：`-n auto` —— 用 pytest-xdist 自动并行执行测试，加快速度
- 第 51-54 行：把覆盖率数据作为 CI 工件上传，供 Codecov 下载分析
- **整体设计意图**：dify 通过 CI 集中收集覆盖率，每个 PR 都能看到覆盖率变化趋势，避免覆盖率悄悄下降

## 4. 关键要点总结

- **行覆盖**：最基础，容易达到高百分比
- **分支覆盖**：dify 默认开启，更严格，推荐使用
- **路径覆盖**：理论上完美，实际工程不可行
- 高覆盖率 ≠ 高质量，要结合 **断言质量** 综合判断
- dify 用 `pytest-cov` + CI 工件上传，追踪覆盖率趋势

## 5. 练习题

### 练习 1：基础（必做）

在本地运行 `cd api && uv run --project api --dev pytest api/tests/unit_tests/core/rag/embedding/test_embedding_base.py --cov=api.core.rag.embedding.embedding_base --cov-report=term-missing`，查看行覆盖和分支覆盖报告。

### 练习 2：进阶

为 `api/services/billing_service.py` 中的某个方法（如 `_send_request`）写 3 个测试，使该方法的分支覆盖率达到 100%。对比只写 1 个测试时的覆盖率差异。

### 练习 3：挑战（选做）

阅读 `api/tests/unit_tests/test_pytest_dify.py`，理解 dify 是如何用 pytest 的 coverage 插件控制哪些模块需要覆盖的，并尝试为 `api/services/` 目录设置一个 80% 的覆盖率门禁。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pytest.ini`（覆盖率配置）
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`（CI 覆盖率上传）
- `/Users/xu/code/github/dify/codecov.yml`（Codecov 阈值配置）
- coverage.py 官方文档：https://coverage.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13