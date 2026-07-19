# 1.1.15 Python 包管理：`uv` 与 `pyproject.toml`

> 掌握现代 Python 项目管理工具 `uv` 与配置文件 `pyproject.toml`，理解 dify 后端的依赖组织方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `pyproject.toml` 的结构与作用
- 熟练使用 `uv` 创建、激活与管理虚拟环境
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

### 1.2 虚拟环境：创建、激活与使用

虚拟环境（virtual environment）把项目依赖隔离在独立目录中，避免污染系统 Python、也避免不同项目互相踩版本。

`uv` 默认把虚拟环境放在项目根目录的 **`.venv/`**。

#### 创建虚拟环境

```bash
# 在当前目录创建 .venv（使用当前可用的 Python）
uv venv

# 指定 Python 版本（需本机已安装，或由 uv 自动下载）
uv venv --python 3.12

# 指定路径（非默认 .venv 时）
uv venv /path/to/my-env
```

项目场景下更常见的是 **`uv sync`**：它会在需要时自动创建 `.venv`，并按 `pyproject.toml` / `uv.lock` 安装依赖，一步完成「建环境 + 装包」。

```bash
# 推荐：同步依赖时自动创建/更新 .venv
uv sync

# 仅同步生产依赖（不含 dev 组）
uv sync --no-dev
```

#### 激活虚拟环境

激活后，当前 shell 的 `python` / `pip` 会指向 `.venv` 内的解释器。

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (cmd)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

激活成功后，提示符前通常会出现 `(.venv)`：

```bash
(.venv) $ which python
# /path/to/project/.venv/bin/python

(.venv) $ python -c "import sys; print(sys.prefix)"
# .../project/.venv
```

退出虚拟环境：

```bash
deactivate
```

#### 不激活也能用：`uv run`

日常开发**不必每次都手动 `source`**。`uv run` 会自动找到项目 `.venv`（没有则创建并同步），再在环境中执行命令：

```bash
# 等价于「激活 .venv 再执行 python main.py」
uv run python main.py

# 跑测试、工具
uv run pytest
uv run ruff check .

# 在环境中打开 Python REPL
uv run python
```

| 方式 | 适用场景 | 说明 |
|------|----------|------|
| `source .venv/bin/activate` | 交互式调试、长时间在同一 shell 里敲命令 | 改的是当前 shell 的 `PATH` |
| `uv run <cmd>` | 脚本、CI、一次性命令 | 自动使用项目环境，无需激活 |
| IDE 选择解释器 | VS Code / PyCharm 等 | 把解释器指到 `.venv/bin/python` |

#### 查看与切换解释器

```bash
# 当前 shell 用的是哪个 Python（激活后应指向 .venv）
which python
python --version

# 不激活时，用 uv 查看项目环境中的解释器
uv run which python
uv run python --version

# 列出 uv 管理的 Python 版本
uv python list

# 为项目固定 Python 版本（写入 .python-version）
uv python pin 3.12
```

#### 删除与重建

依赖搞乱、Python 版本换错时，最干净的做法是删掉 `.venv` 再同步：

```bash
# 删除虚拟环境
rm -rf .venv

# 重新创建并安装锁定依赖
uv sync
```

> **提示**：`.venv` 一般应加入 `.gitignore`，不要提交到仓库；团队成员 clone 后执行 `uv sync` 即可复现环境。

### 1.3 `pyproject.toml` 的结构

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

### 1.4 常用 `uv` 命令

```bash
# 初始化项目（会创建 .venv）
uv init my-project
cd my-project

# 创建虚拟环境（一般可交给 uv sync / uv run 自动处理）
uv venv --python 3.12

# 添加依赖
uv add requests

# 添加开发依赖
uv add --dev pytest

# 同步依赖（创建/更新 .venv，并安装 pyproject.toml 中的包）
uv sync

# 运行命令（自动在虚拟环境中，无需先 activate）
uv run python main.py
uv run pytest

# 直接运行工具
uv run ruff check .

# 锁定依赖版本
uv lock
```

### 1.5 锁定文件 `uv.lock`

`uv.lock` 是跨平台的依赖锁定文件，记录：
- 每个包的确切版本
- 每个包的哈希值
- 兼容的平台

