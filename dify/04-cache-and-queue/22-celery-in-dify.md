# 4.3.9 dify 的 async_workflow_service 与任务分发

> dify 的 `AsyncWorkflowService` 是异步工作流执行的核心，理解它能掌握 dify 后端最复杂的业务流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `AsyncWorkflowService.trigger_workflow_async` 的完整流程
- 掌握订阅级别 → 队列的映射机制
- 理解配额预留与回滚的设计
- 能修改或扩展 dify 的任务分发

## 📚 前置知识

- Celery 任务定义、调用、路由（详见 [Celery 架构](./14-celery-architecture.md)、[任务路由](./17-celery-routing.md)）
- 任务结果与幂等（详见 [任务结果存储](./19-celery-result.md)、[任务幂等性](./20-celery-idempotency.md)）
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
- **队列路由**：按订阅级别分配队列（详见 [任务路由](./17-celery-routing.md)）
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

## 3. dify 仓库源码解读

### 3.1 触发流程完整代码

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 52-186）：

```python
@classmethod
def trigger_workflow_async(
    cls, user: Account | EndUser, trigger_data: TriggerData, *, session: Session
) -> AsyncTriggerResponse:
    """
    Universal entry point for async workflow execution - THIS METHOD WILL NOT BLOCK
    """
    trigger_log_repo = SQLAlchemyWorkflowTriggerLogRepository(session)
    dispatcher_manager = QueueDispatcherManager()
    workflow_service = WorkflowService()

    # 1. Validate app exists
    app_model = session.scalar(select(App).where(App.id == trigger_data.app_id))
    if not app_model:
        raise WorkflowNotFoundError(f"App not found: {trigger_data.app_id}")

    # 2. Get workflow
    workflow = cls._get_workflow(workflow_service, app_model, trigger_data.workflow_id, session=session)

    # commit read only session before starting the billig rpc call
    session.commit()

    # 3. Get dispatcher based on tenant subscription
    dispatcher = dispatcher_manager.get_dispatcher(trigger_data.tenant_id)

    # 5. Determine user role and ID
    if isinstance(user, Account):
        created_by_role = CreatorUserRole.ACCOUNT
        created_by = user.id
    else:  # EndUser
        created_by_role = CreatorUserRole.END_USER
        created_by = user.id

    # 6. Create trigger log entry first (for tracking)
    trigger_log = WorkflowTriggerLog(...)
    trigger_log = trigger_log_repo.create(trigger_log)
    session.commit()

    # 7. Reserve quota (commit after successful dispatch)
    quota_charge = unlimited()
    try:
        quota_charge = QuotaService.reserve(QuotaType.WORKFLOW, trigger_data.tenant_id)
    except QuotaExceededError as e:
        trigger_log.status = WorkflowTriggerStatus.RATE_LIMITED
        trigger_log.error = f"Quota limit reached: {e}"
        trigger_log_repo.update(trigger_log)
        session.commit()
        raise WorkflowQuotaLimitError(...) from e

    # 8. Create task data
    queue_name = dispatcher.get_queue_name()
    task_data = WorkflowTaskData(workflow_trigger_log_id=trigger_log.id)

    # 9. Dispatch to appropriate queue
    task_data_dict = task_data.model_dump(mode="json")
    try:
        task: AsyncResult[Any] | None = None
        if queue_name == QueuePriority.PROFESSIONAL:
            task = execute_workflow_professional.delay(task_data_dict)
        elif queue_name == QueuePriority.TEAM:
            task = execute_workflow_team.delay(task_data_dict)
        else:  # SANDBOX
            task = execute_workflow_sandbox.delay(task_data_dict)
        quota_charge.commit()
    except Exception:
        quota_charge.refund()
        raise

    # 10. Update trigger log with task info
    trigger_log.status = WorkflowTriggerStatus.QUEUED
    trigger_log.celery_task_id = task.id
    trigger_log.triggered_at = datetime.now(UTC)
    trigger_log_repo.update(trigger_log)
    session.commit()

    return AsyncTriggerResponse(
        workflow_trigger_log_id=trigger_log.id,
        task_id=task.id,
        status="queued",
        queue=queue_name,
    )
```

