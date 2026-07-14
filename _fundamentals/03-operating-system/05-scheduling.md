# 3.1.5 进程调度算法

> 调度算法决定哪个进程获得 CPU，是操作系统的核心问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 FCFS、SJF、时间片轮转等调度算法
- 理解各算法的优缺点和适用场景
- 知道 Linux CFS（完全公平调度器）的设计
- 能在 dify 中识别调度的应用（Celery worker）

## 📚 前置知识

- 01-process.md

## 1. 核心概念

### 1.1 调度的目标

1. **公平**：每个进程获得合理的 CPU 时间
2. **高效**：CPU 利用率高（始终有任务执行）
3. **响应时间**：交互任务的响应快
4. **吞吐量**：单位时间完成的任务多
5. **周转时间**：任务从提交到完成的时间

### 1.2 调度算法分类

**按是否抢占**：
- **非抢占**：进程主动让出 CPU（如 FCFS、SJF）
- **抢占**：操作系统强制切换（如时间片轮转、RR）

**按应用场景**：
- **批处理**：吞吐量优先（SJF）
- **交互式**：响应时间优先（RR）
- **实时**：截止时间优先（EDF、RM）

### 1.3 FCFS（先来先服务）

**思想**：按到达顺序执行，先到先服务。

```
进程：P1(24ms), P2(3ms), P3(3ms) 到达时间都是 0

执行顺序：P1 → P2 → P3

等待时间：P1=0, P2=24, P3=27
平均等待时间：(0 + 24 + 27) / 3 = 17ms
```

**优点**：简单
**缺点**：平均等待时间长（"护航效应"：长作业卡短作业）

### 1.4 SJF（最短作业优先）

**思想**：选执行时间最短的作业。

```
进程：P1(24ms), P2(3ms), P3(3ms)

执行顺序：P2 → P3 → P1

等待时间：P2=0, P3=3, P1=6
平均：(0 + 3 + 6) / 3 = 3ms
```

**优点**：最优平均等待时间
**缺点**：
- 需要预知执行时间
- **长作业饥饿**
- **非抢占**：一旦开始就不能切换

### 1.5 时间片轮转（Round Robin, RR）

**思想**：每个进程分配时间片（如 100ms），时间片用完就切换。

```
时间片 = 4ms
进程：P1(24ms), P2(3ms), P3(3ms)

执行：P1(4) → P2(3) → P3(3) → P1(4) → P1(4) → P1(4) → P1(4) → P1(4)
```

**优点**：公平，响应时间可预测
**缺点**：
- 时间片太小：切换开销大
- 时间片太大：退化为 FCFS

### 1.6 多级反馈队列（MLFQ）

**思想**：综合 SJF 和 RR，多个队列优先级不同。

```
高优先级队列：RR（短作业快速完成）
中优先级队列：RR（中等作业）
低优先级队列：FCFS（长作业）
```

**规则**：
- 新作业进入高优先级队列
- 用完时间片降到下一级
- 长作业最终落到低优先级队列

### 1.7 Linux CFS（完全公平调度器）

**思想**：模拟"完全公平"——每个进程获得等量 CPU 时间。

**核心**：用**红黑树**管理可运行进程，按"虚拟运行时间"排序。

```
CFS 选择下一个进程：
1. 找红黑树最左节点（vruntime 最小的进程）
2. 调度它运行
3. 运行一段时间后，更新 vruntime
4. 重新插入红黑树
```

### 1.8 调度算法对比

| 算法 | 平均等待时间 | 响应时间 | 公平 | 抢占 | 适用 |
|------|-------------|---------|------|------|------|
| FCFS | 差 | 差 | ✓ | ✗ | 批处理 |
| SJF | **最优** | 差 | ✗ | ✗ | 批处理 |
| RR | 中 | **好** | ✓ | ✓ | **交互式** |
| MLFQ | 优 | 好 | ✓ | ✓ | 通用 |
| CFS | 优 | 好 | **✓✓** | ✓ | Linux |

## 2. 代码示例

### 2.1 模拟 FCFS 调度

```python
# 文件：fcfs.py
from typing import List, Tuple

def fcfs_scheduling(processes: List[Tuple[str, int]]) -> dict:
    """FCFS 调度模拟。

    processes: [(pid, burst_time), ...]
    """
    wait_time = {}
    turnaround = {}
    current_time = 0

    for pid, burst in processes:
        wait_time[pid] = current_time
        current_time += burst
        turnaround[pid] = current_time

    return {
        "wait_time": wait_time,
        "turnaround": turnaround,
        "avg_wait": sum(wait_time.values()) / len(wait_time),
    }

# 测试
processes = [("P1", 24), ("P2", 3), ("P3", 3)]
print(fcfs_scheduling(processes))
```