```bash
# 团队协作：clone 后只需
uv sync
# 自动创建 .venv 并安装 lock 中锁定的所有依赖
```

### 1.6 Workspace（多包项目）

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

### 2.2 虚拟环境完整工作流

```bash
uv init demo-venv
cd demo-venv

# 方式 A：显式创建环境，再同步依赖
uv venv --python 3.12
uv sync

# 方式 B（推荐）：直接 sync，自动创建 .venv 并装依赖
# uv sync

# 手动激活后使用（交互式）
source .venv/bin/activate
python -c "import sys; print(sys.executable)"
# 应输出 .../demo-venv/.venv/bin/python
deactivate

# 不激活，用 uv run（推荐日常命令）
uv run python -c "import sys; print(sys.executable)"

# 环境坏了：删掉重建
rm -rf .venv
uv sync
```

在 IDE 中：打开项目后，把 Python 解释器选为 `./.venv/bin/python`（Windows 为 `.\.venv\Scripts\python.exe`），调试与终端就会使用同一环境。

### 2.3 添加、移除依赖

```bash
# 添加（会写入 pyproject.toml，并更新 .venv）
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

### 2.4 常见错误：虚拟环境相关

```bash
# ❌ 错误 1：用系统 pip 安装，污染全局 / 装错位置
pip install flask

# ✅ 正确：用 uv 管理依赖
uv add flask
# 或已激活 .venv 时：
# source .venv/bin/activate && pip install flask
# （仍更推荐 uv add / uv sync）

# ❌ 错误 2：激活了 A 项目的 .venv，却在 B 项目目录里装包
# 表现为 import 成功但路径不对，或依赖装到错误环境

# ✅ 正确：确认当前解释器路径
which python
# 或
uv run which python

# ❌ 错误 3：只装了包、没在项目环境中跑
python main.py   # 可能用的是系统 Python，ImportError

# ✅ 正确
uv run python main.py
# 或
source .venv/bin/activate && python main.py
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
- 虚拟环境默认在项目根目录 `.venv/`；`uv venv` 创建，`uv sync` 可自动创建并装依赖
- 激活：`source .venv/bin/activate`（退出：`deactivate`）；日常更推荐 `uv run`，无需手动激活
- 常用命令：`uv venv` / `uv add` / `uv sync` / `uv run` / `uv lock`
- `uv.lock` 锁定依赖版本，团队协作时只需 `uv sync`（`.venv` 不提交 git）
- Workspace 模式适合 monorepo，dify 用它管理 30+ 个 provider 子包
- dify 后端用 `uv run --project api <command>` 执行所有命令

## 5. 练习题

### 练习 1：基础（必做）

在本地用 `uv init` 创建一个新项目，添加 `requests` 和 `pydantic` 依赖，写一个简单的 main.py 用 `uv run python main.py` 运行。

### 练习 2：虚拟环境（必做）

1. 用 `uv venv --python 3.12` 创建环境，`source .venv/bin/activate` 后执行 `which python`，确认路径落在项目 `.venv` 下
2. `deactivate` 后执行 `uv run which python`，对比是否仍指向同一 `.venv`
3. 故意用系统 `python -c "import requests"`（若失败属预期），再用 `uv run python -c "import requests"` 验证环境隔离

### 练习 3：进阶

阅读 `/Users/xu/code/github/dify/api/pyproject.toml`，统计：
1. `dependencies` 中共有多少个直接依赖
2. `tool.uv.workspace.members` 包含哪些子目录
3. `tool.uv.sources` 中用 `git` 源安装的依赖有几个

### 练习 4：挑战（选做）

在 dify 仓库根目录执行 `uv run --project api python -c "import flask; print(flask.__version__)"`，验证你能在本地跑通 dify 的 Python 解释器。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pyproject.toml`
- `/Users/xu/code/github/dify/uv.lock`（依赖锁定文件）
- uv 官方文档：https://docs.astral.sh/uv/
- uv 虚拟环境：https://docs.astral.sh/uv/pip/environments/
- PEP 621：https://peps.python.org/pep-0621/

---

**文档版本**：v1.1
**最后更新**：2026-07-19