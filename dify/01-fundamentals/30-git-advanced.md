# 1.5.1 Git 进阶：`rebase` / `cherry-pick` / `bisect`

> 掌握 Git 高级命令，能优雅地整理提交历史、移植补丁、定位引入 bug 的提交。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `rebase` 整理提交历史
- 用 `cherry-pick` 移植特定提交
- 用 `bisect` 二分查找引入 bug 的提交
- 用 `reflog` 找回丢失的提交

## 📚 前置知识

- Git 基础：`commit`、`branch`、`merge`、`push`、`pull`
- 命令行基础

## 1. 核心概念

### 1.1 Git 内部模型（30 秒复习）

Git 是一个**内容寻址文件系统**：
- 每个 commit 指向一个 tree（目录快照）
- 每个 commit 指向父 commit（s）
- 分支只是指向某个 commit 的**可移动指针**

```
A ← B ← C ← D   (master)
       \
        E ← F   (feature)
```

### 1.2 `rebase` vs `merge`：整理历史

**Merge**：保留分支的"分叉-合并"形态：

```
       C ← D   (feature)
      /     \
A ← B ─────── M   (master，merge commit)
```

**Rebase**：把 feature 的提交"重放"到 master 之后，历史变直线：

```
A ← B ← C ← D ← E ← F   (master，feature rebase 后)
```

```bash
# 在 feature 分支执行
git rebase master
# 把 feature 的提交一个个 cherry-pick 到 master 最新 commit 之后

# 交互式 rebase（编辑提交历史）
git rebase -i HEAD~5   # 编辑最近 5 个提交
# 可选操作：pick / reword / edit / squash / fixup / drop
```

### 1.3 `cherry-pick`：移植单个提交

```bash
# 把另一个分支的某个 commit 应用到当前分支
git cherry-pick <commit-hash>

# 移植多个连续提交
git cherry-pick <hash1>..<hash2>

# 不自动提交，只应用修改
git cherry-pick --no-commit <hash>
```

**适用场景**：
- 修复 bug 的提交需要同步到多个发布分支
- 从 feature 分支借一个提交到 hotfix

### 1.4 `bisect`：二分查找坏提交

```bash
# 启动 bisect
git bisect start

# 标记当前 commit 为坏
git bisect bad

# 标记某个已知的"好" commit
git bisect good v1.0

# Git 自动 checkout 中间 commit，测试后告诉它好坏
git bisect good   # 这个 commit 没问题
git bisect bad    # 这个 commit 有问题

# 重复直到定位到引入 bug 的第一个 commit

# 结束 bisect
git bisect reset
```

**自动化**：提供脚本自动判断好坏：

```bash
git bisect run ./test.sh
# test.sh 退出 0 = good，非 0 = bad
```

### 1.5 `reflog`：找回丢失的提交

几乎所有"丢失"的 commit 都能通过 `reflog` 找回：

```bash
# 查看 HEAD 的历史（即使分支被删、reset 也能找回）
git reflog

# 输出：
# a1b2c3d HEAD@{0}: reset: moving to main
# e4f5g6h HEAD@{1}: commit: fix bug
# i7j8k9l HEAD@{2}: checkout: moving from feature to main

# 找回 e4f5g6h 这个 commit
git checkout e4f5g6h
git branch recovery e4f5g6h
```

## 2. 代码示例

### 2.1 交互式 rebase 整理提交

```bash
# 假设最近 5 个提交比较乱
git rebase -i HEAD~5

# 编辑器打开，类似：
# pick a1b2c3 Add API
# pick d4e5f6 Fix typo
# pick g7h8i9 WIP
# pick j1k2l3 Add tests
# pick m4n5o6 Update docs

# 修改为：
# pick a1b2c3 Add API
# squash d4e5f6 Fix typo    # 合并到上一个
# drop g7h8i9 WIP           # 丢弃
# pick j1k2l3 Add tests
# pick m4n5o6 Update docs
```

**结果**：原本 5 个 commit 变成 3 个，WIP 被丢弃，typo 被合并到 API commit。

### 2.2 移植 hotfix 到 release 分支

```bash
# 场景：在 main 分支修复了一个 bug，需要同步到 release-1.0

# 1. 切到 release 分支
git checkout release-1.0

# 2. 找到 main 上修复 bug 的 commit
git log main --oneline | grep "fix"
# a1b2c3d fix: app crash on empty inputs

# 3. cherry-pick
git cherry-pick a1b2c3d

# 4. 推送
git push origin release-1.0
```

### 2.3 用 bisect 找引入性能问题的 commit

