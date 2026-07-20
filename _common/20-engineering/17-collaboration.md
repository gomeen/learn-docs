# 27 跨团队协作与沟通

> 代码是写给人看的,顺便让机器执行——跨团队协作的本质,是让「别人能放心依赖你的代码」。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解跨团队协作的四大核心要素：API 契约、RFC、SLA、上下游对齐
- 区分同步 / 异步沟通的适用场景,做出合适选择
- 掌握冲突管理的三个原则：对事不对人、共同目标、第三方调解
- 编写一份专业、清晰的跨团队沟通模板
- 理解 dify 的领域异常分层（services/errors）作为协作契约

## 📚 前置知识

- 基本的 HTTP / API 知识
- 了解微服务架构下的「服务边界」概念
- 阅读过 `../../dify/01-fundamentals/12-async-asyncio.md`,理解异步任务的边界

## 1. 核心概念

### 1.1 为什么跨团队协作这么难？

当代码只在一个团队内部流通时,**沟通成本可控**——大家共享上下文,有共同的代码所有权。但跨团队时,情况变了：

| 团队内部               | 跨团队                       |
| ---------------------- | ---------------------------- |
| 「这个函数干嘛的」     | 「你的 API 怎么调？」        |
| 随时找人 review        | 等对方排期,可能要 1 周       |
| Slack 群里吼一声       | 跨时区、跨公司,异步沟通     |
| 改接口不打招呼         | 改接口 = 对方 P0 事故        |
| 失败了一起加班         | 失败时互相甩锅               |

**根本原因**：跨团队协作的核心是**「降低对方的认知负担」**。每一个文档、每一个异常、每一次同步,都是在为「不需要找你确认」做投资。

### 1.2 跨团队协作的四大支柱

#### 支柱一：API 契约（Contract）

API 是跨团队协作的**最核心契约**。契约要回答：

- **What**：这个 API 做什么（功能）
- **How**：参数是什么、返回是什么（接口）
- **When**：SLA 是多少（可用性、延迟）
- **What if**：错误码代表什么（异常语义）
- **Change**：怎么变更（兼容性策略）

**dify 的实践**：`api/services/errors/` 下的领域异常定义了**服务间错误契约**——服务之间通过异常类型沟通,而不是直接传 HTTP 状态码。

#### 支柱二：RFC（Request For Comments）

重大决策（数据库选型、架构升级、API 大改）必须**先 RFC,后实现**：

```markdown
# RFC 模板（简化版）

## 标题：把用户认证从 Session 迁到 JWT
## 状态：Draft / Accepted / Rejected / Superseded
## 作者：alice
## 截止日期：2026-08-01

## 背景
- 当前痛点: 服务端 session 不能横向扩展
- 影响范围: 所有 API

## 方案 A：纯 JWT
- 优点: 无状态
- 缺点: 撤销困难,无法踢人下线

## 方案 B：JWT + Redis 黑名单
- 优点: 兼顾无状态 + 可撤销
- 缺点: 引入 Redis 依赖

## 决策
采纳方案 B。

## 影响
- 前端: 改 1 处
- 后端: 改 3 处
- 运维: 监控加 2 个指标
```

**关键**：RFC 是**异步决策工具**——不强制开会,让利益相关方在评论里讨论,最后归档。

#### 支柱三：SLA（Service Level Agreement）

SLA 定义「服务的承诺底线」,是**对方规划工作的依据**：

| 指标             | 示例承诺                          |
| ---------------- | --------------------------------- |
| 可用性           | 99.9% (月停机 < 43 分钟)         |
| 延迟 P95         | < 200ms                           |
| 错误率           | < 0.1%                            |
| 变更通知         | 至少提前 5 个工作日                |
| 事故响应         | P0 30 分钟内首响,P1 2 小时        |

**没有 SLA 的服务 = 不可依赖的服务**。SLA 倒逼自己做好可观测性和降级方案。

#### 支柱四：上下游对齐

