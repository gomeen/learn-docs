# 11.09 DRY / KISS / YAGNI

> 消除重复知识、选择简单方案，并只实现当前真正需要的能力。

## 🎯 学习目标

完成本文档后，你将能够：

- 区分 DRY 所说的“重复知识”和表面相似代码
- 用 KISS 评估设计的认知成本与可读性
- 用 YAGNI 推迟没有证据支持的未来功能
- 识别 DRY 导致的过度抽象，并安全回退
- 理解 dify 工程规则中显式、复用和文件规模约束的设计意图

## 📚 前置知识

- Python 函数、类、模块和类型注解
- 基本单元测试与重构知识
- 已阅读 `07-code-smells.md`
- 已阅读 `08-solid.md`

## 🪶 核心概念

### 三条原则解决不同问题

DRY、KISS、YAGNI 经常一起出现，但关注点不同：

| 原则 | 核心问题 | 常见误解 |
|---|---|---|
| DRY | 同一知识是否有多个来源？ | 任何两段相似代码都必须合并 |
| KISS | 当前方案是否足够直接易懂？ | 只能写短代码或拒绝必要设计 |
| YAGNI | 当前需求是否真的需要它？ | 永远不考虑演进与风险 |

三者共同目标是降低维护成本，而不是追求最少代码行数。
少量清晰重复可能比错误抽象更简单；必要的安全边界也不能以 KISS 为由删除。

### DRY：Don't Repeat Yourself

DRY 的经典含义是：系统中的每一项知识都应有单一、明确、权威的表示。
重点是**知识重复**，而不是字符重复。

以下情况通常值得提取：

- 相同计费规则在三个 endpoint 中分别实现
- 同一状态映射被复制到 controller 和 task
- 同一租户隔离条件在多个查询中容易漏写
- 多处维护同一错误码与 HTTP 映射

以下情况不一定违反 DRY：

- 两个领域恰好都把金额乘以 10%
- 测试为可读性重复少量 Arrange 数据
- 两个模块现在相似，但由不同团队和规则独立变化
- 代码模式相同，业务语义不同

判断问题可以是：“一个业务决定改变时，需要同步修改几个地方？”
若答案大于一个，就应寻找权威所有者。

### DRY 的常见陷阱：过度抽象

开发者看到第二次重复时，容易立即提取一个支持大量参数的通用函数。
随着差异增加，它可能出现：

- 多个布尔开关
- 调用者传入回调来改变每一步行为
- 难以理解的泛型和继承层次
- 修改一个场景时意外影响其他场景

这叫错误抽象（Wrong Abstraction）。常用策略是：

- 先内联回具体调用点
- 恢复两份清晰实现
- 观察真实变化轴
- 只提取稳定且语义相同的最小知识

“允许暂时重复”有时比维护错误共享边界更负责。

### KISS：Keep It Simple, Stupid

KISS 要求在满足约束的方案中选择更简单、直接和可理解的一种。
简单不是“看起来短”，而是让读者容易预测控制流、状态和副作用。

符合 KISS 的设计通常具备：

- 直白命名和显式条件
- 较少的隐藏状态与魔法行为
- 清晰的输入、输出和错误
- 与当前问题规模匹配的抽象层级
- 容易调试、记录日志和编写测试

一行嵌套表达式可能比五行 guard clause 更难理解；
反射式自动注册可能比显式列表更短，却增加发现成本。

KISS 不等于拒绝模块化。面对复杂领域，合理分层反而是最简单的总体方案，
因为每一层只处理自己能解释的概念。

### YAGNI：You Aren't Gonna Need It

YAGNI 要求不要在需求到来之前实现功能。
它反对的是投机性成本，而不是架构思考。

常见 YAGNI 信号包括：

- 没有调用者的可选参数
- “以后可能支持”但没有需求的配置开关
- 单一实现上方的多层插件框架
- 未被使用的缓存、重试或多租户模式
- 为假想平台建立兼容适配层

