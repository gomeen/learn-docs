# 26 知识分享：内部 Tech Talk

> 知识不分享就会衰减——你能讲清楚,才算真的懂；Tech Talk 不是表演,是**团队学习的基础设施**。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分三种 Tech Talk 形式（Lightning / Deep Dive / Workshop）的适用场景
- 从 PR、bug、RFC 中挖掘高质量的分享选题
- 用「背景→问题→方案→代码→教训」五段式结构组织演讲
- 准备一份可执行的大纲模板
- 利用 dify 的 CONTRIBUTING.md 作为新人引导演讲素材

## 📚 前置知识

- 至少有 1 次 PR 经验（dify 或其他项目）
- 基本的演讲表达经验（团队 standup 也算）
- 阅读过 `12-issue-management.md`,理解 issue 生命周期

## 1. 核心概念

### 1.1 为什么需要内部 Tech Talk？

工程团队常见的知识困境：

- **信息孤岛**：A 组用 Celery,B 组用 RQ,谁也不知道为什么
- **重复踩坑**：上周小王踩的坑,这周小李又踩一次
- **决策无记录**：「为什么不用 MongoDB?」——「当时 XX 决定的」—— XX 已离职
- **新人 onboarding 痛苦**：1 个月才搞懂项目结构

Tech Talk 是**最低成本**的解决方案：
- 1 次 30 分钟分享 = 1 个工程师 1 天的踩坑 = 全团队复用知识
- 演讲过程**强迫整理思路**——讲不清楚往往是自己没想清楚

### 1.2 三种 Tech Talk 形式

| 形式           | 时长       | 选题类型                              | 频次推荐       |
| -------------- | ---------- | ------------------------------------- | -------------- |
| Lightning Talk | 5-10 分钟  | 一个踩坑、一个技巧、一个新工具         | 每周 1-2 次    |
| Deep Dive      | 30-60 分钟 | 一项设计决策、一次性能优化、一次重构   | 每月 1-2 次    |
| Workshop       | 2-4 小时   | 新人培训、新流程演练、code kata       | 每季度 1 次    |

**怎么选**：
- 你今天遇到一个 bug 修了 1 小时 → Lightning
- 你做了一项大设计决策（数据库选型、架构升级） → Deep Dive
- 你要让 5 个新人 2 周上手 → Workshop

### 1.3 选题挖掘：从「日常」到「素材」

**最容易被忽略的好选题**：

1. **刚合的 PR**：尤其是改架构、改依赖、改范式的 PR
2. **生产事故复盘**：Postmortem 是最有价值的素材
3. **Code Review 反复出现的争论**：如果一个 PR 来回 5 轮,主题值得分享
4. **被拒的需求**：为什么不做？分享给团队避免重复提出
5. **新工具/库的评估报告**：选型过程本身就是知识
6. **新人入职 1 个月的感受**：新鲜视角往往戳中老员工的盲点

**质量自检三问**：
- 「这个分享能让团队**少踩坑**吗？」
- 「半年后还有人会想看回放吗？」
- 「听众听完能**做出更好的决策**吗？」

三个都答「是」,就是好选题。

### 1.4 五段式结构

不论哪种形式,**结构都建议遵循五段式**：

```
┌─────────────────────────────────────────┐
│ 1. 背景（5%）    —— 我们在做什么项目   │
│ 2. 问题（15%）   —— 遇到了什么难题     │
│ 3. 方案（30%）   —— 我们怎么解决的     │
│ 4. 代码（35%）   —— 关键代码长什么样   │
│ 5. 教训（15%）   —— 还能怎么改进       │
└─────────────────────────────────────────┘
```

**关键原则**：
- **背景** 1-2 句话,**别花 10 分钟介绍项目**
- **问题** 要具体（数字、复现步骤、影响范围）
- **方案** 讲**权衡**,不是只讲「最终选了什么」
- **代码** 是**核心**——讲不清楚代码,等于没讲
- **教训** 是**给听众的礼物**——下次他们能怎么做

### 1.5 演讲的「反模式」

| 反模式                       | 为什么差                  | 正确做法                  |
| ---------------------------- | ------------------------- | ------------------------- |
| 念 PPT                       | 听不清、不走心            | 多用代码、demo、图        |
| 只讲 happy path              | 听众学不到教训            | **必讲**踩坑和回滚        |
| 过度铺垫背景                 | 浪费 5 分钟               | 1 句话带过                |
| 抽象无例子                   | 听完就忘                  | 至少 2 个具体例子         |
| 「我」如何如何               | 缺乏共情                  | 改为「我们」团队如何      |
| 时间严重超                   | 不尊重听众                | 提前练 2 次,卡 80% 时间   |

## 2. 代码示例

### 2.1 一份 Tech Talk 大纲模板

