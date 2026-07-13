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

## 3. dify 仓库源码解读

### 3.1 dify 后端的 `pyproject.toml`

**文件位置**：`/Users/xu/code/github/dify/api/pyproject.toml`
**核心代码**（行 1-30）：

```toml
[project]
name = "dify-api"
version = "1.16.0-rc1"
requires-python = "~=3.12.0"

dependencies = [
    # Legacy: mature and widely deployed
    "bleach>=6.4.0,<7.0.0",
    "boto3>=1.43.24,<2.0.0",
    "celery>=5.6.3,<6.0.0",
    "croniter>=6.2.2,<7.0.0",
    "dify-agent",
    "flask>=3.1.3,<4.0.0",
    "flask-cors>=6.0.2,<7.0.0",
    "gevent>=26.4.0,<26.5.0",
    "gevent-websocket==0.10.1",
    "gmpy2>=2.3.0,<3.0.0",
    "google-api-python-client>=2.196.0,<3.0.0",
    "gunicorn>=26.0.0,<27.0.0",
```

**解读**：
- 第 3 行：`requires-python = "~=3.12.0"` 限制 Python 主版本必须 3.12（`~=` 等价于 `>=3.12,<3.13`）
- 第 6-29 行：依赖分组——`Legacy`（成熟稳定的）、`Stable`（生产验证的）、`Emerging`（较新的）
- **关键设计**：通过注释区分依赖的成熟度，新包倾向使用兼容性范围 `>=X,<Y+1`

### 3.2 Workspace 配置

**文件位置**：`/Users/xu/code/github/dify/api/pyproject.toml`
**核心代码**（行 60-80）：

```toml
[tool.uv.workspace]
members = ["providers/vdb/*", "providers/trace/*"]
exclude = ["providers/vdb/__pycache__", "providers/trace/__pycache__"]

[tool.uv.sources]
dify-agent = { path = "../dify-agent", editable = true }
flask-restx = { git = "https://github.com/asukaminato0721/flask-restx", rev = "27758e26f8f740d7525d5039c51a9e524b6e2b68" }
dify-vdb-alibabacloud-mysql = { workspace = true }
dify-vdb-analyticdb = { workspace = true }
dify-vdb-baidu = { workspace = true }
# ... 30+ 个 vdb provider
```

**解读**：
- 第 1-3 行：`members` 列出所有子包，dify 把每个向量数据库 provider 当作独立子包
- 第 6-7 行：可编辑安装 `dify-agent`（同仓库不同目录）+ git 源安装第三方修改版 `flask-restx`
- 第 8-12 行：所有 `dify-vdb-*` 子包用 workspace 方式管理，统一版本
- **关键设计**：monorepo 模式让所有 provider 共享主项目的依赖，同时可以独立开发

## 4. 关键要点总结

- `pyproject.toml` 是 PEP 621 标准的单一项目配置文件
- `uv` 是 Rust 编写的现代包管理器，速度比 pip 快 10-100 倍
- 常用命令：`uv add` / `uv sync` / `uv run` / `uv lock`
- `uv.lock` 锁定依赖版本，团队协作时只需 `uv sync`
- Workspace 模式适合 monorepo，dify 用它管理 30+ 个 provider 子包
- dify 后端用 `uv run --project api <command>` 执行所有命令

## 5. 练习题

### 练习 1：基础（必做）

在本地用 `uv init` 创建一个新项目，添加 `requests` 和 `pydantic` 依赖，写一个简单的 main.py 用 `uv run python main.py` 运行。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/pyproject.toml`，统计：
1. `dependencies` 中共有多少个直接依赖
2. `tool.uv.workspace.members` 包含哪些子目录
3. `tool.uv.sources` 中用 `git` 源安装的依赖有几个

### 练习 3：挑战（选做）

在 dify 仓库根目录执行 `uv run --project api python -c "import flask; print(flask.__version__)"`，验证你能在本地跑通 dify 的 Python 解释器。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pyproject.toml`
- `/Users/xu/code/github/dify/uv.lock`（依赖锁定文件）
- uv 官方文档：https://docs.astral.sh/uv/
- PEP 621：https://peps.python.org/pep-0621/

---

**文档版本**：v1.0
**最后更新**：2026-07-13