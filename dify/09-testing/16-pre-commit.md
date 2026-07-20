# 21 Pre-commit Hook

> 掌握 pre-commit hook 的配置和原理，能在 dify 中集成 Git 提交前的自动化检查。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 pre-commit hook 的工作机制
- 掌握 dify 的 `.vite-hooks/pre-commit` 配置
- 能为项目编写自定义 pre-commit 脚本
- 应用：能在 dify 中配置自己的 pre-commit hook

## 📚 前置知识

- Git 基础（commit、hook；进阶命令详见 [Git 进阶](../../_common/15-git/01-git-advanced.md)）
- 09-testing/14-lint-tools.md
- 09-testing/15-type-check.md

## 1. 核心概念

### 1.1 什么是 Pre-commit Hook

**Pre-commit hook** 是 Git 在 `git commit` 前自动执行的脚本。常见用途：

```
git commit
   ↓
触发 pre-commit hook
   ↓
运行 lint / format / type-check / test
   ↓
全部通过？  → 允许 commit
    ↓ 否
  拒绝 commit，要求修复
```

**好处**：
- 把质量门禁**前置**到本地，而不是等 CI 失败
- 节省 CI 时间
- 强制团队规范统一

### 1.2 两类 Pre-commit 方案

**1. 框架方案（pre-commit.com）**

```yaml
# 文件：.pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff
      - id: ruff-format
```

**2. 自定义脚本方案**

dify 用方案 2：`.vite-hooks/pre-commit` 是个 shell 脚本。

### 1.3 为什么 dify 用自定义脚本

| 优势 | 原因 |
|------|------|
| 灵活性 | 可以判断 modified 文件，只跑相关检查 |
| 性能 | 不需要下载第三方 hook 仓库 |
| 可读性 | shell 脚本一目了然 |
| 维护成本 | 不需要升级 hook 版本 |

## 2. 代码示例

### 2.1 标准 pre-commit 框架配置

```yaml
# 文件：.pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.20.2
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest (fast)
        entry: pytest -x --timeout=10
        language: system
        pass_filenames: false
```

### 2.2 自定义 shell hook 示例

```bash
#!/bin/sh
# 文件：.git/hooks/pre-commit

# 1. 获取暂存的文件
files=$(git diff --cached --name-only)

# 2. 判断哪些模块被修改
api_modified=false
web_modified=false

for file in $files; do
  case "$file" in
    api/*.py) api_modified=true ;;
    web/*)    web_modified=true ;;
  esac
done

# 3. 跑对应模块的 lint
if $api_modified; then
  echo "Running Ruff on api..."
  uv run --project api --dev ruff check --fix ./api || exit 1
fi

if $web_modified; then
  echo "Running ESLint on web..."
  cd web && pnpm lint:fix || exit 1
fi
```

### 2.3 安装 hook 到 .git/hooks/

```bash
# 方式 1：用 pre-commit 框架
$ pip install pre-commit
$ pre-commit install

# 方式 2：手动复制
$ cp .vite-hooks/pre-commit .git/hooks/pre-commit
$ chmod +x .git/hooks/pre-commit

# 方式 3：通过项目脚本
$ make install-hooks
```

## 3. 关键要点总结

- Pre-commit hook 在 `git commit` 前自动运行，把质量门禁前置
- dify 用**自定义 shell 脚本**而非 pre-commit 框架
- 关键设计：只跑**修改过的模块**的 lint，大幅加快 commit 速度
- 智能跳过：merge / rebase / cherry-pick 场景下不强制检查
- `.vite-hooks/pre-commit` 在仓库内，`make install-hooks` 复制到 `.git/hooks/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
