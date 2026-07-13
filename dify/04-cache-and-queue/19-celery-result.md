# 4.3.6 任务结果存储与查询

> Celery 任务结果默认存 Redis / DB，dify 因为大量任务不需要结果，主动关闭结果存储。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Result Backend 的工作原理
- 掌握 `AsyncResult` 查询任务状态
- 配置 `ignore_result` 控制结果存储
- 理解 dify 为何默认关闭结果存储 + 用 trigger_log 替代

## 📚 前置知识

- Celery 基础架构
- 14-celery-architecture.md

## 1. 核心概念

### 1.1 什么是 Result Backend？

任务执行完毕后，Celery 把**返回值**存到 Backend（如 Redis），客户端可以通过 `task_id` 查询。

```
Worker 执行 → 存结果到 Backend (Redis)
                          ↓
Client 查询 AsyncResult(task_id) → Backend 读取
```

### 1.2 AsyncResult API

```python
from celery.result import AsyncResult

result = my_task.delay(1, 2)

# 状态
print(result.state)  # PENDING / STARTED / SUCCESS / FAILURE / RETRY

# 同步等待
value = result.get(timeout=10)

# 异步检查
if result.ready():
    print(result.result)

# 失败时
if result.failed():
    print(result.traceback)

# 进度（如果用 update_state）
print(result.info)  # {"current": 5, "total": 10}
```

### 1.3 五种状态

| 状态 | 含义 |
|------|------|
| PENDING | 任务提交，未开始（可能不存在） |
| STARTED | Worker 开始执行 |
| SUCCESS | 执行成功 |
| FAILURE | 执行失败 |
| RETRY | 重试中 |
| REVOKED | 被取消 |

### 1.4 配置选项

```python
app.conf.task_ignore_result = True  # 全局关闭
app.conf.result_expires = 3600      # 结果 1 小时后过期

@shared_task(ignore_result=False)   # 单任务开启
def important_task():
    return result

@shared_task(ignore_result=True)    # 单任务关闭
def fire_and_forget():
    pass
```

### 1.5 何时需要 Result Backend？

**不需要**：
- 任务只需执行，不关心结果（清理、通知）
- 高频短任务（每秒几千次），存结果开销大

**需要**：
- 任务结果需要查询（生成 PDF、跑批数据）
- 长时间任务，需要进度更新
- 失败需要重试查询

### 1.6 Result Backend 存储格式

**Redis 存储**：
```
Key: celery-task-meta-{task_id}
Type: Hash
Fields: status, result, traceback, children, ...
TTL: result_expires（默认 1 天）
```

## 2. 代码示例

### 2.1 查询任务状态

```python
from celery.result import AsyncResult

def get_task_status(task_id: str) -> dict:
    result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.successful() else None,
    }

# API endpoint
@app.route("/task/<task_id>")
def task_status(task_id):
    return get_task_status(task_id)
```

### 2.2 进度更新

```python
@shared_task(bind=True)
def long_task(self, items):
    total = len(items)
    for i, item in enumerate(items):
        process(item)
        # 更新进度（前端可查）
        self.update_state(state="PROGRESS", meta={"current": i + 1, "total": total})
    return {"processed": total}
```

```python
# 前端轮询
def poll_progress(task_id):
    result = AsyncResult(task_id)
    if result.state == "PROGRESS":
        return result.info  # {"current": 5, "total": 10}
    elif result.state == "SUCCESS":
        return result.result  # {"processed": 10}
```

### 2.3 全局关闭结果

```python
# celery_config.py
app.conf.task_ignore_result = True  # 默认不存结果

# 重要任务显式开启
@shared_task(ignore_result=False)
def important_task():
    return critical_result
```

### 2.4 结果过期清理

```python
app.conf.result_expires = 3600  # 1 小时后过期
```

### 2.5 常见错误：结果未存但调用 .get()

```python
# 默认 task_ignore_result=True
@shared_task
def add(x, y):
    return x + y

result = add.delay(3, 5)
result.get(timeout=10)  # TimeoutError，因为结果没存
```

## 3. dify 仓库源码解读

### 3.1 默认关闭结果存储

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 118-128）：

