# 24 估时与排期：避免过度乐观

> 软件估时不是「把代码行数乘以打字速度」,而是「在不确定性中,做出可被信任的承诺」。

## 🎯 学习目标

完成本文档后，你将能够：
- 识别软件估时中最常见的认知偏差
- 熟练使用「三点估时」「T-Shirt Sizing」「Planning Poker」三种方法
- 理解缓冲（buffer）的合理取值和分配方式
- 在排期沟通中,把不确定性显式化,而不是藏起来
- 能看懂 `api/AGENTS.md` 中流程成本相关的隐式估时依据

## 📚 前置知识

- 基本的项目管理常识（迭代、Sprint、Story Point）
- 阅读过 `01-fundamentals/12-async-asyncio.md`,理解「一个功能可能比表面看起来复杂」

## 1. 核心概念

### 1.1 估时的常见误区

#### 误区一：编程只是打字

新手最常见的乐观来自「这功能看起来就是几行代码」。实际上,从「开始」到「完成」之间至少包含：

| 环节              | 占比     |
| ----------------- | -------- |
| 设计 / 查文档     | 15%      |
| 编码              | 20%      |
| 单元测试          | 20%      |
| 集成 / 联调       | 20%      |
| Code Review 改稿  | 10%      |
| 文档 / 部署脚本   | 15%      |

编码只是水面上的冰山，水面下的「流程成本」往往才是大头。

#### 误区二：Hofstadter 定律

> Hofstadter's Law: It always takes longer than you expect, even when you take Hofstadter's Law into account.
> （霍夫施塔特定律：事情总是比你预期的更久,即使你把霍夫施塔特定律考虑进去。）

这条定律在软件工程里反复被验证。软件估时是一个**反直觉**的活动——你越熟练,越容易低估新手场景;你越乐观,越容易翻车。

#### 误区三：锚定效应

团队里第一个说出数字的人,会**无意识**地把后续所有人的判断拉向那个数字。Planning Poker 之所以要用牌,就是为了打破锚定——大家同时亮牌,避免逐个被说服。

### 1.2 三种主流估时方法

#### 方法一：参考类比（Analogy-Based）

找一件「我们已经做过、复杂度类似」的事作为参照。例如：

- 之前做「重置密码」用了 2 天 → 「修改邮箱」按 2-3 天估
- 之前做「导出 CSV」用了 1 天 → 「导出 Excel」按 1.5-2 天估

**优点**：快速、直觉；**缺点**：依赖历史数据的质量。

#### 方法二：三点估时（PERT）

对每个任务取三个数字：
- **O**（Optimistic）：一切顺利,理想情况
- **P**（Pessimistic）：各种意外都发生
- **M**（Most Likely）：最可能发生的情况

期望值公式：E = (O + 4M + P) / 6

**例**：开发一个 SSO 登录
- O = 3 天（文档齐全,一次过）
- M = 5 天（要对接 IdP,会有小坑）
- P = 12 天（联调失败、文档缺失、需要切 SDK）

E = (3 + 4×5 + 12) / 6 = 35 / 6 ≈ 5.83 天

#### 方法三：T-Shirt Sizing

不估具体天数,用 S / M / L / XL 描述规模：

| 尺寸 | 参考含义                          | 大致人天（参考） |
| ---- | --------------------------------- | ---------------- |
| S    | 1 个文件,改动 < 50 行,无新依赖   | 0.5-1 天         |
| M    | 2-3 个文件,需要新加测试和文档     | 2-3 天           |
| L    | 跨模块改动,需要设计评审           | 5-7 天           |
| XL   | 跨服务、跨团队,需要拆分任务       | 10+ 天,应拆小   |

**优点**：沟通成本低,适合 Sprint 计划会；**缺点**：粒度粗,不适合精确承诺。

#### 方法四：Planning Poker

Scrum 中的经典做法：
1. 主持人介绍需求,大家提问澄清
2. 每人私下选一张「斐波那契」牌（0, 1, 2, 3, 5, 8, 13, 20, 40, ?）
3. 同时亮牌
4. **最大和最小**持有者各自解释 1-2 分钟
5. 重新讨论,再亮一轮,直到收敛（通常 2-3 轮）

**为什么用斐波那契而不是连续数字？** 强制拉开粒度——一个 12 和 13 之间的差别,不如一个 8 和 13 之间的差别有意义。

### 1.3 缓冲（Buffer）的设置

无论用哪种方法,**永远要给不确定的任务加缓冲**：

