# 14 dify 的 PR 规范

> 参与 dify 贡献时，先用 Issue 对齐问题与方案，再按仓库模板提交包含测试、文档、视觉证据和本地检查结果的原子 PR。

## 🎯 学习目标

完成本文档后，你将能够：

- 根据 `CONTRIBUTING.md` 描述 dify 从 Issue 讨论到合并的 PR 流程
- 理解“Before you draft a PR, please create an issue”的协作目的
- 正确使用 `Fixes #<issue number>` 关联并自动关闭 Issue
- 逐项填写 `.github/PULL_REQUEST_TEMPLATE.md`
- 提炼并执行模板 Checklist 中的五条关键要求
- 为后端、前端和自动化 Agent 创建的 PR 提供对应证据

## 📚 前置知识

- GitHub Issue、Fork、Branch 与 Pull Request 基础
- Markdown 注释、表格和任务清单语法
- 了解 Lint、Type Check、测试和文档更新
- 建议先学习：[提 PR 的最佳实践](./13-pr-best-practices.md)
- 建议配合：[Reviewer 检查清单](./12-review-checklist.md)

## 🧭 核心概念

### dify 的规范来源

本篇聚焦两个仓库文件：

- `.github/PULL_REQUEST_TEMPLATE.md`：创建 PR 时直接呈现给作者的填写模板
- `CONTRIBUTING.md`：贡献流程、Issue 要求、测试与项目设置说明

二者职责不同：贡献指南解释完整流程，PR 模板把最关键要求放到提交现场，减少遗漏。若模板文字与仓库当前自动化检查存在变化，应结合实际 CI 和维护者反馈确认；但提交时不应跳过模板中的明确要求。

### Issue First：先讨论，再实现

`CONTRIBUTING.md` 明确写道：

> Before you draft a PR, please create an issue to discuss the changes you want to make

这里的重点不是增加手续，而是让代码实现前先对齐：

- 问题是否真实存在，是否属于 dify 仓库范围
- Feature 或 Bug 的优先级
- 预期行为和验收标准
- 方案是否符合架构与产品方向
- 是否已有其他贡献者处理相同问题

PR 模板进一步要求存在关联 Issue，而且贡献者已经被分配到该 Issue。对于 typo，模板说明“无前置讨论可能关闭”的规则不适用；除此之外，应先创建或选择 Issue，并等待必要确认。

### `Fixes #<issue>` 的语法

模板指定使用 `Fixes #<issue number>`，例如 `Fixes #38651`。

当 PR 合并到默认分支时，GitHub 会根据 closing keyword 自动关闭对应 Issue。使用时注意：

- `Fixes` 与 `#编号` 之间保留空格
- 使用真实 Issue 编号，不保留尖括号
- 最好放在 PR 描述的 Summary 附近，便于维护者看到
- 仅写 `#38651` 通常只是引用，不表达自动关闭意图
- 如果 PR 只完成 Issue 的一部分，写 `Related to #38651`，不要错误关闭
- 跨仓库 Issue 可使用 `Fixes owner/repository#123`，但应先确认维护流程

### PR 模板是提交契约

模板中的 HTML 注释不会显示在最终渲染内容中，但它们是作者填写指南。提交前应：

- 用真实内容替换 `Summary` 下方的提示
- 替换 Screenshots 表格中的 `...`
- 对不适用的截图明确写“无 UI 改动”
- 只勾选实际完成的 Checklist
- 删除无意义占位内容，但保留有助于 Reviewer 的结构

## 🔄 dify PR 完整流程

### Fork 仓库

外部贡献者先 Fork dify 仓库，在自己的远程仓库中创建分支和提交。Fork 让贡献者拥有推送权限，同时通过 PR 将改动送回上游仓库。

### 创建 Issue 并讨论

在写实现前创建 Issue。Bug Issue 应提供清晰标题、详细描述、复现步骤、预期行为、日志和必要截图；Feature Issue 应说明功能、使用场景和上下文。

维护者确认方向后，确保你已被分配到该 Issue。模板把“关联且已分配”列为重要前提。

### 创建新分支

从正确基线创建聚焦分支。分支只服务于当前 Issue，不混入其他实验或无关格式化。分支名可表达类型和范围，例如 `fix/batch-import-empty-email` 或 `feat/workflow-run-filter`。具体命名仍应遵守仓库当时的维护者约定。

### 实现并添加测试

贡献指南要求按改动添加测试。测试应证明新功能的主要行为、Bug 的原始复现场景、关键边界与异常路径，以及修改不会破坏已有行为。

模板还要求尽可能保持 single atomic change。实现、必要测试和对应文档应组成一个完整、可独立验证的变更。

### 运行现有检查

贡献指南要求代码通过现有测试。模板具体列出后端命令 `make lint && make type-check`，以及前端命令 `cd web && pnpm exec vp staged`。此外还应运行改动对应的测试。若命令因本地环境无法执行，PR 中应清楚说明，而不是勾选已完成。

