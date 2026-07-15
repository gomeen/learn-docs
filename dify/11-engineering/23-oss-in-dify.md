# 11.5.5 dify 的开源协作模式分析
> 从 Issue 模板、PR 模板、Contributing 指南、标签与优先级联动，理解 dify 如何把大规模社区反馈转化为可治理的工程变更。

## 🎯 学习目标
完成本文档后，你将能够：

- 从仓库协作文件还原 dify 的开源贡献路径
- 分析 Issue 模板、PR 模板和 Contributing 指南之间的职责分工
- 解释标签体系和优先级模型如何支持 Triage
- 识别 Cloud、Docker（详见 [Docker 核心概念](../../_common/09-containerization/01-concepts.md)）与 Source 三类部署对缺陷诊断的影响
- 总结 dify 社区运营的入口设计、仓库分流与质量门禁特点
- 根据 dify 模式为其他大型开源项目设计协作闭环

## 📚 前置知识
- GitHub Issue、Pull Request、Discussion 与 Release 基础
- 软件测试、Code Review 和持续集成基础
- 建议先阅读 `./19-issue-management.md`
- 建议先阅读 `./20-contributing.md`
- 建议先阅读 `./21-release-process.md`
- 建议先阅读 `./22-community.md`

## 🧭 核心概念
### 分析协作模式要看“控制面”
开源项目的协作模式不只存在于文字口号中，还编码在仓库的控制文件里：

- 提交入口允许用户选择什么
- 表单要求哪些字段必填
- 哪些渠道被禁止或重定向
- PR 必须提供哪些证据
- 自动化按什么文件和语义打标签
- 哪些角色可以 Review 或合并
- CI 在合并前验证什么

因此，分析时既要读 `CONTRIBUTING.md`，也要读 `.github/` 下的模板、工作流和所有权配置。

### dify 协作链路概览
从当前仓库配置可以还原出一条主路径：

```text
User / Contributor
       ↓
阅读 License、Code of Conduct、Contributing
       ↓
选择 Bug / Feature / Refactor 模板，或被分流到其他渠道
       ↓
Maintainer Triage：类型、范围、优先级、重复项、责任仓库
       ↓
先讨论并认领 Issue
       ↓
Fork + Branch + Implementation + Tests
       ↓
PR Summary + Screenshots + Checklist + Fixes #issue
       ↓
Code Review + CI + Ownership checks
       ↓
Merge + Release / 后续维护
```

这条路径的核心不是工具数量，而是每个阶段都增加结构化信息，并把前一阶段的上下文传给下一阶段。

## 🗂️ 关键文件清单
| 文件 | 协作职责 |
| --- | --- |
| `/Users/xu/code/github/dify/CONTRIBUTING.md` | 总入口、Issue 质量、优先级、PR 流程、帮助渠道 |
| `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml` | Bug 自检、版本、部署方式、复现和行为对比 |
| `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/feature_request.yml` | 用户问题、附加上下文和贡献意愿 |
| `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/refactor.yml` | Refactor/Chore 的动机和范围 |
| `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/config.yml` | 禁用空白 Issue，分流安全、插件、文档和讨论 |
| `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md` | Summary、截图、测试、文档和本地检查清单 |
| `/Users/xu/code/github/dify/.github/CODEOWNERS` | 路径级 Review 责任 |
| `/Users/xu/code/github/dify/.github/labeler.yml` | 根据变更文件自动添加范围标签 |
| `/Users/xu/code/github/dify/.github/workflows/labeler.yml` | 执行自动标签工作流 |
| `/Users/xu/code/github/dify/.github/workflows/semantic-pull-request.yml` | 校验 PR 语义规范 |
| `/Users/xu/code/github/dify/api/AGENTS.md` | 后端局部工程规范、检查与架构边界 |
| `/Users/xu/code/github/dify/web/AGENTS.md` | 前端局部工程规范与工作流 |
| `/Users/xu/code/github/dify/.github/DISCUSSION_TEMPLATE/` | 一般讨论、帮助与建议的结构化入口 |

这份清单体现“总则 + 入口模板 + 自动化 + 目录局部规范”的分层治理。

## 🐛 Issue、标签与优先级分析
### Bug 模板：强调可诊断性
Bug 模板收集贡献指南与去重确认、Dify 版本、部署形态、复现步骤、日志、预期行为和实际行为。这些信息直接支持判断“是否已修复、在哪类部署复现、怎样验证偏差”。

