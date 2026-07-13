# 12 Reviewer 检查清单：功能 / 设计 / 风格

> Reviewer 应按“功能正确 → 设计合理 → 风格一致”的顺序审查，把注意力优先放在对用户和系统影响最大的风险上。

## 🎯 学习目标

完成本文档后，你将能够：

- 从功能、设计、风格三个层面系统检查一个 Pull Request
- 识别正常路径之外的边界条件、异常处理和测试缺口
- 判断改动是否符合分层架构、命名、抽象层级和扩展性要求
- 区分应由 Ruff 等工具处理的机械风格问题和需要人工判断的可读性问题
- 使用 dify `api/AGENTS.md` 中的架构、日志、异常和检查命令审查后端改动

## 📚 前置知识

- Git diff 与 Pull Request Review 基础
- Python 函数、异常、类型标注和单元测试基础
- 了解 Controller、Service、Core/Domain 的基本职责
- 建议先学习：[Code Review 的价值与流程](./11-code-review.md)

## 🧭 核心概念

### 为什么要使用 Checklist

Review 很容易受注意力和经验影响：Reviewer 可能在命名上留下十条评论，却遗漏一个越权访问问题。Checklist 的价值在于建立稳定的最低审查标准。

它不替代思考，而是帮助 Reviewer：

- 先检查高影响问题，再看局部细节
- 在不同 PR 间保持一致标准
- 避免忘记异常、测试、日志和兼容性
- 将项目约定转化为可执行问题

推荐顺序是：先问**功能是否做对**，再问**设计是否放在正确位置**，最后检查**风格是否便于他人阅读和维护**。

如果功能目标本身错误，就不必先花大量时间修改变量名。

## 🧪 功能层面

### 是否解决目标问题

Reviewer 首先阅读关联 Issue、验收条件和 PR 描述，然后检查 diff。需要回答：

- 当前实现与 Issue 描述的是同一个问题吗
- 用户可观察行为是否符合预期
- 是否只修复表象，根因仍然存在
- 是否引入与目标无关的行为变化
- 是否保留必要的向后兼容性

可以尝试用一句话复述：“给定什么输入，系统现在应产生什么结果。”如果无法复述，说明 PR 上下文不完整，应先向作者提问。

### 边界条件

正常路径通过不代表功能正确。常见边界包括：

- 空值、空列表、空字符串和仅含空白字符
- 最小值、最大值、负数和超长输入
- 重复请求、并发更新和乱序事件
- 资源不存在、已删除或状态已经变化
- 不同 tenant、权限角色和资源所有者
- 分页最后一页、无下一页和游标过期
- 旧数据、缺失字段和版本兼容

Reviewer 可从每一个条件分支反向提问：“另一条分支有测试吗？”

### 异常处理

检查异常时，不只看有没有 `try/except`，还要看错误是否在正确层级处理：

- 底层是否抛出具有业务语义的 domain-specific exception
- Controller 是否将领域错误转换为正确 HTTP 响应
- 是否误吞异常后继续执行，造成部分成功状态
- 日志是否包含 tenant、app、workflow 等定位标识
- 可重试错误与终止错误是否使用合理日志级别
- 返回信息是否泄露密钥、SQL 或内部堆栈

宽泛的 `except Exception`、用 `None` 表示多种失败、以及使用 `print` 记录错误，通常都值得重点检查。

### 测试覆盖

不要只看覆盖率数字，要看测试是否证明需求。至少确认：

- 正常路径有断言，而不是只执行不报错
- Issue 中的失败场景有回归测试
- 关键边界和异常路径被覆盖
- Mock 没有把真正需要验证的逻辑全部替代
- 测试名称能表达场景和预期
- 测试在修改前失败、修改后通过

如果 PR 修复一个缺陷但没有测试，Reviewer 应询问如何防止同一问题再次出现。

## 🏗️ 设计层面

### 是否符合架构

架构审查关注职责是否放在正确位置。以 dify 后端为例：

- Controller 负责输入解析、调用 Service 和序列化响应
- Service 协调仓储、Provider 与后台任务
- Core/Domain 承担核心规则和领域行为

如果 Controller 包含复杂业务分支，或者通用 Core 逻辑反向依赖 HTTP 层，就破坏了边界。还要优先复用已有 helper，避免为一次调用建立重复抽象。

### 命名是否表达意图

名称应说明业务语义，而不是只暴露实现细节。检查：

- 函数名是否表达动作与结果
- 布尔变量是否可以自然读成判断句
- 类名是否与责任匹配
- 同一领域概念是否在不同文件使用同一术语
- 缩写是否为团队熟知，而非作者个人约定

例如，`handle()` 往往过于模糊；`validate_workflow_access()` 更容易说明责任。

