# 3.1.1 进程基础与进程控制块（PCB）

> 进程是操作系统资源分配的基本单位，理解进程才能理解并发。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解进程的定义和与程序的区别
- 掌握 PCB（进程控制块）的核心字段
- 了解进程的生命周期（创建、就绪、运行、阻塞、退出）
- 能在 dify 中识别进程的应用（Celery worker）

## 📚 前置知识

- 计算机基础

## 1. 核心概念

### 1.1 进程 vs 程序

- **程序**：存储在磁盘上的可执行文件（静态）
- **进程**：程序的一次执行实例（动态）

```
程序：foo.py（一个文件）
进程：python foo.py → 操作系统创建一个进程实例
多次执行：每次都是新的进程（独立的地址空间）
```

### 1.2 进程的特征

1. **动态性**：进程有生命周期
2. **并发性**：多个进程可同时执行
3. **独立性**：每个进程有独立的地址空间
4. **异步性**：进程执行走走停停

### 1.3 进程控制块（PCB）

PCB 是进程存在的**唯一标识**，存储在操作系统内核中。

**关键字段**：

| 字段 | 说明 |
|------|------|
| PID | 进程唯一标识 |
| 状态 | 就绪/运行/阻塞/退出 |
| 程序计数器 | 下一条指令地址 |
| 寄存器 | CPU 上下文 |
| 内存指针 | 代码段、数据段、堆栈 |
| 打开的文件 | fd 列表 |
| 调度信息 | 优先级、时间片 |
| 父子关系 | 父进程 PID |

### 1.4 进程的五状态模型

```
            创建
             ↓
        ┌──── 就绪 ────┐
        │      ↑       │
   调度  │      │ 时间片
        ↓      │ 到期
        运行 ───┘
        │  ↓
   I/O请求  系统调用
        ↓
        阻塞 ──→ I/O 完成 ──→ 就绪
        │
        ↓ 终止
        退出
```

### 1.5 进程的创建

**Linux 创建进程的系统调用**：
- `fork()`：复制当前进程（子进程是父进程的副本）
- `exec()`：替换当前进程的代码
- `clone()`：更灵活的创建（用于线程）

### 1.6 进程的内存布局

```
高地址
   ↓
  ┌─────────────────┐
  │ 内核空间          │  ← 操作系统
  ├─────────────────┤
  │ 栈（Stack）       │  ← 局部变量、函数调用（向下增长）
  ├─────────────────┤
  │ 堆（Heap）        │  ← malloc / new（向上增长）
  ├─────────────────┤
  │ BSS 段           │  ← 未初始化全局变量
  ├─────────────────┤
  │ 数据段（Data）    │  ← 已初始化全局变量
  ├─────────────────┤
  │ 代码段（Text）    │  ← 程序代码（只读）
  └─────────────────┘
低地址
```

## 2. 代码示例

### 2.1 Python 创建子进程

```python
# 文件：process_demo.py
import os
import time

print(f"父进程 PID: {os.getpid()}")

# fork 创建子进程（仅 Unix）
pid = os.fork()
if pid == 0:
    # 子进程
    print(f"子进程 PID: {os.getpid()}, 父进程 PID: {os.getppid()}")
    time.sleep(1)
    print("子进程退出")
else:
    # 父进程
    print(f"父进程创建了子进程: {pid}")
    os.waitpid(pid, 0)  # 等待子进程结束
    print("父进程退出")
```

### 2.2 multiprocessing 模块

```python
# 文件：multiprocessing_demo.py
import multiprocessing
import time

def worker(name: str, duration: int) -> None:
    print(f"Worker {name} 开始 (PID: {multiprocessing.current_process().pid})")
    time.sleep(duration)
    print(f"Worker {name} 结束")

if __name__ == "__main__":
    # 创建两个进程
    p1 = multiprocessing.Process(target=worker, args=("A", 2))
    p2 = multiprocessing.Process(target=worker, args=("B", 3))

    p1.start()
    p2.start()

    print(f"主进程 PID: {multiprocessing.current_process().pid}")

    p1.join()  # 等待 p1 结束
    p2.join()  # 等待 p2 结束

    print("所有 worker 完成")
```

### 2.3 用 ps 查看进程

```python
# 文件：process_info.py
import os
import psutil

def get_process_info(pid: int) -> dict:
    """获取进程信息。"""
    try:
        p = psutil.Process(pid)
        return {
            "pid": p.pid,
            "name": p.name(),
            "status": p.status(),
            "create_time": p.create_time(),
            "memory_mb": p.memory_info().rss / 1024 / 1024,
            "cpu_percent": p.cpu_percent(),
            "num_threads": p.num_threads(),
        }
    except psutil.NoSuchProcess:
        return {}

# 当前进程信息
info = get_process_info(os.getpid())
print(info)
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Celery worker（多进程）

**文件位置**：`/Users/xu/code/github/dify/api/celery_entrypoint.py`
**核心代码**（行 1-50）：

```python
import os
import sys

from celery import Celery

# 创建 Celery app
app = Celery("dify")

# 从配置文件读取 broker 和 backend
app.config_from_object("celery_config")

# 自动发现 tasks 模块
app.autodiscover_tasks(["tasks"])

# Celery worker 启动入口
# 实际命令：celery -A celery_entrypoint worker --loglevel=info

# dify 用 Celery 的多进程机制：
# - 启动时创建 N 个 worker 进程（每个 worker 是独立的 OS 进程）
# - 每个 worker 处理一个任务，互不干扰
# - 通过 Redis broker 通信
# - 通过数据库 backend 存储结果

# 进程间通信（IPC）方式（详见 [03-ipc](./03-ipc.md)）：
# 1. Redis pub/sub：任务分发
# 2. PostgreSQL：结果存储
# 3. 信号：进程控制（如优雅退出）

# 进程生命周期：
# 1. celery worker 命令启动进程
# 2. 进程连接 Redis，等待任务
# 3. 收到任务 → fork 子进程执行
# 4. 子进程返回结果 → 写回 Redis
# 5. 重复 3-4 直到收到 SIGTERM
```

**解读**：
- 第 13 行：`autodiscover_tasks` 自动加载所有任务
- **Celery worker 是多进程**：每个 worker 进程独立处理任务
- **进程间通信**：用 Redis pub/sub（任务分发）+ PG（结果存储）
- **设计意图**：用多进程模型隔离任务失败（一个 worker 崩溃不影响其他）

## 4. 关键要点总结

- 进程 = 程序的一次执行，有独立的地址空间
- **PCB**：进程控制块，存储进程所有信息
- 五状态：创建、就绪、运行、阻塞、退出
- 创建：`fork` / `exec` / `clone`
- 内存布局：代码段、数据段、堆、栈
- dify 用 Celery 多进程处理后台任务

## 5. 练习题

### 练习 1：基础（必做）

用 `multiprocessing` 创建两个子进程，每个子进程打印自己的 PID 和父进程 PID。验证父子进程关系。

### 练习 2：进阶

阅读 `api/celery_entrypoint.py`，说明 dify 为何用 Celery 多进程而不是线程处理任务（提示：GIL、隔离性）。

### 练习 3：挑战（选做）

用 Python 实现一个简单的进程监控工具：每秒打印当前进程的 CPU 使用率、内存占用、线程数。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/celery_entrypoint.py`
- 《操作系统概念》第 3 章 进程
- Linux `ps`、`top`、`/proc` 文件系统

---

**文档版本**：v1.0
**最后更新**：2026-07-13