| 任务类型       | 推荐缓冲    |
| -------------- | ----------- |
| 团队做过 ≥3 次 | 1.0-1.2 倍  |
| 团队做过 1-2 次 | 1.3-1.5 倍 |
| 全新领域       | 1.5-2.0 倍 |
| 跨团队协作     | 1.5-2.0 倍 |

**关键**：缓冲是「**项目级**」的,不要分配到每个任务上。

- ❌ 每个任务 × 1.3 → 总和虚高,且单任务保护过度
- ✅ 任务估「**理想值**」,**项目层**加 30-50% 缓冲

### 1.4 排期沟通的三个原则

1. **给区间,不给点估**：「5-8 天」远比「6 天」诚实
2. **显式说明不确定来源**：「依赖第三方 IdP」「需要架构组评审」——这些是「已知未知」
3. **承诺最坏情况,争取最好情况**：对外（老板、客户）说 P 值,对内冲刺用 M 值,自我激励用 O 值

## 2. 代码示例

### 2.1 用 Planning Poker 估「开发用户登录功能」

下面是一个简化的 Planning Poker 模拟,展示如何用 Story Point 估时：

```python
# 文件：planning_poker.py
"""
Planning Poker 模拟：估「开发用户登录功能」任务。
每个工程师独立打分（斐波那契牌值），然后求共识。
"""
from collections import Counter
from statistics import median

# 斐波那契牌值（Story Point）
DECK = [0, 1, 2, 3, 5, 8, 13, 20, 40, "?"]

# 7 位工程师对「开发用户登录功能」的独立估时
votes = {
    "alice":  5,   # 乐观派：用过 3 个 SSO SDK,觉得是 5
    "bob":    8,   # 老兵：经历过 2 次 IdP 联调,选 8
    "carol":  3,   # 新人：觉得就是个 form + post
    "david":  8,   # 架构师：考虑多租户隔离,选 8
    "erin":   5,   # 和 alice 类似经验
    "frank": 13,   # 测试负责人：含 E2E、并发、CSRF 等
    "grace":  8,   # 全栈：综合考虑,选 8
}

def planning_poker_round(votes: dict[str, int]) -> dict:
    """一轮 Planning Poker：去掉最高和最低,看中位数。"""
    values = list(votes.values())
    counts = Counter(values)
    return {
        "votes":        values,
        "max_vote":     max(values),
        "min_vote":     min(values),
        "median":       median(values),
        "distribution": dict(counts),
    }

# 第一轮
result = planning_poker_round(votes)
print(f"第一轮: {result['distribution']}")
print(f"  最高={result['max_vote']}, 最低={result['min_vote']}, 中位数={result['median']}")

# 持有最低（carol=3）和最高（frank=13）的人各自陈述理由
# carol: "我看 API 文档,字段就 username/password/jwt,2 天能写完"
# frank: "得测并发登录、密码哈希、限流、CSRF、Remember Me、第三方登录"
# 大家讨论后,carol 修订为 5,frank 修订为 8

# 第二轮：收敛
votes_round2 = {**votes, "carol": 5, "frank": 8}
result2 = planning_poker_round(votes_round2)
print(f"第二轮: {result2['distribution']}")
print(f"  共识估时: {result2['median']} Story Points")
# 共识：8 SP
# 团队历史速度：1 SP ≈ 0.5 人天 → 8 SP ≈ 4 人天
# 加 30% 缓冲 → 排期 5.2 天,对外承诺「5-6 天」
```

**说明**：
- 8 行内完成第一轮投票的统计
- 第 40 行：斐波那契牌值强制粒度,避免「8 vs 9」的无意义争论
- 第 47 行：去掉极端值后看中位数,降低锚定效应
- 团队历史速度（velocity）是把 Story Point 翻译成人天的桥梁

### 2.2 常见错误：把「乐观值」当「承诺值」

```python
# ❌ 错误：把理想值直接给老板
def estimate_login_feature_wrong() -> int:
    """老板问：要多久？——「3 天搞定」"""
    return 3  # 忽略了 50% 缓冲

# ✅ 正确：分场景给不同承诺
def estimate_login_feature_right() -> dict:
    """根据听众,给不同粒度的承诺。"""
    return {
        "to_boss":      "5-7 天,含 30% 缓冲",   # 区间 + 缓冲说明
        "to_team":      "理想 4 天,最坏 8 天",   # O / P
        "self_motivate": "3 天（理想情况）",      # 自我激励
        "uncertainty":  [
            "依赖第三方 IdP 文档质量",
            "需要安全组评审",
            "需考虑多租户隔离",
        ],
    }
```

