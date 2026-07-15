# 3.1 策略模式（Strategy）

> 策略模式定义一系列算法，把它们一个个封装起来，并且使它们可以互相替换。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解策略模式的核心（算法族可替换）
- 区分策略 vs 状态模式
- 识别 dify 的模型提供商策略
- 知道策略模式的适用场景

## 📚 前置知识

- 02-factory-method.md
- 多态

## 1. 核心概念

### 1.1 策略模式的核心思想

定义一系列**可互换**的算法，把算法封装成独立的策略类，让客户端在运行时选择。

### 1.2 适用场景

- 多种算法实现同一功能
- 算法需要动态切换
- 消除大量的 if/else 分支

### 1.3 策略 vs 状态

| 维度 | 策略 | [状态](./19-state.md) |
|------|------|------|
| 切换方 | **客户端主动选择** | 状态自动转换 |
| 互相感知 | 策略之间独立 | 状态之间知道彼此 |

> 📌 **Sighting**：状态模式详见 [19-state](./19-state.md)。

## 2. 代码示例

### 2.1 支付策略

```python
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float) -> bool: ...

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"Paid {amount} by credit card")
        return True

class PayPalPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"Paid {amount} by PayPal")
        return True

class CryptoPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"Paid {amount} by crypto")
        return True


class CheckoutContext:
    """上下文——持有当前策略"""
    def __init__(self, strategy: PaymentStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: PaymentStrategy):
        self._strategy = strategy

    def execute_payment(self, amount: float) -> bool:
        return self._strategy.pay(amount)


# 客户端自由选择
context = CheckoutContext(CreditCardPayment())
context.execute_payment(99.99)

context.set_strategy(PayPalPayment())  # 运行时切换策略
context.execute_payment(99.99)
```

### 2.2 排序策略

```python
class SortStrategy(ABC):
    @abstractmethod
    def sort(self, data: list) -> list: ...

class QuickSort(SortStrategy):
    def sort(self, data: list) -> list:
        return sorted(data)  # 简化

class MergeSort(SortStrategy):
    def sort(self, data: list) -> list:
        return sorted(data)

# 客户端根据数据量选择
data_size = len(data)
strategy = QuickSort() if data_size < 1000 else MergeSort()
sorted_data = strategy.sort(data)
```

## 3. dify 仓库源码解读

### 3.1 dify 的模型提供商策略

**文件位置**：`/Users/xu/code/github/dify/api/core/model_manager.py`
**核心代码**（行 1-50）：

```python
from abc import ABC, abstractmethod

class LargeLanguageModel(ABC):
    """LLM 策略接口——所有 LLM 提供商都实现这个接口"""
    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> "LLMResult":
        ...

    @abstractmethod
    def get_num_tokens(self, text: str) -> int:
        ...

# 具体策略：每个提供商一个实现
class OpenAILLM(LargeLanguageModel):
    def invoke(self, prompt: str, **kwargs):
        # 调用 OpenAI API
        ...

class AnthropicLLM(LargeLanguageModel):
    def invoke(self, prompt: str, **kwargs):
        # 调用 Anthropic API
        ...


# 客户端：动态选择策略
def get_llm_strategy(provider: str) -> LargeLanguageModel:
    strategies = {
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
        "cohere": CohereLLM,
    }
    return strategies[provider]()


# 使用
llm = get_llm_strategy("openai")  # 运行时选择策略
result = llm.invoke("Hello")
```

**解读**：
- 每个 LLM 提供商都是一个策略实现
- 客户端通过配置决定使用哪个策略——无需改业务代码
- **整体设计**：用策略模式支持 30+ 模型提供商

### 3.2 dify 的工作流调度策略

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
**核心代码**：

```python
from typing import Protocol

class WorkflowRunner(Protocol):
    """工作流执行器接口——策略"""
    def run(self, workflow_id: str, inputs: dict) -> dict: ...

class SyncRunner:
    def run(self, workflow_id: str, inputs: dict) -> dict:
        """同步执行——立即返回结果"""
        return execute_workflow_sync(workflow_id, inputs)

class AsyncRunner:
    def run(self, workflow_id: str, inputs: dict) -> dict:
        """异步执行——Celery 任务"""
        run_id = run_workflow_task.delay(workflow_id=workflow_id, inputs=inputs)
        return {"run_id": run_id}


# 客户端选择
def execute_workflow(workflow_id: str, inputs: dict, async_mode: bool = False) -> dict:
    runner: WorkflowRunner = AsyncRunner() if async_mode else SyncRunner()
    return runner.run(workflow_id, inputs)
```

**解读**：
- 同步/异步两种执行策略
- 客户端根据场景选择——策略模式
- **整体设计**：用策略模式实现执行模式切换

## 4. 关键要点总结

- 策略 = 算法族可替换
- 客户端主动选择策略（与状态模式相反）
- 消除 if/else 分支
- dify 的模型提供商（30+）是经典策略模式
- 适用：多种算法、动态切换

## 5. 练习题

### 练习 1：基础
为压缩算法（ZIP / RAR / 7Z）实现策略模式。

### 练习 2：进阶
阅读 `dify/api/core/model_manager.py`，找出所有模型提供商策略类。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/model_manager.py`
- `/Users/xu/code/github/dify/api/core/workflow/workflow_entry.py`
- 《设计模式》第 5 章：策略模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13