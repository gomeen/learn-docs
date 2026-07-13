# 20 类型检查：mypy / pyright

> 掌握 Python 类型检查工具，能用 mypy 和 pyrefly 在 dify 中做静态类型检查。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解类型检查与 Lint 的区别
- 掌握 mypy 和 pyrefly 的基本用法
- 熟悉 dify 的类型检查配置
- 应用：能在 dify 中运行 `make type-check` 并修复类型错误

## 📚 前置知识

- 01-fundamentals/01-type-hints.md
- Python typing 模块
- 09-testing/19-lint-tools.md

## 1. 核心概念

### 1.1 类型检查 vs Lint

| 维度 | Lint (Ruff) | Type Check (mypy/pyright) |
|------|-------------|---------------------------|
| 检查对象 | 风格、语法、模式 | 类型一致性 |
| 速度 | 极快 | 较慢 |
| 配置 | 简单（启用规则集合） | 复杂（排除路径、strict 级别） |
| 修复 | 通常可自动修复 | 只能手动修复 |
| 误报率 | 中等 | 较高（特别在泛型/类型推断时） |

### 1.2 类型检查工具对比

| 工具 | 开发方 | 速度 | 严格度 | dify 使用 |
|------|--------|------|--------|-----------|
| **mypy** | Python 官方 | 慢 | 高 | ✓ |
| **pyright** | Microsoft | 中 | 极高 | ✗ |
| **pyrefly** | Meta (Facebook) | 快 | 高 | ✓（新增） |
| **pyre** | Meta (旧版) | 中 | 高 | ✗ |

dify 同时使用 **mypy + pyrefly** 双重检查：
- mypy 成熟稳定，社区标准
- pyrefly 速度更快，适合本地开发

### 1.3 类型检查的两大模式

**宽模式（默认）**：允许隐式 Any，宽松
**严格模式（strict）**：禁止隐式 Any、要求函数返回类型

dify 用 **宽模式**（不启用 `--strict`），通过排除特定文件平衡严格度和实用性。

## 2. 代码示例

### 2.1 mypy 基础

```bash
# 基本检查
$ uv --directory api run mypy api/core/

# 排除 migrations/ 和 tests/
$ uv --directory api run mypy --exclude migrations/ --exclude tests/ api/

# 严格模式
$ uv --directory api run mypy --strict api/

# 显示错误码
$ uv --directory api run mypy --show-error-codes api/
```

### 2.2 类型错误示例

```python
# ❌ 类型错误：参数类型不匹配
def add(a: int, b: int) -> int:
    return a + b

result = add("1", "2")  # mypy error: Argument 1 has incompatible type "str"; expected "int"

# ❌ 类型错误：返回值缺失
def get_user(user_id: int) -> User:  # mypy error: Missing return statement
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        return user
    # 没有 else 分支！

# ✅ 正确
def get_user(user_id: int) -> User | None:
    user = db.query(User).filter_by(id=user_id).first()
    return user  # type: ignore[return-value] 如果没有 Optional
```

### 2.3 pyrefly 基础

```bash
# pyrefly 是 Meta 出品的新类型检查器，速度快
$ ./dev/pyrefly-check-local api/core/

# 检查整个项目
$ ./dev/pyrefly-check-local
```

### 2.4 dify 的 mypy 配置模式

```bash
# dify 的实际命令（从 Makefile 提炼）
$ uv --directory api run mypy \
    --exclude-gitignore \
    --exclude '(^|/)conftest\.py$' \
    --exclude 'tests/' \
    --exclude 'migrations/' \
    --exclude 'dev/generate_swagger_specs.py' \
    --exclude 'dev/generate_fastopenapi_specs.py' \
    --check-untyped-defs \
    --disable-error-code=import-untyped \
    .
```

**关键选项解读**：
- `--exclude-gitignore`：尊重 .gitignore 排除
- `--exclude 'tests/'`：测试代码通常不强制类型
- `--check-untyped-defs`：检查**没有类型注解的函数**（默认跳过）
- `--disable-error-code=import-untyped`：忽略 `import` 语句找不到类型的报错

