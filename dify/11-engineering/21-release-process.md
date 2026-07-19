# 11.5.3 发布流程：语义化版本与 Changelog
> 用 SemVer 表达兼容性承诺，用 Changelog 解释用户可感知变化，再用可追踪的 PR 流程保证发布信息可信。
## 🎯 学习目标
完成本文档后，你将能够：
- 解释 `major.minor.patch` 三段版本号的兼容性语义
- 判断 Breaking Change、Feature 和 Bug Fix 应升级哪一段版本
- 按 Keep a Changelog 组织 Added、Changed、Fixed 等条目
- 区分 Git 提交历史、Changelog 与 GitHub Releases 的用途
- 设计从 Issue、PR、CI 到 Tag 和 Release Notes 的发布流程
- 理解 dify 的 PR 约束如何为发布归类和追踪奠定基础
## 📚 前置知识
- Git Commit、Tag、Branch 与 Pull Request 基础（详见 [Git 进阶](../../_common/15-git/01-git-advanced.md)、[Conventional Commits / SemVer](../../_common/15-git/03-conventional-commits.md)）
- 持续集成与自动化测试的基本概念（详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)）
- Markdown 链接、标题和列表语法
- 建议先阅读 `./13-pr-best-practices.md`
- 建议先阅读 `./20-contributing.md`
## 🧭 核心概念
### 发布不只是打一个 Tag
一个可维护的发布流程需要同时回答：
- **范围**：本次包含哪些变更，不包含哪些变更
- **质量**：经过了哪些测试、构建和安全检查
- **兼容性**：用户升级是否需要修改配置、代码或数据
- **可追踪性**：每个条目来自哪个 Issue 或 PR
- **可恢复性**：发布失败时如何回滚或发布补丁
- **可沟通性**：用户从哪里知道升级价值和风险
版本号负责压缩表达兼容性，Changelog 和 Release Notes 负责展开说明变化。
### SemVer 的基本形式
语义化版本使用：
```text
MAJOR.MINOR.PATCH
  2  .  4  .  1
```
- `MAJOR`：出现不向后兼容的公共接口变化
- `MINOR`：以向后兼容方式增加功能
- `PATCH`：以向后兼容方式修复问题
因此，从 `2.4.1`：
- 修复请求超时问题 → `2.4.2`
- 增加可选导出功能 → `2.5.0`
- 删除已公开但仍有人使用的配置项 → `3.0.0`
SemVer 是对“公共 API”的承诺。公共 API 不只指函数签名，也可能包括 CLI 参数、配置项、数据库格式、事件结构、插件协议和部署行为。
### Breaking Change 的判断
以下变化通常需要升级 Major：
- 删除、重命名或改变公共接口的含义
- 把可选字段改为必填字段
- 改变默认行为，导致现有系统产生不同结果
- 修改持久化格式且没有兼容迁移
- 停止支持仍在承诺范围内的运行时或平台
若提供完整兼容层，旧用法仍正常工作，则可以先在 Minor 中增加新接口并标记弃用，未来 Major 再删除旧接口。
### `0.y.z` 的现实约定
SemVer 规定 `0.y.z` 用于初始开发，公共 API 可能不稳定。实践中仍应写清楚项目自己的兼容承诺，不能把 `0.x` 当作随意破坏用户的借口。
例如可以约定：
- `0.MINOR.0` 可能包含 Breaking Change
- `0.y.PATCH` 只做向后兼容修复
- 每次破坏性变化必须提供迁移说明
### 预发布版本和构建元数据
SemVer 支持：
- 预发布：`2.5.0-alpha.1`、`2.5.0-rc.2`
- 构建元数据：`2.5.0+build.184`
预发布版本的优先级低于正式版，适合让社区提前验证。构建元数据不参与版本优先级判断，适合记录构建流水线信息。
### Changelog 不等于 Git Log
Git Log 记录实现过程，面向开发者；Changelog 记录用户可感知变化，面向升级者。
一个提交历史可能包含：
- 修复拼写
- 调整测试夹具
- Review 后重命名变量
- 合并主分支
这些对代码审计有价值，但不应逐条出现在 Changelog。Changelog 应按功能影响整合，并使用用户能理解的语言。
### Keep a Changelog 的结构
常见顶级结构是：
```text
Changelog
├── Unreleased
│   ├── Added
│   ├── Changed
│   ├── Deprecated
│   ├── Removed
│   ├── Fixed
│   └── Security
├── 2.5.0 - 2026-07-13
└── 2.4.1 - 2026-06-20
```
六个类别的含义：
- `Added`：新增能力
- `Changed`：现有行为变化
- `Deprecated`：未来会移除，但当前仍可用
- `Removed`：已删除的能力
- `Fixed`：缺陷修复
- `Security`：安全修复或安全相关说明
`Unreleased` 是待发布变更的缓冲区。发布时把条目移入带日期的版本章节，再创建新的空 `Unreleased` 区域。
### Changelog 条目的写法
好条目应包含：
- 用户能观察到的行为变化
- 影响范围或启用条件
- 必要时附迁移或规避说明
- 对应 PR 或 Issue 标识
差的写法：
```text
- Refactor service helper.
```
更好的写法：
```text
- Reduced workflow retry latency after transient provider failures (#4812).
```
后者说明用户收益，并保留追踪入口。
### GitHub Releases 的定位
GitHub Release 通常绑定 Git Tag，可以提供：
- 发布标题、版本说明和发布日期
- 二进制文件、校验和或安装包
- 自动生成的 PR 列表
- Full Changelog 比较链接
- 预发布或 Latest 标识
仓库可以同时维护 `CHANGELOG.md` 和 GitHub Releases，也可以只使用 Releases。关键是建立稳定入口，并确保自动生成内容经过人工编辑，突出 Breaking Change、迁移步骤和安全事项。
## 💻 代码示例（独立）
### 一段符合 Keep a Changelog 的条目
下面示例共 30 行，演示 `Unreleased`、版本日期、分类、迁移提示和版本比较链接。
```markdown
# Changelog

All notable changes to this project are documented in this file.
The format follows Keep a Changelog and Semantic Versioning.

## [Unreleased]

### Added

- Added CSV export for filtered audit events (#184).

### Changed

- New installations now enable strict cookie settings by default (#191).

### Fixed

- Prevented duplicate jobs after a worker reconnects (#188).

## [2.3.0] - 2026-07-13

### Added

- Added read-only API tokens with configurable expiration (#172).

### Deprecated

- Deprecated `LEGACY_TOKEN`; use `API_TOKEN` before version 3.0.0.

### Security

- Masked credentials in diagnostic logs (#179).

[Unreleased]: https://example.com/compare/v2.3.0...HEAD
[2.3.0]: https://example.com/compare/v2.2.1...v2.3.0
```
**说明**：
- 文件只收录 notable changes，而不是复制全部 Commit Message
- `Unreleased` 让贡献者在开发阶段归类条目，发布时不必回忆所有变化
- `Deprecated` 同时给出替代项和预计移除版本
- `Security` 描述效果，但不泄露可帮助攻击者利用未升级系统的细节
- 比较链接使读者可以继续检查完整代码差异
## 🔍 dify 仓库源码解读
### PR 流程是发布追踪的输入层
**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（行 63-72）：
```markdown
### Pull Request Process

1. Fork the repository
1. Before you draft a PR, please create an issue to discuss the changes you want to make
1. Create a new branch for your changes
1. Please add tests for your changes accordingly
1. Ensure your code passes the existing tests
1. Please link the issue in the PR description, `fixes #<issue_number>`
1. Get merged!

