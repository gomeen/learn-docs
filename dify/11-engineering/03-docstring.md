# 11.04 注释与文档字符串：何时写、写什么

> 注释解释"为什么"，docstring 解释"做什么"，代码本身解释"怎么做"。

## 🎯 学习目标

完成本文档后，你将能够：

- 区分 docstring（文档字符串）和 # 注释的适用场景
- 列出 docstring 的常见风格（Google / NumPy / Sphinx）
- 解释"代码即文档"的边界——什么时候必须写注释
- 阅读 dify `api/AGENTS.md` 中关于注释的规范
- 为自己的函数、类、模块写合适的 docstring

## 📚 前置知识

- 已完成 [01-pep8.md](./01-pep8.md)
- 已完成 [03-naming.md](../../_common/20-engineering/01-naming.md)
- Python 函数、类、异常处理基础

## 1. 核心概念

### 1.1 三种"说明代码"的工具

| 工具 | 位置 | 受众 | 用途 |
|---|---|---|---|
| 代码本身 | 函数体 | 所有人 | 表达"怎么做" |
| `# 注释` | 函数体内 / 同行 | 维护者 | 解释"为什么这么做" |
| docstring | 函数 / 类 / 模块的开头 | 调用者 | 说明"做什么、怎么用" |

核心原则：**代码本身是第一文档**。如果能用好命名让代码自我解释，就不要写注释。

### 1.2 何时写 docstring（PEP 257 + dify 强制）

PEP 257 规定**所有公共模块、函数、类、方法都应该有 docstring**。
dify 在 `api/AGENTS.md` 中进一步明确：

> Before changing any backend code under `api/`, you MUST read the surrounding docstrings and comments. These notes contain required context (invariants, edge cases, trade-offs) and are treated as part of the spec.

dify 把 docstring 视为**规范的延伸**——缺失 docstring 等同于规范不完整。

### 1.3 何时写 `#` 注释

`#` 注释应该解释**代码无法表达的信息**：

1. **为什么**（why）：为什么用这个算法而不是另一个？
2. **历史背景**：为什么这里有一个看似奇怪的 workaround？
3. **非显然的坑**：某个边界条件，调用方不知道会触发 bug
4. **TODO/FIXME**：标注未来要做的事

不该写 `#` 注释的情况：
- 解释"做了什么"（代码本身已经说清楚了）
- 重复函数名（`# calculate total` 在 `def calculate_total()` 旁边）
- 长篇大论的架构说明（应该放到模块 docstring 或 ADR）

### 1.4 docstring 风格对比

主流风格有三种：

| 风格 | 特点 | 例子 |
|---|---|---|
| **Google** | 用 `Args:` / `Returns:` / `Raises:` 段落 | dify 推荐风格 |
| **NumPy** | 用下划线分隔 | 数据科学常用 |
| **Sphinx** | 用 `:param x:` 指令 | 老项目常用 |

dify 默认采用 Google 风格（推断自样例）。

## 2. 代码示例

### 2.1 一个有完整 docstring 的例子

```python
# 文件：example_docstring.py

from datetime import datetime


def calculate_refund_amount(
    original_amount: float,
    refund_rate: float,
    refunded_at: datetime,
) -> float:
    """根据退款比例和退款时间计算实际退款金额。

    Args:
        original_amount: 原订单金额（必须大于 0）。
        refund_rate: 退款比例（0~1 之间，0.5 表示退一半）。
        refunded_at: 退款发起时间，用于审计日志。

    Returns:
        实际退款金额，保留两位小数。

    Raises:
        ValueError: 当 original_amount <= 0 或 refund_rate 不在 [0, 1] 范围内。
    """
    if original_amount <= 0:
        raise ValueError(f"original_amount must be positive, got {original_amount}")
    if not 0.0 <= refund_rate <= 1.0:
        raise ValueError(f"refund_rate must be in [0, 1], got {refund_rate}")

    # 使用 round 而不是 Decimal 是因为支付通道只接受两位小数
    # （Stripe 的金额单位是"分"，这里已经是"元"，所以只需 round）
    return round(original_amount * refund_rate, 2)
```

**说明**：
- 第一段：一句话概括函数做什么
- `Args:`：每个参数一行，名称、类型、含义
- `Returns:`：返回值的类型和含义
- `Raises:`：列出可能抛出的异常
- 函数体内的 `# 注释` 解释了"为什么不用 Decimal"——这是代码无法表达的

### 2.2 反例：注释过多 / 注释过少

```python
# ❌ 反例 1：注释解释"做了什么"（赘述）
def calculate_total(price, quantity):
    # 把价格乘以数量
    return price * quantity  # 返回总价

# ✅ 正确做法：好命名 + 无注释
def calculate_total(unit_price: float, quantity: int) -> float:
    return unit_price * quantity
```

