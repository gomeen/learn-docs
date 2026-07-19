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
- **可靠性**：任务持久化（不丢）+ 重试机制（详见 [任务重试与死信队列](./21-celery-retry.md)）

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
| **Backend** | 存储任务结果（Redis / DB；详见 [任务结果存储](./19-celery-result.md)）|
| **Beat** | 定时任务调度器（可选；详见 [Celery Beat](./18-celery-beat.md)）|

### 1.3 任务生命周期

```python
# 1. 定义任务（@shared_task 是装饰器，详见 [装饰器](../01-fundamentals/10-decorator.md)；任务参数详见 [任务定义](./15-celery-tasks.md)）
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

> 📌 **Sighting**：进程 / 线程 / 协程等并发模型对比见 [并发模型](../01-fundamentals/23-concurrency.md)；此处只说明 dify Worker 选用 gevent 的原因。

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

> 定时调度细节（crontab / 高可用）见 [Celery Beat](./18-celery-beat.md)。

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

> 路由与优先级完整配置见 [任务路由](./17-celery-routing.md)。

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

## 3. dify 仓库源码解读

### 3.1 Celery 初始化入口

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 99-128）：

```python
def init_app(app: DifyApp) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            from core.logging.context import init_request_context

            with app.app_context():
                # Initialize logging context for this task (similar to before_request in Flask)
                init_request_context()
                return self.run(*args, **kwargs)

    broker_transport_options = get_celery_broker_transport_options()

    celery_app = Celery(
        app.name,
        task_cls=FlaskTask,
        broker=dify_config.CELERY_BROKER_URL,
        backend=dify_config.CELERY_RESULT_BACKEND,
    )

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
- **第 100-107 行**：自定义 `FlaskTask` 让 Celery 任务能访问 Flask 的 `app_context`（用于数据库连接、配置读取）
- **第 109 行**：`broker_transport_options` 配置 Sentinel 支持
- **第 121 行**：`broker_connection_retry_on_startup=True` 启动时 Redis 没起来也能重试
- **第 126 行**：`task_ignore_result=True` 默认不存任务结果（节省 Redis 空间，需要结果时显式 `ignore_result=False`）

### 3.2 gevent 模式启动

**文件位置**：`/Users/xu/code/github/dify/api/celery_entrypoint.py`
**核心代码**（行 1-13）：

```python
import psycogreen.gevent as pscycogreen_gevent
from grpc.experimental import gevent as grpc_gevent

# grpc gevent
grpc_gevent.init_gevent()
print("gRPC patched with gevent.", flush=True)  # noqa: T201
pscycogreen_gevent.patch_psycopg()
print("psycopg2 patched with gevent.", flush=True)  # noqa: T201


from app import app, celery

__all__ = ["app", "celery"]
```

**解读**：
- dify 的 Celery 用 **gevent 协程**（不是默认的 prefork 多进程）
- **`pscycogreen_gevent`**：让 psycopg2（PostgreSQL 驱动）变成非阻塞
- **`grpc_gevent`**：让 gRPC 调用变成非阻塞
- **原因**：dify 大量调用 LLM API（I/O 密集），gevent 可以用单进程处理数千并发
- 启动命令：
  ```bash
  celery -A celery_entrypoint.celery worker -P gevent --concurrency=100
  ```

### 3.3 任务导入列表

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 153-159）：

```python
imports = [
    "tasks.async_workflow_tasks",  # trigger workers
    "tasks.trigger_processing_tasks",  # async trigger processing
    "tasks.generate_summary_index_task",  # summary index generation
    "tasks.regenerate_summary_index_task",  # summary index regeneration
    "tasks.app_generate.resume_agent_app_task",  # ENG-635: Agent v2 chat ask_human resume
]
```

**解读**：
- Celery 需要显式 import 所有任务模块才能注册
- dify 的核心任务：
  - `async_workflow_tasks`：异步工作流执行（按订阅级别分队列）
  - `trigger_processing_tasks`：触发器处理
  - `generate_summary_index_task`：生成摘要索引
  - `resume_agent_app_task`：Agent 恢复执行
- **新加任务必须加到这个列表**

## 4. 关键要点总结

- Celery 四大组件：Producer / Broker / Worker / Backend（+ Beat 定时）
- dify 用 **gevent 协程**而不是 prefork 多进程，适合 I/O 密集场景
- 必须显式 import 任务模块才会注册
- `FlaskTask` 让 Celery 能用 Flask 的 app_context
- `task_ignore_result=True` 节省 Redis 空间

## 5. 练习题

### 练习 1：基础（必做）

写一个最简单的 Celery 应用：
- 一个 `add(x, y)` 任务
- 用 redis 作为 broker
- 启动 worker 并测试 `add.delay(3, 5).get()`

### 练习 2：进阶

实现多队列路由：
- `tasks.email.send_email` → email 队列
- `tasks.report.generate` → report 队列
- 启动两个 worker，分别监听不同队列

### 练习 3：挑战（选做）

阅读 `extensions/ext_celery.py` 的 Beat schedule 配置，理解 dify 有哪些定时任务（如 `clean_embedding_cache_task`），并思考它们为什么要在凌晨跑。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`（第 99-159 行）
- `/Users/xu/code/github/dify/api/celery_entrypoint.py`
- Celery 官方文档：https://docs.celeryq.dev/
- Celery 入门教程：https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13