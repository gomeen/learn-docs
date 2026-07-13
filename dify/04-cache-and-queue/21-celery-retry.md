# 4.3.8 任务重试与死信队列

> 任务失败时合理重试可提高成功率，过多重试会造成死信堆积。理解重试策略与死信处理是构建可靠系统的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 Celery 任务的重试（`retry` / `autoretry_for`）
- 设计指数退避策略
- 实现死信队列处理永久失败的任务
- 理解 dify 任务的重试策略

## 📚 前置知识

- Celery 任务定义与调用
- 异常处理基础
- 15-celery-tasks.md、20-celery-idempotency.md

## 1. 核心概念

### 1.1 为什么需要重试？

外部依赖**不稳定**：
- 网络抖动（API 调用失败）
- 临时资源不足（DB 连接池满）
- 服务临时不可用（第三方 API 限流）

直接失败 → 用户体验差。**智能重试** → 成功率大幅提升。

### 1.2 重试 vs 死信

```
任务失败
  ↓
重试 N 次
  ↓ 仍失败
死信队列（DLQ）
  ↓
人工处理 / 报警 / 丢弃
```

### 1.3 重试策略

| 策略 | 说明 | 示例 |
|------|------|------|
| 立即重试 | 失败立即重试 | 适用于本地资源竞争 |
| 固定间隔 | 每 N 秒重试 | 简单但不够灵活 |
| 指数退避 | 2^n × base 秒 | 网络抖动的最佳实践 |
| 指数退避 + 抖动 | 加随机量 | 防"重试风暴" |
| 最大时间上限 | 退避不超过 max | 防止退避过久 |

### 1.4 Celery 重试 API

```python
@shared_task(bind=True, max_retries=5)
def my_task(self):
    try:
        call_api()
    except SomeException as exc:
        # countdown：延迟秒数
        raise self.retry(exc=exc, countdown=60)
```

`self.retry()` 把任务重新扔回队列，延迟执行。

### 1.5 autoretry_for 自动重试

```python
@shared_task(
    autoretry_for=(RequestException, ConnectionError),
    retry_backoff=True,           # 指数退避
    retry_backoff_max=60,         # 最大 60 秒
    retry_jitter=True,            # 加随机抖动
    max_retries=5,
)
def fetch_data(url):
    return requests.get(url).json()
```

### 1.6 死信队列（DLQ）

Celery 没有原生 DLQ，但可以用：
1. **路由失败任务**：定义 `on_failure` 回调，把任务路由到 DLQ
2. **数据库记录**：每次失败写一条记录，定期清理
3. **手动监控**：监控 `task_id` 状态超过 N 分钟未成功则报警

## 2. 代码示例

### 2.1 手动重试（指数退避）

```python
@shared_task(bind=True, max_retries=5)
def call_external_api(self, url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        # 指数退避：1, 2, 4, 8, 16 秒（加抖动）
        countdown = min(2 ** self.request.retries, 60)
        raise self.retry(exc=exc, countdown=countdown)
```

### 2.2 autoretry_for 自动重试

```python
from requests.exceptions import RequestException, Timeout

@shared_task(
    bind=True,
    autoretry_for=(RequestException, Timeout),
    retry_backoff=True,
    retry_backoff_max=120,  # 最大 2 分钟
    retry_jitter=True,      # 加随机抖动
    max_retries=5,
)
def fetch_user(self, user_id):
    """自动捕获 RequestException 并重试"""
    response = requests.get(f"https://api.example.com/users/{user_id}")
    response.raise_for_status()
    return response.json()
```

### 2.3 区分可重试与不可重试异常

```python
class RetryableError(Exception):
    """可重试错误"""
    pass

class FatalError(Exception):
    """不可重试错误（业务错误）"""
    pass

@shared_task(bind=True, max_retries=5)
def process_order(self, order_id):
    try:
        result = call_api(order_id)
    except FatalError as e:
        # 业务错误：不重试
        logger.error(f"Fatal error for order {order_id}: {e}")
        notify_admin(order_id, str(e))
        return {"status": "failed", "error": str(e)}
    except RetryableError as exc:
        # 临时错误：重试
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### 2.4 死信队列实现

```python
DEAD_LETTER_QUEUE = "celery_dead_letter"

@shared_task(bind=True, max_retries=3)
def important_task(self, data):
    try:
        process(data)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # 重试耗尽，发到 DLQ
            dead_letter_task.delay({
                "original_task": "important_task",
                "args": data,
                "error": str(exc),
                "traceback": self.request.traceback,
            })
            return
        raise self.retry(exc=exc, countdown=60)

@shared_task(queue=DEAD_LETTER_QUEUE)
def dead_letter_task(payload):
    """处理永久失败的任务"""
    logger.error(f"Dead letter: {payload}")
    # 报警 / 人工处理 / 写数据库
    db.insert("failed_tasks", payload)
```

### 2.5 重试回调

```python
@shared_task(bind=True)
def my_task(self):
    try:
        process()
    except Exception as exc:
        # 记录重试次数
        logger.warning(f"Retry {self.request.retries} for task {self.request.id}")
        raise self.retry(exc=exc, countdown=60)

# 任务最终失败时
@my_task.on_failure(exc, task_id, args, kwargs, einfo)
def on_failure(exc, task_id, args, kwargs, einfo):
    logger.error(f"Task {task_id} finally failed: {exc}")
    notify_admin(task_id, str(exc))
```

### 2.6 常见错误：max_retries 太大

```python
# ❌ 错误：max_retries=1000
# 失败任务长期占用资源，队列积压