```
**解读**：
- Issue 先于 PR，让需求背景、优先级与验收条件在实现前可追踪
- 独立分支与聚焦 PR 使发布工具更容易按 PR 归类变更
- 新增测试和已有测试共同形成发布质量门禁的基础
- `fixes #<issue_number>` 把发布条目、实现与原始问题连接起来
- PR 合并只是进入可发布分支，并不等于版本已经发布；Tag、构建与 Release 仍是后续步骤
### PR 模板要求变更证据
**文件位置**：`/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`  
**核心代码**（行 6-24）：
```markdown
## Summary

<!-- Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context. List any dependencies that are required for this change. -->
<!-- If this PR was created by an automated agent, add `From <Tool Name>` as the final line of the description. Example: `From Codex`. -->

## Screenshots

| Before | After |
|--------|-------|
| ... | ... |

## Checklist

- [ ] This change requires a documentation update, included: [Dify Document](https://github.com/langgenius/dify-docs)
- [ ] I understand that this PR may be closed in case there was no previous discussion or issues. (This doesn't apply to typos!)
- [ ] I've added a test for each change that was introduced, and I tried as much as possible to make a single atomic change.
- [ ] I've updated the documentation accordingly.
- [ ] I ran `make lint && make type-check` (backend) and `cd web && pnpm exec vp staged` (frontend) to appease the lint gods
```
**解读**：
- Summary 收集动机、上下文、依赖与关联 Issue，可直接成为 Release Notes 的原始材料
- Before/After 截图让 UI 变化在 Review 和发布整理时更易理解
- 文档、测试、原子变更和本地检查清单降低把不完整变更带入发布分支的概率
- 自动化 Agent 需要披露工具名，增加变更来源透明度
### dify 的 Changelog 现状
在本次学习材料对应的 dify 仓库快照中，仓库根目录没有 `CHANGELOG.md`。因此不能把不存在的文件当作版本历史来源。
从协作文件可以看出，dify 以结构化 Issue、聚焦 PR、关联编号和测试门禁积累发布元数据；面向用户的版本变化主要通过 **GitHub Releases** 组织，并可基于 PR 自动归类后再编辑说明。
这种方式的优势是减少手工维护一个长期文件的冲突，局限是离线读取仓库时不一定能直接看到完整版本历史。因此：
- 查某次正式发布内容，应以对应 GitHub Release 为入口
- 查某项变化的动机与实现，应沿 Release → PR → Issue 追踪
- 自动生成分类不能替代人工突出 Breaking Change 和迁移步骤
- 不应根据“没有 CHANGELOG.md”推断项目没有发布说明
### 版本号的多源真相
dify 是 monorepo，至少有 4 处声明版本号：
| 组件 | 文件 | 当前版本 |
|---|---|---|
| 后端 API | `/api/pyproject.toml`（行 3） | `1.16.0-rc1` |
| 前端 Web | `/web/package.json`（行 4） | `1.16.0-rc1` |
| Agent Backend | `/dify-agent/pyproject.toml`（行 3） | `1.16.0-rc1` |
| CLI（difyctl） | `/cli/package.json`（行 4） | `0.2.0-alpha` |
**关键观察**：
- 三个核心组件**同版本号**——保证后端、前端、Agent 同步发布
- CLI 独立节奏（`0.2.0-alpha`）——还在快速迭代
- **多包发布必须先统一版本号**，否则会出现"前端 v1.16 调用后端 v1.15 缺失接口"
## 🚀 一个可靠的发布流程
### 准备阶段
- 冻结本次范围，确认阻塞 Issue 已关闭或明确延期
- 检查所有 PR 有类型标签、清晰 Summary 和关联 Issue
- 识别 Breaking Change、数据库迁移、配置变化和安全修复
- 确认版本号与兼容性影响一致
- 生成候选 Release Notes，并由功能负责人复核
### 验证阶段
- 运行 lint、类型检查、单元测试和关键 E2E 流程
- 在接近生产的环境执行升级演练
- 验证新安装与从上一受支持版本升级两条路径
- 检查数据库迁移是否可重复、可观测且有回滚方案
- 对容器、二进制或包进行签名或校验和验证
### 发布阶段
- 从受保护提交创建不可变 Tag
- 构建并发布制品，记录构建来源
- 创建 GitHub Release，加入升级提示和已知问题
- 更新 `Latest`、文档版本或安装渠道
- 监控错误率、回滚指标和社区反馈
### 发布后阶段
- 将遗漏但重要的说明补充到 Release Notes
- 对严重回归决定回滚或发布 Patch
- 把后续工作建立为 Issue，而不是遗留在聊天记录
- 复盘自动化失败、手工步骤和版本判断争议
## 🤖 发布自动化的真实样貌
dify 的发布是**半自动**的：核心构建由 CI 完成，但版本号、Tag、Release 由人创建。
### Docker 镜像 Tag 规则

