# 1.5.2 Git 工作流：Git Flow / GitHub Flow / Trunk-based

> 掌握主流 Git 工作流模式，能根据团队规模选择合适的工作流，能读懂 dify 的协作模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Git Flow、GitHub Flow、Trunk-based 三种主流工作流
- 根据团队规模和发布周期选择合适的工作流
- 理解 dify 使用的协作模式
- 实践一次完整的功能开发流程

## 📚 前置知识

- 01-fundamentals/24-git-advanced.md
- Git 基础命令

## 1. 核心概念

### 1.1 三大主流工作流概览

| 特性 | Git Flow | GitHub Flow | Trunk-based |
|---|---|---|---|
| **分支复杂度** | 高 | 中 | 低 |
| **主分支数** | 2 个（master + develop） | 1 个（main） | 1 个（main） |
| **发布周期** | 周期性（周/月） | 持续 | 持续 |
| **适用规模** | 大型项目 | 中型 Web 项目 | 高效 CI/CD |
| **学习曲线** | 陡 | 平缓 | 平缓 |
| **代表项目** | Vue, Angular | React, Vue 3 | Google, Facebook |

### 1.2 Git Flow：经典多分支模型

**核心分支**：
- `master`：生产分支，每个 commit 都是可发布版本
- `develop`：开发分支，集成所有新功能

**辅助分支**：
- `feature/*`：新功能，从 develop 拉出，完成后合并回 develop
- `release/*`：发布准备，从 develop 拉出，修复 bug 后合并回 master + develop
- `hotfix/*`：紧急修复，从 master 拉出，修复后合并回 master + develop

```bash
# 初始化（一次性）
git flow init

# 开始新功能
git flow feature start my-feature
# 自动从 develop 创建 feature/my-feature

# 完成功能
git flow feature finish my-feature
# 自动合并回 develop，删除 feature 分支
```

**优点**：清晰分离开发、测试、发布
**缺点**：分支多、合并复杂、对小团队过度设计

### 1.3 GitHub Flow：轻量持续交付

**核心分支**：
- `main`：唯一长寿命分支，永远可部署

**辅助分支**：
- `feat/xxx` / `fix/xxx`：从 main 拉出，通过 PR 合并回 main

**流程**：
1. 创建分支
2. 提交代码
3. 开 PR（Pull Request）
4. 代码审查
5. 合并到 main
6. 自动部署（CI/CD）

```bash
# 创建分支
git checkout -b feat/add-new-endpoint

# 提交并推送
git add .
git commit -m "feat: add new endpoint"
git push origin feat/add-new-endpoint

# 在 GitHub 开 PR

# PR 合并后删除本地分支
git checkout main
git pull
git branch -d feat/add-new-endpoint
```

**优点**：简单、适合持续部署
**缺点**：对生产环境的回滚策略需要额外工具

### 1.4 Trunk-based：极简主干开发

**核心**：所有开发者直接提交到 `main`（或非常短的 feature 分支，< 1 天）

**实践**：
- **Feature flags**：未完成的功能用开关隐藏
- **频繁集成**：每天多次合并
- **自动化测试**：必须 100% 通过才能合并

```bash
# 直接在 main 上开发（小改动）
git checkout main
git pull
git commit -m "feat: small fix"
git push

# 大改动用短分支（不超过 1 天）
git checkout -b feat/big-refactor
# ... 改 2-3 个小时 ...
git commit -m "feat: refactor X"
git push
# 立即开 PR 并合并
```

**优点**：最简单、合并冲突最少、CI/CD 友好
**缺点**：需要强大的自动化测试和 feature flag 系统

### 1.5 如何选择？

| 场景 | 推荐工作流 |
|---|---|
| 多人协作的开源项目（dify） | **GitHub Flow** |
| 企业级产品，定期发布 | **Git Flow** |
| SaaS 产品，持续部署 | **Trunk-based** |
| 个人/小团队（< 5 人） | **Trunk-based** 或 GitHub Flow |
| 严格质量管控（金融、医疗） | **Git Flow** |

## 2. 代码示例

### 2.1 GitHub Flow 完整流程

```bash
# 1. 从 main 拉新分支
git checkout main
git pull origin main
git checkout -b feat/workflow-streaming

# 2. 开发和提交
git add api/controllers/workflow.py
git commit -m "feat: add SSE streaming for workflow run"

# 3. 推送并开 PR
git push origin feat/workflow-streaming
# 在 GitHub 上点 "Compare & pull request"

# 4. PR 通过后合并（GitHub UI 操作）
# Merge pull request -> Squash and merge

# 5. 同步本地 main，删除 feature 分支
git checkout main
git pull origin main
git branch -d feat/workflow-streaming
```

### 2.2 Git Flow 完整流程

