# 1.2.3 环境变量与 12-Factor 配置原则

> 掌握环境变量的使用与 12-Factor App 配置原则，理解 dify 中所有配置项的来源。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 12-Factor App 的核心原则
- 熟练使用 `os.environ` 读写环境变量
- 理解 dify 中配置分层（环境变量 → 配置文件 → 默认值）
- 用 `.env` 文件管理本地开发配置

## 📚 前置知识

- 命令行基础
- 01-fundamentals/28-config-file-format.md

## 1. 核心概念

### 1.1 12-Factor App 配置原则

**The Twelve-Factor App** 是 SaaS 应用的最佳实践指南，其中**第 III 要素：Config** 要求：

> **配置（Config）应在环境中存储**，而不是代码中。

理由：
- 不同环境（dev/staging/prod）需要不同配置
- 配置应该**可以立即修改**，不需要重新部署代码
- 配置应该**与代码完全分离**

### 1.2 环境变量基础

```python
import os

# 读取
host = os.environ["DB_HOST"]               # KeyError 如果不存在
host = os.getenv("DB_HOST")                # None 如果不存在
host = os.getenv("DB_HOST", "localhost")   # 提供默认值
host = os.getenv("DB_HOST", "localhost").lower()  # 链式调用

# 遍历所有环境变量
for key, value in os.environ.items():
    print(f"{key}={value}")

# 设置（仅当前进程）
os.environ["MY_VAR"] = "value"
```

### 1.3 类型转换

环境变量**都是字符串**，需要手动转换：

```python
# 整数
port = int(os.getenv("PORT", "5000"))

# 布尔
debug = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# 列表
hosts = os.getenv("REDIS_HOSTS", "").split(",")  # "a,b,c" → ["a", "b", "c"]

# JSON
import json
config = json.loads(os.getenv("CONFIG_JSON", "{}"))
```

### 1.4 `.env` 文件

本地开发用 `.env` 文件存储环境变量（**不应提交到 git**）：

```bash
# .env 文件
DATABASE_URL=postgresql://localhost/dify_dev
DEBUG=true
SECRET_KEY=dev-secret-change-me
```

**加载方式**：

```python
# 方式 1：手动解析
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# 方式 2：用 python-dotenv
# pip install python-dotenv
from dotenv import load_dotenv
load_dotenv()  # 自动读取 .env 并写入 os.environ
```

### 1.5 配置分层（dify 风格）

dify 的配置加载逻辑：
1. **环境变量**（最高优先级，覆盖一切）
2. **配置文件**（如 `pyproject.toml`）
3. **默认值**（代码中写死）

```
环境变量 > .env 文件 > 配置文件 > 代码默认值
```

## 2. 代码示例

### 2.1 健壮的环境变量读取

```python
import os
from typing import Optional

def get_env(key: str, default: Optional[str] = None, *, required: bool = False) -> str:
    """读取环境变量，支持必填校验。"""
    value = os.getenv(key, default)
    if required and value is None:
        raise RuntimeError(f"Required environment variable {key} is not set")
    return value or ""

# 使用
DEBUG = get_env("DEBUG", "false").lower() == "true"
PORT = int(get_env("PORT", "5000"))
SECRET = get_env("SECRET_KEY", required=True)  # 必填，缺失时报错
```

### 2.2 用 `python-dotenv` 管理本地配置

```python
# .env
# DATABASE_URL=postgresql://localhost/dify_dev
# REDIS_URL=redis://localhost:6379/0

# app.py
from dotenv import load_dotenv
import os

load_dotenv()  # 在所有 import 之前调用

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]
```

### 2.3 常见错误：把 secret 提交到 git

```bash
# ❌ 错误：把 .env 加入 git
git add .env
git commit -m "add config"

# ✅ 正确：把 .env 加入 .gitignore
echo ".env" >> .gitignore

# 同时提供 .env.example 模板（不含真实 secret）
cat > .env.example <<EOF
DATABASE_URL=postgresql://localhost/your_db
SECRET_KEY=change-me
EOF
```

