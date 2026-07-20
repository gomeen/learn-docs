# 1.5.3 Conventional Commits 与语义化版本

> 掌握 Conventional Commits 规范与 SemVer（语义化版本），能为 dify 贡献符合规范的提交。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Conventional Commits 规范
- 掌握 SemVer 版本号规则
- 用 commitlint / standard-version 自动化版本管理
- 看懂 dify 的 CHANGELOG 与 release notes

## 📚 前置知识

- Git 基础：`commit`、`tag`
- [Git 工作流](./02-git-workflow.md)

## 1. 核心概念

### 1.1 Conventional Commits 规范

一种**机器可读的提交消息规范**，让工具能自动生成 CHANGELOG、确定版本号。

**格式**：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Type 类型**：

| Type | 含义 | SemVer 影响 |
|---|---|---|
| `feat` | 新功能 | MINOR（次版本号 +1） |
| `fix` | Bug 修复 | PATCH（修订号 +1） |
| `docs` | 文档变更 | 无 |
| `style` | 格式调整（不影响代码） | 无 |
| `refactor` | 重构（既不是 feat 也不是 fix） | 无 |
| `perf` | 性能优化 | PATCH |
| `test` | 测试相关 | 无 |
| `build` | 构建系统、依赖变更 | 无 |
| `ci` | CI 配置变更 | 无 |
| `chore` | 其他杂项 | 无 |
| `revert` | 回滚之前的提交 | 看原 commit |

**Breaking Changes**（破坏性变更）：任何位置包含 `BREAKING CHANGE:` 都会触发 MAJOR 版本 +1。

**示例**：

```bash
# 新功能
git commit -m "feat(api): add streaming endpoint for workflow"

# Bug 修复
git commit -m "fix(core): handle null inputs in code node"

# 破坏性变更（注意 ! 和 footer）
git commit -m "feat(api)!: rename /v1/apps/:id to /v1/applications/:id

BREAKING CHANGE: The endpoint /v1/apps/:id has been renamed to /v1/applications/:id.
Existing API consumers must update their code."
```

### 1.2 SemVer（语义化版本）

版本号格式：`MAJOR.MINOR.PATCH`（如 `1.16.0`）

| 部分 | 含义 | 何时 +1 |
|---|---|---|
| **MAJOR** | 主版本 | 包含不兼容的 API 变更 |
| **MINOR** | 次版本 | 新增功能，向后兼容 |
| **PATCH** | 修订号 | Bug 修复，向后兼容 |

**前置版本**：`1.0.0-alpha.1`、`1.0.0-beta.2`、`1.0.0-rc.1`

### 1.3 Conventional Commits → SemVer 自动映射

工具（如 `standard-version`、`release-please`）能根据提交历史自动决定版本号：

```
当前版本：1.5.3

提交历史：
  feat: add new API endpoint         → 1.6.0 (MINOR)
  fix: handle edge case              → 1.6.0 (累计，但 MINOR 优先)
  feat!: rename endpoint             → 2.0.0 (MAJOR)
```

**规则**：
- 任何 `feat` → MINOR
- 任何 `BREAKING CHANGE` → MAJOR
- 仅 `fix` / `perf` → PATCH

### 1.4 自动化工具

```bash
# commitlint：检查提交消息格式
npm install --save-dev @commitlint/cli @commitlint/config-conventional
# 配合 husky 在 commit 时校验

# standard-version：自动 bump 版本 + 生成 CHANGELOG + 打 tag
npx standard-version

# release-please（Google 出品）：PR 化的版本管理
# 提交 feat 后，开一个 "Release PR" 自动生成
```

## 2. 代码示例

### 2.1 规范的提交消息

```bash
# ✅ 良好的提交
git commit -m "feat(api): add SSE streaming for workflow run endpoint

Allow clients to receive LLM output token-by-token using Server-Sent Events.
This improves perceived latency for long-running workflows.

Closes #1234"

# ✅ 简单的 bug 修复
git commit -m "fix(core): handle null inputs in code node"

# ✅ 破坏性变更（用 ! 标记）
git commit -m "feat(api)!: rename /v1/apps to /v1/applications"

# ✅ 带 BREAKING CHANGE footer
git commit -m "refactor(core): migrate to Pydantic v2

BREAKING CHANGE: All custom validators must be updated to Pydantic v2 API.
See https://docs.pydantic.dev/latest/migration/"
```

### 2.2 不规范的提交

```bash
# ❌ 没有 type
git commit -m "add new feature"

# ❌ type 大写
git commit -m "FEAT: add new feature"

# ❌ 描述超过 72 字符（不换行）
git commit -m "feat: this is a very long commit message that exceeds the recommended 72 character limit"

# ❌ 模糊不清
git commit -m "fix: bug"
```

### 2.3 配置 commitlint