**解读**（按步骤）：

**Step 1-2 验证（行 87-92）**：
- 验证 App 存在 + Workflow 存在
- `_get_workflow` 根据 `workflow_id` 或默认 workflow 获取
- `session.commit()` 释放只读事务（避免与后面 Billing RPC 冲突）

**Step 3 队列分发（行 98）**：
- `QueueDispatcherManager.get_dispatcher(tenant_id)` 返回 `ProfessionalQueueDispatcher` / `TeamQueueDispatcher` / `SandboxQueueDispatcher`
- 根据订阅计划决定队列名

**Step 5 用户角色（行 103-108）**：
- 区分 Account（账户）vs EndUser（终端用户）
- 用于审计追踪

**Step 6 创建 trigger_log（行 111-136）**：
- PENDING 状态入库
- 即使任务失败也有记录可查

**Step 7 配额预留（行 138-152）**：
- `QuotaService.reserve()` 立即扣配额
- 超限 → 标记 `RATE_LIMITED` → 抛 `WorkflowQuotaLimitError`
- **关键**：配额是**预扣**，任务失败/成功不影响配额

**Step 9 任务派发（行 161-172）**：
- 三选一 `delay()`：PROFESSIONAL / TEAM / SANDBOX
- 成功 → `quota_charge.commit()` 确认
- 失败 → `quota_charge.refund()` 退还

**Step 10 返回结果（行 181-186）**：
- 返回 `workflow_trigger_log_id`（查状态用）+ `task_id`（Celery 任务 ID）
- 状态 `"queued"`

### 3.2 重试入口

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 188-234）：

```python
@classmethod
def reinvoke_trigger(
    cls, user: Account | EndUser, workflow_trigger_log_id: str, *, session: Session
) -> AsyncTriggerResponse:
    trigger_log_repo = SQLAlchemyWorkflowTriggerLogRepository(session)
    trigger_log = trigger_log_repo.get_by_id(workflow_trigger_log_id)

    if not trigger_log:
        raise ValueError(f"Trigger log not found: {workflow_trigger_log_id}")

    # Reconstruct trigger data from log
    trigger_data = TriggerData.model_validate_json(trigger_log.trigger_data)

    # Reset log for retry
    trigger_log.status = WorkflowTriggerStatus.RETRYING
    trigger_log.retry_count += 1
    trigger_log.error = None
    trigger_log.triggered_at = datetime.now(UTC)
    trigger_log_repo.update(trigger_log)
    session.commit()

    # Re-trigger workflow (this will create a new trigger log)
    return cls.trigger_workflow_async(user, trigger_data, session=session)
```

**解读**：
- 旧 log 标记为 `RETRYING`，`retry_count += 1`
- 用 `trigger_workflow_async` 创建**新 log**（保留历史）
- **最大重试次数**：调用方控制（用 `get_failed_logs_for_retry` 过滤 `max_retry_count`）

### 3.3 队列分发器

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
**核心代码**（行 84-111）：

```python
@classmethod
def get_dispatcher(cls, tenant_id: str) -> BaseQueueDispatcher:
    """
    Get dispatcher based on tenant's subscription plan
    """
    if dify_config.BILLING_ENABLED:
        try:
            billing_info = BillingService.get_info(tenant_id)
            plan = billing_info.get("subscription", {}).get("plan", "sandbox")
        except Exception:
            # If billing service fails, default to sandbox
            plan = "sandbox"
    else:
        # If billing is disabled, use team tier as default
        plan = "team"

    dispatcher_class = cls.PLAN_DISPATCHER_MAP.get(
        plan,
        SandboxQueueDispatcher,  # Default to sandbox for unknown plans
    )

    return dispatcher_class()
```

**解读**：
- **调用 BillingService** 获取租户订阅计划
- Billing 故障 → 默认 SANDBOX（**保守降级**）
- Billing 关闭 → 默认 TEAM（**开发环境**）

### 3.4 Worker 执行入口

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
**核心代码**（行 110-186）：

