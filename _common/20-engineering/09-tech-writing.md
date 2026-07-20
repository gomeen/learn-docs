# 11.15 技术文档写作：README / ADR / Runbook

> 用面向读者和任务的方式编写 README、ADR 与 Runbook，让知识可以被发现、执行和长期维护。

## 🎯 学习目标

完成本文档后，你将能够：

- 说明 README、ADR、Runbook 分别服务于什么读者和场景
- 用“是什么—怎么开始—如何使用—怎样参与”的结构组织 README
- 用 Context / Decision / Consequences 记录架构决策
- 把故障处置过程写成可操作、可验证、可回滚的 Runbook
- 识别空泛描述、过期命令和缺少责任边界等常见文档问题
- 看懂 dify `CONTRIBUTING.md` 如何引导贡献者进入项目

## 📚 前置知识

- Markdown 基础语法：标题、列表、链接和代码块
- Git 与 Pull Request 的基本流程（详见 [Git 工作流](../../_common/15-git/02-git-workflow.md)）
- 软件项目中的开发、测试、部署和故障处理常识
- 建议先浏览 `/Users/xu/code/github/dify/README.md`

## 🧭 核心概念

### 技术文档首先是一种工程接口

代码接口约束调用者如何传参，技术文档则约束读者如何理解和操作系统。
一篇有效文档至少要回答三个问题：

- **谁来读**：新用户、贡献者、架构师还是值班工程师？
- **为什么读**：安装软件、理解决策，还是恢复服务？
- **读完做什么**：运行命令、提交变更，还是执行回滚？

因此，写文档不能从“我知道什么”出发，而应从“读者下一步要完成什么”出发。
README、ADR 和 Runbook 的共同目标都是降低信息不对称，但它们的时间尺度不同：

| 文档类型 | 主要问题 | 主要读者 | 时间视角 |
| --- | --- | --- | --- |
| README | 项目是什么，怎样开始？ | 用户、开发者 | 现在如何使用 |
| ADR | 为什么选择这个方案？ | 开发者、架构师 | 当时为何决定 |
| Runbook | 出现某种情况怎么办？ | 运维、值班人员 | 事件中如何行动 |

### README：项目的入口页

README 是读者接触仓库时的第一层导航，不需要包含全部细节，但必须建立正确心智模型。
一个完整 README 通常包含以下核心要素。

#### 是什么

用一到两段话给出项目定位、目标用户和核心能力。
避免只写抽象口号，应让读者能判断“它是否解决我的问题”。
可以补充架构图或特性列表，但不能用它们替代清晰定义。

#### 快速开始

提供从零到第一次成功运行的最短路径，包括：

- 必要的系统要求与依赖
- 安装或拉取命令
- 最少配置项
- 启动命令
- 成功标志，例如访问地址或预期输出

命令必须能够复制执行，并明确它们应在哪个目录运行。
如果快速开始依赖外部服务，要说明默认值和失败时的排查入口。

#### 使用示例

快速开始证明“能运行”，使用示例则证明“能解决问题”。
示例应覆盖一个最小但真实的任务，并展示输入、操作和结果。
对库项目可给出 API 调用；对应用项目可展示典型工作流。

#### 贡献方式

贡献入口至少应说明：

- 到哪里寻找或创建 Issue
- 如何建立分支和运行检查
- Pull Request 需要提供什么信息
- 更完整的规则位于哪个贡献指南

README 可以提供摘要，再把细节委托给 `CONTRIBUTING.md`，避免入口页无限增长。

#### 许可证

许可证决定别人能否使用、修改和分发项目。
README 应明确许可证名称并指向仓库中的许可证正文。
贡献者协议与行为准则也应从贡献文档中可被发现。

### ADR：保留决策上下文

ADR 是 **Architecture Decision Record**，即架构决策记录（完整写法详见 [ADR](11-adr.md)）。
它记录一个重要决策的背景、最终选择和后果，而不是复述代码当前长什么样。

