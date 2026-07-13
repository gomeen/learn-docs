# 11.17 架构决策记录（ADR）

> 用 Architecture Decision Record 保存重大技术选择的背景、结论和后果，让团队能够理解“为什么这样设计”。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释 ADR 的用途、边界和生命周期
- 判断哪些重大技术选型或不可逆决策值得写 ADR
- 使用 Context / Decision / Consequences 组织决策记录
- 比较候选方案，并诚实记录被接受的负面后果
- 通过状态和替代关系维护 ADR 历史
- 从 dify `api/AGENTS.md` 识别隐式架构决策及其局限

## 📚 前置知识

- 基本软件架构概念：模块、依赖、边界和质量属性
- Git 版本控制与代码评审流程
- 对数据库、消息队列、API 或部署至少一种工程场景有基础认识
- 建议先学习 [技术文档写作：README / ADR / Runbook](./15-tech-writing.md)

## 🧭 核心概念

### ADR 是什么

ADR 是 **Architecture Decision Record**，即架构决策记录。
每一条 ADR 聚焦一个重要决策，说明当时的上下文、采用的方案以及带来的后果。
多条 ADR 按时间组成 Architecture Decision Log，构成系统设计演进的可追溯历史。

ADR 不等于完整架构设计文档：

- 架构图描述系统现在由什么组成
- API 文档描述系统如何被调用
- ADR 解释为何在特定约束下选择这种架构
- Git commit 描述某次代码变更，但通常不足以承载完整权衡

ADR 的价值不在篇幅，而在于保留代码之外的决策信息。

### 为什么只读代码不够

假设代码显示系统通过 Redis 投递后台任务。
代码可以说明队列名称、重试次数和消费者实现，却无法可靠表达：

- 当时业务要求 API 在多少毫秒内响应？
- 团队为什么没有采用数据库轮询？
- 为什么允许“至少一次”投递而不是“恰好一次”？
- 引入 Redis 后承担了哪些运维成本？
- 流量达到什么规模时需要重新评估？

这些问题决定未来变更是否安全，却很容易随着人员变化而丢失。
ADR 把口头背景变成与代码一起版本化的工程资产。

### 何时应该写 ADR

判断标准不是“改动代码多不多”，而是**决策影响是否广、代价是否高、未来是否容易被误解**。

#### 重大技术选型

以下场景通常值得记录：

- 选择数据库、缓存、消息队列或搜索引擎
- 确定同步、异步或事件驱动的交互模式
- 引入核心框架、公共库或云服务
- 选择单体、模块化单体或微服务边界
- 统一认证、授权、租户隔离和密钥管理策略
- 定义公共 API 兼容与版本策略

#### 不可逆或回退成本很高的决策

“不可逆”并非绝对无法修改，而是修改会涉及大规模迁移、兼容或停机，例如：

- 数据主键与分区策略
- 持久化格式和事件 Schema
- 对外 API 的公开契约
- 多租户数据隔离模型
- 基础设施提供商的深度绑定

决策越难回退，越应该在实施前记录并评审。

#### 存在真实争议与取舍

如果多个合理方案各有优劣，ADR 能防止评审结论散落在会议、聊天和 PR 评论中。
记录被否决方案不是为了证明谁错了，而是避免后来者在相同约束下重复完整调研。

### 何时不必写 ADR

以下内容通常无需单独创建 ADR：

- 容易回退的局部重构
- 已有团队规范明确覆盖的普通实现选择
- 不影响架构属性的变量命名和格式化
- 仅描述操作步骤的内容，应写入 Runbook
- 仅描述 API 字段的内容，应写入 API 文档

但如果一个“小改动”改变了安全边界、数据一致性或公共兼容性，它仍可能是架构决策。

### ADR 的最小结构

#### Context

Context 描述为什么必须决策，而不是提前为某个答案辩护。
应包含：

- 当前问题和业务目标
- 规模、时延、可靠性、成本等约束
- 已知事实与假设
- 相关质量属性
- 候选方案及评估标准

高质量 Context 能让未来读者在同样条件下理解为何得到相同结论。

#### Decision

Decision 要写明确结论和适用边界。
避免“我们决定使用更先进的方案”这类不可执行表述。
应说明选了什么、在何处使用、关键规则是什么、哪些内容明确不在范围内。

#### Consequences

Consequences 记录决策后的现实，包括正面、负面和中性影响：

- 获得哪些能力
- 牺牲哪些能力
- 增加哪些依赖与维护工作
- 需要哪些迁移、监控和培训
- 出现哪些新故障模式

如果一条 ADR 只有收益没有成本，通常意味着权衡分析还不充分。

### 建议补充的元数据

一个可维护的 ADR 通常还包含：

- **编号**：例如 `ADR-0012`
- **标题**：使用决策语句而不是宽泛主题
- **状态**：Proposed、Accepted、Deprecated、Superseded
- **日期**：结论生效或接受的日期
- **决策者**：团队或角色，不一定是个人
- **关联记录**：被哪条 ADR 替代，或替代了哪条 ADR

