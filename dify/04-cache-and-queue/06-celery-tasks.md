# 4.3.2 任务定义：@shared_task 与绑定

> Celery 任务定义看似简单，但 `bind`、`max_retries`、`acks_late` 等参数决定任务的可靠性。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `@shared_task` 定义可被任意模块调用的任务
- 理解 `bind=True` 让任务能访问自身状态（重试、ID）
- 配置 `max_retries` / `acks_late` / `autoretry_for`
- 在 dify 中识别不同任务的可靠性要求

## 📚 前置知识

- Celery 基础架构（详见 [Celery 架构](./05-celery-architecture.md)）
- Python 装饰器（详见 [装饰器](../01-fundamentals/11-decorator.md)）——`@shared_task` 本质是带配置的装饰器

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
| `max_retries` | 最大重试次数（策略详见 [任务重试](./13-celery-retry.md)）|
| `default_retry_delay` | 重试间隔（秒）|
| `acks_late` | 任务执行成功后才 ack |
| `autoretry_for` | 自动重试的异常类型 |
| `retry_backoff` | 指数退避 |
| `ignore_result` | 不存结果（详见 [任务结果存储](./11-celery-result.md)）|
| `queue` | 默认队列（详见 [任务路由](./08-celery-routing.md)）|

### 1.4 acks_late：防止任务丢失

**默认行为**：Worker **拉取任务时立即 ack**（从队列删除）。如果 Worker 崩溃，任务**永久丢失**。

**`acks_late=True`**：任务**执行成功后才 ack**。Worker 崩溃时任务**重新入队**。

```python
@shared_task(acks_late=True, max_retries=3)
def important_task(x):
    # 即使 worker 崩溃，任务会重新执行
    process(x)
```

**代价**：可能重复执行（如果任务不幂等）。需要任务幂等性设计（详见 [任务幂等性设计](./12-celery-idempotency.md)）。

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

## 3. 关键要点总结

- `@shared_task` 让任务模块化（不依赖 Celery app）
- `bind=True` 任务能访问 self（重试、状态）
- **`acks_late=True` 防止任务丢失**（代价是可能重复执行）
- `autoretry_for` 自动捕获异常并重试
- `queue="..."` 分配任务到特定队列
- dify 任务按订阅级别 / 功能分队列（workflow_professional / dataset / workflow_storage）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