```python
celery_app.conf.update(
    result_backend=dify_config.CELERY_RESULT_BACKEND,
    broker_transport_options=broker_transport_options,
    broker_connection_retry_on_startup=True,
    worker_log_format=dify_config.LOG_FORMAT,
    worker_task_log_format=dify_config.LOG_FORMAT,
    worker_hijack_root_logger=False,
    timezone=pytz.timezone(dify_config.LOG_TZ or "UTC"),
    task_ignore_result=True,
    task_annotations=dify_config.CELERY_TASK_ANNOTATIONS,
)
```

**解读**：
- **第 126 行**：`task_ignore_result=True`，dify 默认**不存任务结果**
- 原因：
  1. dify 任务大多是**异步执行**（执行完毕用户也不在线）
  2. **存储开销大**：每天百万任务 × 几 KB = 几个 GB Redis
  3. **有 trigger_log 替代**：dify 自己维护任务状态表

### 3.2 用 trigger_log 跟踪任务状态

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 111-133）：

```python
# 6. Create trigger log entry first (for tracking)
trigger_log = WorkflowTriggerLog(
    tenant_id=trigger_data.tenant_id,
    app_id=trigger_data.app_id,
    workflow_id=workflow.id,
    root_node_id=trigger_data.root_node_id,
    trigger_metadata=(
        trigger_data.trigger_metadata.model_dump_json() if trigger_data.trigger_metadata else "{}"
    ),
    trigger_type=trigger_data.trigger_type,
    workflow_run_id=None,
    outputs=None,
    trigger_data=trigger_data.model_dump_json(),
    inputs=json.dumps(dict(trigger_data.inputs)),
    status=WorkflowTriggerStatus.PENDING,
    queue_name=dispatcher.get_queue_name(),
    retry_count=0,
    created_by_role=created_by_role,
    created_by=created_by,
    celery_task_id=None,
    error=None,
    elapsed_time=None,
    total_tokens=None,
)

trigger_log = trigger_log_repo.create(trigger_log)
session.commit()
```

**解读**：
- `WorkflowTriggerLog` 是 dify 自定义的**任务状态表**（PostgreSQL）
- 字段：
  - `status`：PENDING → QUEUED → RUNNING → SUCCESS / FAILED
  - `celery_task_id`：Celery 分配的任务 ID
  - `error`：失败信息
  - `elapsed_time`：耗时
- **优势**：可以 join 其他表（如 App、Workflow），支持复杂查询
- **劣势**：需要事务保证（Celery 结果存 Redis 不需要事务）

### 3.3 任务状态更新

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
**核心代码**（行 130-135）：

```python
# Update status to running
trigger_log.status = WorkflowTriggerStatus.RUNNING
trigger_log_repo.update(trigger_log)
session.commit()
```

**解读**：
- Worker 接到任务后立刻更新 trigger_log 为 `RUNNING`
- 失败时更新 `FAILED` + error 信息（详见 188-200 行）
- **状态机**：
  ```
  PENDING → QUEUED → RUNNING → SUCCESS / FAILED
                                    ↓
                                  RETRYING → PENDING
  ```

### 3.4 配额回滚与任务状态

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 161-172）：

```python
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
```

**解读**：
- 任务入队失败 → `quota_charge.refund()` 退还配额
- 任务入队成功 → `quota_charge.commit()` 确认扣费
- **任务结果不存 Redis，但 trigger_log 存了 task_id，可关联**

## 4. 关键要点总结

- **Result Backend** 存任务返回值到 Redis / DB
- `task_ignore_result=True` 全局关闭，dify 用此配置
- **dify 用 PostgreSQL 表**（`WorkflowTriggerLog`）跟踪任务状态
- 优势：可 join 查询、复杂状态机、事务保证
- 任务状态变更通过 `trigger_log_repo.update()` 持久化

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `get_task_status(task_id)` 函数，返回任务状态、结果（如果有）、traceback（如果失败）。

### 练习 2：进阶

实现一个长任务，用 `self.update_state` 更新进度，前端轮询显示进度条。

### 练习 3：挑战（选做）

阅读 `models/trigger.py`（如果存在），理解 `WorkflowTriggerLog` 的状态机，并画出状态转换图。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`（第 118-128 行）
- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`（第 111-186 行）
- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`（第 130-200 行）
- Celery Result 文档：https://docs.celeryq.dev/en/stable/reference/celery.result.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13