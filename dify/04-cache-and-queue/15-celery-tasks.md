# 4.3.2 任务定义：@shared_task 与绑定

> Celery 任务定义看似简单，但 `bind`、`max_retries`、`acks_late` 等参数决定任务的可靠性。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `@shared_task` 定义可被任意模块调用的任务
- 理解 `bind=True` 让任务能访问自身状态（重试、ID）
- 配置 `max_retries` / `acks_late` / `autoretry_for`
- 在 dify 中识别不同任务的可靠性要求

## 📚 前置知识

- Celery 基础架构
- Python 装饰器
- 14-celery-architecture.md

## 1. 核心概念

### 1.1 `@shared_task` vs `@app.task`

```python
# 方式 1：在 Celery app 同文件
from celery import Celery
app = Celery("tasks")
@app.task
def add(x, y):
    return x + y

# 方式 2：可被任意模块导入
from celery import shared_task

@shared_task
def add(x, y):
    return x + y
```

**dify 用 `@shared_task`**——任务定义文件可以放在 `tasks/` 目录下任意位置，无需持有 Celery app 引用。

### 1.2 bind=True：让任务访问 self

```python
@shared_task(bind=True, max_retries=3)
def my_task(self, x):
    try:
        process(x)
    except Exception as exc:
        self.retry(exc=exc, countdown=60)  # self.retry() 而不是 my_task.retry()
```

**`self` 提供的属性**：
- `self.request`：任务请求信息（id、args、retries 等）
- `self.retry()`：触发重试
- `self.update_state()`：更新任务状态

### 1.3 任务参数

| 参数 | 作用 |
|------|------|
| `bind=True` | 让任务能访问 self |
| `max_retries` | 最大重试次数 |
| `default_retry_delay` | 重试间隔（秒）|
| `acks_late` | 任务执行成功后才 ack |
| `autoretry_for` | 自动重试的异常类型 |
| `retry_backoff` | 指数退避 |
| `ignore_result` | 不存结果 |
| `queue` | 默认队列 |

### 1.4 acks_late：防止任务丢失

**默认行为**：Worker **拉取任务时立即 ack**（从队列删除）。如果 Worker 崩溃，任务**永久丢失**。

**`acks_late=True`**：任务**执行成功后才 ack**。Worker 崩溃时任务**重新入队**。

```python
@shared_task(acks_late=True, max_retries=3)
def important_task(x):
    # 即使 worker 崩溃，任务会重新执行
    process(x)
```

**代价**：可能重复执行（如果任务不幂等）。需要任务幂等性设计（详见 4.3.7）。

### 1.5 任务队列分配

```python
@shared_task(queue="dataset")
def clean_dataset_task(...):
    pass

@shared_task(queue="workflow")
def execute_workflow(...):
    pass
```

Worker 只消费指定队列：
```bash
celery worker -Q dataset
celery worker -Q workflow
```

## 2. 代码示例

### 2.1 @shared_task 基础

```python
# tasks/email.py
from celery import shared_task

@shared_task
def send_email(to, subject, body):
    """发送邮件"""
    smtp.send(to, subject, body)
    return {"sent": True, "to": to}

# 任意地方调用
from tasks.email import send_email
result = send_email.delay("alice@example.com", "Hi", "Hello")
```