推迟实现的收益包括：

- 未来需求到来时掌握更多真实信息
- 当前代码更少，测试和维护面更小
- 不会被早期错误假设锁定
- 团队把精力放在可交付价值上

但安全、数据迁移、公开 API 兼容等高代价决策需要提前评估。
YAGNI 的意思是“不提前实现”，不是“不提前识别不可逆风险”。

### 三者发生冲突时怎么选

假设两个 service 出现相似的导出逻辑：

- DRY 提醒你检查是否重复了同一规则
- KISS 要求比较提取前后哪个更容易理解
- YAGNI 阻止你顺便设计十种未来导出格式

推荐决策流程：

- 明确两段代码的业务所有者和变化原因
- 只提取稳定、同义的部分
- 为共享规则建立行为测试
- 保留不同领域的显式入口
- 不加入当前调用者用不到的选项

### 与 SOLID 的关系

这些原则互相制衡：

- DRY 的共享规则可能借助 SRP 找到合适所有者
- KISS 防止为 OCP 创建没有真实变化轴的扩展框架
- YAGNI 防止 DIP 演变成“每个类都必须有接口”
- ISP 帮助公共抽象只暴露调用者真正需要的能力

原则不是得分表。最好的方案是在当前上下文中让变化更局部、行为更明确。

## 💻 代码示例

### DRY 与错误抽象的边界

**示例文件**：`examples/dry_without_overengineering.py`  
**示例代码**（行 1-49，独立可运行示例）：

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Invoice:
    subtotal: Decimal
    country: str


# ❌ 为假想需求设计：mode、cap、rounding 让调用者理解内部策略。
def calculate_adjustment(
    amount: Decimal,
    rate: Decimal,
    mode: str,
    cap: Decimal | None = None,
) -> Decimal:
    value = amount * rate
    if mode == "discount":
        value = -value
    elif mode != "tax":
        raise ValueError("unknown mode")
    if cap is not None:
        value = min(value, cap)
    return value


# ✅ 只共享当前真正相同的知识：百分比计算。
def percentage(amount: Decimal, rate: Decimal) -> Decimal:
    return amount * rate


def tax_for(invoice: Invoice) -> Decimal:
    rates = {"CN": Decimal("0.13"), "US": Decimal("0.07")}
    try:
        rate = rates[invoice.country]
    except KeyError as exc:
        raise ValueError("unsupported country") from exc
    return percentage(invoice.subtotal, rate)


def vip_discount(subtotal: Decimal, is_vip: bool) -> Decimal:
    if not is_vip:
        return Decimal("0")
    return percentage(subtotal, Decimal("0.10"))


invoice = Invoice(Decimal("100.00"), "CN")
assert tax_for(invoice) == Decimal("13.0000")
assert vip_discount(invoice.subtotal, True) == Decimal("10.0000")
```

坏版本把税和折扣强行统一为“调整”，调用者需要理解 `mode`、正负号和上限。
好版本只提取稳定的数学知识 `percentage`，税率选择与 VIP 资格仍由各自函数负责。

如果未来税额与折扣的舍入规则不同，可以再次内联 `percentage`；
不要为了维持 DRY 的表面形式而扭曲领域语义。

## 🔍 dify 仓库源码解读

### KISS：控制文件规模并保持显式

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 95-108）：

```markdown
### General Rules

- Use Pydantic v2 conventions.
- Use `uv` for Python package management in this repo (usually with `--project api`).
- Prefer simple functions over small “utility classes” for lightweight helpers.
- Avoid implementing dunder methods unless it’s clearly needed and matches existing patterns.
- Never start long-running services as part of agent work (`uv run app.py`, `flask run`, etc.); running tests is allowed.
- Keep files below ~800 lines; split when necessary.
- Keep code readable and explicit—avoid clever hacks.

### Architecture & Boundaries

