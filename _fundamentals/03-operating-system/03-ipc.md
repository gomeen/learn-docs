# 3.1.3 进程间通信（IPC）

> 进程间通信（IPC）是分布式系统、微服务架构的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 5 种 IPC 方式：管道、消息队列、共享内存、信号量、Socket
- 理解每种方式的优缺点和适用场景
- 能在 dify 中识别 IPC 的应用（Celery + Redis、HTTP API）

## 📚 前置知识

- 01-process.md
- 02-thread.md

## 1. 核心概念

### 1.1 为什么需要 IPC？

进程有**独立的地址空间**，不能直接访问对方内存。需要操作系统提供 IPC 机制。

### 1.2 IPC 五大方式

```
进程 A ←→ 进程 B
   ↓ 通信机制 ↓
1. 管道（Pipe）
2. 消息队列（Message Queue）
3. 共享内存（Shared Memory）
4. 信号量（Semaphore）
5. Socket
```

### 1.3 管道（Pipe）

**匿名管道**：
- 父子进程专用
- 半双工（一端读，一端写）
- `pipe()` 系统调用

**命名管道（FIFO）**：
- 可用于无亲缘关系进程
- 文件系统中的一个特殊文件
- `mkfifo` 命令

```
父进程
  │
  ├──→ 管道 → 子进程
```

### 1.4 消息队列（Message Queue）

**原理**：内核维护一个消息链表，进程通过 `msgsnd`/`msgrcv` 读写。

```
进程 A → msgsnd → 内核消息队列 → msgrcv → 进程 B
```

**特点**：
- 独立于进程生命周期
- 支持多对多通信
- 有消息格式（type + data）
- **应用**：System V IPC、POSIX 消息队列

**生产级应用**：RabbitMQ、Kafka、Redis Stream

### 1.5 共享内存（Shared Memory）

**原理**：多个进程映射同一块物理内存，访问速度最快。

```
进程 A  地址空间
   ├── 代码段
   ├── 数据段
   └── 共享内存段 ←────→ 进程 B  地址空间
                            ├── 代码段
                            ├── 数据段
                            └── 共享内存段
```

**特点**：
- **最快**的 IPC（无内核参与）
- 需要**同步**（信号量）防止竞态

### 1.6 信号量（Semaphore）

**原理**：计数器，控制对共享资源的访问。

```
P 操作（wait）：sem--，若 < 0 则阻塞
V 操作（signal）：sem++，若 ≤ 0 则唤醒等待者
```

**应用**：
- 互斥（sem=1）
- 同步（生产者-消费者）
- 资源计数（sem=N 表示有 N 个资源）

### 1.7 Socket

**原理**：网络接口，可用于**不同主机**的进程通信。

```
进程 A ←→ Socket ←→ TCP/UDP ←→ Socket ←→ 进程 B
```

**类型**：
- **Stream Socket**（TCP）：面向连接、可靠
- **Datagram Socket**（UDP）：无连接、不可靠
- **Unix Domain Socket**：本机进程间，性能更好

### 1.8 IPC 对比

| 方式 | 速度 | 跨主机 | 复杂度 | 适用场景 |
|------|------|--------|--------|----------|
| 管道 | 中 | ✗ | 低 | 父子进程 |
| 消息队列 | 中 | ✗ | 中 | 结构化消息 |
| 共享内存 | **最快** | ✗ | **高** | 大数据共享 |
| 信号量 | - | ✗ | 中 | 同步控制 |
| Socket | 中 | **✓** | 中 | **分布式** |

## 2. 代码示例

### 2.1 Python 管道（multiprocessing）

```python
# 文件：pipe_demo.py
from multiprocessing import Process, Pipe

def sender(conn):
    """发送方。"""
    conn.send("Hello from sender")
    conn.send([1, 2, 3])
    conn.close()

def receiver(conn):
    """接收方。"""
    print(f"收到: {conn.recv()}")
    print(f"收到: {conn.recv()}")
    conn.close()

if __name__ == "__main__":
    parent_conn, child_conn = Pipe()
    p1 = Process(target=sender, args=(child_conn,))
    p2 = Process(target=receiver, args=(parent_conn,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
```

### 2.2 Python 队列（Queue）

```python
# 文件：queue_demo.py
import multiprocessing
import time

def producer(queue):
    for i in range(5):
        queue.put(f"item-{i}")
        time.sleep(0.1)
    queue.put(None)  # 哨兵

def consumer(queue):
    while True:
        item = queue.get()
        if item is None:
            break
        print(f"消费: {item}")

if __name__ == "__main__":
    q = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=producer, args=(q,))
    p2 = multiprocessing.Process(target=consumer, args=(q,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
```

