# 19 Lint 工具：Ruff / Flake8 / Black

> 掌握 Python Lint 工具链，理解 dify 选择 Ruff 作为统一 Lint 工具的原因和配置方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Ruff 的安装、配置和常用命令
- 理解 Lint 与 Formatter 的区别
- 熟悉 dify 的 `.ruff.toml` 配置
- 应用：能在 dify 中运行 `make lint` 并修复问题

## 📚 前置知识

- Python 基础语法
- 09-testing/01-pytest-basics.md

## 1. 核心概念

### 1.1 Lint 工具的三大类

| 类型 | 作用 | 工具 |
|------|------|------|
| **Linter** | 检查代码错误（语法、风格、潜在 bug） | Ruff, Flake8, Pylint |
| **Formatter** | 自动格式化代码风格 | Black, Ruff format, isort |
| **Type Checker** | 静态类型检查 | mypy, pyright, pyrefly |

dify 用 **Ruff** 一统江湖：
- Ruff 是 Rust 编写的超快 Linter + Formatter
- 兼容 Flake8、Black、isort 的规则
- 一个工具替代多个，速度提升 10-100 倍

### 1.2 Ruff vs 传统工具链

**传统组合**（dify 早期可能用过）：
- Flake8（lint）+ Black（format）+ isort（import 排序）

**dify 当前选择**：
- Ruff（lint + format 全部）
- 配合 mypy 和 pyrefly 做类型检查

```
旧：   flake8 (1秒) + black (3秒) + isort (2秒) = 6秒
新：   ruff check + ruff format = 0.5秒
```

### 1.3 dify 的 Ruff 规则

`api/.ruff.toml` 启用的核心规则：

| 规则类别 | 含义 | 示例 |
|----------|------|------|
| `B` | flake8-bugbear | 常见 bug 模式 |
| `E` / `W` | pycodestyle | PEP 8 风格 |
| `F` | pyflakes | 未使用变量、未定义名称 |
| `I` | isort | import 排序 |
| `N` | pep8-naming | 命名约定 |
| `S` | flake8-bandit | 安全检查 |
| `UP` | pyupgrade | 新语法升级 |
| `PT` | flake8-pytest-style | pytest 风格 |
| `SIM` | flake8-simplify | 简化代码 |
| `TID` | flake8-tidy-imports | 整洁 import |

## 2. 代码示例

### 2.1 基本命令

```bash
# 格式化（自动修复格式问题）
$ uv run --project api --dev ruff format ./api

# 检查并自动修复 lint 问题
$ uv run --project api --dev ruff check --fix ./api

# 仅检查，不修复
$ uv run --project api --dev ruff check ./api

# 查看具体规则说明
$ uv run --project api --dev ruff rule S307
```

### 2.2 配置文件示例

```toml
# 文件：.ruff.toml
line-length = 120

[format]
quote-style = "double"

[lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long（自定义 line-length=120 时允许更长）
    "B008",  # function call in default argument
]

[lint.per-file-ignores]
"tests/*" = ["T201"]  # 允许 print
"__init__.py" = ["F401"]  # 允许 unused import
```

### 2.3 自动修复前后对比

```python
# ❌ 修复前
import os,sys
from typing import List
def foo(x:int)->int:
    unused=42
    return x+1

# ✅ 修复后（Ruff 跑 ruff check --fix 后）
import os
import sys


def foo(x: int) -> int:
    return x + 1
```

### 2.4 flake8-bug（B）规则示例

```python
# B006: 不要用 mutable default argument
def add_item(item, target=[]):  # ❌ Bug！
    target.append(item)
    return target

def add_item(item, target=None):  # ✅ 正确
    if target is None:
        target = []
    target.append(item)
    return target
```

## 3. 关键要点总结

- Ruff = Linter + Formatter，单工具替代 Flake8 + Black + isort
- dify 用 `.ruff.toml` 集中配置规则，覆盖 Bug、风格、安全、现代化
- `make lint` 是 dify 的**完整质量门禁**：Ruff + importlinter + 契约检查 + dotenv-linter
- `line-length = 120` 反映 dify 偏宽松的代码风格
- 测试代码通过 `per-file-ignores` 允许一些警告（print、try-except-pass）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