状态使读者能够区分历史记录与当前规则。
不要删除已经失效的 ADR；保留它并链接新的替代记录，才能保存演进路径。

### ADR 生命周期

```text
发现问题
   ↓
起草 Proposed ADR
   ↓
评审 Context、候选方案与后果
   ↓
接受 Accepted / 拒绝 Rejected
   ↓
实施并关联代码与迁移
   ↓
条件变化时创建新 ADR
   ↓
旧 ADR 标记 Superseded
```

ADR 最适合在实现前或实现过程中编写。
如果等到项目结束再补，Context 往往已被成功结果重新解释，负面信息也更容易遗失。

### ADR 与评审机制

ADR 应与代码一样接受评审，但评审重点不同：

- 问题和约束是否真实、完整？
- 候选方案是否公平比较？
- 结论是否清楚到能指导实现？
- 负面后果是否被接受并有缓解措施？
- 是否定义重新评估条件？

对于高影响决策，可以先合并 Accepted ADR，再分阶段合并实现。
实施 PR 应反向链接 ADR，使“决策—代码”可以双向追踪。

### 常见失败模式

#### 把 ADR 写成事后宣传

只列最终方案优点，不记录替代方案和代价，会让 ADR 失去可信度。
应保留当时真实的不确定性，并区分事实、假设和偏好。

#### 记录过多实现细节

具体类名和临时代码结构变化快，会加速 ADR 过期。
ADR 应聚焦稳定边界和原则；实现细节放在设计文档、代码和测试中。

#### 原地修改历史结论

覆盖旧 ADR 会抹掉当时语境。
正确做法是创建新记录并将旧记录标为 Superseded，只有拼写和不改变语义的小修正适合原地修改。

#### 决策没有触发条件

“以后再评估”不可操作。
应写成“当日任务量超过 100 万或端到端 P95 超过 5 秒时重新评估”一类可观察条件。

## 💻 代码示例

### 完整 ADR：后台任务采用 Redis 队列

下面是一个独立示例。它不是 dify 源码，而是一份可直接放入项目 `docs/adr/` 的完整记录。

**示例文件**：`docs/adr/0007-use-redis-for-background-jobs.md`  
**示例行号**：第 1-42 行

```markdown
# ADR-0007：后台任务使用 Redis 队列

- Status: Accepted
- Date: 2026-07-13
- Deciders: Backend Team, SRE Team

## Context

HTTP 接口需要在 300 ms 内返回，但报表生成通常耗时 10-90 秒。
当前在请求进程内执行任务，会造成超时，并在进程重启时丢失工作。
系统日均产生约 50,000 个任务，允许至少一次投递，但不能静默丢失。
团队已经维护 Redis，用于缓存和短期协调。

候选方案包括：

- 继续同步执行并提高网关超时
- 使用数据库任务表，由 Worker 轮询
- 使用 Redis 队列，由独立 Worker 消费

## Decision

后台任务使用 Redis 队列，HTTP 接口只验证输入并返回 `job_id`。
Worker 必须以幂等方式处理任务，失败任务最多指数退避重试 5 次。
任务状态持久化到数据库；Redis 不作为业务结果的唯一存储。
涉及资金结算的任务暂不采用此通道，继续使用事务性数据库流程。

## Consequences

### Positive

- API 响应时间不再取决于任务执行时长
- Worker 可以独立扩缩容，并隔离任务故障
- 复用团队已有 Redis 运维能力

### Negative

- 系统新增队列积压、重复投递和 Worker 不可用等故障模式
- 所有任务处理器都要实现幂等性
- 本地开发和测试需要启动 Redis 与 Worker

## Rollout

先迁移报表任务，监控一周的排队时间、失败率和重复执行次数，
再迁移邮件任务。保留同步路径作为首阶段回滚开关。

## Revisit when

当日任务量超过 1,000,000、P95 排队时间超过 5 秒，
或需要严格顺序与跨服务事务时，重新评估专用消息中间件。
```

**说明**：

- Context 给出可量化时延、任务规模和可靠性约束
- Decision 不仅写“使用 Redis”，还限定状态存储、重试、幂等和排除范围
- Consequences 同时承认扩缩容收益与新故障模式
- Rollout 和 Revisit when 将决策连接到实施、监控和未来演进

## 🔍 dify 仓库源码解读

### `api/AGENTS.md` 中的隐式架构规则

dify 仓库当前没有用显式 `docs/adr/` 目录集中保存这些规则，但 `AGENTS.md` / `CLAUDE.md` 等面向开发者和 Agent 的指导文件承担了部分 ADR 职能。
例如，下面片段明确规定后端分层、复用方向、可观测性和异常边界。

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（第 105-118 行）：

