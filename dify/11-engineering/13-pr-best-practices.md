# 13 提 PR 的最佳实践

> 好的 Pull Request 不只是“把代码推上去”，而是把问题、方案、验证证据和审查路径组织成一个可快速理解的变更单元。

## 🎯 学习目标

完成本文档后，你将能够：

- 写出清晰、可搜索且能表达改动类型的 PR 标题
- 在 PR 描述中说明背景、方案、范围、验证和风险
- 使用 `Fixes #<issue>` 等语法关联 Issue
- 将大改动拆成 atomic change，降低 Review 与回滚成本
- 为 UI 改动提供有效截图或录屏
- 在请求 Review 前完成测试、Lint、类型检查和文档自检
- 看懂并正确填写 dify 的 Pull Request 模板

## 📚 前置知识

- Git 分支、Commit 与 GitHub Pull Request 基础（工作流详见 [Git 工作流](../01-fundamentals/31-git-workflow.md)；提交规范详见 [Conventional Commits](../01-fundamentals/32-conventional-commits.md)）
- Markdown 标题、列表、任务清单和表格语法
- 了解 Issue、CI（详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)）、Lint、Type Check 和自动化测试
- 建议先学习：[Code Review 的价值与流程](./11-code-review.md)
- 建议配合：[Reviewer 检查清单](./12-review-checklist.md)

## 🧭 核心概念

### PR 是可审查的变更单元

Pull Request 同时承担三种职责：

- **协作界面**：作者与 Reviewer 在此讨论设计与实现
- **质量门槛**：CI、测试和人工审查在此汇合
- **变更记录**：合并后，标题与描述解释系统为什么变化

因此，PR 质量不仅取决于代码，也取决于信息组织。一个 Reviewer 应能在阅读 diff 前回答：

- 为什么需要改
- 用户将观察到什么变化
- 改动范围在哪里
- 作者如何证明它正确
- 哪些风险最值得检查

### 标题应具体且可搜索

标题应简洁表达“范围 + 行为变化”，例如：`fix(api): reject empty email during batch import`、`feat(web): add before/after preview for theme settings` 或 `refactor(workflow): reuse domain error for missing node`。

避免以下标题：

- `fix bug`：不知道修了什么
- `update files`：只描述动作，不描述结果
- `changes requested`：无法作为长期变更记录
- 在标题塞入所有实现细节：难以阅读，细节应放在描述中

如果仓库有既定命名约定，应优先遵守仓库规则，而不是机械套用示例格式。

## 📝 写好 PR 描述

### Summary：先说结果

Summary 用一到三句话说明用户可观察变化及关联问题。好的 Summary 回答“这次 PR 改变了什么”，而不是罗列文件名。

例如：

> 批量导入用户时，现在会在进入异步通知流程前拒绝空邮箱，避免任务延迟失败。Fixes #842。

### Motivation：解释为什么

Motivation 提供 Issue 之外的必要上下文：

- 当前行为有什么问题
- 哪类用户或场景受影响
- 为什么现在需要处理
- 有哪些历史约束或兼容要求

Reviewer 理解动机后，才能判断实现是否解决根因，而不是只看代码能否运行。

### Changes：明确范围

Changes 应按行为或模块组织，避免逐文件复述 diff。建议同时写明：

- 做了什么
- 没有做什么
- 是否改变 API、Schema、配置或迁移
- 是否增加依赖
- 是否存在后续工作

“没有做什么”能阻止 Review 范围失控，也能暴露作者是否遗漏关键部分。

### Verification：提供证据

Verification 不要只写“测试通过”，应提供可复现信息：

- 执行了哪些命令
- 哪些自动化测试覆盖新行为
- 手动验证步骤与结果
- 异常路径如何验证
- 因环境限制未执行哪些检查

如果跳过测试，必须解释原因和替代证据。

### Risk 与回滚

风险说明可帮助 Reviewer 分配注意力。可考虑：

- 数据迁移与不可逆写入
- 权限或 tenant 隔离
- 并发、幂等和重试
- API 向后兼容
- 性能和资源消耗
- Feature Flag 与回滚步骤

小改动也可以写“低风险：仅修改测试文案，无运行时行为变化”，关键是明确判断依据。

## 🔗 关联 Issue

### 为什么先有 Issue

