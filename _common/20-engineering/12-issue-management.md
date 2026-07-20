# 11.5.1 Issue 管理：标签、模板、优先级
> 用结构化标签、Issue Form 与统一优先级，把零散反馈转化为可搜索、可分派、可执行的工程任务。
## 🎯 学习目标
完成本文档后，你将能够：
- 解释 Issue 标签在分类、路由、筛选和自动化中的作用
- 设计包含表单字段、必填项与自检清单的 GitHub Issue Form
- 使用 P0/P1/P2/P3 或 Critical/High/Medium/Low 评估处理顺序
- 区分 `kind/bug`、`enhancement`、`needs-triage`、`good-first-issue` 与 `help-wanted`
- 看懂 dify 的 Bug 与 Feature Request 模板如何提升反馈质量
## 📚 前置知识
- Git 与 GitHub 的基本使用（进阶详见 [Git 进阶](../../_common/15-git/01-git-advanced.md)）
- YAML 的缩进、列表和键值对语法（详见 [配置文件格式](../17-config/01-config-file-format.md)）
- 了解软件缺陷、功能需求与技术债务的区别
- 建议先阅读 `08-pr-best-practices.md`
## 🧭 核心概念
### Issue 不是聊天消息
一个可执行的 Issue 至少需要回答四个问题：
- **发生了什么**：问题、需求或维护工作的清晰描述
- **在哪里发生**：版本、部署方式、操作系统、模块等上下文
- **如何验证**：复现步骤、预期行为、实际行为或验收条件
- **下一步由谁处理**：负责人、标签、优先级和里程碑
如果 Issue 只写“功能坏了”，维护者还要反复追问信息；模板的价值，就是在提交入口收集最低限度的诊断上下文。
### 标签体系的四个维度
成熟项目通常不会把所有概念混在一组标签里，而会按维度组织。
| 维度 | 标签示例 | 解决的问题 |
| --- | --- | --- |
| 类型 | `kind/bug`、`enhancement`、`refactor` | 这是什么工作？ |
| 状态 | `needs-triage`、`needs-info`、`blocked` | 当前处于哪个阶段？ |
| 范围 | `web`、`api`、`docker`、`plugin` | 影响哪个模块？ |
| 参与 | `good-first-issue`、`help-wanted` | 社区成员是否适合参与？ |
`kind/bug` 与简单的 `bug` 都能表达类型。带命名空间的形式在大型仓库中更易分组，但必须避免为了“整齐”而一次性创建过多标签。
### 常见标签的准确语义
- `kind/bug` 或 `bug`：已有行为偏离预期，通常需要复现与回归测试
- `enhancement`：对现有能力的增强，也可承载新的功能建议
- `needs-triage`：尚未确认类型、影响范围或优先级
- `good-first-issue`：边界清楚、风险较低、说明充分，适合首次贡献者
- `help-wanted`：维护者认可方向，并明确欢迎外部贡献
- `needs-info`：缺少版本、日志、复现步骤等关键信息
- `duplicate`：已有同类 Issue，应链接原 Issue 后关闭重复项
需要特别注意：`good-first-issue` 不是“低价值 Issue”。它应当拥有清晰的验收条件和足够的实现线索，否则新贡献者更容易受挫。
### Issue Form 的组成
GitHub Issue Form 使用 YAML 描述结构化输入，常见字段包括：
- `input`：适合版本号、URL、短文本
- `dropdown`：适合部署方式、操作系统等有限选项
- `textarea`：适合复现步骤、日志、方案描述
- `checkboxes`：适合自检清单与协议确认
- `markdown`：展示说明，不收集用户输入
字段的 `validations.required` 只解决“是否填写”，不能保证内容质量。因此还需要清楚的 `description` 和可模仿的 `placeholder`。
### 自检清单的作用
提交前自检把高频人工提醒前移到表单入口。常见项目包括：
- 已阅读贡献指南与行为准则
- 已搜索开放和关闭的 Issue
- 确认提交的是 Bug，而不是一般问题
- 已使用社区约定的语言
- 已填写全部必填字段
自检项不宜无限增加。每一项都应该能减少重复 Issue、错误分流或无效沟通，否则会变成机械勾选。
### 优先级不是严重程度
**严重程度（Severity）**描述影响有多坏，**优先级（Priority）**描述应该多快处理。两者相关，但并不相同。
例如，一个只影响单个付费客户的普通缺陷，可能因为合同承诺而进入高优先级；一个影响很多用户但有简单规避方法的问题，严重程度较高，却可能排在紧急安全修复之后。
### P0/P1/P2/P3 模型
| 级别 | 响应含义 | 典型场景 |
| --- | --- | --- |
| P0 | 立即处理，必要时暂停发布 | 安全漏洞、数据丢失、核心服务不可用 |
| P1 | 当前迭代优先处理 | 登录失败、主流程中断、广泛性能退化 |
| P2 | 正常排期 | 非核心缺陷、常用功能增强 |
| P3 | 有余力时处理 | 文案、轻微 UI 问题、低频改进 |
也可以映射为 `Critical / High / Medium / Low`。重要的不是名称，而是团队对响应时间、升级条件和负责人有一致理解。
### 一个可操作的评估公式
评估时可以依次询问：
- 影响面：多少用户、租户或部署受到影响？
- 破坏性：是否涉及安全、数据完整性或核心路径？
- 可规避性：是否存在低成本 workaround？
- 紧迫性：是否阻塞发布、客户交付或合规期限？
- 置信度：是否已稳定复现，证据是否充分？
不要把公式算出的分数当成绝对真理。它的主要价值是帮助 triage 参与者使用同一种语言讨论取舍。
## 💻 代码示例（独立）
### 一个最小但完整的 Bug Issue Form
下面的示例可以放入任意项目的 `.github/ISSUE_TEMPLATE/bug.yml`，共 35 行，包含自动标签、自检、环境信息和行为对比。
```yaml
name: Bug report
description: Report a reproducible problem
title: "[Bug] "
labels:
  - bug
  - needs-triage
body:
  - type: checkboxes
    attributes:
      label: Self-check
      options:
        - label: I searched open and closed issues.
          required: true
        - label: I can reproduce this on the latest version.
          required: true
  - type: input
    id: version
    attributes:
      label: Version
      placeholder: "1.8.0"
    validations:
      required: true
  - type: dropdown
    id: priority
    attributes:
      label: Suspected impact
      options:
        - Critical
        - High
        - Medium
        - Low
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Steps, expected result, and actual result
    validations:
      required: true
```
**说明**：
- 模板只让报告者提供“疑似影响”，最终优先级仍由维护者确认
- `needs-triage` 表明 Issue 尚未完成分类，避免把提交者判断当作最终结论
- 复现、预期与实际行为合并在一个输入框可保持模板简洁；复杂项目可拆成三个字段
- 所有必填项都直接服务于复现或分流，没有加入无用途的确认项
## 🔍 dify 仓库源码解读
### Bug 模板：提交前自检
**文件位置**：`/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml`  
**核心代码**（行 1-22）：
```yaml
name: "🕷️ Bug report"
description: Report errors or unexpected behavior
labels:
  - bug
body:
  - type: checkboxes
    attributes:
      label: Self Checks
      description: "To make sure we get to you in time, please check the following :)"
      options:
        - label: I have read the [Contributing Guide](https://github.com/langgenius/dify/blob/main/CONTRIBUTING.md) and [Language Policy](https://github.com/langgenius/dify/issues/1542).
          required: true
        - label: This is only for bug report, if you would like to ask a question, please head to [Discussions](https://github.com/langgenius/dify/discussions/categories/general).
          required: true
        - label: I have searched for existing issues [search for existing issues](https://github.com/langgenius/dify/issues), including closed ones.
          required: true
        - label: I confirm that I am using English to submit this report, otherwise it will be closed.
          required: true
        - label: 【中文用户 & Non English User】请使用英语提交，否则会被关闭 ：）
          required: true
        - label: "Please do not modify this template :) and fill in all the required fields."
          required: true

```
**解读**：
- 行 3-4 自动添加 `bug`，让新 Issue 进入缺陷筛选视图
- 行 6-22 使用强制复选框确认贡献指南、分流规则、去重搜索和语言政策
- “问题请前往 Discussions”把可执行缺陷与开放式问答分开
- 同时搜索已关闭 Issue，可以发现已有结论、规避方案或历史重复项
### Bug 模板：版本和部署环境
**文件位置**：`/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml`  
**核心代码**（行 23-41）：
```yaml
  - type: input
    attributes:
      label: Dify version
      description: See about section in Dify console
    validations:
      required: true

  - type: dropdown
    attributes:
      label: Cloud or Self Hosted
      description: How / Where was Dify installed from?
      multiple: true
      options:
        - Cloud
        - Self Hosted (Docker)
        - Self Hosted (Source)
    validations:
      required: true

```
**解读**：
- 版本号是定位回归范围和判断是否已修复的关键字段
- Cloud、Docker 与 Source 可能拥有不同配置、升级路径和责任边界
- `multiple: true` 允许报告者声明问题在多种环境中复现
- 两组字段均为必填，说明 dify 把“在哪个版本、哪种部署中发生”视为最低诊断信息
### Bug 模板：复现与行为对比
**文件位置**：`/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml`  
**核心代码**（行 42-66）：
```yaml
  - type: textarea
    attributes:
      label: Steps to reproduce
      description: We highly suggest including screenshots and a bug report log. Please use the right markdown syntax for code blocks.
      placeholder: Having detailed steps helps us reproduce the bug. If you have logs, please use fenced code blocks (triple backticks ```) to format them.
    validations:
      required: true

  - type: textarea
    attributes:
      label: ✔️ Expected Behavior
      description: Describe what you expected to happen.
      placeholder: What were you expecting? Please do not copy and paste the steps to reproduce here.
    validations:
      required: true

  - type: textarea
    attributes:
      label: ❌ Actual Behavior
      description: Describe what actually happened.
      placeholder: What happened instead? Please do not copy and paste the steps to reproduce here.
    validations:
      required: false

