# 11.5.2 Contributing 指南编写
> 一份好的 Contributing 指南把“我想贡献”转化为一条可重复、可验证、对维护者友好的协作路径。

## 🎯 学习目标
完成本文档后，你将能够：

- 设计 Contributing 指南的前置说明、安装、开发、测试、提交与社区章节
- 清楚描述 Dev Environment、Coding Style、Testing 和 PR 流程
- 将仓库中分散的 README、脚本和规范组织为贡献者入口
- 识别贡献指南中容易过时、含糊或不可执行的内容
- 看懂 dify 如何引导首次贡献者、Bug 报告者和 PR 作者

## 📚 前置知识
- Git 分支、提交、Fork 和 Pull Request 基础
- Markdown 标题、列表、链接与代码块语法
- 基本的软件测试和持续集成概念
- 建议先阅读 `./13-pr-best-practices.md`
- 建议结合 `./19-issue-management.md` 理解 Issue 与 PR 的衔接

## 🧭 核心概念
### Contributing 指南解决什么问题
README 面向所有使用者，Contributing 指南主要面向准备改变项目的人。它应缩短以下路径：

```text
发现项目
   ↓
选择任务或提出问题
   ↓
搭建开发环境
   ↓
实现并验证变更
   ↓
提交 PR
   ↓
参与 Review 与后续维护
```

如果这条路径依赖维护者口头解释，项目会不断重复回答相同问题。指南的目的不是写得长，而是把关键决策和可执行命令放到正确位置。

### 前置说明：先建立协作契约
开头应该回答：

- 项目是否欢迎贡献，哪些贡献最需要帮助
- 贡献适用什么许可证或 Contributor Agreement
- 社区遵循哪份 Code of Conduct
- 大功能是否需要先开 Issue 或 Discussion
- 模型、插件、文档等工作是否属于其他仓库

欢迎语很重要，但不能只有欢迎语。贡献者要在前几十行内知道“我下一步应该去哪里”。

### 安装：让环境可复现
安装章节至少应包含：

- 支持的操作系统或已知限制
- 语言运行时与包管理器版本
- Docker、数据库、缓存等外部依赖
- 获取源码、安装依赖、准备配置的命令
- 启动开发服务和验证安装的方法
- 常见错误的排查入口

避免使用“安装必要依赖”这类不可执行描述。最好给出可复制命令，并说明成功标志，例如健康检查返回什么、页面应显示什么。

### 开发环境：说明仓库地图
大型单体仓库通常包含多个子系统。Dev Environment 章节应说明：

- 目录职责，例如 `api/`、`web/`、`docker/`
- 前后端能否独立启动
- 配置文件从哪里复制，哪些值不能提交
- 数据库迁移、种子数据或本地存储如何准备
- 修改某类功能前应阅读哪份局部规范

顶层指南不需要复制每个子项目的全部命令。更可维护的做法是：顶层提供路线图，子目录文档提供具体步骤。

### Coding Style：把规则连接到工具
“代码要整洁”无法验证。有效规范应绑定自动化工具：

| 规则 | 可执行检查 |
| --- | --- |
| 格式化 | Ruff、Prettier 等 formatter |
| 静态检查 | ESLint、Ruff、Hadolint |
| 类型检查 | Pyrefly、TypeScript compiler |
| 命名与架构 | 项目规范、Code Review |
| 用户文案 | i18n 检查、Review |

同时说明自动修复命令和只读检查命令。贡献者本地能复现 CI，才不会把 Review 时间浪费在格式问题上。

### Testing：说明“测什么”和“跑什么”
测试章节不能只写“请添加测试”。应回答：

- 什么变化必须增加单元测试、组件测试或 E2E 测试
- 测试文件放在哪里，如何命名
- 如何运行全量和定向测试
- 是否要求回归测试先失败再通过
- 哪些集成测试只在 CI 环境运行
- 不能本地验证时，PR 中应如何披露

对于 Bug 修复，理想流程是先写能重现问题的失败测试，再修改生产代码，最后确认回归测试和已有测试全部通过。

### 提交规范：优化历史可读性
提交章节可以约定：

- 一个提交或 PR 尽量只解决一个问题
- Commit Message 是否采用 Conventional Commits
- 不提交密钥、构建产物、个人配置和无关格式化改动
- 大型机械修改是否需要提前讨论
- 是否允许 AI 辅助，以及如何披露生成内容

原子变更不仅方便 Review，也方便回滚、cherry-pick 和发布说明归类。

### PR 流程：明确进入与退出条件
一个完整 PR 流程通常包括：

- Fork 或创建分支
- 先用 Issue 讨论非平凡变更
- 编写实现与测试
- 执行格式、lint、类型检查和测试
- 填写 PR 模板，关联 Issue
- 响应 Review，保持分支可合并
- 获得批准、CI 通过后由维护者合并