上游（依赖方）和下游（被依赖方）的责任**不对称**：
- **下游**有责任**提前通知**变更（breaking change 警告）
- **上游**有责任**理解契约**（不能假设下游会配合你）

**常见反模式**：
- ❌ 下游悄悄改 API → 上游线上 P0
- ✅ 下游 deprecate 旧字段,加 `Deprecation` header,文档说明 6 个月后删除
- ❌ 上游不看 changelog,直接用新字段 → 上游自己背锅
- ✅ 上游监控 changelog,主动升级依赖

### 1.3 同步 vs 异步沟通

| 维度       | 同步（会议）              | 异步（文档 / IM）       |
| ---------- | ------------------------- | ----------------------- |
| 适合       | 复杂决策、冲突解决、bonding | 状态同步、决策记录、答疑 |
| 优势       | 信息密度高、即时反馈      | 可搜索、不打断、可深思  |
| 劣势       | 时区敏感、容易跑题        | 反馈慢、易误解          |

**经验法则**：
- **能用异步,先用异步**——发一条结构化的消息,等待回复
- **异步解决不了,再开同步**——会议必须有明确议程和结论
- **结论必落地文档**——会议开完,5 分钟内发纪要

### 1.4 冲突管理三原则

#### 原则一：对事不对人

- ❌「你这个方案不行」→ 人身攻击
- ✅「这个方案在 X 场景下不适用,因为 Y」→ 关注方案本身

#### 原则二：寻找共同目标

冲突往往来自**虚假对立**。找到共同目标后,方案差异自然缩小：

- ❌「前端要快 vs 后端要稳」
- ✅「我们都要让用户爽」→ 共同目标：用户满意度

#### 原则三：第三方调解

当冲突升级,**找不涉及利益的中立方**（架构师、Tech Lead、经理）作为调解人。中立方要：
- 倾听双方,理解诉求
- 重述问题,确认共识
- 提供选项,不强加答案
- 记录决策,follow up 落实

## 2. 代码示例

### 2.1 一个跨团队沟通邮件/Issue 模板

下面是一份**给上游团队**提交集成需求的 Issue 模板,展示异步沟通的「结构化」:

```python
# 文件：cross_team_issue_template.md
"""
跨团队 Issue 模板：把口头请求变成可追踪、可决策的协作。
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class CrossTeamRequest:
    title:           str
    target_team:     str
    requester:       str
    context:         str
    requirements:    list[str] = field(default_factory=list)
    sla_needed:      str | None = None
    deadline:        date | None = None
    blocked_by_us:   list[str] = field(default_factory=list)
    blocked_by_them: list[str] = field(default_factory=list)
    alternatives:    list[str] = field(default_factory=list)


# 示例: 向基础设施团队申请 Redis 集群
req = CrossTeamRequest(
    title="申请专用 Redis 集群用于 Celery 任务幂等性",
    target_team="infra",
    requester="backend-team / alice",
    context="""
        我们正在为金融相关 Celery 任务加幂等性,需要 Redis 存储幂等键。
        当前所有任务共用一个 Redis 实例,担心互相影响。
    """,
    requirements=[
        "Redis 7.x,内存 4GB 起步",
        "支持 cluster 模式（未来横向扩展）",
        "持久化关闭（幂等键可丢失,失败重试）",
        "我们组专属 namespace,便于监控隔离",
    ],
    sla_needed="""
        可用性 99.5%（与现有 Redis 一致即可）
        延迟 P95 < 5ms
    """,
    deadline=date(2026, 8, 15),
    blocked_by_us=[
        "已经在 PR #38500 实现 fallback: Redis 不可用时降级为 DB 唯一约束",
    ],
    blocked_by_them=[
        "需要 infra 评估集群规格",
        "需要 infra 提供连接方式和监控",
    ],
    alternatives=[
        "方案 A: 专用集群（推荐,隔离干净）",
        "方案 B: 复用现有 Redis + 单独 DB index（成本低,但有干扰）",
        "方案 C: 用现有 PostgreSQL 唯一约束（已实现 fallback）",
    ],
)

# 渲染成 Issue 正文
body = f"""
# {req.title}

**目标团队**: {req.target_team}
**发起人**: {req.requester}
**截止日期**: {req.deadline}

## 背景
{req.context}

## 需求
{chr(10).join(f"- {r}" for r in req.requirements)}

## SLA 要求
{req.sla_needed}

## 我们这边的准备
{chr(10).join(f"- {x}" for x in req.blocked_by_us)}

## 需要你们支持
{chr(10).join(f"- {x}" for x in req.blocked_by_them)}

## 备选方案
{chr(10).join(req.alternatives)}

cc @infra-lead @backend-lead
"""
print(body)
```