```python
# ❌ 反例 2：完全没有 docstring
def process(data, mode):
    if mode == 'strict':
        return [x for x in data if validate(x)]
    return data

# 1. data 是什么类型？
# 2. mode 还有哪些取值？
# 3. validate() 的副作用是什么？

# ✅ 正确做法：完整 docstring
def filter_valid_items(items: list[Item], mode: FilterMode) -> list[Item]:
    """根据 mode 过滤 items。

    Args:
        items: 待过滤的项列表。
        mode: 过滤模式。'strict' 表示严格校验；'lenient' 表示保留所有项。

    Returns:
        通过校验的项列表。
    """
    if mode == FilterMode.STRICT:
        return [item for item in items if item.validate()]
    return items
```

```python
# ❌ 反例 3：过时注释（最危险）
def divide(a, b):
    # 注意：调用前必须确保 b != 0
    return a / b

# 这条注释没说"如何确保 b != 0"，也没说"不确保会怎样"
# 而且如果代码后来加了 b != 0 的检查，注释就会过时

# ✅ 正确做法：用代码表达约束
def divide(a: float, b: float) -> float:
    """计算 a / b。

    Raises:
        ZeroDivisionError: 当 b == 0 时。
    """
    return a / b  # Python 自身会抛出 ZeroDivisionError
```

### 3.1 AGENTS.md 中的注释维护规则（节选）

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`

```markdown
## Rules (must follow)

In this section, "notes" means module/class/function docstrings plus any relevant paragraph/block comments.

- **Before working**
  - Read the notes in the area you'll touch; treat them as part of the spec.
  - If a docstring or comment conflicts with the current code, treat the **code as the single source of truth** and update the docstring or comment to match reality.
  - If important intent/invariants/edge cases are missing, add them in the closest docstring or comment (module for overall scope, function for behaviour).
- **During working**
  - Keep the notes in sync as you discover constraints, make decisions, or change approach.
  - If you move/rename responsibilities across modules/classes, update the affected docstrings and comments so readers can still find the "why" and the invariants.
- **When finishing**
  - Update the notes to reflect what changed, why, and any new edge cases/tests.
  - Remove or rewrite any comments that could be mistaken as current guidance but no longer apply.
```

**解读**：
- 第 33 行：**"code as the single source of truth"** —— 当注释和代码冲突时，以代码为准。**这是反过时注释的核心机制**。
- 第 34 行：**"If important intent... missing, add them"** —— 不只是被动维护，还要主动补充。
- 第 37 行：**"Keep the notes in sync"** —— 工作中发现的约束要立即记到注释里，不能事后补。
- 第 38 行：跨模块重构时，**被移动模块的 docstring 也必须迁移**，否则"为什么"会丢失。
- 第 42-43 行：**完成时清理过时注释**——保留可能误导的注释是危险的。

### 3.2 实际示例：异常类的 docstring

**文件位置**：`/Users/xu/code/github/dify/api/services/errors/__init__.py`
**核心代码**（行 0-12，模块顶部 + 第一组异常）：

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
- 第 0-12 行：`__init__.py` **没有模块 docstring**——这是 dify 的一处小不一致；正常情况下"按 AGENTS.md"应该补一个目的说明。但它做了**正确的事**：把子模块聚合暴露，按领域拆分（`account`、`app`、`dataset`、`message`）——调用方写 `from services.errors import account, app` 即可
- 第 0-12 行的 `from . import (...)` 是 dify 反复使用的"子模块聚合"惯用法：把一组相关异常按领域拆到不同文件，再在 `__init__.py` 一次导出
- 命名上每个子模块都是 `snake_case` 单数（`account.py` 而非 `accounts.py`），保持 PEP 8 一致

**对比 dify 实际异常基类**（`api/services/errors/base.py` 行 0-2）：

```python
class BaseServiceError(ValueError):
    def __init__(self, description: str = ""):
        self.description = description
```

**解读**：
- 第 0 行：dify 用 `BaseServiceError` 继承 `ValueError`——所有领域异常的根基
- 第 1-2 行：构造函数接受 `description`，**不在异常里存 traceback**——上层（controller / middleware）翻译成 HTTP 响应时统一取 `description`
- 这种"描述字段"模式让异常既能上抛、又能直接渲染给前端，不需要额外的 `if isinstance` 分支

## 3. 关键要点总结

- **代码 > docstring > # 注释**：能省则省，能用代码表达就不用注释
- docstring 是**行为契约**：参数、返回、副作用、异常——缺一不可
- `#` 注释只解释**why**，不解释 **what**
- dify 强制把 docstring 当作"规范延伸"——缺失 docstring 等同于规范不完整
- 注释必须**与代码同步**：代码为准，注释永远跟随代码更新
- 注释应分层（模块 / 类 / 函数 / 段落），禁止重复
- 避免**过时注释**——它比没有注释更危险，因为读者会误信

---

**文档版本**：v1.0
**最后更新**：2026-07-13