Issue 是需求、缺陷复现和方案讨论的入口，PR 是实现。先讨论有几个好处：

- Maintainer 可确认问题与优先级
- 避免多个贡献者重复实现
- 提前校准方案和范围
- PR Review 不必重新讨论需求是否成立

### Closing keyword

GitHub 支持在默认分支合并时自动关闭关联 Issue。常见语法包括 `Fixes #842`、`Closes #842` 和 `Resolves #842`。

dify 模板明确要求使用 `Fixes #<issue number>`。

注意：`#842` 只建立可点击引用，`Fixes #842` 才表达合并后的关闭关系。若 PR 只是部分工作，不应提前关闭 Issue，可写 `Related to #842` 并说明剩余事项。

## ⚛️ 拆分粒度：Atomic Change

### 什么是 Atomic Change

Atomic change 是一个目的清楚、可独立理解和验证的变更。它通常具有以下特点：

- 只解决一个主要问题
- 每个改动都服务于同一目标
- 测试与实现一起提交
- 合并后仓库仍处于完整状态
- 必要时可以单独回滚

原子改动不是机械追求“文件少”或“行数少”。一个跨 Controller、Service 和测试的修复仍可能是原子的，因为这些修改共同完成一个行为。

### 应拆分的信号

以下情况通常应拆成多个 PR：

- 同时修复无关 Bug 和增加新功能
- 重构与行为变化混在一起，难以判断差异来源
- 前后端改动可通过兼容接口独立上线
- 大规模重命名掩盖了少量业务变化
- 某一部分可以安全合并，另一部分仍需设计讨论

一种常见拆法是：

1. 先做不改变行为的重构，并用现有测试证明等价
2. 再用单独 PR 增加行为和对应测试

### 不应错误拆分的情况

不要把完整行为拆成多个无法独立工作的 PR，例如先提交生产代码、以后再补测试。每个 PR 合并后都应保持可构建、可测试和可运行。

## 🖼️ 截图与录屏

### 什么时候需要

以下变化应提供视觉证据：

- 页面布局、间距、颜色和响应式行为
- 交互流程、动画和状态切换
- 错误、空状态、加载状态和禁用状态
- 跨浏览器或移动端问题

纯后端改动可在 Screenshots 中写“无 UI 改动”，不要保留模板中的 `...`。

### 如何提供有效证据

截图或录屏应做到：

- Before/After 使用相同窗口尺寸和数据
- 标注验证的页面、状态和浏览器
- 避免包含 Token、邮箱或真实用户数据
- 动态交互优先使用短录屏
- 响应式改动提供关键 viewport
- 截图之外仍需自动化测试，视觉证据不能替代行为验证

## ✅ 请求 Review 前的自检

### 代码自检

先从 Reviewer 视角完整阅读 diff：

- 是否包含调试输出、临时文件或无关格式变化
- 命名和注释是否与最终方案一致
- 是否意外提交密钥、个人路径或生成产物
- 新增依赖是否必要且锁文件同步
- 数据库、配置或 API 变化是否有迁移说明

### 自动化检查

根据改动范围运行项目要求的命令。dify 模板要求关注：

- Backend：`make lint && make type-check`
- Frontend：`cd web && pnpm exec vp staged`
- 改动对应的测试

如果某项无法本地运行，在 PR 中如实说明，不要直接勾选。

### 描述自检

提交前确认：

- 标题描述可观察行为
- Summary、动机与上下文完整
- 使用正确语法关联 Issue
- 测试命令和结果已记录
- UI 变化有截图或录屏
- 文档更新已完成或说明不需要
- 自动化 Agent 创建的 PR 标明工具来源

## 💻 代码示例

### 一个完整的 PR 描述范例

下面是独立示例，展示如何将标题、关联 Issue、范围、测试、视觉证据和风险放在一个紧凑描述中。

**示例文件**：`examples/pr-description.md`  
**示例代码**（行 1-40）：

