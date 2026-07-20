# 1.2.2 YAML / TOML 配置文件

> 掌握 YAML 和 TOML 两种常用配置文件的语法，能读写 dify 中的配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 YAML 基础语法（缩进、列表、字典）
- 掌握 TOML 基础语法（节、表、数组）
- 区分两种格式的适用场景
- 在 dify 中找到典型的配置样例

## 📚 前置知识

- Python 基础：字典、列表
- ../../dify/01-fundamentals/11-json-processing.md（推荐）

## 1. 核心概念

### 1.1 为什么需要配置文件？

代码与配置分离（[12-Factor](02-env-vars.md) 原则）：
- **代码**：逻辑，写一次
- **配置**：环境相关，每个环境不同

```python
# ❌ 硬编码
DATABASE_URL = "postgresql://localhost/dev"

# ✅ 从配置读取
DATABASE_URL = os.environ["DATABASE_URL"]
```

### 1.2 YAML 基础

YAML（YAML Ain't Markup Language）强调**可读性**，用缩进表示层级：

```yaml
# 注释以 # 开头
name: dify
version: 1.0.0

# 嵌套字典（用 2 空格缩进）
database:
  host: localhost
  port: 5432
  name: dify_db
  credentials:
    user: admin
    password: secret  # 生产环境用环境变量注入

# 列表（用 - 开头）
plugins:
  - name: redis
    enabled: true
  - name: celery
    enabled: true

# 多行字符串
description: |
  这是多行字符串
  保留所有换行

# 引用与锚点
defaults: &defaults
  timeout: 30
  retry: 3

production:
  <<: *defaults      # 合并 anchors
  workers: 8
```

**YAML 解析**：

```python
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

# config = {
#     "name": "dify",
#     "database": {"host": "localhost", ...},
#     "plugins": [...],
# }
```

**警告**：永远用 `yaml.safe_load`，**不要**用 `yaml.load`（会执行任意代码，安全风险）。

### 1.3 TOML 基础

TOML（Tom's Obvious Minimal Language）强调**显式**，用 `[section]` 表示节：

```toml
# pyproject.toml 示例
[project]
name = "dify-api"
version = "1.16.0"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0",
    "sqlalchemy>=2.0",
]

# 嵌套表
[project.optional-dependencies]
dev = ["pytest>=8.0", "mypy>=1.0"]

# 数组内联
plugins = ["redis", "celery", "sentry"]

# 表数组
[[tool.uv.workspace.members]]
path = "providers/vdb/*"

# 日期/时间
started_at = 2026-07-13T10:00:00
```

**TOML 解析**：

```python
# Python 3.11+ 内置 tomllib（只读）
import tomllib

with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)

# Python 3.11+ 无内置 toml writer，常用 tomli_w
import tomli_w
tomli_w.dump(config, open("out.toml", "wb"))
```

### 1.4 YAML vs TOML vs JSON 对比

JSON 专题见 [17-json-processing](../../dify/01-fundamentals/17-json-processing.md)。

| 特性 | YAML | TOML | JSON |
|---|---|---|---|
| 可读性 | 高 | 中 | 低 |
| 注释支持 | 是 | 是 | 否 |
| 复杂结构 | 优秀（锚点引用） | 一般 | 一般 |
| 解析速度 | 慢 | 快 | 最快 |
| 主要场景 | K8s / CI 配置 | Python 项目配置 | API 数据 |

**dify 选择**：
- `pyproject.toml`：Python 项目元数据（PEP 621）
- `docker-compose.yaml`：容器编排
- `*.json`：API 数据、数据库 JSON 字段

## 2. 代码示例

### 2.1 读写 YAML 配置

```python
import yaml
from pathlib import Path

# 写入
config = {
    "app": {
        "name": "myapp",
        "debug": False,
        "max_connections": 100,
    },
    "plugins": ["cache", "logger"],
}
Path("config.yaml").write_text(
    yaml.safe_dump(config, default_flow_style=False, allow_unicode=True)
)

# 读取
loaded = yaml.safe_load(Path("config.yaml").read_text())
assert loaded == config
```

### 2.2 读写 TOML 配置

```python
import tomllib
import tomli_w
from pathlib import Path

# 写入（Python 3.11+ 用 tomli_w）
config = {
    "tool": {
        "ruff": {
            "line-length": 120,
            "target-version": "py312",
        }
    }
}
with open("pyproject.toml", "wb") as f:
    tomli_w.dump(config, f)

# 读取
with open("pyproject.toml", "rb") as f:
    loaded = tomllib.load(f)
```

### 2.3 常见错误：YAML 缩进错误

```yaml
# ❌ 错误：缩进不一致
database:
  host: localhost
   port: 5432    # 多了 1 个空格

# ✅ 正确：统一 2 空格
database:
  host: localhost
  port: 5432
```

YAML 不允许 Tab，**必须用空格**，且同层级缩进必须一致。

## 3. dify 仓库源码解读

### 3.1 pyproject.toml：项目元数据

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
]
```

**解读**：
- 第 1 行：`[project]` 是 PEP 621 标准段
- 第 4 行：`requires-python = "~=3.12.0"` 锁定 Python 主版本
- 第 6-13 行：依赖列表，每行一个字符串

### 3.2 Docker Compose YAML 配置

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 1-30）：

```yaml
services:
  api:
    build:
      context: ../
      dockerfile: docker/Dockerfile
    ports:
      - "5001:5001"
    environment:
      - MODE=api
      - DB_DATABASE=dify
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
    volumes:
      - ../api:/app/api

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**解读**：
- 第 1 行：根节点是 `services`（字典）
- 第 2-19 行：`api` 服务定义了构建、端口、环境变量、依赖、卷挂载
- 第 12-14 行：**环境变量注入实现 12-Factor 配置**——配置与代码分离
- **关键设计**：通过环境变量可以无修改切换 dev/staging/prod 环境

## 4. 关键要点总结

- YAML 用**缩进**表示层级，必须用空格，**永不使用 Tab**
- TOML 用**节（[section]）**显式分组，适合"键值对 + 少量嵌套"
- JSON 不支持注释，YAML 和 TOML 支持
- 解析 YAML 必须用 `safe_load`，避免任意代码执行
- Python 3.11+ 内置 `tomllib` 读取 TOML，写入需 `tomli_w`
- dify 用 TOML 做项目配置、用 YAML 做 Docker 配置、用 JSON 做 API 数据

## 5. 练习题

### 练习 1：基础（必做）

写一个 `config.yaml`，包含：
- `app.name`、`app.port`、`app.debug`
- `database.host`、`database.port`、`database.pool_size`
- `features`（列表，包含 3 项）

然后用 `yaml.safe_load` 读取并打印。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/pyproject.toml`，找出 `tool.uv.workspace` 段，理解 dify 的 workspace 配置用了什么 TOML 特性。

### 练习 3：挑战（选做）

用 Python 写一个 `load_config(path)` 函数，自动检测文件扩展名（`.yaml` / `.toml` / `.json`）并用对应的库解析，返回统一格式的 dict。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pyproject.toml`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- YAML 规范：https://yaml.org/spec/
- TOML 规范：https://toml.io/en/
- PEP 518（pyproject.toml）：https://peps.python.org/pep-0518/

---

**文档版本**：v1.0
**最后更新**：2026-07-13