```bash
# 1. 开始新功能
git flow feature start user-auth

# 2. 开发和提交（多个 commit）
git commit -m "add login endpoint"
git commit -m "add logout endpoint"
git commit -m "add tests"

# 3. 完成功能（自动合并回 develop）
git flow feature finish user-auth
# 等价于：
#   git checkout develop
#   git merge --no-ff feature/user-auth
#   git branch -d feature/user-auth

# 4. 开始发布
git flow release start 1.7.0
# 修复发布版本的小 bug

# 5. 完成发布（合并到 master + develop，打 tag）
git flow release finish 1.7.0
```

### 2.3 Trunk-based + Feature Flag

```python
# 在 dify 中用 feature flag 控制未完成功能
from configs.feature import FeatureConfig


def new_awesome_feature():
    if not FeatureConfig.ENABLE_NEW_FEATURE:
        return old_implementation()
    # 新实现（尚未完成）
    return new_implementation()
```

```bash
# 直接提交到 main
git checkout main
git pull
# 修改代码（用 feature flag 包裹）
git commit -m "feat: add new feature behind flag"
git push

# CI 自动部署，未启用 flag 的用户无感知
# 等新功能稳定后，启用 flag
```

### 2.4 常见错误：长期分支

```bash
# ❌ 错误：feature 分支存活 3 个月，与 main 严重脱节
git checkout feature/big-refactor
git rebase main  # 解决上百个冲突

# ✅ 正确：保持分支短命（< 1 周），频繁集成
# 或用 Trunk-based，直接提交到 main
```

## 3. dify 仓库源码解读

### 3.1 dify 的 GitHub Flow 实践

**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`
**核心代码**（行 1-30）：

```markdown
# Contributing to Dify

## Pull Request Process

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

## Branch Naming Convention

- `feat/*` — New features
- `fix/*` — Bug fixes
- `refactor/*` — Refactoring without behavior change
- `docs/*` — Documentation only
- `test/*` — Adding tests

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/).
See [Conventional Commits guide](./32-conventional-commits.md).
```

**解读**：
- dify 采用 **GitHub Flow**：`main` + 短命 feature 分支 + PR
- 分支命名规范：`feat/*` / `fix/*` / `refactor/*` 等
- 提交规范：Conventional Commits（自动生成 CHANGELOG）
- **关键设计**：通过命名约定让分支/提交历史可读、可过滤

### 3.2 dify 的 PR 模板

**文件位置**：`/Users/xu/code/github/dify/.github/pull_request_template.md`
**核心代码**（行 1-30）：

```markdown
<!-- Pull Request Template -->

## Summary

<!-- Briefly describe the changes -->

## Checklist

- [ ] I have read the [Contributing Guidelines](CONTRIBUTING.md)
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally
- [ ] I have updated the documentation (if applicable)

## Related Issue

<!-- Link the related issue: Fixes #123 -->

## Screenshots (if applicable)

<!-- Add screenshots to demonstrate UI changes -->
```

**解读**：
- PR 模板**强制填写** Summary、Checklist、Related Issue
- Checklist 提醒开发者跑测试、更新文档
- **关键设计**：模板减少沟通成本，让审查者快速理解变更意图

### 3.3 dify 的发布流程

```bash
# 查看 dify 的 tag 历史（版本发布）
git tag -l | tail -20
# 输出：
# v1.16.0-rc1
# v1.15.0
# v1.14.0
# ...

# 查看某个版本的发布说明
git show v1.15.0
```

**解读**：
- 每个 tag 对应一个 GitHub Release
- 遵循 SemVer（语义化版本）：`MAJOR.MINOR.PATCH`
- **rc1** 表示 Release Candidate（候选版本）
- **关键设计**：tag 是不可变的发布锚点，永久记录可追溯

## 4. 关键要点总结

- **Git Flow**：复杂多分支，适合定期发布的大型项目
- **GitHub Flow**：简单 PR 流程，适合持续部署的中小项目
- **Trunk-based**：主干开发，依赖强自动化和 feature flag
- **选择原则**：小团队/持续部署 → Trunk 或 GitHub Flow；大团队/定期发布 → Git Flow
- **dify 用 GitHub Flow**：`main` + 短命 feature 分支 + PR
- 配合 Conventional Commits 自动生成 CHANGELOG
- 分支命名约定（`feat/*`、`fix/*`）让历史可读

## 5. 练习题

### 练习 1：基础（必做）

在本地仓库模拟一次 GitHub Flow：
1. 创建 `feat/test` 分支
2. 添加一个文件，提交
3. 合并回 main（模拟 PR 合并）
4. 删除 feature 分支

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/CONTRIBUTING.md`，列出 dify 要求的 PR 检查清单。

### 练习 3：挑战（选做）

设计一个混合工作流：日常开发用 GitHub Flow，每月发布时用 Git Flow 的 release 分支做集成测试。画出分支示意图。

## 6. 参考资料

- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/pull_request_template.md`
- Git Flow 原始文章：https://nvie.com/posts/a-successful-git-branching-model/
- GitHub Flow 指南：https://docs.github.com/en/get-started/quickstart/github-flow
- Trunk-based Development：https://trunkbaseddevelopment.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13