```markdown
# fix(web): preserve filters after returning from app details

## Summary

从应用详情页返回列表时保留搜索词、状态过滤器和当前页。

Fixes #9124

## Motivation

用户检查多个应用时，每次返回都会丢失筛选条件，需要重复输入并翻页。

## Changes

- 将列表查询状态同步到 URL search params
- 从详情页返回时恢复搜索词、状态和页码
- 为缺失或非法页码提供默认值
- 增加 URL 状态序列化与恢复测试
- 不修改后端 API 或数据库结构

## Screenshots

| Before | After |
|--------|-------|
| 返回后重置列表 | 返回后保留筛选与页码 |

录屏：`artifacts/preserve-app-filters.webm`

## Verification

- [x] `pnpm exec vp staged`
- [x] 相关组件测试通过
- [x] 手动验证搜索、状态过滤、分页和浏览器后退
- [x] 验证非法 `page` 参数回退到第 1 页

## Risk and rollback

风险：旧书签可能包含非法查询参数；当前实现会忽略非法值并使用默认状态。
如需回滚，可恢复列表页的本地状态，不涉及数据迁移。

## Documentation

无需更新用户文档；页面功能与入口不变。
```

**说明**：

- 标题同时包含类型、范围和行为变化
- `Fixes #9124` 建立明确的 Issue 关闭关系
- Changes 既列出实现范围，也声明不涉及后端和数据库
- Verification 同时覆盖工具、自动化测试、手动路径和边界输入
- Risk 指出旧书签兼容问题，并给出无需数据操作的回滚方式

## 🔍 dify 仓库源码解读

### dify PR 模板如何约束最佳实践

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

- 第 3 行把贡献指南设为提交前必读材料，PR 不能脱离仓库协作规则
- 第 4-5 行要求 Issue 已关联、贡献者已被分配，并规范 `Fixes` 语法
- 第 7-10 行要求 Summary 不只概括改动，还要提供动机、上下文和依赖
- 第 10 行对自动化 Agent 的来源披露提出明确格式要求
- 第 12-16 行的 Before/After 表格适合 UI 变化；无 UI 改动时应明确写出，而非保留占位符
- 第 20、23 行分别检查文档需求与实际更新，提醒作者判断并落实文档同步
- 第 22 行把“每项改动有测试”和“尽量保持单一原子改动”绑定在一起
- 第 24 行列出后端与前端提交前检查，是请求 Review 前的最低自检证据

## 🚫 常见反模式

### 空洞描述

只写“修复问题，测试通过”会让 Reviewer 从头重建上下文。应说明触发条件、影响、改动范围和实际测试命令。

### 巨型 PR

数千行改动同时包含重构、功能和格式化时，Reviewer 很难建立可信心智模型。应尽早拆分，而不是在 Review 末期才处理。

### 截图替代测试

截图证明某一时刻看起来正确，却不能稳定验证交互、边界和回归。截图服务于理解，测试服务于重复验证，两者不能互相替代。

### 勾选未执行的检查

Checklist 是事实声明。如果环境限制导致命令不能运行，应取消勾选并写明原因、失败日志和替代验证。

### Review 后不断追加无关改动

Review 开始后追加功能会使旧反馈和批准失效。新发现的无关问题应另建 Issue 或 PR；必须追加时，主动提醒 Reviewer 重新检查。

## ✅ 关键要点总结

- 标题应表达范围和用户可观察变化，避免空洞描述
- PR 描述至少包含 Summary、Motivation、Changes、Verification 和 Risk
- 使用 `Fixes #<issue>` 建立合并后自动关闭关系；部分工作只做普通关联
- Atomic change 围绕一个目的，可独立验证和回滚，但不等同于机械限制文件数
- UI 变化应附一致环境下的截图或录屏，并保护敏感数据
- 请求 Review 前应自行阅读 diff、运行项目检查、同步测试与文档
- dify 模板把 Issue、测试、原子改动、文档和本地检查设为显式门槛

## 📝 练习题

### 练习：基础（必做）

把标题 `update workflow files` 改写成三个更具体的候选标题，分别适用于 Bug 修复、新功能和重构，并解释每个标题表达了什么行为。

### 练习：进阶

你有一个 PR 同时包含“重命名 40 个类”“修复权限校验”“更新设置页颜色”。设计一个拆分方案，说明每个 PR 的目标、合并顺序和验证方式。

### 练习：挑战（选做）

选择一个最近的真实 PR，仅根据标题和描述写出你认为 Reviewer 应重点检查的五项风险；随后阅读 diff，判断描述是否提供了足够信息，并重写不足部分。

## 🔗 参考资料

- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- GitHub Docs：Linking a pull request to an issue
- GitHub Docs：About pull requests
- Google Engineering Practices：Small CLs

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