只看代码通常能知道“系统采用了 Redis”（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)），却无法知道：

- 为什么没有采用数据库队列？
- 当时有哪些约束？
- 哪些替代方案被否决？
- 未来在什么条件下应重新评估？

ADR 通过保存这些信息，减少团队反复争论和错误推翻历史决策的成本。
一条 ADR 通常不可直接覆盖；决策变化时创建新 ADR，并标记旧记录被取代。

### Runbook：把处置经验变成步骤

Runbook 是面向操作的运行手册，描述怎样完成重复任务或处理已知事件。
典型主题包括部署、证书轮换、队列积压、数据库故障和服务降级。

有效 Runbook 应包含：

- **触发条件**：什么告警或现象意味着应该使用本手册
- **影响范围**：用户、租户和数据是否受影响
- **前置权限**：需要访问哪些系统以及谁可以执行
- **诊断步骤**：先观察什么指标、日志和状态
- **处置步骤**：按顺序执行的命令或操作
- **验证方法**：怎样证明服务已经恢复
- **回滚方案**：处置失败时怎样回到安全状态
- **升级路径**：什么时候停止尝试并联系负责人

Runbook 不是故障原理教材。值班人员在压力下需要的是无歧义动作、预期结果和停止条件。
复杂原理可以链接到设计文档，但关键命令和安全警告必须留在 Runbook 内。

### 三类文档如何配合

一个新贡献者通常先从 README 认识项目，再通过贡献指南搭建环境。
当他修改关键架构时，通过 ADR 理解决策边界；系统上线后，值班人员依靠 Runbook 处置异常。
三者形成“入口—理由—操作”的文档链路：

- README 负责可发现性
- ADR 负责可追溯性
- Runbook 负责可执行性

### 可维护文档的质量标准

#### 准确

文档中的命令、路径、版本和默认值必须与代码一致。
能够由测试或 CI 验证的内容，尽量自动验证，而不是依赖人工记忆。

#### 简洁但完整

简洁不是删除关键前提，而是围绕读者任务组织信息。
将深入细节拆到专题文档，同时保证入口页给出明确导航。

#### 可扫描

标题应表达任务，列表应表达并列关系，警告应靠近危险操作。
读者应能在几十秒内找到启动命令、回滚步骤或决策结论。

#### 有所有者

长期有效的文档需要明确维护责任。
代码变更影响命令或约束时，应在同一个 Pull Request 中更新相关文档。

## 💻 代码示例

### 一个任务导向的 README 模板

下面的独立模板覆盖“是什么、快速开始、使用示例、贡献方式、许可证”五个核心要素。

**示例文件**：`examples/task-board/README.md`  
**示例行号**：第 1-35 行

```markdown
# Task Board

> 一个用于学习 REST API 的最小任务看板服务。

## What it is

Task Board 提供任务创建、查询和完成接口，适合本地教学与原型验证。

## Quick start

要求 Python 3.12+。

~~~bash
git clone https://example.com/task-board.git
cd task-board
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
~~~

访问 `http://localhost:8000/health`，看到 `{"status":"ok"}` 即启动成功。

## Usage

~~~bash
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"write docs"}'
curl http://localhost:8000/tasks
~~~

## Contributing

请先创建 Issue，再建立功能分支；提交 PR 前运行 `pytest`。
详细规则见 `CONTRIBUTING.md`。

## License

本项目使用 MIT License，详见 `LICENSE`。
```

**说明**：

- 定位段让读者先判断项目是否适合自己
- Quick start 同时给出依赖、命令和成功标志
- Usage 使用真实 HTTP 请求建立最小闭环
- 贡献和许可证只给入口，不在 README 重复全部细则

### 一个可复用的 ADR 模板

**示例文件**：`docs/adr/0000-template.md`  
**示例行号**：第 1-29 行

```markdown
# ADR-0000：决策标题

- Status: Proposed
- Date: YYYY-MM-DD
- Deciders: 团队或角色