### 填写模板并关联 Issue

Summary 应包含改动摘要、修复的 Issue、动机、上下文和依赖，并使用 `Fixes #<issue_number>`。

UI 改动填写 Before/After 截图。自动化 Agent 创建的 PR 要在描述最后一行添加 `From <Tool Name>`，例如模板给出的 `From Codex`。

### Review、修改与合并

提交后等待 CI 与同行 Review，逐条回应反馈并推送修正。更新后重新运行受影响的检查。满足以下条件后才能合并：

- Issue 和改动范围已经对齐
- CI 与必要测试通过
- 阻塞 Review 意见已解决
- 文档与截图齐全
- PR 仍然是单一、可理解的原子改动

贡献指南最后一步是“Get merged!”；它是前述质量与协作条件完成后的结果。

## ☑️ 五条关键 Checklist

### 文档需求已经判断并落实

模板先询问变更是否需要 Dify Document 更新，又要求“已相应更新文档”。作者应明确区分：

- 用户功能、配置、部署方式变化：通常需要用户文档
- 内部接口、复杂约束或开发方式变化：可能需要代码注释或开发文档
- 纯测试或无行为重构：可以说明为何无需用户文档

不要机械地把所有项都打勾；不适用时应说明判断依据。

### 已有前置讨论或 Issue

模板警告：没有先前讨论或 Issue 的 PR 可能被关闭，typo 除外。这条要求保护维护者和贡献者双方，防止大量实现完成后才发现方向不接受。

### 每项改动有测试

测试与改动应一一对应。Bug 修复至少包含回归测试；新功能包含主要行为和边界；重构应由现有或新增测试证明行为不变。

### 尽可能保持单一原子改动

“Single atomic change”要求 PR 围绕一个目的。不要顺手清理无关文件、升级无关依赖或加入另一个功能。原子 PR 更容易 Review、合并和回滚。

### 已运行项目检查

模板列出后端和前端命令。只改后端时，前端命令可能不适用；只改前端时同理。作者应根据范围执行相关检查，并在 Verification 中记录命令与结果。

## 💻 代码示例

### 按 dify 规范填写 PR

这是独立示例，不是仓库源码。它展示 Bug 修复如何将 Issue、摘要、截图判断、测试和检查证据组合起来。

**示例文件**：`examples/dify-pr.md`  
**示例代码**（行 1-32）：

```markdown
## Summary

修复工作流运行列表按状态过滤后，翻页会丢失过滤条件的问题。
过滤状态现在会保留在分页请求中，不改变 API 响应结构。

Fixes #40001

Motivation: 用户排查失败运行时，需要在每一页重新选择状态。
Dependencies: None.

## Screenshots

无 UI 样式变化；该修复只影响已有分页操作的请求参数。

## Verification

- [x] 新增“过滤后翻到第二页”的回归测试
- [x] 验证无过滤条件时保持原有行为
- [x] `make lint`
- [x] `make type-check`
- [x] 目标单元测试通过

## Checklist

- [ ] This change requires a documentation update, included: Dify Document
- [x] I understand that this PR may be closed in case there was no previous discussion or issues.
- [x] I've added a test for each change and kept a single atomic change.
- [x] I've updated the relevant code comments; no user documentation change is required.
- [x] I ran the backend lint and type-check commands.

From Example Agent
```

**说明**：

- Summary 说明问题、结果和兼容边界，并使用 `Fixes #40001`
- Screenshots 没有保留占位符，而是解释为何不需要视觉对比
- Verification 列出回归、兼容和工具检查，而不是笼统写“已测试”
- 第一项文档 Checklist 未勾选，随后明确说明无需用户文档；这比虚假勾选更可信
- 最后一行披露自动化 Agent 来源，符合模板注释要求

## 🔍 dify 仓库源码解读

### `.github/PULL_REQUEST_TEMPLATE.md` 全文

**文件位置**：`/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`  
**核心代码**（行 1-24，全文）：

```markdown
> [!IMPORTANT]
>
> 1. Make sure you have read our [contribution guidelines](https://github.com/langgenius/dify/blob/main/CONTRIBUTING.md)
> 1. Ensure there is an associated issue and you have been assigned to it
> 1. Use the correct syntax to link this PR: `Fixes #<issue number>`.

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

- 第 3-5 行是三项提交前条件：阅读指南、关联并认领 Issue、使用正确 closing keyword
- 第 7-10 行定义 Summary 的信息密度，并要求自动化 Agent 披露来源
- 第 12-16 行提供 UI 变化的 Before/After 证据格式
- 第 18-24 行是作者声明：文档、前置讨论、测试、原子性和工具检查均已处理
- Checklist 不是装饰；每个勾选项都应能在 diff、CI 或 PR 描述中找到证据

