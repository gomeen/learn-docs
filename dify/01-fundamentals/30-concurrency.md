# 1.1.23 多线程 vs 多进程 vs 异步

> 理解 Python 中三种并发模型的差异与适用场景，能根据任务类型选择正确的并发方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分「CPU 密集型」「I/O 密集型」任务
- 解释多线程、多进程、异步三种模型的差异
- 用 `concurrent.futures.ThreadPoolExecutor` / `ProcessPoolExecutor` 启动并发任务
- 在 dify 中识别 `ThreadPoolExecutor` 的使用场景

## 📚 前置知识

- Python 基础：函数、类
- [asyncio](./14-async-asyncio.md)
- [GIL](./31-gil.md)（推荐先看或并行看）

## 1. 核心概念

### 1.1 三类任务

| 类型 | 特点 | 例子 |
| --- | --- | --- |
| **CPU 密集型** | 大部分时间在做计算 | 图像处理、数值计算、JSON 序列化大对象 |
| **I/O 密集型** | 大部分时间在等待网络/磁盘 | HTTP 请求、数据库查询、文件读写 |
| **混合型** | 二者兼有 | 爬虫（HTTP + HTML 解析） |

### 1.2 三种并发模型对比

| 模型 | 实现方式 | 适合 | 缺点 |
| --- | --- | --- | --- |
| **多线程**（threading） | 操作系统线程 | I/O 密集（受 GIL 限制） | 不能并行 CPU 计算 |
| **多进程**（multiprocessing） | 启动多个 Python 解释器 | CPU 密集 | 进程间通信复杂、内存开销大 |
| **异步**（asyncio，详见 [12-async-asyncio](./14-async-asyncio.md)） | 协程 + 事件循环 | I/O 密集（高并发） | 不能跑同步阻塞调用 |

> **经验法则**：
> - I/O 密集 + 高并发 → **异步**
> - I/O 密集 + 简单逻辑 → **多线程**
> - CPU 密集 → **多进程**

### 1.3 GIL 的影响

Python 的 CPython 解释器有 **GIL（全局解释器锁）**——同一时刻只有一个线程能执行 Python 字节码（深入机制见 [28-gil](./31-gil.md)）。这意味着：
- **多线程**对 CPU 密集型任务**没有加速**
- **多线程**对 I/O 密集型任务**有效**（I/O 等待时 GIL 释放）
- **多进程**能真正利用多核 CPU（每个进程有独立 GIL）

### 1.4 `concurrent.futures` 高级接口

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
```

`ThreadPoolExecutor` / `ProcessPoolExecutor` 提供统一的「线程池/进程池」接口，简化并发编程。

### 1.5 异步 vs 线程池

| | 线程池 | 异步 |
| --- | --- | --- |
| 资源占用 | 每个线程 ~8MB 栈 | 协程 ~几 KB |
| 10 万并发 | 不可行 | 可行 |
| 代码风格 | 同步写法 | async/await |
| 兼容性 | 任何同步库都能用 | 需要异步库 |

## 2. 代码示例

### 2.1 线程池：并发 HTTP 请求

```python
from concurrent.futures import ThreadPoolExecutor
import time

def fetch(url):
    time.sleep(1)  # 模拟网络请求
    return f"result for {url}"

urls = [f"https://api.com/{i}" for i in range(10)]

# 串行：10 秒
start = time.perf_counter()
results = [fetch(u) for u in urls]
print(f"serial: {time.perf_counter() - start:.2f}s")

# 并发：~1 秒（10 线程并发）
start = time.perf_counter()
with ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(fetch, urls))
print(f"concurrent: {time.perf_counter() - start:.2f}s")
```

### 2.2 进程池：CPU 密集任务

```python
from concurrent.futures import ProcessPoolExecutor

def cpu_heavy(n):
    return sum(i * i for i in range(n))

tasks = [10_000_000] * 8

# 进程池：~N/核数 时间
with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_heavy, tasks))
```

### 2.3 常见错误：在线程池里跑 CPU 密集任务

```python
from concurrent.futures import ThreadPoolExecutor

def cpu_task(n):
    return sum(i * i for i in range(n))

# ❌ 错误：受 GIL 限制，多线程对 CPU 任务无效
with ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(cpu_task, [10_000_000] * 8))

# ✅ 正确：用进程池
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_task, [10_000_000] * 8))
```

### 2.4 `as_completed` 处理完成顺序

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(i):
    import random, time
    time.sleep(random.random())
    return i

with ThreadPoolExecutor(max_workers=3) as pool:
    futures = [pool.submit(fetch, i) for i in range(5)]
    # 按完成顺序处理结果（而不是提交顺序）
    for future in as_completed(futures):
        result = future.result()
        print(f"got: {result}")
```

## 3. 关键要点总结

- **CPU 密集型**用 `ProcessPoolExecutor`；**I/O 密集型**用 `ThreadPoolExecutor` 或 `asyncio`
- GIL 限制多线程不能并行 CPU 任务，但 I/O 等待时会释放 GIL
- `concurrent.futures` 提供统一的「池」接口（`submit` / `map` / `as_completed`）
- dify 大量用 `ThreadPoolExecutor` 处理**含 I/O 的并发任务**（embedding 调用、HTTP 请求）
- 多层并发模型常见：Celery（进程）→ ThreadPoolExecutor（线程）→ 业务调用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