> 📌 **Sighting**：镜像 / 仓库基础见 [Docker 核心概念](../../_common/09-containerization/01-concepts.md)；此处只关心发布时的 Tag 约定。
**文件位置**：`/Users/xu/code/github/dify/.github/workflows/build-push.yml`
**核心代码**（行 210-214）：
```yaml
tags: |
  type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/') && !contains(github.ref, '-') }}
  type=ref,event=branch
  type=sha,enable=true,priority=100,prefix=,suffix=,format=long
  type=raw,value=${{ github.ref_name }},enable=${{ startsWith(github.ref, 'refs/tags/') }}
```
**解读**：
- 第 2 行：`type=raw,value=latest`——只对**正式版**（无 `-` 后缀的 tag）打 `latest` 标签
- `1.16.0-rc1` 不会成为 `latest`——**预发布版不能污染正式渠道**
- 第 3 行：分支名作为镜像 tag（如 `build/feat-x`）——分支级预览
- 第 4 行：每个构建都有 SHA tag——可精确回溯
- 第 5 行：tag 名本身作为镜像 tag（如 `1.16.0`）——版本级拉取
- **关键设计**：`latest` 必须**仅**对应稳定版——避免 `docker pull dify` 拿到 RC 版
### CLI 发布渠道
**文件位置**：`/Users/xu/code/github/dify/cli/scripts/release-naming.mjs`
**核心代码**（行 26-32）：
```javascript
const CHANNELS = [
  { name: 'stable', prerelease: false, versionForm: /^\d+\.\d+\.\d+(\+[0-9A-Z.-]+)?$/i },
  { name: 'alpha',  prerelease: true,  versionForm: /^\d+\.\d+\.\d+-alpha(\.\d+)?$/ },
  { name: 'rc',     prerelease: true,  versionForm: /^\d+\.\d+\.\d+-rc\.\d+$/ },
  { name: 'edge',   prerelease: true,  versionForm: /^\d+\.\d+\.\d+-edge\.[0-9a-f]{7,40}$/ },
]
```
**解读**：
- 第 1 行：四种渠道——`stable`（正式版）、`alpha`（早期预览）、`rc`（候选发布）、`edge`（主分支即时构建）
- 每种渠道**正则校验**版本格式——不接受非法版本号
- `edge` 渠道用 `git short SHA` 后缀——天然支持任意 commit 都能发布
- **关键设计**：渠道正则把"什么版本属于什么渠道"编码成机器可读的规则——避免人工判断
### 手工与自动化的边界
| 步骤 | 责任人 | 频率 |
|---|---|---|
| 修改 `pyproject.toml` / `package.json` 版本号 | 人 | 每次发布 |
| 推送 git tag（如 `1.16.0`） | 人 | 每次发布 |
| 创建 GitHub Release | 人 | 每次发布 |
| 构建 Docker 镜像（api / web / agent） | 自动（tag push 触发） | 每次发布 |
| 构建 CLI 二进制（5 平台） | 自动（Release 事件触发） | 每次发布 |
| 校验和 / Provenance tag | 自动 | 每次发布 |
| Edge 渠道构建（主分支 push 触发） | 自动 | 每次 push |
| Hotfix cherry-pick 校验 | 自动 | 每个 hotfix PR |
| 实际部署到生产 | 人 + 内部 deploy 工具 | 每次发布 |
**关键观察**：
- **版本号和 Tag 必须由人创建**——避免机器误发布
- **构建和分发全自动化**——避免人为错误
- **部署是手工+内部工具**——最后一步必须由人确认
## 🏷️ PR 自动归类建议
发布自动化可以根据标签映射：
| PR 标签 | Release 分类 |
| --- | --- |
| `enhancement` | Added |
| `bug` | Fixed |
| `breaking-change` | Changed / Breaking Changes |
| `security` | Security |
| `documentation` | Documentation |
| `dependencies` | Maintenance |
`needs-triage` 不应该进入正式发布分类，因为它表示变更类型尚未确认。合并前清理标签，是生成高质量 Release Notes 的前提。
## ⚠️ 常见版本陷阱
### 把“大改动”当作 Major
代码改动很多不等于 Breaking Change。只要公共行为保持兼容，大型内部重构也可能只需要 Patch，甚至不需要单独发布条目。
### 把“新接口”当作 Patch
向后兼容的新能力通常应升级 Minor。Patch 表示修复，不应悄悄扩大公共能力，以免依赖方错误估计升级风险。
### 只写功能，不写迁移
“删除旧认证方式”说明了变化，却没有告诉用户怎么办。Breaking Change 必须附受影响对象、替代方案、迁移步骤和必要的回滚说明。
### 从 Commit Message 直接发布
Commit Message 粒度面向实现，经常包含噪音。应优先根据 PR Summary、标签和 Issue 验收条件生成，再由人类编辑面向用户的语言。
### 发布后移动 Tag
Tag 一旦对应公开版本，不应悄悄指向另一个提交。需要修复时发布新的 Patch，保持供应链和排障过程可审计。
## ✅ 关键要点总结
- SemVer 用 Major、Minor、Patch 表达公共接口兼容性
- Breaking Change 的判断依据是用户契约，不是代码行数
- Changelog 面向用户，Git Log 面向实现审计，两者不能互相替代
- Keep a Changelog 用 Unreleased 和六类变化建立稳定结构
- GitHub Releases 可以作为主要发布说明入口，并基于 PR 标签自动归类
- dify 当前根目录没有 `CHANGELOG.md`，其 Issue/PR 追踪体系为 Releases 提供基础
- 自动生成说明后仍需人工补充迁移风险、已知问题和重要变化
## 📝 练习题
### 练习：基础（必做）
判断下列变化应从 `1.4.2` 升级为什么版本，并解释理由：修复日志脱敏、增加可选导出格式、删除旧 CLI 参数。
**检查点**：是否分别得到 Patch、Minor 和 Major，并以公共兼容性而不是工作量解释？
### 练习：进阶
把最近十条 Commit Message 整理成一段 Keep a Changelog。删除内部噪音，合并重复修复，并给每个条目选择正确分类。
**检查点**：每一条是否描述用户可感知变化，是否保留追踪编号？
### 练习：挑战（选做）
设计一个从 PR 标签生成 GitHub Release 草稿的流程。要求说明未知标签、Breaking Change、回滚说明和人工审批如何处理。
**检查点**：自动化是否会阻止 `needs-triage` 或无分类 PR 被静默发布？
## 📖 参考资料
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/.github/workflows/semantic-pull-request.yml`
- `/Users/xu/code/github/dify/.github/workflows/post-merge.yml`
- Semantic Versioning 2.0.0：https://semver.org/
- Keep a Changelog：https://keepachangelog.com/
- GitHub Docs：Managing releases in a repository
- GitHub Docs：Automatically generated release notes
---
**文档版本**：v1.0  
**最后更新**：2026-07-13