```markdown

### Architecture & Boundaries

- Mirror the layered architecture: controller → service → core/domain.
- Reuse existing helpers in `core/`, `services/`, and `libs/` before creating new abstractions.
- Optimise for observability: deterministic control flow, clear logging, actionable errors.

### Logging & Errors

- Never use `print`; use a module-level logger:
  - `logger = logging.getLogger(__name__)`
- Include tenant/app/workflow identifiers in log context when relevant.
- Raise domain-specific exceptions (`services/errors`, `core/errors`) and translate them into HTTP responses in controllers.
- Log retryable events at `warning`, terminal failures at `error`.
```

**解读**：

- 第 108 行的 `controller → service → core/domain` 是明确的架构边界，可直接指导代码放置与依赖方向
- 第 109 行优先复用现有 helper，抑制平行抽象和局部“新框架”扩散
- 第 110 行把可观测性提升为架构质量目标，而不是实现结束后的附加工作
- 第 114-118 行统一日志和异常职责：领域层抛领域异常，控制器转换 HTTP 响应
- 这些内容相当于 ADR 的 **Decision** 和部分 **Consequences**，能防止实现偏离既有架构

### 为什么它只是“隐式 ADR”

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（第 1-25 行）：

```markdown
# API Agent Guide

## Notes for Agent (must-check)

Before changing any backend code under `api/`, you MUST read the surrounding docstrings and comments. These notes contain required context (invariants, edge cases, trade-offs) and are treated as part of the spec.

Look for:

- The module (file) docstring at the top of a source code file
- Docstrings on classes and functions/methods
- Paragraph/block comments for non-obvious logic

### What to write where

- Keep notes scoped: module notes cover module-wide context, class notes cover class-wide context, function/method notes cover behavioural contracts, and paragraph/block comments cover local “why”. Avoid duplicating the same content across scopes unless repetition prevents misuse.
- **Module (file) docstring**: purpose, boundaries, key invariants, and “gotchas” that a new reader must know before editing.
  - Include cross-links to the key collaborators (modules/services) when discovery is otherwise hard.
  - Prefer stable facts (invariants, contracts) over ephemeral “today we…” notes.
- **Class docstring**: responsibility, lifecycle, invariants, and how it should be used (or not used).
  - If the class is intentionally stateful, note what state exists and what methods mutate it.
  - If concurrency/async assumptions matter, state them explicitly.
- **Function/method docstring**: behavioural contract.
  - Document arguments, return shape, side effects (DB writes, external I/O, task dispatch), and raised domain exceptions.
  - Add examples only when they prevent misuse.
- **Paragraph/block comments**: explain *why* (trade-offs, historical constraints, surprising edge cases), not what the code already states.
```

**解读**：

- 第 5 行把不变量、边界情况和权衡视为规范，说明 dify 重视代码附近的设计上下文
- 第 9-11 行将信息分散到模块、类、函数和局部注释，发现路径与代码作用域一致
- 第 15-24 行规定各层 docstring 应记录的稳定信息，确实能保存部分“为什么”
- 但该片段没有 ADR 常见的日期、状态、候选方案和被替代关系
- 因此它适合表达**当前必须遵守的开发规则**，却不完全替代对重大历史选型的独立 ADR

## ✅ 关键要点总结

- ADR 是 Architecture Decision Record，记录重大决策的背景、选择和后果
- 重大技术选型、不可逆决策和高成本迁移尤其需要 ADR
- Context / Decision / Consequences 是最小且稳定的核心结构
- 负面后果、替代方案与重新评估条件决定 ADR 是否真正有用
- 决策变化时创建新 ADR 并标记旧记录 Superseded，不应抹去历史
- dify 的 `AGENTS.md` / `CLAUDE.md` 承担部分 ADR 职能，但缺少显式决策记录的完整历史结构

## 🧪 练习题

### 练习：基础（必做）

判断下列事项是否需要 ADR，并分别写出理由：

- 将一个函数从 80 行拆成 3 个函数
- 把公共 API 认证从 Session 改为 OAuth 2.0
- 统一变量名拼写
- 将租户数据从共享表迁移为独立 Schema
- 为一个已知告警补充重启步骤

提示：关注影响范围、回退成本和是否存在长期权衡。

### 练习：进阶

为“前端共享状态采用 Jotai 而不是新增全局事件监听器”起草 ADR。
至少包含三个候选方案，并说明状态频率、所有权、调试能力和迁移成本。

### 练习：挑战（选做）

从 `/Users/xu/code/github/dify/api/AGENTS.md` 中选择一条架构规则，将它改写成完整 ADR。
你需要补充原文件没有提供的信息：

- 哪些事实是假设，必须向维护者确认
- 至少两个候选方案
- 正面和负面后果
- 可观察的重新评估条件

不要把自己的推测伪装成 dify 的真实历史；未知内容应明确标注为“待确认”。

## 📖 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/CLAUDE.md`
- `/Users/xu/code/github/dify/web/CLAUDE.md`
- Architecture Decision Records：https://adr.github.io/
- Michael Nygard, Documenting Architecture Decisions：https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- MADR Template：https://adr.github.io/madr/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
