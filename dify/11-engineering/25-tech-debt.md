# 25 技术债务管理

> 技术债务不是「坏的代码」,而是「为了短期速度,主动接受的长期成本」——管理债务,而不是被债务管理。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Ward Cunningham 的原始定义理解技术债务的本质
- 区分「主动债务 vs 被动债务」「有意 vs 无意」四象限
- 识别常见的代码坏味道（code smell）
- 设计合理的还款策略（重写 / 重构 / 增量改进 / 专项 sprint）
- 在 dify 仓库中,识别 AGENTS.md 中规定的「债务预防」约束

## 📚 前置知识

- 基本的面向对象 / 函数式编程概念
- 阅读过 `01-fundamentals/12-async-asyncio.md`,理解「长期可维护性」的价值
- 了解 dify 的分层架构（controller → service → core）

## 1. 核心概念

### 1.1 技术债务的定义（Ward Cunningham, 1992）

> 「发布代码就如同背负债务：只要持续开发新功能,就一直在『借债』——少量债务可以加速开发,但如果长期不还,就会面临『债务危机』,需要把越来越多的开发精力用于『还债』。」
> —— Ward Cunningham, OOPSLA 1992

注意 Cunningham 的原话重点：
- 债务**不是错误**,是**权衡**
- 适度的债务**能加速**（先发布再重构,比一开始就完美更快）
- **不还**才会致命（利息累积,变更成本指数增长）

### 1.2 债务的四象限

按「**主动/被动** × **有意/无意**」划分,技术债务有四类：

|              | 主动（明知）          | 被动（不知）          |
| ------------ | --------------------- | --------------------- |
| **有意**     | A. 战略债务（合理）   | C. 战术债务（待清理） |
| **无意**     | B. 鲁莽债务（危险）   | D. 幼稚债务（需培训） |

- **A 战略债务**：「先发 MVP,下个迭代再重构」——记录在 issue 里,有计划
- **B 鲁莽债务**：「没时间做对,先这样吧」——没有文档,没有 owner,危险
- **C 战术债务**：「当时没想到会这么火」——可以原谅,但要尽快还
- **D 幼稚债务**：「新同学不知道公司规范」——靠培训、Code Review 解决

**管理债务的第一步**：把所有债务分类到这四象限。**B 类要立刻处理,D 类要靠流程预防,A/C 类要记账**。

### 1.3 常见代码坏味道（Code Smells）

Martin Fowler 在《Refactoring》中列举的常见坏味道,按 dify 实际场景举例：

| 坏味道              | dify 中的表现                              | 还款方式             |
| ------------------- | ------------------------------------------ | -------------------- |
| Long Method         | 某 Service 函数 > 100 行,做 5 件事         | Extract Method       |
| Large Class         | 某 Manager 类 > 800 行（违反 AGENTS.md）   | Extract Class        |
| Duplicated Code     | 多个 Controller 重复同样的参数校验         | Extract Helper       |
| Dead Code           | 注释掉的代码、永不调用的私有函数           | 删除                 |
| Speculative Generality | 没人用的抽象类、永远为 null 的配置项     | Collapse Hierarchy   |
| Shotgun Surgery     | 改一个需求要动 5 个文件                     | Move Method / Field  |
| Feature Envy        | Service 大量 getter 跨域访问 Model         | Move Method          |

### 1.4 债务度量：怎么知道债务有多少？

| 指标                   | 工具                            | 目标           |
| ---------------------- | ------------------------------- | -------------- |
| 圈复杂度（Cyclomatic） | `radon cc -s api/`              | 平均 < 10      |
| 重复率                 | `jscpd` / `pylint --disable=all --enable=duplicate-code` | < 3%          |
| 测试覆盖率             | `pytest --cov=api`              | 核心模块 > 80% |
| 文件行数               | `cloc api/` 或 shell             | 遵循 800 行规则 |
| 坏味道数量             | `ruff check --select=PLR0915`   | 持续下降       |

**关键**：度量是手段,不是目的。**一个 100% 覆盖、零坏味道的代码库,可能是过度工程**。

### 1.5 还款策略

#### 策略一：专项 Sprint（Boy Scout Rule 的进阶版）

每隔 4-6 个迭代,专门留 1 个 sprint **只做技术债**。比例参考：
- 初创期（速度优先）：0% 专项,随业务迭代时顺手还
- 成长期（产品稳定）：15-20% 时间
- 成熟期（性能 / 稳定优先）：25-30% 时间

