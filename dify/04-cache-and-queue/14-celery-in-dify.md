# 4.3.9 dify 的 async_workflow_service 与任务分发

> dify 的 `AsyncWorkflowService` 是异步工作流执行的核心，理解它能掌握 dify 后端最复杂的业务流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `AsyncWorkflowService.trigger_workflow_async` 的完整流程
- 掌握订阅级别 → 队列的映射机制
- 理解配额预留与回滚的设计
- 能修改或扩展 dify 的任务分发

## 📚 前置知识

- Celery 任务定义、调用、路由（详见 [Celery 架构](./05-celery-architecture.md)、[任务路由](./08-celery-routing.md)）
- 任务结果与幂等（详见 [任务结果存储](./11-celery-result.md)、[任务幂等性](./12-celery-idempotency.md)）
- dify 整体架构

## 1. 核心概念

### 1.1 AsyncWorkflowService 的职责

`AsyncWorkflowService` 是 dify **异步工作流执行的统一入口**：

```
用户触发 API
   ↓
AsyncWorkflowService.trigger_workflow_async()
   ↓
   1. 验证 App / Workflow
   2. 获取订阅级别的 Dispatcher
   3. 创建 trigger_log
   4. 预留配额
   5. 提交到对应 Celery 队列
   6. 更新 trigger_log 状态
   ↓
返回 task_id（不阻塞）
   ↓
Celery Worker 执行
   ↓
更新 trigger_log 状态
```

**关键特性**：
- **非阻塞**：API 立即返回
- **队列路由**：按订阅级别分配队列（详见 [任务路由](./08-celery-routing.md)）
- **配额管理**：任务前预留，失败回滚（限流 / 配额语义详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）
- **状态追踪**：trigger_log 完整记录

### 1.2 三大组件协作

```
┌─────────────────────┐
│ AsyncWorkflowService │ ← 业务入口
└──────────┬──────────┘
           │
           ├─→ QueueDispatcher ──── 决定队列
           │
           ├─→ TriggerLogRepo ──── 状态追踪
           │
           └─→ QuotaService ────── 配额管理
                       ↓
                  Celery Worker
```

### 1.3 三个执行入口

| 入口 | 用途 |
|------|------|
| `trigger_workflow_async()` | 主入口，触发新工作流 |
| `reinvoke_trigger()` | 重试失败的触发 |
| `get_trigger_log()` | 查询触发状态 |

## 2. 代码示例

### 2.1 简化的 trigger_workflow_async

```python
class AsyncWorkflowService:
    @classmethod
    def trigger_workflow_async(cls, user, trigger_data, *, session):
        # 1. 验证 App
        app = session.query(App).filter_by(id=trigger_data.app_id).first()
        if not app:
            raise WorkflowNotFoundError(...)

        # 2. 获取 Workflow
        workflow = cls._get_workflow(...)

        # 3. 选择队列
        dispatcher = QueueDispatcherManager.get_dispatcher(trigger_data.tenant_id)
        queue_name = dispatcher.get_queue_name()

        # 4. 创建 trigger_log
        trigger_log = WorkflowTriggerLog(
            status=WorkflowTriggerStatus.PENDING,
            queue_name=queue_name,
            ...
        )
        session.add(trigger_log)
        session.commit()

        # 5. 预留配额
        quota_charge = QuotaService.reserve(QuotaType.WORKFLOW, trigger_data.tenant_id)

        # 6. 提交到 Celery
        try:
            task = submit_to_celery(queue_name, trigger_log.id)
            quota_charge.commit()
        except Exception:
            quota_charge.refund()
            raise

        # 7. 更新状态
        trigger_log.status = WorkflowTriggerStatus.QUEUED
        trigger_log.celery_task_id = task.id
        session.commit()

        return AsyncTriggerResponse(
            workflow_trigger_log_id=trigger_log.id,
            task_id=task.id,
            queue=queue_name,
        )
```

## 3. 关键要点总结

- `AsyncWorkflowService` 是 dify 异步工作流的**统一入口**
- **10 步流程**：验证 → 队列 → log → 配额 → 提交 → 更新
- **三个队列**：PROFESSIONAL / TEAM / SANDBOX（按订阅）
- **配额预扣 + 失败回滚**：保证业务不超额
- **trigger_log** 完整记录：状态、配额、task_id、错误
- **重试 = 新 trigger_log**：保留历史
- **Worker 端释放事务**：避免长事务阻塞连接池

---

**文档版本**：v1.0
**最后更新**：2026-07-13
