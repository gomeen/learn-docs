# 3.7 状态模式（State）

> 状态模式允许对象在内部状态改变时改变它的行为，看起来像是修改了类。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解状态模式的核心（状态决定行为）
- 区分状态 vs 策略
- 识别 dify/ruoyi 中的状态机
- 知道状态模式的适用场景

## 📚 前置知识

- 13-strategy.md
- 19-state.md（状态机基础）

## 1. 核心概念

### 1.1 状态模式的核心思想

把"状态"封装成独立类，每种状态有自己的行为。状态之间可以相互转换。

### 1.2 状态 vs 策略

| 维度 | 状态 | 策略 |
|------|------|------|
| 切换 | 状态自动转换 | 客户端主动选择 |
| 互相感知 | 状态知道彼此 | 策略之间独立 |
| 目的 | 消除大量 if/else | 算法可替换 |

### 1.3 适用场景

- 对象行为随状态变化而变化
- 有大量 if/else 分支判断状态
- 状态转换逻辑复杂

## 2. 代码示例

### 2.1 经典状态模式

```python
from abc import ABC, abstractmethod

class State(ABC):
    @abstractmethod
    def handle(self, context: "Context") -> None:
        ...


class IdleState(State):
    def handle(self, context: "Context") -> None:
        print("Idle: waiting for user input")
        context.set_state(WorkingState())


class WorkingState(State):
    def handle(self, context: "Context") -> None:
        print("Working: processing task")
        context.set_state(DoneState())


class DoneState(State):
    def handle(self, context: "Context") -> None:
        print("Done: task completed")
        context.set_state(IdleState())


class Context:
    """上下文——持有当前状态"""
    def __init__(self):
        self._state: State = IdleState()

    def set_state(self, state: State) -> None:
        self._state = state

    def request(self) -> None:
        self._state.handle(self)


# 使用：状态自动转换
ctx = Context()
ctx.request()  # Idle → Working
ctx.request()  # Working → Done
ctx.request()  # Done → Idle
```

### 2.2 订单状态机

```python
class OrderState(ABC):
    @abstractmethod
    def pay(self, order: "Order") -> None: ...
    @abstractmethod
    def ship(self, order: "Order") -> None: ...
    @abstractmethod
    def cancel(self, order: "Order") -> None: ...


class PendingState(OrderState):
    def pay(self, order):
        order.set_state(PaidState())
        print("Order paid")

    def cancel(self, order):
        order.set_state(CancelledState())
        print("Order cancelled")

    def ship(self, order):
        print("Cannot ship pending order")


class PaidState(OrderState):
    def ship(self, order):
        order.set_state(ShippedState())
        print("Order shipped")
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的工作流运行状态

**文件位置**：`/Users/xu/code/github/dify/api/models/workflow.py`
**核心代码**（行 1-30）：

```python
from enum import Enum

class WorkflowRunStatus(str, Enum):
    """工作流运行状态枚举"""
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    SUCCEEDED = "succeeded"    # 成功
    FAILED = "failed"          # 失败
    PARTIAL_SUCCEEDED = "partial-succeeded"  # 部分成功
    STOPPED = "stopped"        # 停止


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default=WorkflowRunStatus.PENDING)
    # 状态转换：PENDING → RUNNING → (SUCCEEDED | FAILED)
```

**解读**：
- 工作流有多种状态，每种状态对应不同行为
- 状态转换由外部事件触发
- **整体设计**：状态枚举 + 状态转换方法（可改进为状态类）

### 3.2 ruoyi 的订单状态机

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/service/order/TradeOrderServiceImpl.java`
**核心代码**：

```java
@Service
public class TradeOrderServiceImpl implements TradeOrderService {

    @Override
    @Transactional
    public void cancelOrder(Long orderId, String reason) {
        // 1. 查询订单
        TradeOrderDO order = orderMapper.selectById(orderId);

        // 2. 检查状态合法性（当前状态 → 取消）
        if (!OrderStatus.CANCELED.canTransitFrom(order.getStatus())) {
            throw exception(ORDER_STATUS_INVALID);
        }

        // 3. 更新状态
        order.setStatus(OrderStatus.CANCELED.getCode());
        order.setCancelReason(reason);
        orderMapper.updateById(order);

        // 4. 发布事件（订单取消事件）
        eventPublisher.publishEvent(new OrderCancelledEvent(order));
    }
}
```

**解读**：
- 订单有状态机（待支付 → 已支付 → 已发货 → 已完成 / 已取消）
- 每个操作前校验状态合法性
- **整体设计**：用枚举 + 校验方法实现状态模式

## 4. 关键要点总结

- 状态 = 状态决定行为
- 状态自动转换（与策略相反）
- 消除大量 if/else 分支
- dify 的工作流状态、ruoyi 的订单状态都是状态模式
- 适用：对象行为随状态变化

## 5. 练习题

### 练习 1：基础
为电梯实现状态机（停止 / 运行中 / 维修中），每种状态对按钮响应不同。

### 练习 2：进阶
阅读 dify 的 `WorkflowRunStatus`，画出完整的状态转换图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/workflow.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-trade/`
- 《设计模式》第 5 章：状态模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13