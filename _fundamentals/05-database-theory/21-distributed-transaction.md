# 4.6 分布式事务：2PC / 3PC / TCC / Saga

> 当业务跨多个服务/数据库时，单机事务不再适用，需要分布式事务方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式事务的 4 种主流方案
- 知道每种方案的优缺点
- 在 dify/ruoyi 中识别分布式事务
- 为业务场景选择合适方案

## 📚 前置知识

- 16-acid.md
- 微服务基础

## 1. 核心概念

### 1.1 为什么需要分布式事务？

```
单体应用：
  BEGIN → 减库存 → 减金额 → 加积分 → COMMIT  ← 单机事务

微服务架构：
  订单服务 → 减库存（库存服务）
            → 减金额（账户服务）
            → 加积分（积分服务）
            → 三个数据库，无法用单机事务
```

### 1.2 4 种主流方案

| 方案 | 全称 | 思想 | 一致性 | 性能 |
|------|------|------|--------|------|
| 2PC | Two-Phase Commit | 预提交 + 提交 | 强一致 | 差 |
| 3PC | Three-Phase Commit | 2PC + 超时机制 | 强一致 | 较差 |
| TCC | Try-Confirm-Cancel | 业务补偿 | 最终一致 | 中 |
| Saga | 长事务拆分 | 子事务 + 补偿 | 最终一致 | 好 |

### 1.3 2PC（两阶段提交）

```
协调者（Coordinator）
   │
   ├─ 阶段 1: Prepare（预提交）
   │     ├─ 订单服务：预扣库存
   │     ├─ 账户服务：预扣金额
   │     └─ 积分服务：预加积分
   │     → 全部 ACK？
   │
   └─ 阶段 2: Commit / Rollback
         ├─ 全部 ACK → 全部 Commit
         └─ 任一失败 → 全部 Rollback
```

**问题**：协调者单点故障、阻塞、锁资源时间长

### 1.4 TCC（Try-Confirm-Cancel）

业务层面分 3 步：
- **Try**：预留资源（冻结，不实际扣减）
- **Confirm**：确认扣减（Try 必须全部成功才能 Confirm）
- **Cancel**：释放资源（Try 失败时调用）

**举例**：下单扣库存
- Try：冻结库存
- Confirm：实际扣减
- Cancel：解冻库存

### 1.5 Saga

把长事务拆成多个**子事务**，每个子事务有对应的**补偿操作**：
- 成功：依次执行子事务
- 失败：依次执行补偿操作（回滚）

```
正向：T1 → T2 → T3 → T4
补偿：C1 ← C2 ← C3 ← C4（任意失败触发）
```

## 2. 代码示例

### 2.1 2PC 简化实现

```python
class TwoPhaseCommit:
    """两阶段提交简化版"""

    def __init__(self, participants: list):
        self.participants = participants  # [order_svc, account_svc, point_svc]

    def execute(self, operation: callable) -> bool:
        # 阶段 1: Prepare
        prepared = []
        for participant in self.participants:
            try:
                participant.prepare(operation)
                prepared.append(participant)
            except Exception:
                self._rollback(prepared)
                return False

        # 阶段 2: Commit
        try:
            for participant in prepared:
                participant.commit()
            return True
        except Exception:
            # 极端情况：Commit 失败，需人工介入
            raise
```

### 2.2 Saga 简化实现

```python
class Saga:
    """Saga 模式：正向操作 + 补偿操作"""

    def __init__(self):
        self.compensations: list[callable] = []  # 待执行的补偿

    def step(self, action: callable, compensation: callable) -> None:
        """定义一步：action（正向） + compensation（补偿）"""
        try:
            action()
            self.compensations.append(compensation)  # 成功后注册补偿
        except Exception:
            self._compensate()
            raise

    def _compensate(self) -> None:
        """倒序执行补偿"""
        while self.compensations:
            compensation = self.compensations.pop()
            try:
                compensation()
            except Exception:
                # 补偿失败：告警 + 人工介入
                logger.error(f"Compensation failed: {compensation}")


# 使用
saga = Saga()
try:
    saga.step(
        lambda: order_service.create_order(),
        lambda: order_service.cancel_order(),
    )
    saga.step(
        lambda: account_service.deduct(),
        lambda: account_service.refund(),
    )
    saga.step(
        lambda: inventory_service.deduct(),
        lambda: inventory_service.restock(),
    )
except Exception:
    print("Failed, but compensated")
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify：Celery 异步任务（无强分布式事务）

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 1-30）：

```python
from tasks.workflow import run_workflow_task

def trigger_workflow(tenant_id: str, workflow_id: str) -> str:
    """触发工作流——不依赖分布式事务"""
    # 1. 同步：记录任务状态到数据库
    with Session(db.engine) as session:
        run = WorkflowRun(tenant_id=tenant_id, workflow_id=workflow_id, status="pending")
        session.add(run)
    # 2. 异步：Celery 任务执行工作流
    run_workflow_task.delay(tenant_id=tenant_id, workflow_id=workflow_id)
    return run.id
```

**解读**：
- dify 用 **Saga 风格**：主流程同步落库 + Celery 异步执行
- 失败可重试，无强一致要求（最终一致）
- **设计意图**：dify 是 LLM 业务，对一致性要求不强，但要求可恢复

### 3.2 ruoyi：Seata 分布式事务

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**：

```java
@GlobalTransactional(name = "create-order", rollbackFor = Exception.class)
public Long createOrder(OrderSaveReqVO reqVO) {
    // 1. 创建订单（订单服务）
    OrderDO order = orderService.createOrder(reqVO);
    // 2. 扣减库存（库存服务）
    stockService.deduct(reqVO.getSkuId(), reqVO.getQuantity());
    // 3. 扣减金额（账户服务）
    payService.deduct(reqVO.getUserId(), reqVO.getAmount());
    return order.getId();
}
```

**解读**：
- `@GlobalTransactional` 是 Seata 框架的注解
- 自动实现 AT 模式（基于 2PC + 全局锁）
- 任一子事务失败，自动回滚全部
- **整体设计**：ruoyi 用 Seata 处理跨服务事务

## 4. 关键要点总结

- 4 种方案：2PC（强一致差性能）、3PC（改善 2PC）、TCC（业务补偿）、Saga（长事务拆分）
- dify 用 Saga 风格（Celery 异步任务）
- ruoyi 用 Seata（AT 模式 = 增强 2PC）
- 实际工程：金融级用 TCC/TX，互联网业务用 Saga/异步消息

## 5. 练习题

### 练习 1：基础
对比 2PC 和 Saga 的优劣，说明为什么互联网业务多用 Saga。

### 练习 2：进阶
阅读 ruoyi 的 `yudao-module-trade` 模块，找出一个用 `@GlobalTransactional` 的方法。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- Seata 文档：https://seata.io/zh-cn/
- 《数据密集型应用系统设计》第 9 章：一致性与共识

---

**文档版本**：v1.0
**最后更新**：2026-07-13