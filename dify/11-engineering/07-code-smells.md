# 11.07 识别代码坏味道

> 坏味道不是错误判决，而是提醒开发者进一步调查设计问题的信号。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释六种经典代码坏味道及其常见成因
- 区分“代码很长”和“职责混乱”等真正的设计问题
- 为坏味道选择小步、可验证的重构手法
- 避免把个人风格偏好误判为坏味道
- 在 dify 的 controller、service、core 和 task 场景中发现风险信号

## 📚 前置知识

- Python 函数、类、模块与类型注解
- 基本的单元测试知识
- 已阅读 `06-refactor-basics.md`
- 了解单一职责和模块边界的基本含义

## 👃 核心概念

### 坏味道是线索，不是定罪

Code Smell（代码坏味道）描述代码中“可能存在更深层设计问题”的表面特征。
它不等同于 Bug，也没有脱离上下文的统一阈值。

例如，20 行解析协议的函数可能职责单一且非常清楚；
另一个只有 8 行的函数却可能同时查数据库、发消息和修改全局状态。
判断时应继续追问：

- 这段代码为什么频繁变化？
- 一次需求是否总要修改多个不相干位置？
- 能否仅通过函数名理解意图？
- 测试是否必须构造大量无关依赖？
- 重复的是语法，还是同一条业务知识？

坏味道的处理顺序通常是：观察信号、收集证据、补测试、实施小步重构。
不要看到 `if` 重复就立刻创建抽象基类。

### Long Method：过长方法

Long Method 的核心问题不是物理行数，而是一个方法包含太多抽象层级或职责。
典型信号包括：

- 函数中出现多个可独立命名的阶段
- 注释用于标出“校验”“保存”“通知”等代码区块
- 局部变量很多，必须上下滚动才能理解
- 条件与循环深层嵌套
- 修改一个阶段时容易影响另一个阶段

常用重构手法有 Extract Function、Guard Clause、Replace Temp with Query，
以及将独立职责移动到专门对象。

在 dify 中，一个 controller 如果同时解析请求、执行工作流业务、写数据库并组装响应，
即使代码不长，也已经具有 Long Method 和职责泄漏的味道。

### Large Class：过大的类

Large Class 往往拥有过多字段、方法和变化原因。
判断证据包括：

- 方法只使用类中一小部分字段，形成多个字段簇
- 类名越来越抽象，如 `Manager`、`Processor`、`Helper`
- 不相关需求总是修改同一个类
- 单元测试必须初始化大量与目标无关的依赖

可按业务能力使用 Extract Class，或将协调与计算拆开。
在 dify 的 service 中，若一个服务同时管理账号、计费、模型调用和通知，
应检查它是否只是把多个子系统堆在同一个类中。

### Long Parameter List：过长参数列表

参数太多会增加调用者负担，也容易发生位置传参错误。
更重要的信号是某组参数总是一起出现，例如：

```text
tenant_id, app_id, workflow_id, user_id
```

可以考虑引入有明确语义的 Parameter Object、从已有对象取得数据，
或把操作移动到拥有这些数据的对象上。

但不要为了减少数量把所有值塞进无类型的 `dict`，那只是隐藏了接口。
在 dify 中，跨 controller → service → core 传递 `tenant_id` 是租户隔离契约；
重构参数时必须保留这种端到端可见性。

### Duplicate Code：重复代码

Duplicate Code 不只是字符相同，更重要的是**同一知识在多个位置表达**。
如果业务规则变化时必须同步修改多个副本，就存在分叉风险。

适合的处理方式包括：

- 同一函数内重复：Extract Function
- 同一模块中重复：提取模块级函数
- 兄弟类重复：提取组合对象，谨慎使用继承
- 不同层重复：先确认是否真是同一规则，再选择规则的所有者

两个代码块现在相似，但未来由不同业务原因变化，则不应强行合并。
错误抽象通常比少量重复更昂贵。

### Dead Code：无效代码

Dead Code 包括永远不会执行的分支、无人调用的函数、过期参数、
被注释掉的旧实现，以及已不再使用的兼容层。

它的问题是制造错误线索：读者会花时间理解一个实际上没有作用的路径。
版本控制已经保存历史，确认无引用且测试覆盖契约后，应直接删除，
不要把旧实现长期留在注释里。

在 dify 中可结合静态搜索、类型检查、覆盖率和入口注册方式判断；
尤其要注意 Celery task、事件订阅和框架反射调用，不能只依赖文本引用数量。

### Speculative Generality：臆想式通用性

Speculative Generality 指为了“以后可能需要”而提前加入抽象：

- 只有一个实现的复杂插件框架
- 从未使用的配置开关和扩展点
- 只被一个调用者使用的多层接口
- 没有真实变化轴却设计大量泛型参数
- 为假想场景保留的参数和钩子

处理方式通常是 Collapse Hierarchy、Inline Class、Remove Parameter。
在 dify 中，新增 provider 或 storage 抽象可能确有真实扩展需求；
但一个局部字符串格式化操作通常不需要工厂、策略和注册器三层结构。

### 用变化原因判断优先级

发现多个坏味道时，可按以下顺序处理：

- 先确认测试是否保护关键行为
- 优先处理阻碍当前需求的味道
- 优先降低高频修改区域的认知负担
- 一次只做一种结构调整
- 每一步验证行为不变

