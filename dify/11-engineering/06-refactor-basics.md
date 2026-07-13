# 11.06 重构基础：Red-Green-Refactor

> 以测试保护行为，用最小实现通过测试，再持续改善代码结构。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释 TDD 的 Red → Green → Refactor 循环
- 区分“增加行为”和“保持行为不变的结构调整”
- 使用测试为重构建立安全网
- 理解 Kent Beck 所说的“两顶帽子”工作方式
- 将 dify 的开发检查流程应用到日常重构中

## 📚 前置知识

- Python 函数、类、断言与异常基础
- `pytest` 的基本用法
- 能阅读简单的类型注解
- 了解 Git 小步提交的基本操作

## 🧭 核心概念

### TDD 不是“最后补测试”

TDD（Test-Driven Development，测试驱动开发）把测试放在实现之前。
它的基本节奏是：

```text
Red（测试失败） → Green（测试通过） → Refactor（整理结构）
        ↑                                      ↓
        └────────────── 下一轮需求 ────────────┘
```

这三个阶段分别回答不同问题：

| 阶段 | 核心问题 | 可接受状态 |
|---|---|---|
| Red | 我希望系统新增什么行为？ | 新测试因正确原因失败 |
| Green | 怎样用最小改动实现这个行为？ | 所有测试通过 |
| Refactor | 怎样让代码更清晰且不改变行为？ | 所有测试仍然通过 |

循环的重点不是追求一次完成，而是缩短反馈时间。每次只前进一步，
失败时就能快速定位最近的改动。

### Red：先观察正确的失败

Red 阶段先写一个表达需求的测试，然后运行它。
测试必须失败，而且应当因为功能尚未实现而失败。

如果测试一开始就通过，可能有三种原因：

- 测试没有覆盖目标行为
- 目标行为已经存在
- 断言过弱，不能识别错误结果

如果测试因导入错误、拼写错误或环境问题失败，也不算有效的 Red。
先修正测试基础设施，直到失败信息准确表达缺失的行为。

### Green：只写足够通过的实现

Green 阶段的目标是尽快恢复绿色，而不是立即设计最终架构。
可以先使用直接、显式的实现，避免同时引入多个抽象。

“最小实现”不等于故意写坏代码，它强调：

- 不实现测试之外的未来需求
- 不在缺少证据时设计通用框架
- 不把功能开发和大规模整理混在一起
- 让下一步重构建立在可运行代码之上

### Refactor：保持外部行为不变

重构是**在不改变可观察行为的前提下调整内部结构**。
常见动作包括：

- 重命名变量、函数和类
- 提取函数或合并重复逻辑
- 拆分职责过多的类
- 移动代码到更合适的模块
- 简化条件表达式
- 删除已被测试证明无用的代码

重构阶段不应新增业务规则。如果需要改变输入、输出、异常、持久化副作用
或公开 API，应重新戴上“功能帽”，从新的 Red 开始。

### 什么叫“行为不变”

行为不仅是函数的返回值，还可能包括：

- 抛出的异常类型与关键错误信息
- 数据库写入和事务边界
- 外部 API 调用及其顺序
- 日志中用于排障的上下文
- 任务是否被投递、是否可重试
- 性能或资源上明确承诺的约束

因此，测试安全网应覆盖真正重要的契约，而不是内部实现细节。
若测试断言某个私有函数被调用一次，重构移动函数时就会产生无意义的失败。
优先从公开入口验证结果与副作用。

### 两顶帽子（Two Hats）

“两顶帽子”是一种工作纪律：同一时刻明确自己在做哪一种活动。

**功能帽（Adding Function）**：

- 修改系统行为
- 先写失败测试
- 允许测试从 Red 变为 Green
- 提交信息说明新增或修复了什么

**重构帽（Refactoring）**：

- 不修改系统行为
- 现有测试应始终保持 Green
- 只改善命名、结构、依赖或重复
- 提交信息说明内部结构如何变化

开发者可以频繁换帽，但不要同时戴两顶帽。
例如，提取函数时发现一个边界条件缺陷，应先暂停重构；
为缺陷补一个失败测试，修复后，再继续原来的结构整理。

### 安全重构的工作节奏

推荐使用以下小步流程：

- 运行相关测试，确认起点为 Green
- 只做一个可描述的结构改动
- 再次运行最小相关测试集
- 定期运行更大的测试集
- 检查格式、Lint 与类型检查
- 提交一个单一意图的变更

测试失败时，优先撤回最近的小步，而不是在多个未验证改动上继续修补。
这也是“小步重构”比一次性重写更容易评审的原因。

## 💻 代码示例

### 用一个折扣规则走完整循环

**示例文件**：`examples/refactor_discount.py`  
**示例代码**（行 1-42，独立可运行示例）：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    subtotal: int
    is_vip: bool = False


# Red：先写期望；calculate_total 尚不存在时，测试会失败。
def test_vip_order_gets_ten_percent_discount() -> None:
    order = Order(subtotal=1000, is_vip=True)
    assert calculate_total(order) == 900


# Green：先用最直接的实现让测试通过。
def calculate_total(order: Order) -> int:
    if order.is_vip:
        return order.subtotal - order.subtotal * 10 // 100
    return order.subtotal