```
**解读**：
- 复现步骤和预期行为必填，使维护者能够构造最小验证路径
- placeholder 明确要求日志使用 fenced code block，提升长日志可读性
- 实际行为被设为可选，这与通常实践略有不同；维护者仍可从标题、描述或附件中获取现象
- 三段式结构对应“操作—预期—实际”，适合直接转化为回归测试
### Feature 模板：问题故事优先
**文件位置**：`/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/feature_request.yml`  
**核心代码**（行 1-20）：
```yaml
name: "⭐ Feature or enhancement request"
description: Propose something new.
labels:
  - enhancement
body:
  - type: checkboxes
    attributes:
      label: Self Checks
      description: "To make sure we get to you in time, please check the following :)"
      options:
        - label: I have read the [Contributing Guide](https://github.com/langgenius/dify/blob/main/CONTRIBUTING.md) and [Language Policy](https://github.com/langgenius/dify/issues/1542).
          required: true
        - label: I have searched for existing issues [search for existing issues](https://github.com/langgenius/dify/issues), including closed ones.
          required: true
        - label: I confirm that I am using English to submit this report, otherwise it will be closed.
          required: true
        - label: "Please do not modify this template :) and fill in all the required fields."
          required: true
  - type: textarea
    attributes:
      label: 1. Is this request related to a challenge you're experiencing? Tell me about your story.
```
**解读**：
- Feature Request 自动获得 `enhancement` 标签，不与 Bug 混排
- 必填字段先问用户正在经历的挑战，而不是直接问“想要什么按钮”
- 以问题故事为起点，有助于维护者发现更通用、成本更低的解决方案
### Feature 模板：协作意愿和单一请求
**文件位置**：`/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/feature_request.yml`  
**核心代码**（行 21-40）：
```yaml
      placeholder: Please describe the specific scenario or problem you're facing as clearly as possible. For instance "I was trying to use [feature] for [specific task], and [what happened]... It was frustrating because...."
    validations:
      required: true
  - type: textarea
    attributes:
      label: 2. Additional context or comments
      placeholder: (Any other information, comments, documentations, links, or screenshots that would provide more clarity. This is the place to add anything else not covered above.)
    validations:
      required: false
  - type: checkboxes
    attributes:
      label: 3. Can you help us with this feature?
      description: Let us know! This is not a commitment, but a starting point for collaboration.
      options:
        - label: I am interested in contributing to this feature.
          required: false
  - type: markdown
    attributes:
      value: Please limit one request per issue.
```
**解读**：
- 附加上下文可选，避免没有截图或链接的用户无法提交
- “愿意贡献”不是承诺，而是后续协作的起点
- 每个 Issue 只包含一个请求，便于独立排序、关闭、回滚和发布说明归类
## 🤖 自动化 Stale 生命周期
dify 使用 `actions/stale` 在不活跃的 Issue 上自动标记 + 关闭。
### 仓库级 Stale 配置
**文件位置**：`/Users/xu/code/github/dify/.github/workflows/stale.yml`
**核心代码**（行 22-30）：
```yaml
      - uses: actions/stale@v8
        with:
          days-before-stale: 15
          days-before-close: 3
          stale-issue-label: 'no-issue-activity'
          stale-pr-label: 'no-pr-activity'
          any-of-labels: '🌚 invalid,🙋‍♂️ question,wont-fix,no-issue-activity,no-pr-activity,💪 enhancement,🤔 cant-reproduce,🙏 help wanted'
          close-comment: 'This issue was closed because it has been inactive for 18 days. Please reopen if you feel this is in error.'
```
**解读**：
- 第 1 行：使用官方 `actions/stale@v8` 工具
- 第 2 行：15 天无活动 → 标记 stale（`no-issue-activity`）
- 第 3 行：再 3 天（合计 18 天）→ 关闭
- 第 5 行：Issue / PR 用不同 stale 标签——便于分别统计
- 第 6 行：**白名单**——8 个标签不会被标记 stale
  - `wont-fix` / `enhancement` / `help wanted` = “长期挂起但有意保留”
  - `question` / `invalid` / `cant-reproduce` = “已被人工分类，无需 bot 干预”
- 第 7 行：关闭时自动评论说明原因——用户可重新打开
- **关键设计**：白名单机制避免”长期有效的 feature request”被误关
### 配置变更带来的影响
- Stale bot 用 `cron` 每天 03:00 UTC 触发——不依赖 push，**主动巡检**
- 标签 emoji 前缀（🌚 🙋‍♂️ 🤔）——视觉上一眼分辨
- 修改 `any-of-labels` 时需谨慎——少加一个标签可能让”长期挂起但合理”的 Issue 被误关
## 🧰 Triage 工作流
收到新 Issue 后，可以按以下顺序处理：
- 验证模板信息是否足够，不足则添加 `needs-info`
- 搜索重复项，重复则链接主 Issue 并关闭当前项
- 确认类型与范围，如 `bug`、`web`、`docker`
- 根据影响面、破坏性、可规避性和紧迫性确定优先级
- 确认负责人、里程碑或等待条件
- 对适合社区参与的工作补充实现线索，再添加 `help-wanted`
- 只有边界小且验收清楚时，才添加 `good-first-issue`
Triage 不是一次性动作。新日志、复现结果、用户反馈和安全评估都可能改变优先级。
## ✅ 关键要点总结
- 标签要表达类型、状态、范围和参与机会，而不是堆砌同义词
- Issue Form 通过必填字段和自检清单前移信息收集与分流
- 严重程度描述影响，优先级描述处理顺序，不能完全等同
- P0/P1/P2/P3 与 Critical/High/Medium/Low 都可以，关键在统一定义
- dify 的 Bug 模板特别重视版本、部署形态、复现步骤与预期行为
- dify 的 Feature 模板从用户问题出发，并主动询问贡献意愿
## 📝 练习题
### 练习：基础（必做）
为一个命令行工具设计 6 个标签，至少覆盖类型、状态、范围和社区参与四个维度。为每个标签写一句不会与其他标签重叠的定义。
**检查点**：是否能明确区分 `needs-triage`、`needs-info` 和 `help-wanted`？
### 练习：进阶
修改独立示例中的模板，增加操作系统、最小复现仓库和日志字段。说明哪些字段必填，并解释为什么不应让提交者决定最终 P0/P1 优先级。
**检查点**：修改后的 YAML 是否保持正确缩进，每个输入是否有稳定的 `id`？
### 练习：挑战（选做）
阅读 dify 的 Bug、Feature、Refactor 三个模板，设计统一的 triage 决策表。要求覆盖重复项、信息不足、安全漏洞、插件问题和核心功能不可用五种情况。
**检查点**：安全漏洞是否被引导到私密披露渠道，而不是公开 Issue？
## 📖 参考资料
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/feature_request.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/refactor.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/config.yml`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- GitHub Docs：Configuring issue templates for your repository
- GitHub Docs：Syntax for GitHub's form schema
---
**文档版本**：v1.0  
**最后更新**：2026-07-13