### Feature 与 Refactor 模板：明确问题类型
Feature 模板先问用户正在经历的挑战，再收集附加上下文和贡献意愿；每个 Issue 只容纳一个请求，便于独立排序。Refactor/Chore 模板则收集 Description、Motivation 和 Additional Context，让内部质量改造也必须解释价值。

### 禁用空白 Issue 与分流
`blank_issues_enabled: false` 用少量入口约束换取统一信息质量。安全漏洞进入私密披露，插件、模型供应商和文档问题进入对应仓库，一般问答进入 Discussions。

### 标签体系
模板自动为 Bug 添加 `bug`、为 Feature 添加 `enhancement`；`.github/labeler.yml` 再根据路径添加 `web`、`e2e` 等范围标签。状态和社区参与通常由 `needs-triage`、`needs-info`、`help-wanted`、`good-first-issue` 表达。若使用 `kind/bug` 风格，应避免与已有 `bug` 形成同义标签。

模板负责收集事实，标签负责表达当前分类和状态。自动范围标签减少漏标，帮助 CODEOWNERS、维护者和发布工具找到相关变更。

### Bug 与 Feature 使用不同优先级模型
dify 把核心服务不可用、无法登录、主流程失败和安全漏洞视为 Critical Bug；非关键缺陷与性能提升为 Medium，小型 UI 或文字问题为 Low。Feature 则综合团队确认、社区反馈热度、核心程度和近期价值，使用 High、Medium、Low 与 Future-Feature。

这种分离避免用 Feature 点赞数影响安全缺陷，也允许项目认可某个请求的长期价值但不承诺立即交付。其边界是没有直接 SLA，“核心功能”和热度偏差仍需 Maintainer 判断；优先级应随新证据复核，而非永久固定。

## 🔀 Issue、PR 与 Contributing 的联动
### Contributing 定义规则
它解释 Bug 和 Feature 应包含什么、如何排序、PR 前为什么要先讨论、提交后需要哪些测试。

### Issue Form 执行最低输入
它把文字规范转成必填字段和自检复选框，减少“读过指南但仍漏填信息”的情况。

### PR 模板执行交付检查
PR 模板要求：

- Summary、动机、上下文和依赖
- 关联 Issue
- UI 变化的 Before/After 截图
- 每项变化对应测试
- 文档同步
- 本地 lint 与类型检查
- 尽量保持单一原子变更

三个层次形成：**指南解释原因，Issue 模板收集问题，PR 模板验证解决方案。**

## 💻 代码示例（独立）
### 一个协作策略配置示例
下面的独立 YAML 不是 dify 源码，而是用于演示如何把类型、优先级和渠道规则表达成可审查配置，共 39 行。

```yaml
collaboration:
  issue_types:
    bug:
      required_fields:
        - version
        - deployment
        - reproduction
        - expected_behavior
      default_labels:
        - bug
        - needs-triage
    feature:
      required_fields:
        - problem_statement
        - use_case
      default_labels:
        - enhancement
        - needs-triage
  priorities:
    critical:
      conditions:
        - security_vulnerability
        - data_loss
        - core_service_unavailable
      escalation: maintainer-on-call
    high:
      conditions:
        - major_workflow_blocked
    medium:
      conditions:
        - workaround_available
        - popular_feature_request
    low:
      conditions:
        - typo
        - minor_ui_confusion
  routing:
    security: private-advisory
    usage_question: discussions
    plugin_bug: plugin-repository
    documentation_bug: docs-repository
  pull_requests:
    require_issue: true
    require_tests: true
    require_docs_review: true
    require_atomic_scope: true
```

**说明**：

- Bug 和 Feature 拥有不同必填项，但都从 `needs-triage` 开始
- Critical 使用安全、数据和核心可用性条件，并声明升级负责人
- 渠道路由避免把安全和跨仓库问题放错位置
- PR 门禁把 Issue 上下文、测试、文档和原子范围连接起来
- 真实 GitHub 仓库会把这些规则分散到 Issue Form、标签、工作流和分支保护中

## 🔍 dify 仓库源码解读
### Contributing：Bug 报告与优先级规范
**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（行 23-41）：