#### 策略二：增量改进（Strangler Fig Pattern）

不重写整个模块,而是**让新代码逐步取代旧代码**。dify 的典型做法：
- 新需求用新模式写（旧代码不动）
- 旧代码只有「被动修改」时才清理
- 长期看,新代码占比会逐渐超过旧代码,达到「无感重构」

#### 策略三：重写（仅在必要时）

**只在以下情况考虑重写**：
- 旧代码**无人能维护**（所有 owner 都离职）
- 旧代码**严重阻碍**新功能交付（每周 50% 时间在还债）
- 重写 ROI > 3 倍（节省的维护时间 > 重写投入）

**不要**因为「代码丑」就重写——丑 ≠ 坏,坏 ≠ 必须重写。

#### 策略四：预防胜于还款

**最便宜的债务是「从未借过的债务」**。在 PR 阶段就阻止坏味道进入,比事后清理便宜 10 倍：
- CI 强制 lint（`make lint`）
- 强制 type-check（`make type-check`）
- 强制测试覆盖新代码（`make test`）

## 2. 代码示例

### 2.1 把「我们以后再优化」作为债务记账

下面是一个**债务登记簿**的极简实现,用于追踪「主动战术债务」：

```python
# 文件：tech_debt_registry.py
"""
技术债务登记簿：把「以后再优化」从口头承诺变成可追踪的 issue。
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class DebtQuadrant(Enum):
    STRATEGIC = "A 战略债务"   # 主动 + 有意
    TACTICAL  = "C 战术债务"   # 主动 + 无意（事后发现需要）
    RECKLESS  = "B 鲁莽债务"   # 被动 + 有意（危险）
    NAIVE     = "D 幼稚债务"   # 被动 + 无意（培训问题）


@dataclass
class TechDebt:
    title:        str
    description:  str
    quadrant:     DebtQuadrant
    location:     str          # 文件路径
    interest:     int = 1      # 每月利息（人为估计,1-5）
    opened_date:  date         = field(default_factory=date.today)
    due_date:     date | None  = None  # 计划还款日期
    owner:        str | None   = None

    def priority_score(self) -> int:
        """还款优先级 = 利息 × 4 象限权重。"""
        weights = {
            DebtQuadrant.RECKLESS:  10,  # B 类最危险,先还
            DebtQuadrant.TACTICAL:   5,
            DebtQuadrant.STRATEGIC:  2,
            DebtQuadrant.NAIVE:      1,  # 靠培训解决,不一定要 code 改
        }
        return self.interest * weights[self.quadrant]


# 示例：登记一个真实债务
debt = TechDebt(
    title="优化 sync_workflow 函数",
    description="async_workflow_service.py::trigger_workflow_async 内部"
                "Session 未复用,每次都新建连接。高并发下连接池压力大。",
    quadrant=DebtQuadrant.TACTICAL,
    location="api/services/async_workflow_service.py",
    interest=4,           # 影响生产环境稳定性
    due_date=date(2026, 8, 30),
    owner="alice",
)

print(f"{debt.title} | 优先级 {debt.priority_score()} | {debt.quadrant.value}")
# 输出: 优化 sync_workflow 函数 | 优先级 20 | C 战术债务
```

**说明**：
- 第 23-26 行：用 `Enum` 明确四象限,避免「模糊债务」
- 第 36-39 行：`priority_score` 把「利息 × 象限」量化,便于排序
- 第 49-56 行：真实登记一笔债务,带位置、利息、Owner、Due Date
- **关键**：「以后再优化」要落到 Owner + Due Date,否则就是 B 类鲁莽债务

### 2.2 常见错误：把债务「藏」在脑子里

```python
# ❌ 错误：口头承诺,无追踪
def ship_feature_v1():
    """先把功能发出去,代码乱点以后再说。"""
    # TODO: refactor this mess later
    # FIXME: this is ugly but works
    pass
# 后果：6 个月后,「以后」永远不来,新同学读不懂,改动成本 × 10

# ✅ 正确：登记到债务簿,排进迭代
def ship_feature_v2():
    """发功能 + 同时开 issue 记录技术债。"""
    # 实现功能
    implement_feature()

    # 同步开 issue（伪代码）
    create_github_issue(
        title="[Tech Debt] 拆分 sync_workflow 大函数",
        body="""
        **位置**: api/services/async_workflow_service.py::trigger_workflow_async
        **象限**: C 战术债务
        **原因**: 当时赶发布,内部 Session 没复用
        **影响**: 高并发下连接池压力大
        **计划**: 2026 Q3 第 2 个迭代
        **Owner**: alice
        """,
        labels=["tech-debt", "priority-medium"],
    )
```