下面是一个**可执行**的 Tech Talk 准备脚本,展示如何把零散笔记整理成可演讲的大纲：

```python
# 文件：tech_talk_outline.py
"""
Tech Talk 大纲模板：五段式 + 时间盒。
每个 Tech Talk 都能用这个模板检查自己的内容是否完整。
"""
from dataclasses import dataclass, field


@dataclass
class Section:
    title:     str
    duration:  int   # 分钟
    bullets:   list[str] = field(default_factory=list)
    must_have: bool  = True  # 必讲 / 选讲


@dataclass
class TechTalkOutline:
    title:        str
    audience:     str              # "backend team" / "new hires" / "all engineers"
    total_min:    int              # 总时长
    sections:     list[Section]    = field(default_factory=list)
    pr_links:     list[str]        = field(default_factory=list)
    references:   list[str]        = field(default_factory=list)

    def validate(self) -> list[str]:
        """检查大纲完整性,返回问题列表。"""
        issues = []
        total = sum(s.duration for s in self.sections)
        if abs(total - self.total_min) > 2:
            issues.append(f"时间合计 {total}min 与总时长 {self.total_min}min 偏差 > 2min")
        if not any(s.title == "代码" for s in self.sections):
            issues.append("缺少「代码」段落——Tech Talk 必须有代码")
        if not any("教训" in s.title or "改进" in s.title for s in self.sections):
            issues.append("缺少「教训」段落——只讲成功不讲失败价值低")
        return issues


# 示例：30 分钟 Deep Dive
talk = TechTalkOutline(
    title="dify 中 Celery 任务幂等性实战：我们如何避免重复扣费",
    audience="backend team",
    total_min=30,
    sections=[
        Section("背景", 2, [
            "dify 的异步任务用 Celery + Redis",
            "2026-06 出现 1 次重复扣费 P1 事故",
        ]),
        Section("问题", 5, [
            "Celery 默认 at-least-once,失败重试 = 重复执行",
            "金融相关操作必须 exactly-once",
            "事故复盘: 涉及 12 个用户,损失约 $230",
        ]),
        Section("方案", 8, [
            "方案 A（弃）: 数据库唯一约束 — 性能太差",
            "方案 B（采纳）: 业务幂等键 + 状态机",
            "方案 C（备用）: Redis 分布式锁 — 用于高并发",
        ]),
        Section("代码", 10, [
            "api/tasks/billing.py 中幂等键的生成",
            "状态机迁移: pending → processing → done",
            "失败回滚的代码片段（见 PR #38500）",
        ], must_have=True),
        Section("教训", 5, [
            "所有 Celery 任务必须设计幂等性",
            "金融任务必须先演练失败注入测试",
            "Postmortem 文档已归档到 wiki",
        ]),
    ],
    pr_links=["https://github.com/langgenius/dify/pull/38500"],
    references=["Celery 官方文档 - Idempotency", "Stripe idempotency-key 设计"],
)

# 检查大纲
problems = talk.validate()
print(f"Talk: {talk.title}")
print(f"听众: {talk.audience} | 时长: {talk.total_min} 分钟")
print(f"问题数: {len(problems)}")
for p in problems:
    print(f"  - {p}")
# 期望输出: 问题数: 0（大纲完整）
```

**说明**：
- 第 27-37 行：`validate()` 强制「必讲代码」「必讲教训」,从源头杜绝反模式
- 第 41-50 行：示例 talk 完整覆盖五段式,时长分配合理（背景 7%,问题 17%,方案 27%,代码 33%,教训 17%）
- 第 66-68 行：`pr_links` 强制关联真实素材,避免空谈

### 2.2 常见错误：「我讲我的,听不听得懂是你的事」

```python
# ❌ 错误：抽象无例子,听众听完就忘
def bad_talk():
    sections = [
        "讲一下幂等性",
        "讲一下状态机",
        "讲一下 Celery",
    ]
    # 问题: 没有具体代码、没有具体事故、没有数字

# ✅ 正确：每个抽象概念必带具体例子
def good_talk():
    sections = [
        ("讲幂等性",
         ["12 个用户被扣 2 次款", "1 个真实 PR 的 diff 截图",
          "1 段 10 行的幂等键生成代码"]),
        ("讲状态机",
         ["1 张状态迁移图（mermaid）", "3 个测试用例覆盖迁移",
          "1 个迁移失败的真实报错日志"]),
        ("讲 Celery 重试",
         ["Celery max_retries=3 配 acks_late 的实际行为",
          "1 个失败注入测试脚本"]),
    ]
    # 原则: 每个抽象概念 → 至少 1 个数字 + 1 段代码 + 1 张图
```

## 3. dify 仓库源码解读

### 3.1 CONTRIBUTING.md 是「贡献者入门演讲」的最佳素材

**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`
**核心代码**（行 1-50）：

```markdown
# CONTRIBUTING

