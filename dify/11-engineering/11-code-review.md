# 11 Code Review 的价值与流程

> Code Review（CR）不是寻找“谁写错了”，而是用协作式反馈让改动更正确、更易维护，并让团队共同理解代码。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释 Code Review 在知识共享、缺陷捕获、风格统一和团队建设方面的价值
- 描述“作者提 PR → 自动 CI → 同行 Review → 修改 → 合并”的完整流程
- 编写信息充分、便于 Reviewer 理解的 Pull Request 描述
- 区分自动化检查与人工 Review 各自擅长发现的问题
- 看懂 dify 的 PR 模板，并用它组织一次可审查的改动

## 📚 前置知识

- Git 的分支、提交、推送与合并基础
- GitHub Pull Request 的基本操作
- 能阅读 Markdown 文档
- 了解单元测试、Lint 和 Type Check 的基本作用

## 🧭 核心概念

### Code Review 是什么

Code Review 是代码进入共享分支前，由作者之外的开发者检查改动并提出反馈的协作过程。审查对象不只是代码语法，还包括：

- 改动是否真正解决了目标问题
- 实现是否符合项目架构和已有约定
- 边界条件、失败路径与安全风险是否被处理
- 测试是否足以证明行为正确
- 后续维护者能否快速理解设计意图

CR 的产物也不只是“Approve”或“Request changes”。高质量 Review 会形成可追踪的设计讨论、补充测试用例，并把个人经验转化为团队知识。

### 知识共享

提交者通常最了解当前改动，Reviewer 则可能更熟悉其他模块、历史约束或线上问题。双方通过 PR 讨论交换上下文：

- 作者说明问题背景、实现方案和取舍
- Reviewer 补充已有 helper、架构边界或历史经验
- 其他成员可通过 PR 记录理解“为什么这样实现”

知识共享能降低代码的“单点所有权”。当原作者不在线时，参与过 Review 的成员仍能维护相关模块。

### 缺陷捕获

自动化工具擅长发现格式、类型和已覆盖行为的问题，人工 Review 更擅长识别：

- 需求理解偏差
- 未覆盖的业务边界
- 不一致的事务或状态变更
- 错误的抽象层级
- 日志缺少关键上下文
- 测试只验证正常路径而未验证异常路径

Reviewer 应关注“系统在失败时会怎样”，而不仅是正常输入下代码是否能运行。

### 风格统一

统一风格的目的不是满足个人偏好，而是减少阅读成本。团队形成稳定约定后，开发者不必反复猜测：

- 变量、函数和类如何命名
- 错误应在哪一层转换
- 日志应包含哪些标识符
- 类型定义与测试应放在哪里
- 是否已有工具可以复用

可由 Formatter、Linter 自动决定的问题，应交给 CI；人工评论应聚焦工具无法判断的可读性和设计一致性。

### 团队建设

CR 是团队日常沟通的重要组成部分。健康的 Review 文化具有以下特点：

- 评论针对代码和影响，不针对作者
- 提问优先于武断命令，例如“这里是否需要处理空列表？”
- 区分阻塞问题与非阻塞建议
- 认可合理的实现和良好的测试
- 作者解释取舍，Reviewer 在新证据出现后愿意调整意见

长期来看，这种反馈机制会建立共同标准和心理安全感，让成员更愿意暴露不确定性并尽早求助。

## 🔄 标准 Review 流程

### 作者准备并提交 PR

作者先将改动整理为清晰、聚焦的提交，然后创建 PR。描述中至少应包含：

- 为什么需要这次改动
- 做了什么，以及刻意没有做什么
- 如何验证
- 风险和回滚思路
- 关联 Issue
- UI 改动的前后截图或录屏

PR 越小、上下文越完整，Reviewer 越容易给出及时且准确的反馈。

### 自动 CI 检查

PR 创建后，CI 通常执行格式、Lint、类型检查、单元测试和构建。CI 的职责是提供稳定、可重复的基础质量门槛。

如果 CI 失败，作者应先阅读日志并修复；不要让 Reviewer 重复发现机器已经明确报告的问题。特殊情况下若失败与改动无关，应在 PR 中记录原因和证据。

### 同行 Review

Reviewer 先理解 Issue 和 PR 描述，再按由大到小的顺序检查：

1. 目标和整体方案是否正确
2. 架构边界和数据流是否合理
3. 异常、边界和兼容性是否充分
4. 测试是否证明关键行为
5. 命名、注释和局部实现是否清晰

先讨论设计，再讨论局部风格，可以避免在最终会被替换的实现细节上浪费时间。

### 作者修改并回应

作者应逐条处理反馈：

- 同意：修改代码并说明如何处理
- 不同意：给出约束、数据或测试证据
- 不确定：继续提问，确认 Reviewer 的核心担忧
- 暂不处理：解释原因，并在需要时创建后续 Issue

不要只标记 conversation resolved 而不说明处理结果。新的提交推送后，应重新检查受影响的测试和 CI。

### 批准与合并

当阻塞意见解决、CI 通过、必要文档和测试齐全后，Reviewer 批准 PR。合并前还应确认：