```bash
# 安装
npm install --save-dev @commitlint/cli @commitlint/config-conventional

# commitlint.config.js
cat > commitlint.config.js <<EOF
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']],
    'subject-max-length': [2, 'always', 72],
  },
};
EOF

# 配合 husky 在 commit 时自动校验
npx husky add .husky/commit-msg 'npx commitlint --edit "$1"'
```

### 2.4 常见错误：忘记 scope

```bash
# ❌ 没 scope 难以追溯是哪个模块的改动
git commit -m "feat: add new feature"

# ✅ 加 scope 更清晰
git commit -m "feat(api): add new endpoint"
git commit -m "feat(web): add dark mode toggle"
git commit -m "fix(core): handle edge case"
```

## 3. dify 仓库源码解读

### 3.1 dify 的 commitlint 配置

**文件位置**：`/Users/xu/code/github/dify/web/.commitlintrc.json`（或类似）
**核心代码**（行 1-15）：

```json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "type-enum": [2, "always", [
      "feat", "fix", "docs", "style",
      "refactor", "perf", "test", "build",
      "ci", "chore", "revert"
    ]],
    "subject-max-length": [2, "always", 72],
    "header-max-length": [2, "always", 72],
    "scope-enum": [2, "always", [
      "api", "core", "web", "docs", "deps"
    ]]
  }
}
```

**解读**：
- 第 3-6 行：限制 type 必须在枚举内（提交时强制）
- 第 7-8 行：subject（标题）不超过 72 字符
- 第 9-14 行：限制 scope（作用域）为固定枚举，便于过滤
- **关键设计**：自动化校验让所有贡献者的提交风格统一

### 3.2 dify 的 release-please 配置

**文件位置**：`/Users/xu/code/github/dify/release-please-config.json`
**核心代码**（行 1-25）：

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "python",
  "package-name": "dify-api",
  "bump-minor-pre-major": false,
  "bump-patch-for-minor-pre-major": false,
  "include-component-in-tag": false,
  "changelog-path": "api/CHANGELOG.md",
  "packages": {
    ".": {
      "package-name": "dify"
    },
    "api": {
      "package-name": "dify-api"
    },
    "web": {
      "package-name": "dify-web"
    }
  }
}
```

**解读**：
- 第 3 行：`"release-type": "python"`——按 Python 项目的语义化版本规则
- 第 10-19 行：多包项目，每个子目录独立的 CHANGELOG
- **关键设计**：dify 是 monorepo，`release-please` 自动为每个子包独立 bump 版本和生成 CHANGELOG

### 3.3 dify 的提交历史示例

```bash
# 查看 dify 最近的提交
git log --oneline -20

# 输出示例：
# a1b2c3d feat(api): add SSE streaming for workflow
# d4e5f6 fix(core): handle null inputs in code node
# g7h8i9 refactor: extract SSRF proxy to helpers
# j1k2l3 docs: update API reference
# m4n5o6 chore(deps): bump flask to 3.1.3
# p7q8r9 test(api): add tests for workflow runner
```

**解读**：
- 所有提交都遵循 `<type>(<scope>): <description>` 格式
- `chore(deps)` 用于依赖升级，对用户无感
- `docs` / `test` 不影响发布版本号
- **关键设计**：通过约定让 `git log --oneline` 自带模块归属信息，便于代码溯源

## 4. 关键要点总结

- Conventional Commits 格式：`<type>(<scope>): <subject>`
- Type 决定版本号影响：`feat` → MINOR、`fix` → PATCH、`feat!` / `BREAKING CHANGE` → MAJOR
- SemVer：`MAJOR.MINOR.PATCH`，前缀 `-alpha.1` / `-rc.1` 表示预发布
- `commitlint` 在提交时校验格式
- `release-please` / `standard-version` 自动 bump 版本、生成 CHANGELOG、打 tag
- dify 用 `release-please` 管理多包（`dify-api`、`dify-web`）的版本发布
- 良好的提交规范让 `git log` 自带"模块归属 + 变更类型"信息

## 5. 练习题

### 练习 1：基础（必做）

为一个模拟项目写 5 个符合 Conventional Commits 规范的提交：1 个 feat、1 个 fix、1 个 refactor、1 个 docs、1 个 BREAKING CHANGE。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/release-please-config.json`，理解 dify 如何为多个子包（api、web）独立管理版本。

### 练习 3：挑战（选做）

为你的个人项目配置 commitlint + husky，并尝试用 `standard-version` 自动生成第一个 CHANGELOG。

## 6. 参考资料

- `/Users/xu/code/github/dify/release-please-config.json`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- Conventional Commits 官网：https://www.conventionalcommits.org/zh-hans/
- SemVer 官网：https://semver.org/lang/zh-CN/
- commitlint 文档：https://commitlint.js.org/
- release-please：https://github.com/googleapis/release-please

---

**文档版本**：v1.0
**最后更新**：2026-07-13