# ✅ 正确：max_retries=3~5，配合指数退避
```

## 3. dify 仓库源码解读

### 3.1 默认重试策略

**文件位置**：`/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`
**核心代码**（行 24-33）：

```python
@shared_task(queue="workflow_storage", bind=True, max_retries=3, default_retry_delay=60)
def save_workflow_execution_task(
    self,
    execution_data: dict[str, Any],
    tenant_id: str,
    app_id: str,
    triggered_from: str,
    creator_user_id: str,
    creator_user_role: str,
) -> bool:
```

**解读**：
- `max_retries=3`：最多重试 3 次
- `default_retry_delay=60`：重试间隔 60 秒
- **没有指数退避**：固定 60 秒（简单可预测）
- **任务**：保存工作流执行结果到 DB
- **失败原因**：DB 连接满 / 复制延迟

### 3.2 异步工作流：不自动重试

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
**核心代码**（行 188-201）：

```python
except Exception as e:
    # Calculate elapsed time for failed execution
    elapsed_time = (datetime.now(UTC) - start_time).total_seconds()

    # Update trigger log with failure
    trigger_log.status = WorkflowTriggerStatus.FAILED
    trigger_log.error = str(e)
    trigger_log.finished_at = datetime.now(UTC)
    trigger_log.elapsed_time = elapsed_time
    trigger_log_repo.update(trigger_log)

    # Final failure - no retry logic (simplified like RAG tasks)
    session.commit()
```

**解读**：
- **关键注释**：`# Final failure - no retry logic (simplified like RAG tasks)`
- 工作流执行失败 → **直接 FAILED，不自动重试**
- **为什么**：工作流执行涉及多个 LLM 调用，重试成本高
- **替代方案**：用户/系统主动调用 `reinvoke_trigger()` 重试

### 3.3 主动重试入口

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 188-234）：

```python
@classmethod
def reinvoke_trigger(
    cls, user: Account | EndUser, workflow_trigger_log_id: str, *, session: Session
) -> AsyncTriggerResponse:
    """
    Re-invoke a previously failed or rate-limited trigger - THIS METHOD WILL NOT BLOCK
    """
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
- 主动重试 = 显式 API 调用
- 重试前检查 `max_retry_count`（默认 3 次）
- **创建新 trigger_log**（保留历史）
- **适合场景**：用户手动重试、定时任务扫描失败 log 重试

### 3.4 失败日志查询

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 284-305）：

```python
@classmethod
def get_failed_logs_for_retry(
    cls, tenant_id: str, max_retry_count: int = 3, limit: int = 100
) -> list[WorkflowTriggerLogDict]:
    """
    Get failed logs eligible for retry
    """
    with sessionmaker(db.engine).begin() as session:
        trigger_log_repo = SQLAlchemyWorkflowTriggerLogRepository(session)
        logs = trigger_log_repo.get_failed_for_retry(
            tenant_id=tenant_id, max_retry_count=max_retry_count, limit=limit
        )

        return [log.to_dict() for log in logs]
```

**解读**：
- `get_failed_for_retry`：查询可重试的失败 log
- `max_retry_count=3`：重试不超过 3 次
- **典型用法**：定时任务每 10 分钟调用 `get_failed_logs_for_retry()` → `reinvoke_trigger()`
- **死信处理**：超过 3 次重试不再处理，需要人工介入

### 3.5 超时任务处理

**文件位置**：`/Users/xu/code/github/dify/api/tasks/human_input_timeout_tasks.py`
**核心代码**（行 45-75）：

```python
def _handle_global_timeout(*, form_id: str, workflow_run_id: str, node_id: str, session_factory: sessionmaker) -> None:
    now = naive_utc_now()
    with session_factory() as session, session.begin():
        workflow_run = session.get(WorkflowRun, workflow_run_id)
        if workflow_run is not None:
            workflow_run.status = WorkflowExecutionStatus.STOPPED
            workflow_run.error = f"Human input global timeout at node {node_id}"
            workflow_run.finished_at = now
            session.add(workflow_run)

        pause_model = session.scalar(select(WorkflowPause).where(WorkflowPause.workflow_run_id == workflow_run_id))
        if pause_model is not None:
            try:
                storage.delete(pause_model.state_object_key)
            except Exception:
                logger.exception(...)
            pause_model.resumed_at = now
            session.add(pause_model)


@shared_task(name="human_input_form_timeout.check_and_resume", queue="schedule_executor")
def check_and_handle_human_input_timeouts(limit: int = 100) -> None:
    """Scan for expired human input forms and resume or end workflows."""
```

**解读**：
- **超时即终止**：表单超时直接标记 `STOPPED`，**不重试**
- Beat 调度每 N 分钟执行（详见 ext_celery.py）
- **设计哲学**：业务超时不应无限重试，应该主动清理

## 4. 关键要点总结

- 智能重试提升成功率（指数退避 + 抖动）
- **区分可重试错误**（临时）和**不可重试错误**（业务）
- Celery 没有原生 DLQ，需要自己实现
- dify 工作流**不自动重试**，需要主动调用 `reinvoke_trigger()`
- **超时即终止**：防止无限占用资源
- `max_retries=3` + `default_retry_delay=60` 是 dify 的标准重试配置

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `fetch_url` 任务：
- 网络错误自动重试
- 指数退避（1, 2, 4, 8 秒）
- 最多 5 次

### 练习 2：进阶

实现死信队列：
- 重试耗尽的任务写入 DLQ
- DLQ 处理任务写数据库 + 发送告警

### 练习 3：挑战（选做）

阅读 `tasks/async_workflow_tasks.py` 和 `services/async_workflow_service.py`，画出工作流从触发到失败到重试的完整状态机。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`（第 24-33 行）
- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`（第 188-201 行）
- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`（第 188-305 行）
- `/Users/xu/code/github/dify/api/tasks/human_input_timeout_tasks.py`
- Celery 重试文档：https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying

---

**文档版本**：v1.0
**最后更新**：2026-07-13