`Fixes #123` 比“相关 #123”更有用，因为 GitHub 能在 PR 合并后自动关闭 Issue，并保留双向关联。

### 社区章节：给“卡住了”一个出口
贡献者无法搭建环境、不了解设计意图或对 Review 有异议时，需要明确求助渠道：

- 具体缺陷或变更上下文：相关 Issue / PR
- 开放式设计讨论：GitHub Discussions
- 快速交流和社区互助：Discord
- 安全漏洞：私密安全通道
- 行为问题：Code of Conduct 中的举报渠道

不同渠道的边界越清楚，重要信息越不容易散落在不可搜索的即时聊天中。

## 💻 代码示例（独立）
### 一个可复用的 CONTRIBUTING.md 模板
下面的 39 行模板适合小型全栈项目。命令必须替换成仓库真实可运行的命令。

```markdown
# Contributing

Thanks for helping improve Example App.
By participating, you agree to follow our Code of Conduct.

## Before starting

- Search existing issues and pull requests.
- Open an issue before making a breaking or large change.
- Never report security vulnerabilities in a public issue.

## Development setup

1. Fork and clone the repository.
2. Install Node.js 22 and pnpm 10.
3. Run `pnpm install --frozen-lockfile`.
4. Copy `.env.example` to `.env.local`.
5. Run `pnpm dev` and open the printed local URL.

## Coding style

- Keep TypeScript strict; do not introduce `any`.
- Run `pnpm lint:fix` before requesting review.
- Keep user-facing strings in locale files.

## Testing

- Add a regression test for every bug fix.
- Run `pnpm test` and `pnpm type-check`.
- Describe any test you could not run in the PR.

## Pull requests

1. Create a focused branch and atomic commits.
2. Link the issue with `Fixes #<number>`.
3. Complete the PR checklist and include screenshots.
4. Address reviews and wait for all checks to pass.

## Community

Use Discussions for design questions and issues for reproducible bugs.
Ask for help in the project Discord when you are blocked.
```

**说明**：

- 模板先定义参与规则和安全边界，再进入环境搭建
- 安装步骤包含版本、命令和启动验证入口，避免隐含前提
- Coding Style 和 Testing 都给出可运行命令
- PR 章节要求关联 Issue、填写证据并通过检查
- 即时聊天用于快速求助，重要结论仍应沉淀回 Issue 或 PR

## 🔍 dify 仓库源码解读
### 开头欢迎段：降低参与门槛
**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（行 1-19）：

```markdown
# CONTRIBUTING

So you're looking to contribute to Dify - that's awesome, we can't wait to see what you do. As a startup with limited headcount and funding, we have grand ambitions to design the most intuitive workflow for building and managing LLM applications. Any help from the community counts, truly.

We need to be nimble and ship fast given where we are, but we also want to make sure that contributors like you get as smooth an experience at contributing as possible. We've assembled this contribution guide for that purpose, aiming at getting you familiarized with the codebase & how we work with contributors, so you could quickly jump to the fun part.

This guide, like Dify itself, is a constant work in progress. We highly appreciate your understanding if at times it lags behind the actual project, and welcome any feedback for us to improve.

