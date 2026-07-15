# 21 Pre-commit Hook

> 掌握 pre-commit hook 的配置和原理，能在 dify 中集成 Git 提交前的自动化检查。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 pre-commit hook 的工作机制
- 掌握 dify 的 `.vite-hooks/pre-commit` 配置
- 能为项目编写自定义 pre-commit 脚本
- 应用：能在 dify 中配置自己的 pre-commit hook

## 📚 前置知识

- Git 基础（commit、hook；进阶命令详见 [Git 进阶](../01-fundamentals/30-git-advanced.md)）
- 09-testing/19-lint-tools.md
- 09-testing/20-type-check.md

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

## 3. dify 仓库源码解读

### 3.1 dify 的 pre-commit 脚本

**文件位置**：`/Users/xu/code/github/dify/.vite-hooks/pre-commit`
**核心代码**（行 1-70）：

```sh
#!/bin/sh
# get the list of modified files
files=$(git diff --cached --name-only)

# check if api or web directory is modified
api_modified=false
web_modified=false
skip_web_checks=false

git_path() {
    git rev-parse --git-path "$1"
}

if [ -f "$(git_path MERGE_HEAD)" ] || \
   [ -f "$(git_path CHERRY_PICK_HEAD)" ] || \
   [ -f "$(git_path REVERT_HEAD)" ] || \
   [ -f "$(git_path SQUASH_MSG)" ] || \
   [ -d "$(git_path rebase-merge)" ] || \
   [ -d "$(git_path rebase-apply)" ]; then
    skip_web_checks=true
fi

for file in $files
do
    # Use POSIX compliant pattern matching
    case "$file" in
        api/*.py)
            # set api_modified flag to true
            api_modified=true
            ;;
        web/*)
            # set web_modified=true
            web_modified=true
            ;;
    esac
done

# run linters based on the modified modules

if $api_modified; then
    echo "Running Ruff linter on api module"
    # run Ruff linter auto-fixing
    uv run --project api --dev ruff check --fix ./api
    # run Ruff linter checks
    uv run --project api --dev ruff check  ./api || status=$?

    status=${status:-0}

    if [ $status -ne 0 ]; then
      echo "Ruff linter on api module error, exit code: $status"
      echo "Please run 'dev/reformat' to fix the fixable linting errors."
      exit 1
    fi
fi

if $skip_web_checks; then
    echo "Git operation in progress, skipping web checks"
    exit 0
fi

vp staged
```

**解读**：
- 第 4 行：`git diff --cached --name-only` —— 只看**暂存区**的文件（即将 commit 的）
- 第 11-23 行：智能判断：merge / cherry-pick / rebase 等场景下跳过 web 检查，避免干扰
- 第 25-37 行：用 `case` 判断每个文件属于哪个模块，设置对应标志
- 第 40-58 行：只对被修改的模块跑 lint（**性能优化**：不每次都跑全部）
- 第 53 行：`status=$?` 捕获 ruff check 的退出码
- 第 65 行：`vp staged` —— 调用自定义 lint 命令工具

### 3.2 dify 的跳过场景处理

```sh
if [ -f "$(git_path MERGE_HEAD)" ] || \
   [ -f "$(git_path CHERRY_PICK_HEAD)" ] || \
   [ -f "$(git_path REVERT_HEAD)" ] || \
   [ -f "$(git_path SQUASH_MSG)" ] || \
   [ -d "$(git_path rebase-merge)" ] || \
   [ -d "$(git_path rebase-apply)" ]; then
    skip_web_checks=true
fi
```

**解读**：
- 这 6 个文件 / 目录是 Git 在执行**特殊操作**时的标记：
  - `MERGE_HEAD`：merge 中
  - `CHERRY_PICK_HEAD`：cherry-pick 中
  - `REVERT_HEAD`：revert 中
  - `SQUASH_MSG`：squash commit 准备中
  - `rebase-merge` / `rebase-apply`：rebase 中
- 这些场景下跳过 web 检查，避免 web lint 失败导致 rebase 中断

### 3.3 dify 的 hooks 目录选择

```
.vite-hooks/
└── pre-commit        # Git hook 脚本
```

**解读**：
- dify 把 hooks 放在 `.vite-hooks/` 而不是 `.git/hooks/`
- `.git/` 是 Git 管理的，hook 不会被 commit
- `.vite-hooks/` 是仓库的一部分，所有开发者都能用

## 4. 关键要点总结

- Pre-commit hook 在 `git commit` 前自动运行，把质量门禁前置
- dify 用**自定义 shell 脚本**而非 pre-commit 框架
- 关键设计：只跑**修改过的模块**的 lint，大幅加快 commit 速度
- 智能跳过：merge / rebase / cherry-pick 场景下不强制检查
- `.vite-hooks/pre-commit` 在仓库内，`make install-hooks` 复制到 `.git/hooks/`

## 5. 练习题

### 练习 1：基础（必做）

阅读 `.vite-hooks/pre-commit`，列出所有被调用的命令（如 `ruff check`），理解每个命令的作用。

### 练习 2：进阶

为本地项目写一个简单的 pre-commit hook：检测到 `*.py` 被修改时，运行 `ruff check --fix <changed_file>` 而不是整个目录。

### 练习 3：挑战（选做）

阅读 `.vite-hooks/pre-commit` 的 `vp staged` 命令（在 `node_modules/.bin/vp` 或 pnpm 脚本中），理解 `vite-plugin-checker` 的 `staged` 模式如何集成 web 端的 lint/type-check。

## 6. 参考资料

- `/Users/xu/code/github/dify/.vite-hooks/pre-commit`（dify 的 pre-commit 脚本）
- pre-commit 官方文档：https://pre-commit.com/
- Git hooks 文档：https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks

---

**文档版本**：v1.0
**最后更新**：2026-07-13