So you're looking to contribute to Dify - that's awesome, we can't wait to see what you do. As a startup with limited headcount and funding, we have grand ambitions to design the most intuitive workflow for building and managing LLM applications. Any help from the community counts, truly.

We need to be nimble and ship fast given where we are, but we also want to make sure that contributors like you get as smooth an experience at contributing as possible. We've assembled this contribution guide for that purpose, aiming at getting you familiarized with the codebase & how we work with contributors, so you could quickly jump in.

...

Looking for something to tackle? Browse our [good first issues](...).

Got a cool new model runtime or tool to add? Open a PR in our [plugin repo](...).

Need to update an existing model runtime, tool, or squash some bugs? Head over to our [official plugin repo](...).

Don't forget to link an existing issue or open a new issue in the PR's description.
```

**解读**：
- 第 1-2 行：开门见山,语气友好——这是 Tech Talk 开场的范本
- 第 3-5 行：「navigate the codebase」「work with contributors」点明双向价值
- 第 7-10 行：「good first issues」「plugin repo」「official plugins」是**新人的三条入口路径**

**给 Tech Talk 的启示**：
- 这篇文档本身就是「dify 贡献者入门」演讲的**完美大纲**——五段式完整
- 直接拿它做 30 分钟 Lightning Talk：「如何成为 dify 贡献者」
- **示范**了「文档驱动」的力量：写好文档 = 做了 100 场新人培训

### 3.2 PR 模板定义了「团队协作语言」

**文件位置**：`/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
**核心代码**（行 1-15）：

```markdown
> [!IMPORTANT]
>
> 1. Make sure you have read our [contribution guidelines](https://github.com/langgenius/dify/blob/main/CONTRIBUTING.md)
> 1. Ensure there is an associated issue and you have been assigned to it
> 1. Use the correct syntax to link this PR: `Fixes #<issue number>`.

## Summary

<!-- Please include a summary of the change and which issue is fixed. ... -->
```

**解读**：
- 第 1-5 行：PR 必须**关联 issue**——这是「决策记录」的形式化
- 第 7-9 行：Summary 模板强制**说明动机和上下文**,防止「改了一行但没人知道为什么」

**给 Tech Talk 的启示**：
- PR 模板是「**为什么我们这么做**」的规范沉淀,每次改动都是「知识分享」
- Tech Talk 可以围绕一个**真实 PR** 展开,讲「为什么这么设计」「权衡了什么」
- 推荐选题：「PR #38500 的设计权衡：我们如何在 5 个备选方案中选 Celery」

## 4. 关键要点总结

- **Tech Talk 是团队学习的基础设施**——讲清楚才算真的懂
- **三种形式**：Lightning（5-10 分钟） / Deep Dive（30-60 分钟） / Workshop（2-4 小时）
- **好选题来自日常**：刚合的 PR、Postmortem、Code Review 争论、被拒的需求
- **五段式结构**：背景→问题→方案→代码→教训（代码 + 教训缺一不可）
- **反模式**：念 PPT、只讲 happy path、过度铺垫、抽象无例子、时间严重超
- **dify 的 CONTRIBUTING.md 本身就是一篇高质量 Tech Talk 大纲**——直接拿来用
- **PR 模板是「决策记录」的形式化**——每个 PR 都是潜在的分享素材

## 5. 练习题

### 练习 2：基础（必做）

为自己准备一个 10 分钟的 Lightning Talk,主题是「我最近一次 PR 学到的 3 件事」。用练习 2.1 的 `TechTalkOutline` 类,填好 sections,并运行 `validate()` 确认无误。

**参考答案**：见 `solutions/26-tech-talk-basic.md`

### 练习 2：进阶

阅读 `CONTRIBUTING.md` 第 1-30 行,把它**改写成**一份 15 分钟 Lightning Talk 大纲,目标听众是「第一次给开源项目提 PR 的工程师」。

### 练习 3：挑战（选做）

**组织一次真实的 Tech Talk**：
- 在团队周会上,讲 10 分钟
- 主题：dify 中某个让你印象深刻的 PR 或 bug（你贡献过的、或你 review 过的）
- 提交：录音 / 录屏 + 配套 slides（可 1 页）

## 6. 参考资料

- `/Users/xu/code/github/dify/CONTRIBUTING.md` —— 贡献者入门演讲素材
- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md` —— PR 模板作为知识沉淀
- `/Users/xu/code/github/dify/api/AGENTS.md` —— 内部规范本身就是 Tech Talk 素材
- 《Presentation Zen》by Garr Reynolds —— 演讲设计
- GitHub Octocat Talk 系列: https://github.com/octocat
- Lightening Talk 范例: https://2018.pycon-au.org/lightning-talks

---

**文档版本**：v1.0
**最后更新**：2026-07-13