## Context

描述当前问题、业务目标、技术约束和必须满足的质量属性。
说明为什么现在需要作出决定，以及不决策会产生什么影响。

## Options considered

- 方案 A：核心思路、优势和成本
- 方案 B：核心思路、优势和成本
- 保持现状：收益与风险

## Decision

明确写出选择的方案、适用边界和实施原则。
决策应具体到后续开发者能够据此判断实现是否合规。

## Consequences

### Positive

- 列出预期收益

### Negative

- 列出已接受的成本、风险和新增维护责任

## Revisit when

记录触发重新评估的指标、规模或外部条件。
```

**说明**：ADR 不是“方案宣传稿”。`Consequences` 必须同时记录收益与代价，`Revisit when` 则避免把阶段性选择误解为永久真理。

## 🔍 dify 仓库源码解读

### 贡献指南如何建立读者上下文

**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（第 1-20 行）：

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

- 第 3 行先欢迎贡献者并说明项目目标，建立“为什么值得参与”的动机
- 第 5 行明确指南的任务：帮助读者熟悉代码库和协作方式，而不是堆砌所有项目知识
- 第 7 行承认文档会落后于实现，并主动邀请反馈，体现文档也是持续演进的产品
- 第 9 行尽早暴露 License 和 Code of Conduct，避免贡献者在流程后期才发现约束
- 第 11-19 行把不同贡献意图导向正确入口，减少在错误仓库提交变更的概率
- 虽然文件名是 `CONTRIBUTING.md`，它仍展示了优秀 README 的入口写法：先定位、再导航、最后推动行动

## 🛠️ 写作工作流

### 先定义读者任务

写作前用一句话填写：“当____读完本文后，能够____。”
如果一句话包含多个互不相关的动作，应拆分文档或设置清晰导航。

### 再收集可验证事实

从代码、配置、CI 和实际运行结果中确认命令。
不要把猜测写成规则；暂时未知的内容应标明负责人和确认方式。

### 按执行顺序组织

README 按认识项目到成功运行组织，ADR 按背景到结论组织，Runbook 按告警到恢复组织。
不要照作者发现信息的顺序原样记录。

### 最后进行桌面演练

请一名没有上下文的读者按文档操作。
对 Runbook，应在非生产环境定期演练，确认权限、命令、预期输出和回滚路径仍然有效。

## ✅ 关键要点总结

- README 是项目入口，核心是“是什么、快速开始、使用、贡献、许可证”
- ADR 保存 Context / Decision / Consequences，解释代码无法表达的“为什么”
- Runbook 把诊断、处置、验证、回滚和升级路径变成可执行步骤
- 文档应围绕读者任务，而不是围绕作者知识组织
- 命令必须可复制、可验证，并注明执行目录和成功标志
- 文档与代码应在同一个变更中维护，避免形成失真的“第二套事实”

## 🧪 练习题

### 练习：基础（必做）

选择一个你熟悉的小项目，按本文模板补全 README 的五个核心部分。
要求另一名读者只依靠 README 在 15 分钟内运行成功，并记录他遇到的第一个阻塞点。

### 练习：进阶

为“后台任务从数据库轮询迁移到 Redis 队列”编写 ADR。
至少比较两个替代方案，并在 Consequences 中分别列出两个正面结果和两个负面结果。

### 练习：挑战（选做）

为“任务队列积压超过 10,000 条”编写 Runbook，包含：

- 触发告警与影响判断
- 三步诊断流程
- 临时扩容和降级方案
- 每一步的预期结果
- 回滚条件与升级联系人角色

完成后让同伴进行桌面演练，检查是否存在依赖口头知识才能继续的步骤。

## 📖 参考资料

- `/Users/xu/code/github/dify/README.md`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- Markdown Guide：https://www.markdownguide.org/
- Architecture Decision Records：https://adr.github.io/
- Google SRE Workbook - Incident Response：https://sre.google/workbook/incident-response/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