坏味道不是要求“把所有代码变得抽象”，而是帮助代码更贴近业务边界。

## 💻 代码示例

### 从混合职责函数到可组合步骤

**示例文件**：`examples/order_smells.py`  
**示例代码**（行 1-47，独立可运行示例）：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    email: str
    subtotal: int
    is_vip: bool


# ❌ Long Method、Duplicate Code、Long Parameter List 混在一起。
def checkout_bad(email: str, subtotal: int, is_vip: bool) -> str:
    if not email or "@" not in email:
        raise ValueError("invalid email")
    if subtotal <= 0:
        raise ValueError("invalid subtotal")
    total = subtotal * (90 if is_vip else 100) // 100
    shipping = 0 if total >= 1000 else 50
    return f"to={email}; total={total + shipping}"


# ✅ Parameter Object 让相关数据形成明确概念。
def validate(order: Order) -> None:
    if not order.email or "@" not in order.email:
        raise ValueError("invalid email")
    if order.subtotal <= 0:
        raise ValueError("invalid subtotal")


def payable_amount(order: Order) -> int:
    discount_rate = 10 if order.is_vip else 0
    return order.subtotal * (100 - discount_rate) // 100


def shipping_fee(amount: int) -> int:
    return 0 if amount >= 1000 else 50


def checkout(order: Order) -> str:
    validate(order)
    amount = payable_amount(order)
    total = amount + shipping_fee(amount)
    return f"to={order.email}; total={total}"


assert checkout(Order("user@example.com", 1200, True)) == (
    checkout_bad("user@example.com", 1200, True)
)
```

重构后，`checkout` 只负责协调，校验、金额和运费规则分别拥有名字。
断言证明示例输入的行为一致；真实项目还应覆盖普通用户、免运费边界和非法输入。

这里没有引入 `ValidatorFactory` 或通用规则引擎，因为目前没有多个实现需求。
这避免了用 Speculative Generality 修复 Long Method，结果制造新的坏味道。

## 🔍 dify 仓库源码解读

### 注释也会重复、过期和产生坏味道

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 12-25）：

```markdown
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
  - Keep comments adjacent to the logic they justify; delete or rewrite comments that no longer match reality.
```

**解读**：

- 第 14 行明确要求避免在不同作用域重复同一知识，对应 Duplicate Code。
- 第 15-23 行把模块、类、函数文档限定在各自职责，降低 Large Class 式的信息堆积。
- 第 17 行要求记录稳定事实，避免“今天如何”的临时描述变成 Dead Code 式误导。
- 第 24-25 行要求解释 `why` 并及时删除过期内容；注释同样需要重构。
- 这些规则强调信息的所有权：一条契约应放在最接近其作用域的位置。

### 显式规则防止聪明代码和超大文件

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 95-109）：

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
- Optimise for observability: deterministic control flow, clear logging, actionable errors.
```

**解读**：

- 第 99 行优先简单函数，避免为了轻量逻辑制造小型工具类和臆想式层次。
- 第 102 行的约 800 行是调查 Large Class/Module 的触发器，不是机械质量判决。
- 第 103 行要求显式可读，深层技巧常使 Long Method 更难理解。
- 第 107 行提供分层归属：业务逻辑出现在 controller 时，应调查职责泄漏。
- 第 108 行要求先复用已有 helper，减少同一知识被复制到新位置。

## ✅ 关键要点总结

- Long Method 关注职责和抽象层级，不只看行数。
- Large Class 的关键信号是过多变化原因和相互独立的字段簇。
- Long Parameter List 可用参数对象改善，但不能用无类型字典掩盖问题。
- Duplicate Code 应以“重复知识”为判断标准，错误抽象可能更糟。
- Dead Code 要考虑框架注册和动态调用，确认后直接删除。
- Speculative Generality 来自没有真实需求支撑的扩展设计。
- 先收集证据和补测试，再以小步重构处理当前最有价值的问题。

## 🧪 练习题

### 练习：坏味道诊断（基础）

阅读独立示例的 `checkout_bad`，为每个坏味道记录：

- 具体代码证据
- 可能造成的维护成本
- 最适合的一个重构手法
- 重构前需要补充的测试

不要只写“函数太长”，要说明它混合了哪些变化原因。

### 练习：区分重复与巧合（进阶）

假设两个 service 都包含相同的 8 行日期格式化代码，
但一个用于用户时区展示，另一个用于 UTC 审计日志。
判断是否应提取公共 helper，并写出支持与反对的证据。
当两个规则未来可能独立变化时，你会如何决策？

### 练习：审查 dify 分层场景（挑战）

从 `/Users/xu/code/github/dify/api/controllers/console/` 选择一个 controller，
只做静态阅读并完成坏味道清单：

- controller 是否只解析输入、调用 service、序列化响应
- 是否存在过长方法或重复校验
- 参数中是否有稳定组合
- 是否可能存在动态注册的“伪 Dead Code”
- 提出不改变行为的三步重构方案

## 📖 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/controllers/`
- `/Users/xu/code/github/dify/api/services/`
- Martin Fowler, *Refactoring: Improving the Design of Existing Code, 2nd Edition*
- Refactoring Guru： https://refactoring.guru/refactoring/smells

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