## 3. dify 仓库源码解读

### 3.1 dify 的类型检查命令

**文件位置**：`/Users/xu/code/github/dify/Makefile`
**核心代码**（行 77-90）：

```makefile
type-check:
	@echo "📝 Running type checks (pyrefly + mypy)..."
	@./dev/pyrefly-check-local $(PATH_TO_CHECK)
	@uv --directory api run mypy --exclude-gitignore --exclude '(^|/)conftest\.py$$' --exclude 'tests/' --exclude 'migrations/' --exclude 'dev/generate_swagger_specs.py' --exclude 'dev/generate_fastopenapi_specs.py' --check-untyped-defs --disable-error-code=import-untyped .
	@echo "✅ Type checks complete"
```

**解读**：
- 第 79 行：先跑 pyrefly（速度快，作为快速反馈）
- 第 80 行：再跑 mypy（更严格，作为权威检查）
- `--exclude-gitignore`：不检查未跟踪的文件
- 排除 `tests/` 和 `migrations/` 是因为这些代码类型注解不完整
- `--check-untyped-defs` 让 mypy 检查未注解函数（更严格）

### 3.2 dify 的类型检查依赖

**文件位置**：`/Users/xu/code/github/dify/api/pyproject.toml`
**核心代码**（行 178-185）：

```toml
[dependency-groups]
dev = [
    "mypy>=1.20.2",
    # "locust>=2.40.4",  # Temporarily removed due to compatibility issues. Uncomment when resolved.
    "pytest-timeout>=2.4.0",
    "pytest-xdist>=3.8.0",
    "pyrefly>=1.0.0",
    "xinference-client>=2.7.0",
]
```

**解读**：
- `mypy>=1.20.2` —— mypy 主版本
- `pyrefly>=1.0.0` —— Meta 的新类型检查器
- dify 选择**两个工具互补**，pyrefly 做快速检查，mypy 做权威检查

### 3.3 dify 的 pyrefly 本地脚本

**文件位置**：`/Users/xu/code/github/dify/dev/pyrefly-check-local`

```bash
#!/bin/bash
# 摘要：本地 pyrefly 检查脚本
set -e
cd "$(dirname "$0")/.."
uv run --directory api pyrefly check "$@"
```

**解读**：
- 用 `uv run` 调用 pyrefly，不需要全局安装
- 把检查脚本放在 `dev/` 目录下，统一管理开发工具
- `$@` 透传参数（如指定检查的路径）

## 4. 关键要点总结

- 类型检查比 Lint 更深入，关注**类型一致性**而非风格
- dify 同时用 **mypy + pyrefly**：pyrefly 快速反馈，mypy 权威检查
- `make type-check` 是 dify 类型检查的标准入口
- 测试代码和 migrations 默认排除（避免噪音）
- `--check-untyped-defs` 让检查更严格
- 类型错误比 Lint 错误更难"自动修复"，通常需要修改代码

## 5. 练习题

### 练习 1：基础（必做）

为下面函数加上完整类型注解，确保 mypy 通过：

```python
def find_user_by_email(email, db_session):
    return db_session.query(User).filter_by(email=email).first()
```

要求：
- `email: str`
- `db_session: Session`
- 返回 `User | None`

### 练习 2：进阶

运行 `./dev/pyrefly-check-local api/core/rag/embedding/`，观察 pyrefly 的输出，尝试修复其中 3 个类型错误（如果有的话）。

### 练习 3：挑战（选做）

阅读 `api/core/workflow/` 下的某个核心模块，理解 dify 在大型模块中如何处理复杂类型（如 Workflow 节点的 `NodeRunResult` 类型）。尝试为一个 Workflow 节点函数写完整的类型注解。

## 6. 参考资料

- `/Users/xu/code/github/dify/Makefile`（`make type-check`）
- `/Users/xu/code/github/dify/api/pyproject.toml`（mypy / pyrefly 依赖）
- `/Users/xu/code/github/dify/dev/pyrefly-check-local`（pyrefly 脚本）
- mypy 官方文档：https://mypy.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13