### `CONTRIBUTING.md` 的 Submitting your PR 流程

用户指定的“Submitting your PR”流程内容位于行 63-72；下面连同上一级标题一起展示。

**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（行 61-72，其中流程为行 63-72）：

```markdown
## Submitting your PR

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

- 第 65 行从 Fork 开始，说明该流程面向外部贡献者
- 第 66 行明确要求 draft PR 前创建 Issue 并讨论，这是 dify PR 流程的核心入口条件
- 第 67 行要求新建分支，隔离当前贡献与其他工作
- 第 68-69 行连续强调添加测试并确保现有测试通过，既验证新行为也防止回归
- 第 70 行要求在描述中使用 `fixes #<issue_number>`；大小写不影响 GitHub keyword 语义，但填写模板时建议遵循模板展示的 `Fixes`
- 第 71 行的合并是前面步骤和 Review 通过后的结果，不是创建 PR 后立即发生的动作

## 🧩 模板各部分填写指南

### IMPORTANT 提醒

创建 PR 前逐项确认：

- 已阅读当前 `CONTRIBUTING.md`
- Issue 存在，且你已被分配
- PR 描述中包含 `Fixes #真实编号`

任何一项不满足，都应先补齐或向维护者确认，而不是删除提醒继续提交。

### Summary

推荐按以下顺序写：

1. 一句话说明行为变化
2. `Fixes #编号`
3. 说明动机和上下文
4. 列出依赖或写 `Dependencies: None`
5. 必要时说明兼容性、迁移或未覆盖范围

若由自动化 Agent 创建，在整个描述最后一行写 `From <Tool Name>`，而不是放在 Summary 中间。

### Screenshots

UI 改动替换 Before/After 单元格。非 UI 改动可以写 `Not applicable: no UI changes.`，不要保留 `...`，因为 Reviewer 无法判断作者是忘记填写还是认为不适用。

### Checklist

每个复选框都是可核验声明：

- 文档链接或“不需要”的理由
- 关联 Issue 与讨论记录
- 新增测试与 atomic change
- 实际文档改动
- 本地命令结果或 CI 结果

如果一项不适用，应保持未勾选并补一句说明，或按维护者认可的方式标注 `N/A`。

## ⚠️ 常见错误与修正

### 先写完代码，再询问是否接受

**问题**：方向、范围或仓库归属可能不符合维护计划。  
**修正**：遵循“Before you draft a PR, please create an issue”，先讨论并获得分配。

### 只写 Issue 编号

**问题**：`#123` 提供引用，但不能清楚表达合并后关闭。  
**修正**：完整写 `Fixes #123`；部分实现则写 `Related to #123`。

### 保留模板占位符

**问题**：`...` 和未处理注释让 PR 看起来未完成，也增加 Reviewer 猜测。  
**修正**：替换真实内容；不适用时明确写 N/A 和原因。

### 所有 Checklist 都直接勾选

**问题**：未执行命令或未更新文档却打勾，会损害 Review 信任。  
**修正**：每一项提供证据，受环境限制时如实记录。

### 一个 PR 混入多个目标

**问题**：违反 single atomic change，导致 Review、测试和回滚边界模糊。  
**修正**：把无关重构、功能和依赖升级拆成独立 PR，并在 Issue 中说明依赖顺序。

## ✅ 关键要点总结

- dify 贡献遵循 Fork → Issue 讨论 → 新分支 → 实现与测试 → 现有检查 → 关联 Issue → Review → 合并
- “Before you draft a PR, please create an issue”要求实现前先确认问题、范围与方案
- 使用 `Fixes #<issue number>`，合并默认分支后自动关闭完整解决的 Issue
- PR 模板要求 Summary、Screenshots 和 Checklist，自动化 Agent 还须披露工具来源
- 五项关键自检是文档判断、前置 Issue、每项改动有测试、single atomic change、运行项目检查
- 不适用的模板项应说明原因，不能保留占位符或虚假勾选

## 📝 练习题

### 练习：基础（必做）

下面哪种写法适合一个完整修复，并说明原因：`#123`、`Related to #123`、`Fixes #123`。再说明 PR 只完成一半工作时应选择哪一种。

### 练习：进阶

根据 `.github/PULL_REQUEST_TEMPLATE.md`，为一个“后端 API 修复、无 UI 变化、无需用户文档”的 PR 填写 Summary、Screenshots 和 Checklist。不能保留 `...`，也不能勾选未执行项。

### 练习：挑战（选做）

模拟一次外部贡献：写出 Issue 摘要、分支名、PR 标题、`Fixes` 语句、测试计划和五项 Checklist 证据。让同伴仅根据这些内容判断是否可以开始 Review。

## 🔗 参考资料

- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/feature_request.yml`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- GitHub Docs：Linking a pull request to an issue
- GitHub Docs：Creating a pull request from a fork

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
