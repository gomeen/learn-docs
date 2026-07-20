# 20 类型检查：mypy / pyright

> 掌握 Python 类型检查工具，能用 mypy 和 pyrefly 在 dify 中做静态类型检查。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解类型检查与 Lint 的区别
- 掌握 mypy 和 pyrefly 的基本用法
- 熟悉 dify 的类型检查配置
- 应用：能在 dify 中运行 `make type-check` 并修复类型错误

## 📚 前置知识

- Python 类型注解（详见 [typing 基础](../01-fundamentals/08-python-typing-basics.md)）
- 09-testing/14-lint-tools.md

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

## 3. 关键要点总结

- 类型检查比 Lint 更深入，关注**类型一致性**而非风格
- dify 同时用 **mypy + pyrefly**：pyrefly 快速反馈，mypy 权威检查
- `make type-check` 是 dify 类型检查的标准入口
- 测试代码和 migrations 默认排除（避免噪音）
- `--check-untyped-defs` 让检查更严格
- 类型错误比 Lint 错误更难"自动修复"，通常需要修改代码

---

**文档版本**：v1.0
**最后更新**：2026-07-13