**说明**：
- 第 30-32 行：明确「目标团队」和「截止日期」,避免请求石沉大海
- 第 45-47 行：SLA 显式提出,对方有据可依
- 第 50-53 行：**双向清单**——既说「我做了什么」,又说「需要你做什么」,避免单向求助
- 第 56-59 行：备选方案给对方面子（A 最好,C 是兜底）,加速决策

### 2.2 常见错误：模糊请求导致来回拉扯

```python
# ❌ 错误：模糊请求,信息不全
def bad_request():
    slack_message = """
        @infra 同学,我们需要个 Redis,
        麻烦帮忙搞一下,谢谢!
    """
    # 问题: 没说规格、没说时间、没说 SLA、没 cc 决策人
    # 结果: 对方要追问 3-5 轮,平均耗时 1 周

# ✅ 正确：结构化请求,一次说清
def good_request():
    issue_body = """
        ## 背景
        我们要为 Celery 任务加幂等性（PR #38500）,
        需要专用 Redis 避免与其他任务互相影响。

        ## 需求规格
        - Redis 7.x,4GB 内存
        - 集群模式支持
        - 专属 namespace: celery-idempotency

        ## SLA
        99.5% 可用性,P95 < 5ms

        ## 时间
        8/15 前需要交付,后续我们 PR 会等合并。

        ## 备选
        如果资源紧张,我们也有 PostgreSQL 兜底方案。

        cc @infra-lead @backend-lead
    """
    # 结果: 一次 review,通过/驳回都有据可依,平均 2-3 天
```

## 3. dify 仓库源码解读

### 3.1 分层架构是「跨服务协作边界」的形式化

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 106-110）：

```markdown
### Architecture & Boundaries

- Mirror the layered architecture: controller → service → core/domain.
- Reuse existing helpers in `core/`, `services/`, and `libs/` before creating new abstractions.
- Optimise for observability: deterministic control flow, clear logging, actionable errors.
```

**解读**：
- 第 107 行：**controller → service → core** 三层架构定义了「跨服务协作边界」
  - Controller 层: 对外 API,**与外部世界的契约**
  - Service 层: 业务流程编排,**与其它 Service 的契约**
  - Core 层: 领域逻辑,**与业务无关的可复用核心**
- 第 108 行：**复用 > 新造**——跨服务时,这个原则尤其重要：先在 `core/`、`services/`、`libs/` 找现成,避免「每个团队都自己造轮子」
- 第 109 行：**可观测性** = 跨团队排错的基础——没有日志,远程团队只能猜

**给跨团队协作的启示**：
- **分层即契约**: Controller 层改了要通知下游,Core 层改了要通知所有 Service 使用方
- **复用是协作润滑剂**: 一个 `libs/` 目录的 helper,被 5 个团队用 = 5 倍的协作收益
- **可观测性是对其他团队的礼貌**: 出问题别人能远程 debug,不用拉你开会

### 3.2 领域异常是「跨服务错误契约」

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 112-118）：

```markdown
### Logging & Errors

- Never use `print`; use a module-level logger:
  - `logger = logging.getLogger(__name__)`
- Include tenant/app/workflow identifiers in log context when relevant.
- Raise domain-specific exceptions (`services/errors`, `core/errors`) and translate them into HTTP responses in controllers.
- Log retryable events at `warning`, terminal failures at `error`.
```

