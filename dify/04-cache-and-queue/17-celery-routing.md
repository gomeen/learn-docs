# 4.3.4 任务路由与队列优先级

> 多队列可以让不同优先级的任务互不干扰，是 Celery 实现 SLA 的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 Celery 任务路由（按任务名分发到不同队列）
- 用 Worker 并发控制实现资源隔离
- 理解 RabbitMQ 优先级队列 vs Redis Sorted Set
- 掌握 dify 的多队列设计（订阅级别）

## 📚 前置知识

- Celery 任务定义与调用
- 队列概念
- 14-celery-architecture.md、15-celery-tasks.md、16-celery-invoke.md

## 1. 核心概念

### 1.1 为什么需要多队列？

单队列的问题：
- **优先级缺失**：所有任务一视同仁
- **资源争抢**：重任务阻塞轻任务
- **故障扩散**：一个任务堆积影响所有任务

多队列的好处：
- **按业务隔离**：邮件、报表、数据处理互不干扰
- **按优先级**：VIP 任务优先处理
- **按资源类型**：CPU 密集 vs I/O 密集分队列

### 1.2 任务路由配置

**全局配置**：
```python
app.conf.task_routes = {
    "tasks.email.*": {"queue": "email"},
    "tasks.report.*": {"queue": "report"},
    "tasks.urgent.*": {"queue": "priority", "priority": 9},
}
```

**任务装饰器配置**（推荐）：
```python
@shared_task(queue="email", bind=True)
def send_email(self, to):
    pass
```

### 1.3 Worker 消费指定队列

```bash
# Worker 1：只处理邮件
celery worker -Q email --concurrency=4

# Worker 2：只处理报表
celery worker -Q report --concurrency=2

# Worker 3：VIP 队列（高并发）
celery worker -Q priority --concurrency=20
```

### 1.4 队列优先级

**RabbitMQ**：原生支持队列优先级（`x-max-priority`）。
**Redis**：不支持原生优先级，但可以用 Sorted Set 模拟。

dify 的"订阅级别"队列本质上是一种**业务优先级**：
- PROFESSIONAL 队列资源最多
- SANDBOX 队列资源最少

### 1.5 任务优先级（task priority）

```python
@shared_task(queue="email", bind=True)
def send_email(self, to, priority=5):
    pass

# 调用时设置
send_email.apply_async(("alice@x.com",), priority=9)  # VIP 邮件
send_email.apply_async(("bob@x.com",), priority=0)    # 普通邮件
```

**注意**：Redis Broker 实际忽略此参数（按 FIFO 处理）。

### 1.6 队列深度监控

```bash
# Redis：查看队列长度
redis-cli LLEN celery

# RabbitMQ：查看队列消息数
rabbitmqctl list_queues
```

## 2. 代码示例

### 2.1 多队列配置

```python
# celery_config.py
from celery import Celery

app = Celery("tasks", broker="redis://localhost:6379/0")

# 路由配置
app.conf.task_routes = {
    "tasks.email.*": {"queue": "email"},
    "tasks.report.*": {"queue": "report"},
    "tasks.ml.*": {"queue": "ml"},
}
```

```python
# tasks/email.py
@shared_task(queue="email")
def send_email(to, subject, body):
    smtp.send(to, subject, body)
```

```python
# tasks/report.py
@shared_task(queue="report")
def generate_report(report_id):
    data = db.query(f"SELECT * FROM reports WHERE id = {report_id}")
    # 生成 PDF...
```

### 2.2 Worker 分级

```bash
# 邮件 worker：低并发（IO 密集，gevent）
celery worker -Q email -P gevent --concurrency=50

# 报表 worker：CPU 密集，预留多进程
celery worker -Q report -P prefork --concurrency=4

# ML 推理：GPU 独占
celery worker -Q ml -P solo --concurrency=1
```

### 2.3 优先级队列（RabbitMQ）

```python
# 创建优先级队列（需 RabbitMQ 配置 x-max-priority）
app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "queue_order_strategy": "priority",
}

# 调用时设置
send_email.apply_async(
    ("vip@example.com", "Important", "Hello"),
    priority=9,  # 最高
)
```

### 2.4 任务路由动态化

```python
def route_task(name, args, kwargs, options, task_type=None, **kw):
    """根据参数动态决定队列"""
    if name == "tasks.email.send_email":
        if "vip" in args[0]:
            return {"queue": "priority"}
        return {"queue": "email"}
    return {"queue": "default"}

app.conf.task_routes = (route_task,)
```