- 分支未意外包含无关改动
- 合并策略符合仓库约定
- PR 标题和描述能成为清晰的变更记录
- 关联 Issue 的关闭语法正确

流程可以概括为：

**作者提 PR → 自动 CI → 同行 Review → 作者修改 → 重新检查 → 批准并合并**。如果 Reviewer 继续发现阻塞问题，则回到“作者修改”环节，直到反馈关闭。

## 💻 代码示例

### 一份便于 Review 的 PR 描述模板

下面是独立示例，可复制到其他项目后按实际情况填写。它同时提供背景、范围、验证方式和风险，避免 Reviewer 只能从 diff 猜测意图。

**示例文件**：`examples/reviewable-pr-description.md`  
**示例代码**（行 1-27）：

```markdown
## Summary

修复批量导入用户时，空邮箱被当作有效值写入数据库的问题。

Fixes #842

## Motivation

空邮箱会导致后续通知任务失败，而且错误要到异步任务阶段才暴露。

## Changes

- 在 service 层统一标准化邮箱输入
- 拒绝空字符串和仅包含空白符的值
- 为正常邮箱、空邮箱和缺失字段补充单元测试
- 不改变现有 API 响应结构

## Verification

- [x] 单元测试通过
- [x] Lint 与类型检查通过
- [x] 手动验证单条与批量导入

## Risk and rollback

风险集中在旧客户端传入空白邮箱的场景；可通过回滚本 PR 恢复旧行为。

## Screenshots

无 UI 改动。
```

**说明**：

- `Summary` 用一句话说明可观察行为，而不是只写“修复 bug”
- `Motivation` 解释不修改会造成什么影响
- `Changes` 明确改动范围，并主动说明兼容性边界
- `Verification` 给 Reviewer 可复现的验证依据
- `Risk and rollback` 迫使作者在提交前思考失败场景

## 🔍 dify 仓库源码解读

### dify 的 Pull Request 模板

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

- 第 1-5 行先放置强提醒：阅读贡献指南、关联并认领 Issue、使用 `Fixes #<issue number>`
- 第 7-10 行要求作者说明摘要、动机、上下文和依赖；自动化 Agent 创建的 PR 还要标明工具来源
- 第 12-16 行用 Before/After 表格降低 UI 变化的理解成本
- 第 18-24 行把文档、前置讨论、测试、原子改动和本地检查变成显式自检项
- 模板将“作者提 PR”标准化，使 Reviewer 在进入 diff 前就能获得必要上下文
- CI 命令与 Checklist 相互补充：作者先自检，平台再自动验证，Reviewer 最后判断业务和设计

## 🤝 如何写高质量 Review 评论

### 区分反馈级别

可以在评论前加上语义标签，减少作者猜测：

- `blocking:` 合并前必须处理的正确性、安全或架构问题
- `suggestion:` 更好的实现建议，不一定阻塞合并
- `question:` 需要补充上下文或确认假设
- `nit:` 很小的非阻塞风格建议
- `praise:` 指出值得保留或推广的良好实践

### 描述影响而不是只给结论

低信息量评论是“这里不对”。更有效的表达是：

> 当 `items` 为空时，这里仍会访问 `items[0]`，批量接口会返回 500。建议增加空列表分支，并补一个回归测试。

这条评论同时包含触发条件、用户影响、建议方向和验证要求，作者可以直接行动。

### 保持讨论可验证

意见不一致时，优先寻找可验证依据：

- 项目已有约定或相邻模块的实现
- 单元测试、类型检查或最小复现
- 性能数据或错误日志
- Issue 中已经确认的验收条件

CR 的目标是提高改动质量，不是证明谁的个人偏好更正确。

## ✅ 关键要点总结

- Code Review 同时服务于知识共享、缺陷捕获、风格统一和团队建设
- 标准流程是作者提 PR、CI 检查、同行 Review、修改反馈，最后批准合并
- 自动化工具负责可重复规则，人工重点审查需求、设计、边界和维护性
- PR 描述是 Review 的输入，应包含背景、范围、验证、风险和关联 Issue
- 评论应说明触发条件与影响，并明确是阻塞问题还是非阻塞建议
- 高质量 CR 是作者与 Reviewer 的共同责任，而不是单向验收

## 📝 练习题

### 练习：基础（必做）

为“登录接口增加失败次数限制”写一份 PR 描述，至少包含 Summary、Motivation、Changes、Verification 和 Risk 五部分，并关联一个虚构 Issue。

**检查标准**：Reviewer 不阅读 diff，也能说清问题、改动范围和验证方法。

### 练习：进阶

假设 CI 已全部通过，但你发现代码在租户 ID 缺失时可能读取其他租户的数据。请写一条 `blocking:` Review 评论，包含触发条件、影响、建议修复方向和测试要求。

### 练习：挑战（选做）

选择最近参与的一个 PR，复盘以下时间点：创建 PR、首次 CI 完成、首次人工反馈、作者响应、合并。找出最长等待环节，并提出一项不会降低质量的流程改进。

## 🔗 参考资料

- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- GitHub Docs：About pull request reviews
- Google Engineering Practices：How to do a code review
- Martin Fowler：Code Review

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