**解读**：
- 第 117 行：**领域异常**（`services/errors`, `core/errors`）是**跨服务的错误契约**
  - Service A 抛 `WorkflowNotFoundError`,Service B 不需要知道是 HTTP 404,只需 catch 这个领域异常
  - Controller 层负责**翻译**（domain exception → HTTP response）
- 第 118 行：`warning` vs `error` 的语义区分——下游看到 `error` 知道是「终态失败」,看到 `warning` 知道是「可重试」

**文件位置**：`/Users/xu/code/github/dify/api/services/errors/__init__.py`
**核心代码**（行 1-13）：

```python
from . import (
    account,
    app,
    app_model_config,
    audio,
    base,
    conversation,
    dataset,
    document,
    enterprise,
    file,
    index,
    message,
)
```

**解读**：
- 第 1-13 行：`services/errors/` 下的**所有领域异常模块**通过这个 `__init__.py` 统一导出
- 这是「**领域异常的集中管理**」——任何 Service 抛异常,只能从这一处 import
- **协作意义**:
  - 上游 Service 知道「抛哪些异常是合法的」——只能从 `services.errors` 里选
  - 下游 Service 知道「要 catch 哪些异常」——也是从这个清单里选
  - 任何人加了新异常,所有相关方 review 一次即可,无需 grep 整个代码库

**给跨团队协作的启示**：
- **领域异常 = 跨服务的接口文档**——和函数签名同等重要
- **集中管理** 让协作更可预测：不需要 `grep -r 'raise' api/` 来发现所有可能的异常
- **分层翻译** 让 Service 可复用: Service 不依赖 HTTP,只依赖领域语义

## 4. 关键要点总结

- **跨团队协作的核心是降低对方认知负担**——每个文档、每个异常、每次同步都是投资
- **四大支柱**：API 契约、RFC、SLA、上下游对齐
- **同步 vs 异步**：能用异步先用异步,异步解决不了再同步,结论必落地文档
- **冲突三原则**：对事不对人、寻找共同目标、第三方调解
- **dify 的分层架构**（controller → service → core）就是**跨服务协作边界**的形式化
- **dify 的领域异常分层**（services/errors）是**跨服务错误契约**——上游抛、下游 catch,Controller 翻译
- **集中管理**比**分散定义**更利于协作——`services/errors/__init__.py` 是协作基础设施

## 5. 练习题

### 练习 1：基础（必做）

阅读 `api/AGENTS.md` 第 106-118 行,写一份**「跨团队服务对接检查清单」**（至少 8 项）,覆盖分层、异常、日志、复用四个维度。

**参考答案**：见 `solutions/27-collaboration-basic.md`

### 练习 2：进阶

为「dify 集成一个新的 LLM Provider（如 Claude 3.5）」这个跨团队项目,写一份**简化版 RFC**（200 字以内）,包含：背景、方案 A/B、决策、影响范围。

### 练习 3：挑战（选做）

在 dify 仓库中,执行 `git log --oneline -- api/services/errors/ | head -20`,观察**领域异常的演化历史**。挑 1 个你认为「演进得很合理」或「演进得很奇怪」的 commit,写 200 字分析,说明它如何体现（或破坏）了跨服务协作契约。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md` —— 行 106-110 架构边界、行 112-118 异常契约
- `/Users/xu/code/github/dify/api/services/errors/__init__.py` —— 领域异常集中管理
- `/Users/xu/code/github/dify/CONTRIBUTING.md` —— 跨团队协作入门
- 《Team Topologies》by Matthew Skelton —— 团队拓扑与协作模式
- Google SRE Book: https://sre.google/sre-book/table-of-contents/ —— SLA 实践
- RFC 文档范例: https://github.com/kubernetes/community/tree/master/contributors/design-proposals

---

**文档版本**：v1.0
**最后更新**：2026-07-13