```bash
# 启动
git bisect start
git bisect bad              # 当前有性能问题
git bisect good v1.2.0      # v1.2.0 没这个问题

# 自动化测试
git bisect run python -c "
import subprocess
result = subprocess.run(['./benchmark'], capture_output=True)
exit(0 if result.returncode == 0 else 1)
"

# bisect 完成后会输出第一个引入问题的 commit hash
# 比如：m4n5o6 引入性能问题
git bisect reset
```

### 2.4 常见错误：在公共分支上 rebase

```bash
# ❌ 危险：在已推送的分支上 rebase，会改写历史
git checkout main
git rebase feature    # main 上有别人提交，rebase 会重写 main 历史
git push --force      # 强推会覆盖别人的提交

# ✅ 安全：只 rebase 自己的 feature 分支
git checkout feature
git rebase main       # 把 feature 接到最新 main 后面
git push --force-with-lease  # 比 --force 更安全
```

## 3. dify 仓库源码解读

### 3.1 dify 的 `.git-blame-ignore-revs`

**文件位置**：`/Users/xu/code/github/dify/.git-blame-ignore-revs`
**核心代码**（行 1-20）：

```gitignore
# 这是 dify 仓库中忽略 blame 的 commit 列表
# 用于批量格式化、迁移等"无关紧要"的 commit
# 配置方法：
#   git config blame.ignoreRevsFile .git-blame-ignore-revs

# 2024-01-15 批量格式化 Python 代码（black）
abc123def456...

# 2024-06-20 重命名 controllers 模块
789ghi012jkl...
```

**解读**：
- 配置 `blame.ignoreRevsFile` 后，`git blame` 不会把这些 commit 显示为某行的最后修改者
- 避免被格式化 commit "抢走"真正的代码作者
- **关键设计**：大型项目用此文件保持 blame 历史的清洁

### 3.2 dify 的分支策略

```bash
# 查看 dify 仓库的分支结构
git branch -a | head -20
# 输出：
# * main                    ← 主分支，最新开发
#   0.6.x                  ← 维护中的旧版本
#   0.5.x                  ← 旧版本
#   remotes/origin/feat/xxx  ← 功能分支
#   remotes/origin/fix/xxx   ← bugfix 分支
```

**解读**：
- `main` 是开发分支
- `0.6.x` / `0.5.x` 等是长期维护的 LTS 分支
- Feature 分支命名 `feat/xxx`，fix 分支命名 `fix/xxx`
- **关键设计**：dify 采用 **GitHub Flow 简化版**，所有 PR 合并到 main，发布时打 tag

### 3.3 dify 的提交规范

**Conventional Commits 规范**（详见 1.5.3 章节）：

```bash
# 查看最近的提交格式
git log --oneline -20
# 输出示例：
# a1b2c3d feat(api): add workflow streaming endpoint
# d4e5f6 fix(core): handle null inputs in code node
# g7h8i9 refactor: extract SSRF proxy to helpers
```

**解读**：
- 格式：`<type>(<scope>): <description>`
- 类型：`feat` / `fix` / `refactor` / `docs` / `test` / `chore`
- 范围：可选，如 `api`、`core`、`web`
- **关键设计**：统一的提交规范便于自动生成 CHANGELOG

## 4. 关键要点总结

- `rebase`：把分支提交"重放"到目标分支之后，历史变直线
- `cherry-pick`：移植单个或多个连续 commit 到当前分支
- `bisect`：二分查找引入 bug 的 commit，可自动化
- `reflog`：找回几乎所有"丢失"的 commit
- **永远不要在公共分支上 rebase + force push**
- 用 `.git-blame-ignore-revs` 忽略批量格式化的 commit
- dify 用 Conventional Commits 规范，便于自动生成 CHANGELOG

## 5. 练习题

### 练习 1：基础（必做）

创建一个临时分支，做 3 个乱七八糟的提交，然后用 `git rebase -i` 整理：合并前两个为 1 个，丢弃第 3 个。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/.git-blame-ignore-revs`，理解 dify 为何要忽略某些 commit。

### 练习 3：挑战（选做）

在 dify 仓库的 git 历史中，找出"第一个引入某个特性"的 commit（提示：用 `git log --all --oneline | grep "feat: xxx"` + `git log` 配合 tag 过滤）。

## 6. 参考资料

- `/Users/xu/code/github/dify/.git-blame-ignore-revs`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- Pro Git 中文版：https://git-scm.com/book/zh/v2
- Learn Git Branching（交互式）：https://learngitbranching.js.org/?locale=zh_CN

---

**文档版本**：v1.0
**最后更新**：2026-07-13