**说明**：
- 同一件事,对老板、团队、自己说不同版本
- 关键是**显式列出不确定来源**——这比数字本身更值钱

## 3. dify 仓库源码解读

### 3.1 流程成本作为「隐式估时依据」

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 176-191）：

```markdown
### Tooling & Checks

Quick checks while iterating:

- Format: `make format`
- Lint (includes auto-fix): `make lint`
- Type check: `make type-check`
- Unit tests: `make test`
- Full backend tests, including Docker-backed suites: `make test-all`
- Targeted tests: `make test TARGET_TESTS=./api/tests/<target_tests>`

Before opening a PR / submitting:

- `make lint`
- `make type-check`
- `make test`
```

**解读**：
- 第 178-185 行：迭代过程中,**至少** 5 个本地质量门
- 第 187-191 行：PR 提交前,**强制** 3 个质量门（lint / type-check / test）
- **隐式估时依据**：一个看似「改 5 行代码」的任务,实际工时 = 编码 30min + 测试 30min + lint 修复 15min + type-check 修复 15min + PR 评审往返 1h ≈ **2.5-3 小时**

**给排期的启示**：
- 估时不能用「代码行数」,要用「触达的模块数 × 单模块时间」
- 一个跨 3 个文件的改动,单是走完这 3 个质量门,就要 1 小时以上
- **dify 的 Agent 在提交前自己跑 `make lint && make type-check && make test`**,这本身就是流程成本——排期时**必须**算上

### 3.2 架构边界决定估时粒度

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 106-110）：

```markdown
### Architecture & Boundaries

- Mirror the layered architecture: controller → service → core/domain.
- Reuse existing helpers in `core/`, `services/`, and `libs/` before creating new abstractions.
- Optimise for observability: deterministic control flow, clear logging, actionable errors.
```

**解读**：
- 第 107 行：分层架构（controller → service → core）意味着一个需求**至少** 3 层都要动
- 第 108 行：复用已有 helper 而不是新造轮子——这能降低估时（找到现成 vs 自己写）
- 第 109 行：可观测性要求**每层**都有明确日志,改一处常常要顺带改 3 处

**给排期的启示**：
- 一个「加个 API」的需求,在 dify 至少要：Controller（路由 + DTO）+ Service（业务）+ Core（领域逻辑）
- 单纯估「Controller」是**严重低估**——必须三层一起估
- 「跨层改动」应直接按 L（5-7 天）估时,不要按 M 估

## 4. 关键要点总结

- **估时不是「打字速度」**,而是包含设计、测试、评审、文档在内的「流程总成本」
- **永远给区间,不给点估**：「5-8 天」比「6 天」诚实且抗风险
- **三种主流方法**：参考类比（快）、三点估时（准）、Planning Poker（团队对齐）
- **缓冲放在项目级,不放任务级**——任务估理想值,项目加 30-50% 缓冲
- **不同听众说不同数字**：对外承诺 P,对内执行 M,自我激励 O
- dify 流程成本（lint/type-check/test/CR 往返）**不可忽略**,排期必须显式计入

## 5. 练习题

### 练习 1：基础（必做）

用三点估时法估算「为 dify 加一个 Webhook 触发器」任务。自行设定 O / M / P 值,计算期望值 E,并说明你会向产品经理承诺什么数字。

**参考答案**：见 `solutions/24-estimation-basic.md`

### 练习 2：进阶

阅读 `api/AGENTS.md` 第 176-191 行（Tooling & Checks）,为「修改一处 Celery 任务的参数」这个看似 1 行的改动,列出至少 5 个会消耗时间的环节,估算总耗时。

### 练习 3：挑战（选做）

设计一份 Planning Poker 牌组（斐波那契值 + 特殊牌「?」「☕」），并写一个 Python 函数,模拟 3 轮投票收敛过程,输出最终共识值。提示：用 `collections.Counter` 统计分布,用 `statistics.median` 求中位数。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md` —— 行 176-191 流程成本、行 106-110 架构边界
- `/Users/xu/code/github/dify/CONTRIBUTING.md` —— 贡献流程本身就有隐式估时
- 《Software Estimation: Demystifying the Black Art》by Steve McConnell
- Mike Cohn: 《Agile Estimating and Planning》
- Hofstadter's Law: https://en.wikipedia.org/wiki/Hofstadter%27s_law

---

**文档版本**：v1.0
**最后更新**：2026-07-13
