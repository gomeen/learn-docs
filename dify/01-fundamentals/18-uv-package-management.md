# 1.1.15 Python 包管理：`uv` 与 `pyproject.toml`

> 掌握现代 Python 项目管理工具 `uv` 与配置文件 `pyproject.toml`，理解 dify 后端的依赖组织方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `pyproject.toml` 的结构与作用
- 熟练使用 `uv` 进行依赖管理（安装、锁定、运行）
- 区分项目依赖、可选依赖、可编辑安装
- 能在 dify 仓库中跑通命令

## 📚 前置知识

- Python 基础：虚拟环境、pip
- 命令行基础

## 1. 核心概念

### 1.1 为什么用 `uv`？

`uv` 是 Rust 编写的 Python 包管理器，比 `pip` 快 **10-100 倍**，并统一了：
- 虚拟环境管理（替代 `venv`）
- 依赖解析（替代 `pip` + `pip-tools`）
- 项目运行（替代 `pipx`）
- Python 版本管理（替代 `pyenv`）

### 1.2 `pyproject.toml` 的结构

PEP 621 标准的项目元数据与依赖配置：

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0.0",
    "sqlalchemy>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "mypy>=1.0"]

[project.scripts]
my-cli = "my_app.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.3 常用 `uv` 命令

```bash
# 初始化项目
uv init my-project
cd my-project

# 添加依赖
uv add requests

# 添加开发依赖
uv add --dev pytest

# 同步依赖（安装 pyproject.toml 中的所有包）
uv sync

# 运行命令（在虚拟环境中）
uv run python main.py
uv run pytest

# 直接运行工具
uv run ruff check .

# 锁定依赖版本
uv lock
```

### 1.4 锁定文件 `uv.lock`

`uv.lock` 是跨平台的依赖锁定文件，记录：
- 每个包的确切版本
- 每个包的哈希值
- 兼容的平台

```bash
# 团队协作：clone 后只需
uv sync
# 自动安装 lock 中锁定的所有依赖
```

### 1.5 Workspace（多包项目）

`uv` 支持 monorepo：

```toml
[tool.uv.workspace]
members = ["packages/*", "apps/api"]
```

dify 后端就是一个 workspace，包含 `providers/vdb/*` 和 `providers/trace/*` 多个子包。

## 2. 代码示例

### 2.1 创建一个新项目

```bash
# 初始化
uv init my-app
cd my-app

# 项目结构
# my-app/
# ├── .python-version      # Python 版本（3.12）
# ├── pyproject.toml       # 项目配置
# ├── README.md
# ├── hello.py             # 入口文件
# └── .venv/               # 自动创建的虚拟环境
```

### 2.2 添加、移除依赖

```bash
# 添加
uv add flask sqlalchemy pydantic

# 指定版本
uv add "fastapi>=0.110,<0.120"

# 添加开发依赖
uv add --dev pytest ruff mypy

# 添加可选依赖组
uv add --optional api uvicorn

# 移除
uv remove flask
```

### 2.3 常见错误：忘记激活虚拟环境

```bash
# ❌ 错误：用系统 pip 安装
pip install flask
# 可能污染全局环境、版本冲突

# ✅ 正确：用 uv run 自动在虚拟环境中执行
uv run python -c "import flask; print(flask.__version__)"
uv run pytest tests/
```

## 3. 关键要点总结

- `pyproject.toml` 是 PEP 621 标准的单一项目配置文件
- `uv` 是 Rust 编写的现代包管理器，速度比 pip 快 10-100 倍
- 常用命令：`uv add` / `uv sync` / `uv run` / `uv lock`
- `uv.lock` 锁定依赖版本，团队协作时只需 `uv sync`
- Workspace 模式适合 monorepo，dify 用它管理 30+ 个 provider 子包
- dify 后端用 `uv run --project api <command>` 执行所有命令

---

**文档版本**：v1.0
**最后更新**：2026-07-13