# 下一轮 Red：普通订单也必须保持原价。
def test_regular_order_keeps_original_total() -> None:
    order = Order(subtotal=1000)
    assert calculate_total(order) == 1000


# Refactor：提取命名良好的纯函数，外部行为保持不变。
def discount_rate(order: Order) -> int:
    return 10 if order.is_vip else 0


def calculate_total_refactored(order: Order) -> int:
    discount = order.subtotal * discount_rate(order) // 100
    return order.subtotal - discount


def test_refactored_version_preserves_behavior() -> None:
    orders = [Order(1000, True), Order(1000, False)]
    for order in orders:
        assert calculate_total_refactored(order) == calculate_total(order)
```

这个例子刻意保留了重构前后的两个函数，便于比较。在真实项目中，
应当在测试保持绿色后直接用重构后的实现替换原实现，而不是长期维护两份逻辑。

需要注意：最后一个等价性测试只适合过渡期；长期测试仍应直接表达业务规则，
否则旧实现的错误可能被新实现完整复制。

## 🔍 dify 仓库源码解读

### 项目级 TDD 与质量约束

**文件位置**：`/Users/xu/code/github/dify/CLAUDE.md`  
**核心代码**（行 23-39）：

```markdown
## Testing & Quality Practices

- Follow TDD: red → green → refactor.
- Use `pytest` for backend tests with Arrange-Act-Assert structure.
- Enforce strong typing; avoid `Any` and prefer explicit type annotations.
- Write self-documenting code; only add comments that explain intent.

## Language Style

- **Python**: Keep type hints on functions and attributes, and implement relevant special methods (e.g., `__repr__`, `__str__`). Prefer `TypedDict` over `dict` or `Mapping` for type safety and better code documentation.
- **TypeScript**: Use the strict config, rely on ESLint (`pnpm lint:fix` preferred) plus `pnpm type-check`, and avoid `any` types.

## General Practices

- Prefer editing existing files; add new documentation only when requested.
- Inject dependencies through constructors and preserve clean architecture boundaries.
- Handle errors with domain-specific exceptions at the correct layer.
```

**解读**：

- 第 25 行直接规定 `Follow TDD: red → green → refactor.`，把循环提升为项目实践。
- 第 26 行要求测试使用 Arrange-Act-Assert，使行为契约更容易辨认。
- 第 27 行的强类型约束和测试互补：测试验证运行时行为，类型检查发现接口不一致。
- 第 28 行强调自解释代码，这正是 Refactor 阶段改善命名与结构的目标。
- 第 38-39 行要求构造器注入和领域异常，重构不能破坏架构边界或错误契约。

### 迭代时的检查与提交前门禁

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 175-190）：

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

- 第 177-184 行区分迭代中的快速反馈与不同范围的测试。
- 重构小步完成后可先运行 targeted tests，缩短 Red/Green 反馈时间。
- 第 186-190 行定义提交前门禁，避免只通过局部测试就认为重构安全。
- Format 与 Lint 可消除机械差异，让评审者聚焦行为和结构。
- Type check 能发现移动函数、拆分类或修改依赖后留下的接口断裂。

## ✅ 关键要点总结

- Red 必须因预期的缺失行为而失败。
- Green 追求最小可行实现，不提前建设未来抽象。
- Refactor 只改变内部结构，所有可观察行为保持不变。
- 测试是重构安全网，但应测试契约而非私有实现。
- 两顶帽子要求功能开发与结构整理在时间上明确分开。
- 小步修改、频繁测试和单一意图提交能降低重构风险。
- 在 dify 后端中，还应同时通过格式、Lint、类型和单元测试检查。

## 🧪 练习题

### 练习：识别当前戴的帽子（基础）

判断下列操作属于“功能帽”还是“重构帽”，并说明理由：

- 将 `user_id` 重命名为 `account_id`
- 新增“余额不足”异常
- 把 60 行函数拆成三个私有函数
- 改变接口的 HTTP 状态码
- 将重复校验提取为纯函数

要求特别说明：哪些操作看似重构，实际上可能改变外部契约？

### 练习：完成一次 Red-Green-Refactor（进阶）

为示例增加“订单满 2000 再减 100”的规则：

- 先写一个因正确原因失败的测试
- 用最小实现让测试通过
- 消除 VIP 折扣与满减计算中的重复
- 每一步记录测试结果以及当前戴的帽子

### 练习：设计 dify 重构检查单（挑战）

选择 `/Users/xu/code/github/dify/api/services/` 下的一个服务文件，
只阅读不修改，设计一份重构计划：

- 列出必须保持的返回值、异常和副作用
- 找到最小相关测试集
- 写出三个可独立验证的小步
- 给出每一步应运行的命令
- 说明何时需要从重构帽切换成功能帽

## 📖 参考资料

- `/Users/xu/code/github/dify/CLAUDE.md`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- Martin Fowler, *Refactoring: Improving the Design of Existing Code, 2nd Edition*
- Kent Beck, *Test-Driven Development: By Example*
- pytest 官方文档：https://docs.pytest.org/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
