# 7.6.3 任务分发与负载均衡

> 掌握多 Agent 系统中的任务分发策略：轮询、加权、动态负载均衡。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述常见的任务分发策略
- 实现轮询、加权、最少连接等分发算法
- 理解 dify 工作流中的任务分发
- 区分同步分发和异步分发

## 📚 前置知识

- [多 Agent](./32-multi-agent.md)
- [Agent 间通信](./33-agent-communication.md)
- Celery 任务队列（详见 [Celery 架构](../04-cache-and-queue/14-celery-architecture.md)、[任务路由](../04-cache-and-queue/17-celery-routing.md)）
- Python 异步（详见 [async/asyncio](../01-fundamentals/12-async-asyncio.md)）

## 1. 核心概念

### 1.1 任务分发的常见策略

| 策略 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **轮询（Round Robin）** | 依次分配 | 简单 | 不考虑负载 |
| **加权轮询** | 按权重分配 | 考虑能力 | 权重难调 |
| **最少连接** | 分给当前任务最少的 | 动态均衡 | 状态同步成本 |
| **随机** | 随机分 | 简单 | 可能不均 |
| **能力匹配** | 按任务需求匹配 | 精确 | 调度复杂 |

### 1.2 同步 vs 异步分发

- **同步分发**：分发后等待结果（简单）
- **异步分发**：分发后立即返回，通过回调/消息队列获取结果（高效）

### 1.3 dify 中的任务分发

dify 的工作流是**确定性的任务分发**：
- 用户编排时确定每个节点的后继
- 引擎按拓扑顺序执行
- 没有动态负载均衡

但 Celery 任务队列层有负载均衡（多个 worker 抢任务；详见 [Celery 架构](../04-cache-and-queue/14-celery-architecture.md)、[任务路由](../04-cache-and-queue/17-celery-routing.md)）。

## 2. 代码示例

### 2.1 轮询分发

```python
class RoundRobinDispatcher:
    def __init__(self, workers: list):
        self.workers = workers
        self.index = 0

    def dispatch(self, task: dict):
        worker = self.workers[self.index % len(self.workers)]
        self.index += 1
        return worker.handle(task)
```

### 2.2 加权分发

```python
class WeightedDispatcher:
    def __init__(self, workers: list, weights: list):
        """workers: [w1, w2, w3], weights: [3, 2, 1] 表示 w1 处理 50%, w2 处理 33%, w3 处理 17%"""
        self.workers = workers
        self.weights = weights
        self.index = 0

    def dispatch(self, task: dict):
        worker = self.workers[self.index % len(self.workers)]
        # 推进 index，直到该 worker 用尽权重
        worker_weight = self.weights[self.workers.index(worker)]
        for _ in range(worker_weight):
            self.index += 1
        return worker.handle(task)


# 测试：每 6 次任务，w1 处理 3 次，w2 处理 2 次，w3 处理 1 次
dispatcher = WeightedDispatcher(["w1", "w2", "w3"], [3, 2, 1])
```

### 2.3 最少连接（最少任务）分发

```python
class LeastLoadedDispatcher:
    def __init__(self, workers: list):
        self.workers = workers
        self.task_counts = {w: 0 for w in workers}

    def dispatch(self, task: dict):
        # 选当前任务最少的 worker
        worker = min(self.task_counts, key=self.task_counts.get)
        self.task_counts[worker] += 1

        try:
            result = worker.handle(task)
        finally:
            self.task_counts[worker] -= 1

        return result
```

### 2.4 异步分发（基于 asyncio）

```python
import asyncio
from typing import Awaitable, Callable


class AsyncDispatcher:
    """异步分发：分发后不等结果"""

    def __init__(self, workers: list):
        self.workers = workers
        self.queue = asyncio.Queue()

    async def dispatch(self, task: dict):
        """立即分发，返回 Future"""
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((task, future))
        return await future

    async def _worker_loop(self, worker):
        """每个 worker 一个循环"""
        while True:
            task, future = await self.queue.get()
            try:
                result = await worker.handle(task)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
```

### 2.5 常见错误：分发后状态不一致

```python
# ❌ 错误：分发后没等 worker 处理完就更新状态
def dispatch(self, task):
    worker = self._select_worker(task)
    worker.handle_async(task)  # 异步执行
    self._update_stats(worker)  # 立即更新，可能不准确

# ✅ 正确：worker 处理完后再更新状态
def dispatch(self, task):
    worker = self._select_worker(task)
    result = worker.handle(task)  # 同步等结果
    self._update_stats(worker)
    return result
```

## 3. dify 仓库源码解读

### 3.1 Celery 任务分发

**文件位置**：`/Users/xu/code/github/dify/api/tasks/workflow.py`（节选）
**核心代码**（示意）：

```python
from celery import shared_task


@shared_task(queue="workflow")
def run_workflow_task(tenant_id, workflow_id, user_id, inputs):
    """Celery 任务：异步执行工作流"""
    # Celery worker 进程会执行这个函数
    # 多个 worker 进程会从队列中抢任务
    from services.async_workflow_service import AsyncWorkflowService
    service = AsyncWorkflowService()
    return service.trigger_workflow_async(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        user_id=user_id,
        inputs=inputs,
    )
```

**解读**：
- dify 用 Celery 做异步任务分发
- 多个 worker 进程从 Redis 队列中抢任务（自然负载均衡）
- `@shared_task(queue="workflow")` 指定队列名，便于隔离

### 3.2 异步工作流服务

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（节选）：

```python
class AsyncWorkflowService:
    """异步工作流服务"""

    async def trigger_workflow_async(
        self,
        tenant_id: str,
        workflow_id: str,
        user: Account,
        inputs: dict[str, Any],
    ) -> str:
        """触发工作流执行，立即返回 run_id"""
        # 1. 同步检查前置条件
        with Session(db.engine, expire_on_commit=False) as session:
            workflow = session.query(Workflow).filter_by(...).first()

        # 2. 提交到 Celery
        run_id = run_workflow_task.delay(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            user_id=user.id,
            inputs=inputs,
        )

        return str(run_id)
```

**解读**：
- API 层用 `task.delay()` 把任务推给 Celery
- Celery 自动负载均衡到空闲的 worker
- API 立即返回 `run_id`，客户端可轮询查询状态

## 4. 关键要点总结

- 任务分发策略：轮询 / 加权 / 最少连接 / 能力匹配
- 异步分发用 Celery（dify 的实现）
- 同步分发简单但阻塞，异步分发高效但复杂
- dify 在 API 层用 Celery 做任务分发，工作流内部按 DSL 静态执行

## 5. 练习题

### 练习 1：基础（必做）

实现一个 RoundRobinDispatcher，分配 10 个任务到 3 个 worker，统计每个 worker 收到的任务数。

### 练习 2：进阶

实现一个 LeastLoadedDispatcher，每个 worker 处理时间不同（用 asyncio.sleep 模拟），观察分发是否均衡。

### 练习 3：挑战（选做）

设计实验：对比 Celery 多 worker 与单 worker 的吞吐量。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- `/Users/xu/code/github/dify/api/tasks/workflow.py`
- Celery 官方文档：https://docs.celeryq.dev/

---

**文档版本**：v1.0
**最后更新**：2026-07-13