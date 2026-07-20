# 02 TDD：红绿重构

> 理解测试驱动开发（Test-Driven Development）的红绿重构循环，并应用到 dify 的开发流程中。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 TDD 的三阶段循环：Red → Green → Refactor
- 掌握 TDD 的实战节奏和常见误区
- 能为 dify 的新功能编写先行的失败测试
- 应用：能按 TDD 流程开发 dify 的 services 或 core 模块

## 📚 前置知识

- Python 类型注解（详见 [typing 基础](../../dify/01-fundamentals/07-python-typing-basics.md)）
- 01-testing-pyramid.md
- 04-aaa-pattern.md（推荐先看）

## 1. 核心概念

### 1.1 TDD 是什么

**测试驱动开发（TDD）** 是一种先写测试、再写实现、最后重构的开发方法，由 Kent Beck 在《测试驱动开发》一书中提出。

它的核心是 **红绿重构循环**：

```
   ┌─────────┐
   │   RED   │  1. 写一个失败的测试
   └────┬────┘
        ↓
   ┌─────────┐
   │  GREEN  │  2. 用最少的代码让测试通过
   └────┬────┘
        ↓
   ┌─────────────┐
   │  REFACTOR   │  3. 在测试保护下改进代码
   └─────────────┘
        ↓
       循环
```

### 1.2 为什么需要 TDD

- **设计压力**：写测试时被迫思考 API 该怎么用，促使你设计更好的接口
- **回归保护**：每个特性都有测试，重构时不会破坏已有功能
- **文档作用**：测试是最鲜活的"如何使用"文档
- **反馈及时**：从"写完代码再发现 bug"变成"写完代码立即知道对不对"

### 1.3 TDD 的常见误区

| 误区 | 正确做法 |
|------|----------|
| 写完所有测试再写实现 | 一个测试一个测试地交替进行 |
| 写很复杂的测试 | 先写最简单的失败测试 |
| 重构时改测试 | 重构阶段**不应该**改测试，只改实现 |
| 跳过 Red 阶段 | **必须**看到测试失败才能进 Green |
| 把 TDD 当成负担 | TDD 实质是"用自动化测试代替人工调试" |

## 2. 代码示例

### 2.1 经典 TDD 流程：实现一个折扣计算器

**第一步：RED（写失败测试）**

```python
# 文件：test_discount_calculator.py
import pytest
from discount_calculator import calculate_discount


class TestCalculateDiscount:
    def test_no_discount_for_zero_amount(self):
        # Arrange
        amount = 0
        user_tier = "regular"

        # Act
        result = calculate_discount(amount, user_tier)

        # Assert
        assert result == 0
```

```bash
# 此时运行测试：失败（模块不存在）
$ pytest test_discount_calculator.py
ModuleNotFoundError: No module named 'discount_calculator'
```

**第二步：GREEN（写最小实现）**

```python
# 文件：discount_calculator.py
def calculate_discount(amount: float, user_tier: str) -> float:
    """最小实现：让测试通过即可。"""
    return 0  # 故意写最简单的代码
```

```bash
$ pytest test_discount_calculator.py
1 passed
```

**第三步：REFACTOR（改进设计）**

随着新测试加入，你会自然地把 `if/elif` 重构为字典查找或策略模式——但**只在测试保护下**做。

### 2.2 一个完整的 TDD 迭代示例

```python
# === 迭代 2：新增测试 ===
def test_regular_user_no_discount_under_100(self):
    assert calculate_discount(50, "regular") == 0

def test_regular_user_10_percent_discount_over_100(self):
    assert calculate_discount(100, "regular") == 10

def test_premium_user_20_percent_discount(self):
    assert calculate_discount(100, "premium") == 20

# === 实现逐步完善 ===
# 第一次实现（Green）
def calculate_discount(amount: float, user_tier: str) -> float:
    if amount < 100:
        return 0
    if user_tier == "premium":
        return amount * 0.2
    return amount * 0.1

# 重构后（Refactor）
DISCOUNT_RATES = {"regular": 0.1, "premium": 0.2}
def calculate_discount(amount: float, user_tier: str) -> float:
    if amount < 100:
        return 0
    return amount * DISCOUNT_RATES.get(user_tier, 0)
```

## 3. dify 仓库源码解读

### 3.1 dify 的测试优先策略

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心内容**：

> Follow TDD: red → green → refactor.

**解读**：
- dify 后端的开发规范明确要求 TDD 流程
- 在 `01-fundamentals` 和 `02-backend` 模块的所有"实战"练习题中，都要求"先写测试再写实现"
- 测试不仅是质量保障，更是设计工具

### 3.2 dify 的单元测试与 TDD 实践

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`
**核心代码**（行 1-14）：

```python
"""Comprehensive unit tests for BillingService.

This test module covers all aspects of the billing service including:
- HTTP request handling with retry logic
- Subscription tier management and billing information retrieval
- Usage calculation and credit management (positive/negative deltas)
- Rate limit enforcement for compliance downloads and education features
- Account management and permission checks
- Cache management for billing data
- Partner integration features

All tests use mocking to avoid external dependencies and ensure fast, reliable execution.
Tests follow the Arrange-Act-Assert pattern for clarity.
"""
```

**解读**：
- 第 12 行：`All tests use mocking to avoid external dependencies` —— 这是 TDD 友好设计的体现
- 第 13 行：`Tests follow the Arrange-Act-Assert pattern` —— dify 强制 AAA 结构，让 TDD 的"先想清楚场景 → 再写断言 → 再实现"流程更顺畅
- **整体设计意图**：dify 的 Service 层都被设计成"通过构造函数注入依赖"的形式，便于 mock，符合 TDD 的要求

## 4. 关键要点总结

- TDD 三阶段：**Red（失败测试）→ Green（最小实现）→ Refactor（在测试保护下改进）**
- 每个循环 5-15 分钟，不是一次性写完所有测试
- Refactor 阶段**只能改实现**，不能改测试
- TDD 适合 dify 的 Service 层和 Core 层；UI / 集成层用其他方法（如 BDD）
- 测试不仅验证正确性，更是 API 设计的探针

## 5. 练习题

### 练习 1：基础（必做）

为 `calculate_discount` 增加一个新需求：**VIP 用户在金额超过 500 时享受 30% 折扣**。按 TDD 流程：
1. 先写一个失败的测试
2. 运行测试看到红色
3. 写最小实现
4. 重构

### 练习 2：进阶

阅读 dify 的 `services/billing_service.py` 中的某个方法（如 `get_subscription`），按 TDD 流程重新实现一遍：先写 `test_*.py`，再写实现。

### 练习 3：挑战（选做）

观察 `api/tests/unit_tests/services/` 下的 5 个测试文件，找出其中最像"事后补写测试"的文件（无 AAA 结构、大量 `print`、测试名不清晰），并按 TDD 规范重写。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`（dify 后端开发规范）
- `/Users/xu/code/github/dify/api/tests/unit_tests/services/test_billing_service.py`（AAA 范例）
- Kent Beck《测试驱动开发》（2003）
- pytest 官方文档：https://docs.pytest.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13