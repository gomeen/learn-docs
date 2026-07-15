# 4.3.3 任务调用：delay / apply_async / 任务签名

> Celery 任务调用方式有多种：`delay()` 简单快捷，`apply_async()` 功能丰富，签名（Signature）支持复杂编排。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `delay()` / `apply_async()` / 任务签名
- 用 `apply_async` 设置延迟执行、优先级、ETA
- 用 canvas（chain / group / chord）编排任务
- 理解 dify 的 `task.delay(...)` 调用方式

## 📚 前置知识

- Celery 任务定义（详见 [任务定义](./15-celery-tasks.md)）
- Python 基础

## 1. 核心概念

### 1.1 三种调用方式对比

| 方式 | 复杂度 | 功能 |
|------|--------|------|
| `task.delay(*args, **kwargs)` | 最简 | 立即入队 |
| `task.apply_async(args, kwargs, ...)` | 中 | 完整控制（ETA、队列、优先级）|
| `task.s(*args, **kwargs)` | 高 | 签名，支持 canvas 编排 |

### 1.2 delay()：最常用

```python
@shared_task
def add(x, y):
    return x + y

# delay() 是 apply_async 的快捷方式
result = add.delay(3, 5)

# 等价于
result = add.apply_async(args=(3, 5))
```

### 1.3 apply_async：完整控制

```python
result = add.apply_async(
    args=(3, 5),
    countdown=10,        # 10 秒后执行
    eta=datetime.now() + timedelta(minutes=5),  # 指定时间执行
    queue="priority",    # 指定队列
    priority=9,          # 优先级（0-9，broker 支持才有意义）
    expires=3600,        # 1 小时后未执行则丢弃
    retry=True,          # 失败重试
)
```

### 1.4 任务签名（Signature）

签名是**任务的"蓝图"**，不立即执行，可与其他签名组合：

```python
from celery import chain, group, chord

# chain：串行执行（前一个的输出是后一个的输入）
workflow = chain(
    fetch_data.s("https://api.com"),  # 返回 {"raw": "data"}
    transform.s("upper"),              # {"raw": "data"} + "upper" → "DATA"
    save.s("user:1"),                  # "DATA" + "user:1" → 存 DB
)
workflow.apply_async()

# group：并行执行
jobs = group(
    send_email.s("a@x.com"),
    send_email.s("b@x.com"),
    send_email.s("c@x.com"),
)
jobs.apply_async()

# chord：group + callback
jobs = chord(
    [send_email.s(addr) for addr in emails],
    aggregate_results.s(),  # 所有 email 发送完后调用
)
```

### 1.5 ETA 与 Countdown

```python
# 相对延迟
add.apply_async((1, 2), countdown=60)  # 60 秒后

# 绝对时间
add.apply_async((1, 2), eta=datetime(2024, 1, 1, 12, 0))
```

dify 用 ETA 实现**延迟任务**（如超时检查）。

### 1.6 优先级

```python
add.apply_async((1, 2), priority=9)  # 最高
add.apply_async((1, 2), priority=0)  # 最低
```

**注意**：Redis 不支持原生优先级，需用 RabbitMQ 或 Sorted Set。

## 2. 代码示例

### 2.1 delay() 基础

```python
from tasks import send_email

# 异步发送
result = send_email.delay("alice@example.com", "Hi", "Hello")
print(f"Task ID: {result.id}")  # 立即返回，不阻塞
print(f"Task state: {result.state}")  # PENDING

# 等待结果（不推荐用 get 阻塞）
result.get(timeout=10)
```

### 2.2 apply_async 高级选项

```python
from datetime import datetime, timedelta

# 30 分钟后执行
result = send_email.apply_async(
    args=["alice@example.com", "Reminder", "Hello"],
    countdown=1800,
)

# 指定队列和优先级
result = send_email.apply_async(
    args=["vip@example.com"],
    queue="priority",
    priority=9,
)

# 设置过期时间（避免积压）
result = send_email.apply_async(
    args=["alice@example.com"],
    expires=datetime.now() + timedelta(hours=1),
)
```

### 2.3 chain 串行编排

```python
from celery import chain

workflow = chain(
    download_file.s(url),      # 下载文件
    extract_data.s(),            # 提取数据
    upload_to_s3.s(bucket),     # 上传到 S3
)
result = workflow.apply_async()
```

### 2.4 group 并行编排

```python
from celery import group

# 批量处理 100 个 URL
jobs = group([
    process_url.s(url, user_id) for url in urls
])
result = jobs.apply_async()
print(f"Job group ID: {result.id}")

# 等待所有完成
result.get(timeout=60)
```