In terms of licensing, please take a minute to read our short [License and Contributor Agreement](./LICENSE). The community also adheres to the [code of conduct](https://github.com/langgenius/.github/blob/main/CODE_OF_CONDUCT.md).

## Before you jump in

Looking for something to tackle? Browse our [good first issues](https://github.com/langgenius/dify/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22good%20first%20issue%22) and pick one to get started!

Got a cool new model runtime or tool to add? Open a PR in our [plugin repo](https://github.com/langgenius/dify-plugins) and show us what you've built.

Need to update an existing model runtime, tool, or squash some bugs? Head over to our [official plugin repo](https://github.com/langgenius/dify-official-plugins) and make your magic happen!

Join the fun, contribute, and let's build something awesome together! 💡✨
```

**解读**：

- 行 3-6 先表达欢迎并解释指南目的，建立贡献者与维护者的共同目标
- 行 8 同时声明 License、Contributor Agreement 和 Code of Conduct，形成法律与行为边界
- 行 10-18 给出三个具体入口：good first issue、插件仓库、官方插件仓库
- “指南也在持续演进”承认文档可能落后，并邀请反馈；但具体命令仍应持续校验

### PR Process：从 Fork 到合并
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

- 先 Issue、后 PR，避免贡献者在方向未达成共识前投入大量实现成本
- 新分支隔离工作，使提交历史和 PR 边界保持清晰
- 新测试与已有测试分别被强调：前者证明变更，后者防止回归
- `fixes #<issue_number>` 建立可自动关闭的追踪关系
- 最后一项轻松简洁，但真正合并条件还应结合 PR 模板和 CI 状态理解

## 🗂️ 推荐章节结构
### 前置说明
用一屏左右回答欢迎、许可证、行为准则、仓库边界和开始入口。不要一上来就堆几十条安装命令。

### 安装与开发
如果项目有多个子系统，顶层文档应提供最小路径和子文档索引。例如：

- 只修改前端需要启动哪些服务
- 只修改后端需要准备哪些依赖
- 完整联调需要使用哪套 Docker Compose
- 配置或数据库升级如何处理

### 代码风格
把原则和命令并列写出。例如“TypeScript 禁止 `any`”是原则，“运行 type-check”是自动验证。架构边界无法完全自动化，则写入 Reviewer Checklist。

### 测试
按变化类型给出最低要求：

| 变化 | 最低验证 |
| --- | --- |
| Bug 修复 | 失败后转绿的回归测试 |
| 新功能 | 正常路径、边界和失败路径 |
| UI 变化 | 组件测试，必要时截图或 E2E |
| 重构 | 原有测试不变，关键契约测试 |
| 文档 | 链接、命令和格式检查 |

### 提交与 PR
将本地检查和远端流程串起来。贡献者应在请求 Review 前完成自检，而不是把 CI 当作第一轮本地调试器。

### 社区与帮助
给每类问题唯一的首选渠道，并说明响应是社区尽力而为，不承诺即时回复。

## ⚠️ 常见反模式
### 复制所有子项目文档
顶层文档复制前端、后端和部署的全部说明后，很快会出现多个不同版本。正确做法是保留唯一事实来源并建立清晰导航。

### 只列工具名，不给命令
“请运行 lint 和测试”仍要求贡献者猜命令。至少应提供本地快速检查和提交前完整检查两组命令。

### 隐藏真正的合并条件
如果仓库事实上要求先认领 Issue、签署 CLA 或运行特定检查，就应该在指南和 PR 模板中明确说明，而不是在 Review 阶段突然提出。

### 指南与 CI 不一致
文档要求的命令若与 CI 使用不同参数，会制造“本地通过、远端失败”。更新工作流或工具链时，应同步检查 Contributing 指南。

### 对社区渠道不分流
让用户在 Discord 报告所有 Bug，会使复现细节和处理状态难以追踪。快速讨论可以发生在 Discord，确认后的工作项应回到 Issue。

## 🔄 维护指南的方法
- 每季度由新贡献者从零执行一次安装步骤
- 工具版本升级时搜索并更新所有命令
- 统计反复出现的问题，把答案前移到指南
- 删除已失效流程，不保留“历史上曾经如此”的规则
- 在 PR 模板中加入“是否需要更新贡献文档”的检查项
- 把目录级规则放在目录内的 `AGENTS.md` 或开发文档中

指南应描述当前真实流程。对过去版本的说明应进入 Release Notes，而不是长期堆积在贡献指南里。

## ✅ 关键要点总结
- Contributing 指南是从选择任务到合并变更的可执行路线图
- 顶层指南负责导航，子项目文档负责环境和命令细节
- Coding Style 必须尽量绑定 formatter、linter 和 type checker
- Testing 章节要说明变化类型、最低覆盖和具体命令
- PR 流程应先讨论、再实现、补测试、跑检查并关联 Issue
- 社区章节要区分 Issue、Discussions、Discord 和安全渠道
- 指南必须与仓库和 CI 的当前行为保持一致

## 📝 练习题
### 练习：基础（必做）
使用独立模板为一个 Python 包编写贡献指南。把 Node.js 命令替换为 `uv` 或你熟悉的包管理器命令，并加入一个可验证的安装成功标志。

**检查点**：首次贡献者能否只根据文档在干净环境中运行一个测试？

### 练习：进阶
审查某个真实仓库的 README、CI 工作流和 Contributing 指南，找出三处命令或版本不一致。提出一个“顶层导航 + 子目录细节”的重组方案。

**检查点**：是否明确了每条信息的唯一事实来源？

### 练习：挑战（选做）
为 dify 的前端或后端贡献流程画一张从 Issue 到 Merge 的检查表。至少包含局部规范、定向测试、全量检查、PR 模板和 Review 响应。

**检查点**：检查表是否区分本地可执行检查与维护者负责的合并动作？

## 📖 参考资料
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/web/AGENTS.md`
- `/Users/xu/code/github/dify/api/README.md`
- `/Users/xu/code/github/dify/web/README.md`
- GitHub Docs：Setting guidelines for repository contributors
- Contributor Covenant：A Code of Conduct for Open Source Communities

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