## 3. dify 仓库源码解读

### 3.1 dify 的 `.env.example` 模板

**文件位置**：`/Users/xu/code/github/dify/.env.example`
**核心代码**（行 1-30）：

```bash
# ------- database ----------
DB_USERNAME=postgres
DB_PASSWORD=difyai123456
DB_HOST=db
DB_PORT=5432
DB_DATABASE=dify

# ------- redis ----------
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# ------- celery ----------
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

**解读**：
- 按"功能模块"用注释分组（database、redis、celery）
- 每个模块的所有配置集中放在一起
- **关键设计**：提供 `.env.example` 而不是 `.env`——模板可提交到 git，真实配置由开发者本地创建

### 3.2 dify 配置加载流程

**文件位置**：`/Users/xu/code/github/dify/api/configs/extra/__init__.py`
**核心代码**（行 1-25）：

```python
import os
from typing import Any

# 读取环境变量，提供类型安全的配置
class Config:
    """dify 全局配置。"""

    @property
    def DEBUG(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"

    @property
    def SECRET_KEY(self) -> str:
        return os.getenv("SECRET_KEY", "")

    @property
    def DB_HOST(self) -> str:
        return os.getenv("DB_HOST", "localhost")

config = Config()
```

**解读**：
- 用 `@property` 把环境变量读取封装成属性，对外暴露**强类型接口**
- 每个属性都有合理的默认值（避免 KeyError）
- **关键设计**：业务代码读 `config.DB_HOST` 而不是 `os.getenv("DB_HOST")`，便于测试时 mock 整个 `config` 对象

### 3.3 dify docker-compose 中的环境注入

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 1-25）：

```yaml
services:
  api:
    build:
      context: ../
      dockerfile: docker/Dockerfile
    environment:
      - MODE=api
      - DB_DATABASE=dify
      - REDIS_HOST=redis
    env_file:
      - .env
```

**解读**：
- 第 9-12 行：`environment` 块直接传 KV
- 第 13-14 行：`env_file` 让 docker-compose 自动加载 `.env` 文件
- **关键设计**：同一个镜像可以在不同环境用不同 `.env` 文件启动，无需改动代码

## 4. 关键要点总结

- 12-Factor 第 III 条：配置存在环境，不在代码中
- `os.environ[key]` 不存在会 KeyError，`os.getenv(key, default)` 返回 None
- 环境变量都是字符串，需要手动转 int / bool / list
- `.env` 文件**不应提交到 git**，应提供 `.env.example` 模板
- 配置分层：环境变量 > `.env` > 配置文件 > 默认值
- dify 风格：用 `@property` 封装环境变量读取，对外暴露强类型配置对象

## 5. 练习题

### 练习 1：基础（必做）

写一个 `load_env_config()` 函数，读取以下环境变量并返回 dict：
- `DB_HOST`（默认 `"localhost"`）
- `DB_PORT`（默认 `5432`，转 int）
- `DEBUG`（默认 `false`，转 bool）
- `SECRET_KEY`（必填，缺失抛异常）

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/docker/docker-compose.yaml`，列出所有环境变量，理解 dify 中各服务（api、worker、web）的环境变量如何区分。

### 练习 3：挑战（选做）

> 学完 [30-pydantic-settings](./30-pydantic-settings.md) 后再做：用 `pydantic-settings` 写一个 `Settings` 类，用环境变量和 `.env` 文件自动加载 dify 的所有 DB / Redis / Celery 配置。

## 6. 参考资料

- `/Users/xu/code/github/dify/.env.example`
- `/Users/xu/code/github/dify/api/configs/extra/__init__.py`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- 12-Factor App：https://12factor.net/zh_cn/config
- python-dotenv：https://pypi.org/project/python-dotenv/

---

**文档版本**：v1.0
**最后更新**：2026-07-13