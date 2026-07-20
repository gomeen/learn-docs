# 4.3.6 任务结果存储与查询

> Celery 任务结果默认存 Redis / DB，dify 因为大量任务不需要结果，主动关闭结果存储。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Result Backend 的工作原理
- 掌握 `AsyncResult` 查询任务状态
- 配置 `ignore_result` 控制结果存储
- 理解 dify 为何默认关闭结果存储 + 用 trigger_log 替代

## 📚 前置知识

- Celery 基础架构（详见 [Celery 架构](./05-celery-architecture.md)）

## 1. 核心概念

### 1.1 什么是 Result Backend？

任务执行完毕后，Celery 把**返回值**存到 Backend（如 Redis，详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)），客户端可以通过 `task_id` 查询。

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

## 3. 关键要点总结

- **Result Backend** 存任务返回值到 Redis / DB
- `task_ignore_result=True` 全局关闭，dify 用此配置
- **dify 用 PostgreSQL 表**（`WorkflowTriggerLog`）跟踪任务状态
- 优势：可 join 查询、复杂状态机、事务保证
- 任务状态变更通过 `trigger_log_repo.update()` 持久化

---

**文档版本**：v1.0
**最后更新**：2026-07-13