### 2.3 Socket 通信

```python
# 文件：socket_demo.py
import socket
import threading

# 服务端
def server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 9999))
    s.listen(1)
    print("服务端等待连接...")
    conn, addr = s.accept()
    print(f"连接来自: {addr}")
    data = conn.recv(1024)
    print(f"收到: {data.decode()}")
    conn.send(b"Hello from server")
    conn.close()

# 客户端
def client():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 9999))
    s.send(b"Hello from client")
    data = s.recv(1024)
    print(f"客户端收到: {data.decode()}")
    s.close()

if __name__ == "__main__":
    t = threading.Thread(target=server)
    t.start()
    time.sleep(0.5)
    client()
    t.join()
```

### 2.4 共享内存（multiprocessing）

```python
# 文件：shared_memory_demo.py
from multiprocessing import Process, Value, Array

def increment_counter(counter):
    for _ in range(1000):
        with counter.get_lock():  # 需要锁
            counter.value += 1

if __name__ == "__main__":
    counter = Value('i', 0)  # 共享整数
    arr = Array('i', [0] * 5)  # 共享数组

    processes = []
    for _ in range(10):
        p = Process(target=increment_counter, args=(counter,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print(f"counter = {counter.value}")  # 应该是 10000
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Celery + Redis IPC

**文件位置**：`/Users/xu/code/github/dify/api/tasks/celery_app.py`
**核心代码**（行 1-50）：

```python
from celery import Celery

# 创建 Celery app
# broker 和 backend 都是 Redis（一种 IPC 机制）
app = Celery(
    "dify",
    broker="redis://localhost:6379/0",  # 消息 broker（任务分发）
    backend="redis://localhost:6379/1",  # 结果 backend（结果存储）
)

# Redis 充当进程间通信的"中间人"：
# 1. 进程 A（API）发布任务到 Redis
# 2. 进程 B（worker）从 Redis 订阅任务
# 3. 进程 B 处理任务，结果写回 Redis
# 4. 进程 A 从 Redis 读取结果

# 这种 IPC 模型：
# - 解耦生产者和消费者
# - 支持跨主机（worker 可以部署在不同机器）
# - 持久化（任务不会丢失）

# dify 的任务流：
@app.task(bind=True, max_retries=3)
def run_workflow_task(self, workflow_run_id: str, ...):
    """工作流执行任务。"""
    try:
        # 1. 加载工作流
        workflow = load_workflow(workflow_run_id)
        # 2. 执行
        result = workflow.run()
        # 3. 写回结果
        update_workflow_status(workflow_run_id, "success", result)
        return {"status": "success"}
    except Exception as exc:
        # 4. 重试
        raise self.retry(exc=exc)


# 调用方（API 进程）：
def trigger_workflow(workflow_id):
    """API 进程发布任务到 Redis。"""
    run_id = run_workflow_task.delay(workflow_id)
    return run_id  # 立即返回，不阻塞
```

**解读**：
- 第 5-9 行：Redis 作为 broker 和 backend
- **Redis 充当 IPC 中间件**：解耦 API 进程和 worker 进程
- 第 23 行：`@app.task` 装饰函数为 Celery 任务
- 第 41 行：`.delay()` 异步发布任务到 Redis
- **设计意图**：用 Redis pub/sub 实现跨进程的异步任务分发

## 4. 关键要点总结

- **IPC 五大方式**：管道、消息队列、共享内存、信号量、Socket
- **共享内存最快**，Socket 支持跨主机
- **生产级 IPC**：Redis、Kafka、RabbitMQ、gRPC
- dify 用 Redis 作为 IPC 中间件（Celery broker）
- Celery = 异步任务队列 = 分布式 IPC

## 5. 练习题

### 练习 1：基础（必做）

用 Python 的 `multiprocessing.Queue` 实现生产者-消费者：一个进程生产数字，一个进程计算平方并打印。

### 练习 2：进阶

阅读 `api/tasks/celery_app.py`，说明 dify 选 Redis 而不是 RabbitMQ 作为 Celery broker 的原因（提示：性能、运维成本）。

### 练习 3：挑战（选做）

用 Python `socket` 实现一个简单的 HTTP 服务器（接收 GET 请求，返回 "Hello"），理解 Socket 与 HTTP 的关系。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/celery_app.py`
- 《操作系统概念》第 3 章 进程
- Redis pub/sub：https://redis.io/docs/manual/pubsub/

---

**文档版本**：v1.0
**最后更新**：2026-07-13