```python
def _execute_workflow_common(
    task_data: WorkflowTaskData,
    cfs_plan_scheduler: AsyncWorkflowCFSPlanScheduler,
    cfs_plan_scheduler_entity: AsyncWorkflowCFSPlanEntity,
):
    """Execute workflow with common logic and trigger log updates."""
    with session_factory.create_session() as session:
        trigger_log_repo = SQLAlchemyWorkflowTriggerLogRepository(session)

        # Get trigger log
        trigger_log = trigger_log_repo.get_by_id(task_data.workflow_trigger_log_id)

        if not trigger_log:
            return

        # Reconstruct execution data from trigger log
        trigger_data = TriggerData.model_validate_json(trigger_log.trigger_data)

        # Update status to running
        trigger_log.status = WorkflowTriggerStatus.RUNNING
        trigger_log_repo.update(trigger_log)
        session.commit()

        start_time = datetime.now(UTC)

        try:
            # Get app and workflow models
            app_model = session.scalar(select(App).where(App.id == trigger_log.app_id))
            workflow = session.scalar(select(Workflow).where(Workflow.id == trigger_log.workflow_id))
            user = _get_user(session, trigger_log)

            # Execute workflow using WorkflowAppGenerator
            generator = WorkflowAppGenerator()
            args = _build_generator_args(trigger_data)
            if trigger_data.workflow_id:
                args["workflow_id"] = str(trigger_data.workflow_id)

            pause_config = PauseStateLayerConfig(...)
            session.commit()  # NOTE: Release the transaction before the blocking generate() call

            generator.generate(
                app_model=app_model,
                workflow=workflow,
                user=user,
                args=args,
                invoke_from=InvokeFrom.SERVICE_API,
                streaming=False,
                call_depth=0,
                triggered_from=trigger_data.trigger_from,
                root_node_id=trigger_data.root_node_id,
                graph_engine_layers=[
                    TriggerPostLayer(cfs_plan_scheduler_entity, start_time, trigger_log.id),
                ],
                pause_state_config=pause_config,
            )

        except Exception as e:
            elapsed_time = (datetime.now(UTC) - start_time).total_seconds()
            trigger_log.status = WorkflowTriggerStatus.FAILED
            trigger_log.error = str(e)
            trigger_log.finished_at = datetime.now(UTC)
            trigger_log.elapsed_time = elapsed_time
            trigger_log_repo.update(trigger_log)
            session.commit()
```

**解读**：
- **状态机**：PENDING → RUNNING → SUCCESS / FAILED
- **CFS 调度器**（`AsyncWorkflowCFSPlanScheduler`）：用于流量控制 / 配额调度
- **关键注释**：第 168 行
  > "Release the transaction before the blocking generate() call, otherwise the connection stays 'idle in transaction' for hours."
  - 工作流可能跑几个小时
  - 必须先 `session.commit()` 释放事务
- **`TriggerPostLayer`**：执行后处理（统计、状态更新）

## 4. 关键要点总结

- `AsyncWorkflowService` 是 dify 异步工作流的**统一入口**
- **10 步流程**：验证 → 队列 → log → 配额 → 提交 → 更新
- **三个队列**：PROFESSIONAL / TEAM / SANDBOX（按订阅）
- **配额预扣 + 失败回滚**：保证业务不超额
- **trigger_log** 完整记录：状态、配额、task_id、错误
- **重试 = 新 trigger_log**：保留历史
- **Worker 端释放事务**：避免长事务阻塞连接池

## 5. 练习题

### 练习 1：基础（必做）

阅读 `AsyncWorkflowService.trigger_workflow_async` 完整代码，画出时序图：API → Service → Repository → Celery → Worker → DB。

### 练习 2：进阶

模拟工作流触发流程：
- 创建一个 `TriggerData`
- 调用 `trigger_workflow_async`
- 查询 `WorkflowTriggerLog` 状态变化

### 练习 3：挑战（选做）

尝试扩展 `AsyncWorkflowService`：添加"延迟触发"功能（10 分钟后才执行）。提示：用 `apply_async(countdown=600)`。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- 相关章节：14-21

---

**文档版本**：v1.0
**最后更新**：2026-07-13