### 抽象层级是否一致

一个函数中不应混杂多个距离很远的抽象层级。例如：

- 一边描述业务流程，一边拼接底层 SQL 字符串
- 一边协调任务，一边解析 HTTP 请求字段
- 为两行代码创建无状态“工具类”
- 为未来可能出现的需求预先设计复杂插件接口

好的抽象会隐藏稳定的实现细节，同时暴露清楚的行为契约。抽象不是越多越好；Reviewer 要同时警惕重复逻辑和过度设计。

### 扩展性与可维护性

扩展性不是“预测所有未来”，而是避免当前设计锁死明显变化方向。可以检查：

- 新增一种类型时是否必须修改大量无关分支
- 外部 I/O、数据库写入等副作用是否明确
- 是否依赖全局可变状态或隐藏配置
- 接口是否有稳定且清楚的输入输出
- 失败后是否可重试，后台任务是否幂等
- 是否引入不必要的依赖或循环依赖

对于尚无实际用例的扩展点，不应为了“以后可能需要”增加复杂度。

### PEP 8 与项目工具

PEP 8 提供 Python 通用风格基线，但仓库配置和自动化工具是更直接的执行标准。在 dify 后端，Ruff 负责格式化与 Lint，行长限制为 120 字符。

Reviewer 不应手工逐个指出 Formatter 能自动修复的空格问题。更有效的做法是要求作者运行项目命令，并把人工注意力留给工具难以判断的内容。

### 命名约定

Python 常用约定包括：

- 变量和函数使用 `snake_case`
- 类使用 `PascalCase`
- 常量使用 `UPPER_CASE`
- 公共 API 添加准确类型标注
- 已知键集合的数据优先使用 `TypedDict`

命名 Review 应基于仓库规则与领域语言，不应变成个人审美争论。

### 注释与文档字符串

注释应解释“为什么”，而不是复述“做了什么”。Review 时检查：

- 非显然约束和取舍是否有说明
- 注释是否紧邻它解释的代码
- 代码改变后注释是否仍然准确
- 函数 docstring 是否描述副作用和领域异常
- 是否出现追加式“最近修复”日志，而没有融入原有说明

错误的注释比没有注释更危险，因为它会给维护者错误信心。

### 可读性

人工风格审查还应覆盖：

- 控制流是否清晰、确定
- 是否有过深嵌套或过长函数
- 是否使用聪明但难懂的技巧
- 重复表达是否可用现有 helper 简化
- 类型是否足以避免“mystery value”

可读性意见应指出维护成本或误用风险，而不是只说“我不喜欢这种写法”。

## 💻 代码示例

### 一份完整的 Reviewer Checklist

这是独立示例。实际 Review 时，可把它贴入个人笔记或 PR 评论，逐项确认；不适用的条目应写明原因，而不是机械勾选。

**示例文件**：`examples/reviewer-checklist.md`  
**示例代码**（行 1-35）：

```markdown
## 功能

- [ ] 改动与关联 Issue、验收条件一致
- [ ] 正常路径产生预期的用户可观察结果
- [ ] 空值、极值、重复请求和并发场景已考虑
- [ ] 权限、tenant 隔离和资源所有权正确
- [ ] 失败路径抛出或返回正确错误
- [ ] 日志包含定位问题所需上下文，且不泄露敏感数据
- [ ] 回归测试在修复前失败、修复后通过
- [ ] 正常、边界和异常路径均有有效断言

## 设计

- [ ] Controller、Service、Core/Domain 职责边界清晰
- [ ] 优先复用已有 helper，而非重复创建抽象
- [ ] 函数、变量和类型名称表达业务意图
- [ ] 单个函数中的抽象层级一致
- [ ] 外部 I/O、数据库写入和任务分发等副作用明确
- [ ] 没有不必要的全局状态、循环依赖或过度设计
- [ ] 明显的扩展方向不会要求修改大量无关代码

## 风格

- [ ] 符合项目 Formatter、Linter 与 PEP 8 约定
- [ ] 变量/函数、类、常量使用正确命名风格
- [ ] 公共 API 与类属性具有准确类型标注
- [ ] 注释解释原因、约束和取舍，而非复述代码
- [ ] 相关 docstring 与当前行为保持一致
- [ ] 控制流清晰，没有过深嵌套或聪明但晦涩的技巧

## 提交前证据

- [ ] Lint 通过
- [ ] Type Check 通过
- [ ] 单元测试通过
- [ ] UI 改动附有 Before/After 截图或录屏
- [ ] 文档与迁移说明已同步
```

**说明**：

- 前 8 项优先验证行为正确性和隔离安全
- 设计项检查职责、复用、抽象和副作用，而不是追求模式数量
- 风格项同时覆盖自动化规则与人工可读性判断
- 最后一组要求作者提供可复查证据，避免“应该没问题”式结论

