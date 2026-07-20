# 4.3.1 Celery 架构：Broker / Worker / Beat / Result Backend

> Celery 是 Python 生态最流行的分布式任务队列，dify 用它处理所有异步任务。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Celery 的四大组件（Broker / Worker / Beat / Backend）
- 掌握任务的完整生命周期
- 配置多队列、并发和路由
- 理解 dify 的 Celery 启动方式（gevent 协程）

## 📚 前置知识

- Python 基础
- 消息队列概念（详见 [MQ 核心概念](../../_common/02-mq/01-concepts.md)）
- Redis 基础（作为 Broker；详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）

## 1. 核心概念

### 1.1 什么是 Celery？

Celery 是**分布式任务队列**，核心思想：
- **异步执行**：API 立即返回，任务在后台跑
- **分布式**：多个 Worker 并行处理
- **可靠性**：任务持久化（不丢）+ 重试机制（详见 [任务重试与死信队列](./13-celery-retry.md)）

### 1.2 四大组件

```
┌─────────┐    提交任务    ┌─────────┐    派发    ┌─────────┐
│ Producer │ ────────────→ │ Broker  │ ────────→ │ Worker  │
│ (App)   │              │ (Redis) │           │ (执行)  │
└─────────┘              └─────────┘           └────┬────┘
                                                    │
                                                    ↓ 存结果
                                              ┌──────────┐
                                              │ Backend  │
                                              │ (Redis)  │
                                              └──────────┘

Beat（定时调度） ──→ Broker ──→ Worker
```

| 组件 | 职责 |
|------|------|
| **Producer** | 发起任务（应用代码）|
| **Broker** | 任务队列（Redis / RabbitMQ；RabbitMQ 详见 [RabbitMQ](../../_common/02-mq/03-rabbitmq.md)）|
| **Worker** | 执行任务（多个进程）|
| **Backend** | 存储任务结果（Redis / DB；详见 [任务结果存储](./11-celery-result.md)）|
| **Beat** | 定时任务调度器（可选；详见 [Celery Beat](./09-celery-beat.md)）|

### 1.3 任务生命周期

```python
# 1. 定义任务（@shared_task 是装饰器，详见 [装饰器](../01-fundamentals/11-decorator.md)；任务参数详见 [任务定义](./06-celery-tasks.md)）
@shared_task
def add(x, y):
    return x + y

# 2. 提交任务（Producer）
result = add.delay(3, 5)  # 异步，立即返回 AsyncResult

# 3. Broker 接收任务（Redis 列表 push）
# 4. Worker 拉取任务（BRPOP）
# 5. Worker 执行任务
# 6. Worker 存结果到 Backend

# 7. 查询结果
print(result.get(timeout=10))  # 8
```

### 1.4 gevent 并发模式

> 📌 **Sighting**：进程 / 线程 / 协程等并发模型对比见 [并发模型](../01-fundamentals/30-concurrency.md)；此处只说明 dify Worker 选用 gevent 的原因。

dify 用 **gevent** 协程而不是多进程：

```python
# celery_entrypoint.py
import psycogreen.gevent as pscycogreen_gevent
from grpc.experimental import gevent as grpc_gevent

grpc_gevent.init_gevent()
pscycogreen_gevent.patch_psycopg()
```

**优势**：单进程处理上千并发任务，**内存占用小**。
**注意**：所有阻塞 I/O 必须用 gevent 兼容的库（pymysql、psycopg2、requests 不行，要用 gevent 打过补丁的版本）。

### 1.5 Worker 并发模式对比

| 模式 | 启动方式 | 并发 | 内存 | 适用 |
|------|---------|------|------|------|
| prefork | `--pool=prefork --concurrency=4` | 多进程 | 高 | CPU 密集 |
| gevent | `--pool=gevent --concurrency=100` | 协程 | 低 | I/O 密集 |
| solo | `--pool=solo` | 单线程 | 低 | 调试 |

## 2. 代码示例

### 2.1 最简单的 Celery 应用

```python
# tasks.py
from celery import Celery

app = Celery("tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

@app.task
def add(x, y):
    return x + y

# 调用
from tasks import add
result = add.delay(3, 5)
print(result.get(timeout=5))  # 8
```

### 2.2 启动 Worker

```bash
# 默认 prefork 模式，CPU 核数并发
celery -A tasks worker --loglevel=info

# 指定并发数
celery -A tasks worker --concurrency=4

# gevent 模式（I/O 密集）
celery -A tasks worker --pool=gevent --concurrency=100

# 指定队列
celery -A tasks worker -Q dataset,workflow
```

### 2.3 启动 Beat 定时任务

> 定时调度细节（crontab / 高可用）见 [Celery Beat](./09-celery-beat.md)。

```bash
# Beat 调度器（独立进程）
celery -A tasks beat --loglevel=info

# 配置文件
app.conf.beat_schedule = {
    "cleanup-every-hour": {
        "task": "tasks.cleanup",
        "schedule": 3600.0,  # 每小时
    },
}
```

### 2.4 多队列路由

> 路由与优先级完整配置见 [任务路由](./08-celery-routing.md)。

```python
app.conf.task_routes = {
    "tasks.email.*": {"queue": "email"},
    "tasks.heavy.*": {"queue": "heavy"},
}
```

```bash
# 不同队列不同 worker
celery -A tasks worker -Q email --concurrency=4
celery -A tasks worker -Q heavy --concurrency=2
```

### 2.5 常见错误：任务结果不存

```python
# 默认 task_ignore_result=True，结果不存到 Backend
result = add.delay(3, 5)
print(result.get())  # 超时！因为 Backend 没存

# 解决：要么改配置 task_ignore_result=False，要么任务返回 None
@shared_task(ignore_result=True)
def add(x, y):
    return x + y
```

## 3. 关键要点总结

- Celery 四大组件：Producer / Broker / Worker / Backend（+ Beat 定时）
- dify 用 **gevent 协程**而不是 prefork 多进程，适合 I/O 密集场景
- 必须显式 import 任务模块才会注册
- `FlaskTask` 让 Celery 能用 Flask 的 app_context
- `task_ignore_result=True` 节省 Redis 空间

---

**文档版本**：v1.0
**最后更新**：2026-07-13