## 3. dify 仓库源码解读

### 3.1 「800 行规则」是债务预防的硬约束

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 100-104）：

```markdown
- Prefer simple functions over small "utility classes" for lightweight helpers.
- Avoid implementing dunder methods unless it's clearly needed and matches existing patterns.
- Never start long-running services as part of agent work (`uv run app.py`, `flask run`, etc.); running tests is allowed.
- Keep files below ~800 lines; split when necessary.
- Keep code readable and explicit—avoid clever hacks.
```

**解读**：
- 第 103 行：**800 行硬上限**——超过必须拆分。这是从源头阻止「God Class」债务
- 第 104 行：**avoid clever hacks**——「聪明代码」是典型的鲁莽债务（B 类），阅读和维护成本极高
- 第 102 行：「Never start long-running services as part of agent work」——禁止 agent 跑长服务,这条是**债务预防**的反例检查：防止「临时调试代码」流入生产

**给债务管理的启示**：
- **预防**比**还款**便宜 10 倍：AGENTS.md 里的 800 行规则,就是从 PR 阶段卡住坏味道
- 这类**编码规范**本身就是「防债务」基础设施——新代码无法积累成债
- 团队入职培训的**第一课**就应该是读 AGENTS.md,避免 D 类幼稚债务

### 3.2 异常分层是「设计债务」的预警

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
- 第 117 行：**领域异常**是 dify 协作契约的一部分,违反这条 = 引入耦合债务
- 第 118 行：`warning` vs `error` 的语义区分——混乱的日志级别会让排查债务累积

**给债务管理的启示**：
- **异常分层**（domain → controller 翻译）是设计层面防债
- 如果一个 Service 直接抛 `HTTPException`,就是**架构债**——Service 知道了 HTTP 细节,无法复用
- 文件 `api/services/errors/__init__.py` 把所有领域异常聚合,**这就是「债务隔离层」**——业务代码不允许直接 import HTTP 异常

## 4. 关键要点总结

- **技术债务 = 主动接受的长期成本**,不是错误。错的是「不记账、不还款」
- **四象限分类**：A 战略（合理）、B 鲁莽（危险）、C 战术（待还）、D 幼稚（培训）
- **常见坏味道**：Long Method、Large Class、Duplicated Code、Dead Code、Shotgun Surgery
- **度量是手段不是目的**——过度追求 100% 覆盖是另一种债
- **还款策略**：专项 sprint、Strangler Fig 增量改进、极少数情况才重写
- **预防胜于还款**——AGENTS.md 里的 800 行规则、avoid clever hacks 就是 PR 阶段的防债
- dify 的**领域异常分层**（services/errors）防止「Service 耦合 HTTP 细节」这种架构债

## 5. 练习题

### 练习 1：基础（必做）

在 dify 仓库中执行 `wc -l api/services/async_workflow_service.py`（或你熟悉的某个 Service 文件），如果它**接近或超过** 800 行,识别其中至少 2 个**可以拆分的职责**,并写出拆分方案（不必真改,描述即可）。

**参考答案**：见 `solutions/25-tech-debt-basic.md`

### 练习 2：进阶

阅读 `api/AGENTS.md` 第 96-118 行（General Rules + Architecture + Logging）,从中**至少识别 3 条**「债务预防规则」,并解释它们分别防止的是哪一类债务（架构债 / 代码债 / 协作债）。

### 练习 3：挑战（选做）

为 dify 设计一个**轻量级技术债务登记 CLI**（用 Python），要求：
- 支持 `add / list / prioritize` 三个子命令
- 数据存储在 `tech_debt.json`
- 输出按 `priority_score` 降序排列
- 提示：参考练习 2.1 的 `TechDebt` dataclass,用 `argparse` 做 CLI,用 `json` 做持久化

## 6. 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md` —— 行 96-118 防债规范
- `/Users/xu/code/github/dify/api/services/errors/__init__.py` —— 领域异常分层（防架构债）
- Martin Fowler: 《Refactoring》（坏味道系统化）
- Ward Cunningham 1992 OOPSLA 演讲：https://wiki.c2.com/?WardExplainsDebtMetaphor
- GitHub Engineering: 「How We Maintain Our Open Source Codebases」

---

**文档版本**：v1.0
**最后更新**：2026-07-13