```markdown
### Bug reports

> [!IMPORTANT]
> Please make sure to include the following information when submitting a bug report:

- A clear and descriptive title
- A detailed description of the bug, including any error messages
- Steps to reproduce the bug
- Expected behavior
- **Logs**, if available, for backend issues, this is really important, you can find them in docker-compose logs（Compose 详见 [Docker Compose](../../_common/09-containerization/04-compose.md)）
- Screenshots or videos, if applicable

How we prioritize:

| Issue Type | Priority |
| ------------------------------------------------------------ | --------------- |
| Bugs in core functions (cloud service, cannot login, applications not working, security loopholes) | Critical |
| Non-critical bugs, performance boosts | Medium Priority |
| Minor fixes (typos, confusing but working UI) | Low Priority |
```

**解读**：

- 报告质量要求覆盖标题、错误信息、复现、预期、日志和视觉证据
- 后端日志被特别强调，并提示从 Docker Compose 日志获取，贴近 Self Hosted 场景
- Critical 直接绑定核心可用性与安全，不以点赞数决定
- 性能提升被放入 Medium，说明并非所有“慢”都等同服务不可用
- 可工作但困惑的 UI 属于 Low，体现破坏性和可规避性的共同判断

### Contributing：Feature 请求与优先级规范
**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（行 42-60）：

```markdown
### Feature requests

> [!NOTE]
> Please make sure to include the following information when submitting a feature request:

- A clear and descriptive title
- A detailed description of the feature
- A use case for the feature
- Any other context or screenshots about the feature request

How we prioritize:

| Feature Type | Priority |
| ------------------------------------------------------------ | --------------- |
| High-Priority Features as being labeled by a team member | High Priority |
| Popular feature requests from our [community feedback board](https://github.com/langgenius/dify/discussions/categories/feedbacks) | Medium Priority |
| Non-core features and minor enhancements | Low Priority |
| Valuable but not immediate | Future-Feature |

```

**解读**：

- Feature 必须有 use case，避免只给实现方案而没有用户价值
- 高优先能力需要团队成员确认，体现路线治理责任
- 社区反馈热度进入 Medium，是排序信号而非自动承诺
- 非核心能力和小增强进入 Low，保护团队对核心体验的投入
- `Future-Feature` 为“认可但不近期实现”提供明确状态

### Cloud 与 Self Hosted：差异化支持字段
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

- 版本字段先确定代码基线，避免在已修复版本上重复排障
- 部署方式不是附加备注，而是必填诊断维度
- Cloud 问题更可能由平台侧统一观测；Self Hosted 需要考虑本地配置、基础设施和升级历史
- Docker 与 Source 分开，说明容器制品问题和源码环境问题可能走不同排查路径
- `multiple: true` 支持报告者表达跨部署验证结果，这对判断通用回归很有价值

## ☁️ 差异化支持与社区运营
### 部署差异
Cloud 环境由服务方控制发布、基础设施与多数观测，排障重点是发生时间、租户上下文、控制台版本、功能路径和请求标识。公开 Issue 仍不应暴露敏感租户数据。

Self Hosted（Docker）需要额外检查镜像 Tag 与摘要、Compose 覆盖配置、依赖版本、容器日志、资源限制和升级迁移；Contributing 对 Docker Compose 后端日志的强调与此一致。

Self Hosted（Source）的变量更多，包括 Git Commit、运行时与包管理器版本、锁文件、本地补丁、启动命令和数据库状态。单独收集 Source 有助于区分产品代码、构建制品和本地环境偏差。

### 社区运营特点总结
- **欢迎与约束并存**：开头鼓励参与，表单同时要求语言、去重和完整字段
- **贡献入口分层**：新贡献者从 `good first issue` 开始，模型和工具进入插件仓库
- **问题先于代码**：先 Issue，Feature 先问挑战，PR 用 `Fixes #...` 回连上下文
- **托管与开源共同治理**：Cloud、Docker、Source 都是明确诊断维度
- **自动化辅助路由**：路径标签、语义 PR、CI 和 CODEOWNERS 处理机械判断
- **质量证据前移**：Issue 要复现和日志，PR 要测试、文档、截图和本地检查
- **多渠道分工**：Discussions/Discord 负责帮助，Issue/PR 负责工程状态，漏洞私密处理

### 可借鉴与需调整之处
可直接借鉴不同 Issue 类型使用不同字段、安全私密披露、部署形态必填、Feature 强制用例、PR 关联测试和文档、按路径自动标注范围。

禁用空白 Issue、所有非小改动先讨论、英语政策、多仓库分流和社区热度排序则要结合团队规模调整。复制模板容易，持续 Triage、Review 和更新规则才是真正成本。