- Mirror the layered architecture: controller → service → core/domain.
- Reuse existing helpers in `core/`, `services/`, and `libs/` before creating new abstractions.
```

**解读**：

- 第 102 行要求文件保持在约 800 行以下，避免单个上下文持续膨胀；“约”表示需要结合内聚性判断。
- 第 103 行直接要求可读、显式并避免 clever hacks，是 KISS 的项目化表达。
- 第 99 行对轻量 helper 优先简单函数，避免无状态 utility class 增加仪式成本。
- 第 100 行只有明确需要时才实现 dunder method，同时体现 KISS 与 YAGNI。
- 第 108 行先复用已有 helper，减少重复知识；但也强调不要先创建新抽象。

### 显式 DTO 规则保持单一知识来源

**文件位置**：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`  
**核心代码**（行 2-13）：

```markdown
This guide describes the expected Flask-RESTX + Pydantic pattern for controller request payloads, query
parameters, response schemas, and Swagger documentation.

## Principles

- Use Pydantic `BaseModel` for request bodies and query parameters.
- Use `fields.base.ResponseModel` for response DTOs.
- Keep runtime validation and Swagger documentation wired to the same Pydantic model.
- Prefer explicit validation and serialization in controller methods over Flask-RESTX marshalling.
- Do not add new Flask-RESTX `fields.*` dictionaries, `Namespace.model(...)` exports, or `@marshal_with(...)` for migrated or new endpoints.
- Do not use `@ns.expect(...)` for GET query parameters. Flask-RESTX documents that as a request body.
```

**解读**：

- 第 9 行让运行时校验和 Swagger 文档连接同一 Pydantic model，减少两份 schema 漂移，体现 DRY。
- 第 10 行偏好显式校验和序列化，体现 KISS 对可预测控制流的要求。
- 第 11 行不再新增旧式 schema 字典，防止同一契约出现多个权威来源。
- 第 12 行禁止看似省事但语义错误的 GET `expect` 用法；简单仍必须正确。
- 这不是追求最少代码，而是减少协议知识的重复表示。

## ✅ 关键要点总结

- DRY 消除的是重复知识，而不是所有相似文本。
- 同一业务决定需要多点同步修改，是重要的 DRY 风险信号。
- 错误抽象出现时可以先恢复重复，再寻找真实变化轴。
- KISS 关注认知、调试和预测成本，不等于最短代码。
- YAGNI 推迟没有当前需求的实现，但仍需评估不可逆风险。
- 三条原则应互相制衡：复用要语义一致，简单要满足约束，扩展要有证据。
- dify 倾向显式代码、简单函数、合理文件规模和已有 helper 复用。

## 🧪 练习题

### 练习：判断是否违反 DRY（基础）

分析以下场景，判断是否应提取共享代码，并说明变化原因：

- 两个 endpoint 使用同一邮箱校验规则
- 账单与 UI 都把时间格式化为 `YYYY-MM-DD`
- 两个领域对象恰好都有 `status == "active"`
- 三个查询都必须包含相同租户隔离条件

不要只依据代码长得是否相同。

### 练习：删除未来参数（进阶）

重构示例中的 `calculate_adjustment`：

- 列出当前没有调用证据的参数和分支
- 用税与折扣的行为测试保护结果
- 替换为语义明确的函数
- 比较重构前后的调用者认知成本
- 说明哪些重复被保留，以及为什么

### 练习：评审 dify helper（挑战）

选择 `/Users/xu/code/github/dify/api/services/` 中的一组相邻功能，调查：

- 是否复用了 `core/`、`services/` 或 `libs/` 的已有 helper
- 是否存在同一业务知识的多份表达
- 公共 helper 是否有未使用的未来参数
- 抽象是否比直接实现更难理解
- 给出“保持、提取、内联或删除”的决策及证据

## 📖 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
- Andrew Hunt & David Thomas, *The Pragmatic Programmer*
- John Ousterhout, *A Philosophy of Software Design*
- Martin Fowler, Refactoring：https://refactoring.com/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