### 2.2 模拟 SJF 调度

```python
# 文件：sjf.py
def sjf_scheduling(processes: List[Tuple[str, int]]) -> dict:
    """SJF（非抢占）调度。"""
    # 按 burst_time 排序
    sorted_procs = sorted(processes, key=lambda p: p[1])
    return fcfs_scheduling(sorted_procs)  # 复用 FCFS

# 测试
processes = [("P1", 24), ("P2", 3), ("P3", 3)]
print(sjf_scheduling(processes))
```

### 2.3 模拟时间片轮转

```python
# 文件：rr.py
from collections import deque
from typing import List, Tuple

def rr_scheduling(
    processes: List[Tuple[str, int]],
    quantum: int = 4,
) -> dict:
    """时间片轮转调度。"""
    queue = deque(processes)
    wait_time = {pid: 0 for pid, _ in processes}
    remaining = {pid: burst for pid, burst in processes}
    arrival = {pid: 0 for pid, _ in processes}
    current_time = 0

    while queue:
        pid, burst = queue.popleft()
        if remaining[pid] <= quantum:
            # 最后一次执行
            current_time += remaining[pid]
            wait_time[pid] = current_time - burst
            remaining[pid] = 0
        else:
            # 用完时间片，重新入队
            current_time += quantum
            remaining[pid] -= quantum
            queue.append((pid, burst))

    return wait_time

# 测试
processes = [("P1", 24), ("P2", 3), ("P3", 3)]
print(rr_scheduling(processes, quantum=4))
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Celery worker 调度

**文件位置**：`/Users/xu/code/github/dify/api/tasks/celery_app.py`
**核心代码**（行 60-100）：

```python
# dify 的 Celery 配置（celery_config.py）

# 任务调度策略
task_routes = {
    "tasks.workflow.run_workflow_task": {"queue": "workflow"},
    "tasks.documents.process_document_task": {"queue": "documents"},
    "tasks.rag.generate_embedding_task": {"queue": "rag"},
}

# 不同队列用不同的 worker 数量
# 类似 MLFQ 的思想：优先级队列

worker_prefetch_multiplier = 1  # 公平调度：一次只取一个任务
worker_max_tasks_per_child = 100  # 处理 100 个任务后重启（避免内存泄漏）

# 调度流程（类似 RR）：
# 1. worker 从 Redis 队列取任务
# 2. 执行任务（时间片 = 任务执行时间）
# 3. 写回结果
# 4. 取下一个任务

# dify 的实际队列：
# - workflow 队列：高优先级（用户实时请求）
# - documents 队列：中优先级（异步处理）
# - rag 队列：低优先级（批量处理）

# 类似 MLFQ：
# - workflow → 立即处理
# - documents → 等待几秒
# - rag → 攒批处理
```

**解读**：
- 第 11 行：路由配置，不同任务到不同队列（MLFQ 思想）
- 第 16 行：`worker_prefetch_multiplier = 1`：公平调度（RR）
- 第 17 行：`worker_max_tasks_per_child`：避免内存泄漏
- **设计意图**：用 Celery 的多队列机制实现类似 MLFQ 的优先级调度

## 4. 关键要点总结

- **FCFS**：简单但可能"护航"
- **SJF**：最优平均等待，但需预知时间
- **RR**：公平，适合交互式系统
- **MLFQ**：综合 SJF 和 RR，多级队列
- **CFS**：Linux 用红黑树实现"完全公平"
- dify 用 Celery 多队列实现类似 MLFQ

## 5. 练习题

### 练习 1：基础（必做）

模拟 FCFS、SJF、RR 调度，比较三个进程在不同算法下的平均等待时间。

### 练习 2：进阶

阅读 `api/tasks/celery_app.py`，说明 dify 的 Celery 调度与 RR、MLFQ 的相似之处。

### 练习 3：挑战（选做）

实现 MLFQ：3 个优先级队列，时间片分别为 8ms、16ms、32ms，模拟调度过程。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/celery_app.py`
- 《操作系统概念》第 5 章 进程调度
- Linux CFS：https://www.kernel.org/doc/html/latest/scheduler/sched-design-CFS.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13