### 2.5 chord：并行 + 回调

```python
from celery import chord

# 抓取 10 个 URL → 全部完成后汇总
jobs = chord(
    [fetch_url.s(url) for url in urls],
    summarize.s(),  # 接收所有结果的列表
)
jobs.apply_async()
```

### 2.6 常见错误：delay 不能传复杂对象

```python
# ❌ 错误：传 Pydantic / SQLAlchemy 对象（不可 JSON 序列化）
from models import User
user = session.query(User).first()
send_email.delay(user.email, ...)  # TypeError: Object of type User is not JSON serializable

# ✅ 正确：传 dict / 字符串 / 数字
send_email.delay(user.email, ...)
```

## 3. dify 仓库源码解读

### 3.1 .delay() 调用：触发工作流

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 161-172）：

```python
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
```

**解读**：
- **第 159 行**：`task_data.model_dump(mode="json")` 把 Pydantic model 转 dict（**避免序列化问题**）
- **第 164-168 行**：根据订阅级别选择不同任务 → 路由到不同队列
- **第 169 行**：`quota_charge.commit()` 提交配额扣费
- **第 170-172 行**：任务入队失败时 `quota_charge.refund()` 退还配额
- **设计亮点**：**配额扣费与任务提交原子化**——任务入队失败 → 配额退还

### 3.2 获取任务 ID 和状态

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 174-179）：

```python
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

**解读**：
- `task.id`：Celery 分配的任务 ID（如 UUID）
- 存到 `trigger_log.celery_task_id` 用于**追踪任务状态**
- 返回 `task_id` 给客户端，前端可查询进度
- **查询任务状态**（在 worker 端）：
  ```python
  from celery.result import AsyncResult
  result = AsyncResult(task_id)
  print(result.state)  # PENDING / STARTED / SUCCESS / FAILURE
  print(result.result)  # 任务返回值
  ```

### 3.3 任务数据传递：Pydantic 序列化

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 153-159）：

```python
# 8. Create task data
queue_name = dispatcher.get_queue_name()

task_data = WorkflowTaskData(workflow_trigger_log_id=trigger_log.id)

# 9. Dispatch to appropriate queue
task_data_dict = task_data.model_dump(mode="json")
```

**解读**：
- `WorkflowTaskData` 是 Pydantic model
- `model_dump(mode="json")` 转 JSON 兼容的 dict
- Worker 端反序列化：
  ```python
  task_data = WorkflowTaskData.model_validate(task_data_dict)
  ```
- **避免常见错误**：直接传 Pydantic 对象会导致 Celery JSON 序列化失败

### 3.4 队列分发器（订阅级别 → 队列）

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
**核心代码**（行 16-22）：

```python
class QueuePriority(StrEnum):
    """Queue priorities for different subscription tiers"""

    PROFESSIONAL = "workflow_professional"  # Highest priority
    TEAM = "workflow_team"
    SANDBOX = "workflow_sandbox"  # Free tier
```

**解读**：
- **三个队列名**：PROFESSIONAL / TEAM / SANDBOX
- 每个订阅级别有独立 Worker：
  ```bash
  celery worker -Q workflow_professional --concurrency=10
  celery worker -Q workflow_team --concurrency=5
  celery worker -Q workflow_sandbox --concurrency=2
  ```
- **优点**：付费用户不受免费用户影响（资源隔离）
- **故障隔离**：sandbox 队列积压不会影响 professional

## 4. 关键要点总结

- `delay()` 是 `apply_async()` 的快捷方式
- `apply_async()` 支持 countdown / eta / queue / priority
- **任务签名**支持 chain / group / chord 编排
- 复杂对象必须先转 dict（`model_dump(mode="json")`）
- dify 用 **3 个订阅队列**（PROFESSIONAL / TEAM / SANDBOX）
- **配额扣费与任务提交原子化**（失败时 refund）

## 5. 练习题

### 练习 1：基础（必做）

用 `delay()` 提交一个 `send_email` 任务，并获取 task_id。

### 练习 2：进阶

用 `chain` 编排一个数据处理流程：下载 → 解析 → 存储，每步依赖上一步的结果。

### 练习 3：挑战（选做）

阅读 `services/async_workflow_service.py`，理解 `quota_charge.commit()` / `refund()` 的实现，并思考为什么任务入队失败要退还配额。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`（第 153-186 行）
- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- Celery 任务调用文档：https://docs.celeryq.dev/en/stable/reference/celery.app.task.html#celery.app.task.Task.apply_async
- Celery Canvas 文档：https://docs.celeryq.dev/en/stable/tutorials/task-cookbook.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13