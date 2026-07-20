# 4.3.3 任务调用：delay / apply_async / 任务签名

> Celery 任务调用方式有多种：`delay()` 简单快捷，`apply_async()` 功能丰富，签名（Signature）支持复杂编排。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `delay()` / `apply_async()` / 任务签名
- 用 `apply_async` 设置延迟执行、优先级、ETA
- 用 canvas（chain / group / chord）编排任务
- 理解 dify 的 `task.delay(...)` 调用方式

## 📚 前置知识

- Celery 任务定义（详见 [任务定义](./06-celery-tasks.md)）
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

## 3. 关键要点总结

- `delay()` 是 `apply_async()` 的快捷方式
- `apply_async()` 支持 countdown / eta / queue / priority
- **任务签名**支持 chain / group / chord 编排
- 复杂对象必须先转 dict（`model_dump(mode="json")`）
- dify 用 **3 个订阅队列**（PROFESSIONAL / TEAM / SANDBOX）
- **配额扣费与任务提交原子化**（失败时 refund）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