### 2.5 常见错误：Worker 没监听对应队列

```python
# ❌ 错误：任务指定 queue="vip"，但 Worker 没启动时监听
@shared_task(queue="vip")
def vip_task():
    pass

# 启动：celery worker （没 -Q vip）
# 结果：任务堆积在 Redis，无人处理
```

## 3. dify 仓库源码解读

### 3.1 订阅级别 → 队列映射

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
**核心代码**（行 16-22、36-69）：

```python
class QueuePriority(StrEnum):
    """Queue priorities for different subscription tiers"""

    PROFESSIONAL = "workflow_professional"  # Highest priority
    TEAM = "workflow_team"
    SANDBOX = "workflow_sandbox"  # Free tier


class ProfessionalQueueDispatcher(BaseQueueDispatcher):
    @override
    def get_queue_name(self) -> str:
        return QueuePriority.PROFESSIONAL

    @override
    def get_priority(self) -> int:
        return 100


class TeamQueueDispatcher(BaseQueueDispatcher):
    @override
    def get_queue_name(self) -> str:
        return QueuePriority.TEAM

    @override
    def get_priority(self) -> int:
        return 50


class SandboxQueueDispatcher(BaseQueueDispatcher):
    @override
    def get_queue_name(self) -> str:
        return QueuePriority.SANDBOX

    @override
    def get_priority(self) -> int:
        return 10
```

**解读**：
- **Protocol 模式**：`BaseQueueDispatcher` 定义协议，不同订阅级别有不同实现
- **数字优先级**：100 / 50 / 10（虽然 Redis 忽略，但用于业务排序）
- **队列名命名**：`workflow_{level}` 便于识别

### 3.2 多任务绑定到不同队列

**文件位置**：`/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`
**核心代码**（行 53-99）：

```python
@shared_task(queue=AsyncWorkflowQueue.PROFESSIONAL_QUEUE)
def execute_workflow_professional(task_data_dict: dict[str, Any]):
    """Execute workflow for professional tier with highest priority"""
    ...

@shared_task(queue=AsyncWorkflowQueue.TEAM_QUEUE)
def execute_workflow_team(task_data_dict: dict[str, Any]):
    """Execute workflow for team tier"""
    ...

@shared_task(queue=AsyncWorkflowQueue.SANDBOX_QUEUE)
def execute_workflow_sandbox(task_data_dict: dict[str, Any]):
    """Execute workflow for free tier with lower retry limit"""
    ...
```

**解读**：
- **三个不同的 Celery 任务**绑定到三个队列
- 共享 `_execute_workflow_common` 核心逻辑
- 启动时需要分别启动 Worker（或一个 Worker 监听多队列）

### 3.3 多功能队列

**文件位置**：`/Users/xu/code/github/dify/api/tasks/`
**示例**：
- `queue="dataset"`：所有数据集相关任务（`clean_dataset_task`、`add_annotation_to_index_task`）
- `queue="workflow_storage"`：工作流存储任务
- `queue="schedule_executor"`：定时任务

**dify 的队列列表**（从 tasks 目录推断）：
| 队列 | 用途 |
|------|------|
| `workflow_professional` | 付费用户工作流 |
| `workflow_team` | 团队用户工作流 |
| `workflow_sandbox` | 免费用户工作流 |
| `dataset` | 数据集操作 |
| `workflow_storage` | 工作流存储 |
| `schedule_executor` | 定时任务 |
| `mail` | 邮件发送（部分任务）|

## 4. 关键要点总结

- 多队列实现**业务隔离 + 资源隔离**
- 任务装饰器 `queue="..."` 是最简单的路由方式
- Worker 用 `-Q queue1,queue2` 监听多个队列
- RabbitMQ 原生支持优先级，Redis 不支持
- dify 的 **3 订阅队列 + 多功能队列** 实现资源分级

## 5. 练习题

### 练习 1：基础（必做）

配置两个队列 `email` 和 `report`，分别定义任务，启动两个 Worker。

### 练习 2：进阶

实现动态路由函数 `route_task(name, args, ...)`，根据任务参数决定队列。

### 练习 3：挑战（选做）

阅读 `services/workflow/queue_dispatcher.py`，理解 `Protocol` 模式如何让队列分发可扩展（增加新订阅级别只需加一个类）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- `/Users/xu/code/github/dify/api/tasks/async_workflow_tasks.py`（第 53-99 行）
- Celery 路由文档：https://docs.celeryq.dev/en/stable/userguide/routing.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13