## 🧑‍💼 CODEOWNERS：模块级所有权
dify 通过 `CODEOWNERS` 把"谁负责哪个目录"编码成文件——这是隐式治理的核心机制。

**文件位置**：`/Users/xu/code/github/dify/.github/CODEOWNERS`
**核心代码**（行 7 + 行 47-72）：

```gitignore
# Default catch-all owners
* @crazywoola @laipz8200

# Backend - Workflow - Engine (Core graph execution engine)
/api/core/workflow/graph_engine/ @laipz8200 @QuantumGhost
/api/core/workflow/runtime/ @laipz8200 @QuantumGhost
/api/core/workflow/graph/ @laipz8200 @QuantumGhost
/api/core/workflow/graph_events/ @laipz8200 @QuantumGhost
/api/core/workflow/node_events/ @laipz8200 @QuantumGhost

# Backend - Workflow - Nodes (Agent, Iteration, Loop, LLM)
/api/core/workflow/nodes/agent/ @Nov1c444
/api/core/workflow/nodes/iteration/ @Nov1c444
/api/core/workflow/nodes/loop/ @Nov1c444
/api/core/workflow/nodes/llm/ @Nov1c444

# Backend - RAG (Retrieval Augmented Generation)
/api/core/rag/ @JohnJyong
/api/services/dataset_service.py @JohnJyong
/api/services/knowledge_service.py @JohnJyong
/api/models/dataset.py @JohnJyong
```

**解读**：
- 第 3 行：默认所有者——所有 PR 至少需要 `@crazywoola` 或 `@laipz8200` 之一 review
- 第 6-10 行：工作流**引擎**有两人共同负责——核心代码 double-check
- 第 13-16 行：工作流**节点**（Agent、Iteration 等）归 `@Nov1c444`——单 owner（trust 模式）
- 第 19-22 行：RAG 模块归 `@JohnJyong`——跨目录归属（包含 service、model、controller）
- **关键设计**：
  - **核心模块双 owner**（互相 review）——降低关键路径风险
  - **周边模块单 owner**（不阻塞）——提高迭代速度
  - **跨目录归属 RAG**——支持"按领域而非按层"的所有权模型
- 启用 "Require review from Code Owners" 后，PR 必须有 owner 批准才能 merge——**机器强制守门**

## ✅ 关键要点总结
- dify 采用总指南、结构化模板、自动化和目录规范组成的分层治理
- Bug 模板优化可诊断性，Feature 模板优化问题发现，Refactor 模板约束技术维护动机
- Bug 优先级看安全与核心可用性，Feature 优先级结合团队路线与社区反馈
- Issue 提供问题上下文，PR 提供解决方案证据，`Fixes #...` 连接两者
- Cloud、Docker 和 Source 是必填诊断维度，体现托管与开源部署并行支持
- 禁用空白 Issue 与跨仓库 contact links 降低噪音和错误路由
- `good first issue`、插件仓库和 Discord/Discussions 共同构建多层参与入口
- 自动化处理标签与检查，Maintainer 保留优先级、架构和合并判断

## 📝 练习题
### 练习：基础（必做）
根据关键文件清单，为“用户在 Docker 部署中无法登录”写出从提交 Issue 到 PR 合并的完整路径。列出每一步产生的结构化信息。

**检查点**：是否包含版本、部署形态、日志、Critical 判断、测试和 Issue 关联？

### 练习：进阶
对比 dify 的 Bug 与 Feature 优先级表，设计一套不会混淆严重程度和产品价值的标签。说明谁能添加、何时复核、什么证据会触发升级。

**检查点**：Feature 的社区热度是否与 Bug 的核心可用性分开评估？

### 练习：挑战（选做）
为一个同时提供 SaaS、Docker 和源码部署的项目设计协作控制面：三个 Issue Form、contact links、PR checklist、自动范围标签和 Triage 流程。

**检查点**：是否能把安全、插件、文档、配置问答和核心 Bug 分流到正确位置？

## 📖 参考资料
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/bug_report.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/feature_request.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/refactor.yml`
- `/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/config.yml`
- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/.github/CODEOWNERS`
- `/Users/xu/code/github/dify/.github/labeler.yml`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/web/AGENTS.md`
- GitHub Docs：Building a strong community
- GitHub Docs：About issue and pull request templates

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