### 2.2 bind=True 与重试

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def fetch_url(self, url):
    """抓取 URL，失败自动重试"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        # 第 N 次重试
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### 2.3 acks_late 防止丢失

```python
@shared_task(acks_late=True, max_retries=3)
def important_task(order_id):
    """关键任务，崩溃后会重新执行"""
    order = db.get_order(order_id)
    if order.status != "paid":
        charge_credit_card(order)
        order.status = "paid"
        db.commit()
```

### 2.4 autoretry_for 自动重试

```python
from requests.exceptions import RequestException

@shared_task(
    autoretry_for=(RequestException, ConnectionError),
    retry_backoff=True,           # 指数退避
    retry_backoff_max=60,         # 最大间隔 60 秒
    max_retries=5,
)
def fetch_data(url):
    return requests.get(url).json()
```

### 2.5 update_state 更新进度

```python
@shared_task(bind=True)
def long_task(self, items):
    for i, item in enumerate(items):
        process(item)
        # 更新任务状态（前端可查询）
        self.update_state(state="PROGRESS", meta={"current": i, "total": len(items)})
```

### 2.6 常见错误：bind 不写 self

```python
# ❌ 错误：bind=True 但函数没有 self 参数
@shared_task(bind=True, max_retries=3)
def my_task(x):  # 缺 self
    self.retry(...)  # NameError: name 'self' is not defined

# ✅ 正确
@shared_task(bind=True, max_retries=3)
def my_task(self, x):
    self.retry(...)
```

## 3. dify 仓库源码解读

### 3.1 异步工作流任务定义

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
**核心代码**（行 53-99）：

```python
@shared_task(queue=AsyncWorkflowQueue.PROFESSIONAL_QUEUE)
def execute_workflow_professional(task_data_dict: dict[str, Any]):
    """Execute workflow for professional tier with highest priority"""
    task_data = WorkflowTaskData.model_validate(task_data_dict)
    cfs_plan_scheduler_entity = AsyncWorkflowCFSPlanEntity(
        queue=AsyncWorkflowQueue.PROFESSIONAL_QUEUE,
        schedule_strategy=AsyncWorkflowSystemStrategy,
        granularity=dify_config.ASYNC_WORKFLOW_SCHEDULER_GRANULARITY,
    )
    _execute_workflow_common(
        task_data,
        AsyncWorkflowCFSPlanScheduler(plan=cfs_plan_scheduler_entity),
        cfs_plan_scheduler_entity,
    )


@shared_task(queue=AsyncWorkflowQueue.TEAM_QUEUE)
def execute_workflow_team(task_data_dict: dict[str, Any]):
    """Execute workflow for team tier"""
    task_data = WorkflowTaskData.model_validate(task_data_dict)
    cfs_plan_scheduler_entity = AsyncWorkflowCFSPlanEntity(
        queue=AsyncWorkflowQueue.TEAM_QUEUE,
        schedule_strategy=AsyncWorkflowSystemStrategy,
        granularity=dify_config.ASYNC_WORKFLOW_SCHEDULER_GRANULARITY,
    )
    _execute_workflow_common(
        task_data,
        AsyncWorkflowCFSPlanScheduler(plan=cfs_plan_scheduler_entity),
        cfs_plan_scheduler_entity,
    )


@shared_task(queue=AsyncWorkflowQueue.SANDBOX_QUEUE)
def execute_workflow_sandbox(task_data_dict: dict[str, Any]):
    """Execute workflow for free tier with lower retry limit"""
    task_data = WorkflowTaskData.model_validate(task_data_dict)
    cfs_plan_scheduler_entity = AsyncWorkflowCFSPlanEntity(
        queue=AsyncWorkflowQueue.SANDBOX_QUEUE,
        schedule_strategy=AsyncWorkflowSystemStrategy,
        granularity=dify_config.ASYNC_WORKFLOW_SCHEDULER_GRANULARITY,
    )
    _execute_workflow_common(
        task_data,
        AsyncWorkflowCFSPlanScheduler(plan=cfs_plan_scheduler_entity),
        cfs_plan_scheduler_entity,
    )
```

**解读**：
- **三个任务**分别绑定到不同队列（professional / team / sandbox）
- **订阅级别 → 队列**映射见 `queue_dispatcher.py`
- 用 `task_data_dict` 而不是单个参数，因为 Celery 序列化复杂对象（如 Pydantic model）需要 dict
- `_execute_workflow_common` 是三个任务共享的核心逻辑

### 3.2 绑定 + 重试：工作流存储任务

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
- **bind=True**：任务能访问 self（用于重试）
- **max_retries=3**：最多重试 3 次
- **default_retry_delay=60**：重试间隔 60 秒
- **queue="workflow_storage"**：单独的存储队列，与执行队列分离
- **作用**：把工作流执行结果**异步存 DB**，避免阻塞执行流程
- **重试场景**：DB 暂时不可用（连接数满、复制延迟）

### 3.3 普通重试任务：注释批处理

**文件位置**：`/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
**核心代码**（行 17-30）：

```python
@shared_task(queue="dataset")
def add_annotation_to_index_task(
    annotation_id: str, question: str, tenant_id: str, app_id: str, collection_binding_id: str
):
    """
    Add annotation to index.

    Usage: clean_dataset_task.delay(dataset_id, tenant_id, indexing_technique, index_struct)
    """
    logger.info(click.style(f"Start build index for annotation: {annotation_id}", fg="green"))
    start_at = time.perf_counter()
```

**解读**：
- **没有 bind=True**：不需要访问 self
- **没有 max_retries**：失败由调用方处理（注释删除/重建）
- **queue="dataset"**：和数据集相关任务同队列
- **特点**：任务简单，不需要复杂状态管理

### 3.4 数据清理任务（简单场景）

**文件位置**：`/Users/xu/code/github/dify/api/tasks/clean_dataset_task.py`
**核心代码**（行 32-52）：

```python
@shared_task(queue="dataset")
def clean_dataset_task(
    dataset_id: str,
    tenant_id: str,
    indexing_technique: str,
    index_struct: str,
    collection_binding_id: str,
    doc_form: str,
    pipeline_id: str | None = None,
):
    """
    Clean dataset when dataset deleted.
    Usage: clean_dataset_task.delay(dataset_id, tenant_id, indexing_technique, index_struct)
    """
```

**解读**：
- **没有 bind / retry**：最简单形式
- **失败处理**：靠 Celery 默认行为（重试 N 次后丢弃）
- **调用方**（`dataset_service.delete_dataset`）会同步删 DB，Celery 任务是清理向量索引等外部资源

## 4. 关键要点总结

- `@shared_task` 让任务模块化（不依赖 Celery app）
- `bind=True` 任务能访问 self（重试、状态）
- **`acks_late=True` 防止任务丢失**（代价是可能重复执行）
- `autoretry_for` 自动捕获异常并重试
- `queue="..."` 分配任务到特定队列
- dify 任务按订阅级别 / 功能分队列（workflow_professional / dataset / workflow_storage）

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `send_email` 任务，绑定到 `email` 队列。

### 练习 2：进阶

实现一个 `fetch_url` 任务：
- bind=True
- max_retries=3
- 用 `autoretry_for` 自动重试网络错误
- 指数退避

### 练习 3：挑战（选做）

阅读 `api/tasks/async_workflow_tasks.py`，理解三个订阅级别任务如何复用 `_execute_workflow_common`，并思考这种"三任务共享核心"的设计优点。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`（第 53-99 行）
- `/Users/xu/code/github/dify/api/tasks/workflow_execution_tasks.py`（第 24-33 行）
- `/Users/xu/code/github/dify/api/tasks/annotation/add_annotation_to_index_task.py`
- `/Users/xu/code/github/dify/api/tasks/clean_dataset_task.py`（第 32-52 行）
- Celery 任务定义文档：https://docs.celeryq.dev/en/stable/reference/celery.app.task.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13