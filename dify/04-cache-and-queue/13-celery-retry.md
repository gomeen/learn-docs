# 4.3.8 任务重试与死信队列

> 任务失败时合理重试可提高成功率，过多重试会造成死信堆积。理解重试策略与死信处理是构建可靠系统的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 Celery 任务的重试（`retry` / `autoretry_for`）
- 设计指数退避策略
- 实现死信队列处理永久失败的任务
- 理解 dify 任务的重试策略

## 📚 前置知识

- Celery 任务定义与调用（详见 [任务定义](./06-celery-tasks.md)）
- 异常处理基础（详见 [异常](../01-fundamentals/06-python-exceptions.md)）
- 任务幂等性（详见 [任务幂等性设计](./12-celery-idempotency.md)）——重试会放大重复执行风险

## 1. 核心概念

### 1.1 为什么需要重试？

外部依赖**不稳定**：
- 网络抖动（API 调用失败）
- 临时资源不足（DB 连接池满）
- 服务临时不可用（第三方 API 限流，详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）

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

> 📌 **Sighting**：死信队列（DLQ）与通用消息重试语义见 [死信队列与重试机制](../../_common/02-mq/06-dead-letter.md)；下文聚焦 Celery 侧配置。

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

## 3. 关键要点总结

- 智能重试提升成功率（指数退避 + 抖动）
- **区分可重试错误**（临时）和**不可重试错误**（业务）
- Celery 没有原生 DLQ，需要自己实现
- dify 工作流**不自动重试**，需要主动调用 `reinvoke_trigger()`
- **超时即终止**：防止无限占用资源
- `max_retries=3` + `default_retry_delay=60` 是 dify 的标准重试配置

---

**文档版本**：v1.0
**最后更新**：2026-07-13