## 🔍 dify 仓库源码解读

### 架构、日志与异常检查标准

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 106-118）：

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

- 第 108 行给出后端分层方向，Reviewer 可据此判断业务逻辑是否误放在 Controller
- 第 109 行要求先复用已有实现，避免同一领域出现多个相似 helper
- 第 110 行把可观测性纳入设计质量：控制流、日志和错误都应可行动
- 第 114-115 行禁止 `print`，并给出模块级 logger 的标准写法
- 第 116 行强调多租户和工作流系统中的关键标识，缺失会显著增加排障成本
- 第 117 行明确领域异常与 HTTP 转换的边界
- 第 118 行用日志级别区分可重试事件和最终失败

### Tooling & Checks 提交清单

用户指定关注的提交前 Checklist 位于第 186-191 行；为保留上下文，下面同时复制该段所属的完整 `Tooling & Checks` 小节。

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 176-191，其中提交前清单为行 186-191）：

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

- 第 178-185 行提供开发迭代期间由快到全的检查方式，可先跑目标测试再扩大范围
- 第 180-181 行表明格式化与 Lint 是不同动作，Lint 还包含自动修复
- 第 182 行要求类型检查，能提前发现仅靠运行测试未触发的接口不一致
- 第 183-185 行区分单元测试、完整测试和目标测试，便于按阶段获得反馈
- 第 186-191 行把 `make lint`、`make type-check`、`make test` 定义为打开或提交 PR 前的最低检查集合
- Reviewer 可要求 PR 提供这三项通过的证据，而不是亲自发现基础工具错误

### 功能问题评论

> `blocking:` 当 `tenant_id` 不匹配时，查询仍然只按资源 ID 命中，可能读取其他租户的数据。请在查询条件中加入 tenant scope，并补充跨租户访问被拒绝的测试。

它明确说明触发条件、影响、修复方向和测试要求。

### 设计问题评论

> `suggestion:` 这段输入解析位于 Service，但相邻 Controller 已使用 Pydantic DTO 完成同类校验。是否可以将解析移回 Controller，让 Service 只接收已验证的领域输入？

它引用现有模式并解释边界，而不是简单要求“重构”。

### 风格问题评论

> `nit:` `data` 同时表示请求 DTO 和数据库结果，后续分支较难区分。可以分别命名为 `request_payload` 与 `workflow_record`。非阻塞。

它说明名称造成的阅读问题，并明确反馈级别。

## ⚖️ 常见误区

### 只审风格，不审行为

大量拼写和空格评论会制造“Review 很细”的错觉，却可能遗漏权限、事务和异常问题。应先验证功能和设计。

### 把 Checklist 当成免责勾选

勾选“测试通过”不等于测试有效。Reviewer 仍需抽查测试输入、断言和 Mock 边界。

### 要求所有代码都为未来扩展

没有真实用例的抽象会增加理解和维护成本。扩展性审查应围绕已知变化方向和当前边界，而非无限泛化。

### 将个人偏好冒充项目规则

如果存在 Formatter、Linter 或 `AGENTS.md`，应引用明确规则。纯偏好应标记为 `nit` 或 `suggestion`，不要阻塞合并。

## ✅ 关键要点总结

- Review 顺序应是功能、设计、风格，先解决影响最大的风险
- 功能检查覆盖目标、边界、异常和测试，而非只看正常路径
- 设计检查关注架构边界、命名、抽象层级、复用和可维护扩展
- 风格检查以项目规则和 PEP 8 为基础，并关注工具无法判断的可读性
- dify 后端强调 controller → service → core/domain、领域异常和结构化日志
- 提 PR 前至少运行 `make lint`、`make type-check` 和 `make test`

## 📝 练习题

### 练习：基础（必做）

使用本文 Checklist 审查一个包含 Controller、Service 和测试的 PR。每个层面至少写出一条“通过证据”或“问题评论”。

### 练习：进阶

某 Service 捕获 `Exception` 后执行 `print(error)` 并返回 `None`。请分别从功能、设计、风格三个角度说明问题，并写出一条合并前必须处理的评论。

### 练习：挑战（选做）

为 dify 的一个后端模块定制 12 项 Checklist：保留通用功能/设计/风格结构，同时加入该模块特有的 tenant、幂等、外部 I/O 或任务队列检查项。

## 🔗 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/services/errors/__init__.py`
- `/Users/xu/code/github/dify/api/core/errors/error.py`
- Python PEP 8：https://peps.python.org/pep-0008/
- Ruff Documentation：https://docs.astral.sh/ruff/
- Google Engineering Practices：What to look for in a code review

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
