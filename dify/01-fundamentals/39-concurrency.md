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
- 01-fundamentals/12-async-asyncio.md
- 01-fundamentals/40-gil.md（推荐先看或并行看）

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
| **异步**（asyncio） | 协程 + 事件循环 | I/O 密集（高并发） | 不能跑同步阻塞调用 |

> **经验法则**：
> - I/O 密集 + 高并发 → **异步**
> - I/O 密集 + 简单逻辑 → **多线程**
> - CPU 密集 → **多进程**

### 1.3 GIL 的影响

Python 的 CPython 解释器有 **GIL（全局解释器锁）**——同一时刻只有一个线程能执行 Python 字节码。这意味着：
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

## 3. dify 仓库源码解读

### 3.1 RAG 索引并发处理（ThreadPoolExecutor + 哈希分片）

**文件位置**：`/Users/xu/code/github/dify/api/core/indexing_runner.py`
**核心代码**（行 608-637）：

```python
        max_workers = 10
        if dataset.indexing_technique == IndexTechniqueType.HIGH_QUALITY:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                # Distribute documents into multiple groups based on the hash values of page_content
                # This is done to prevent multiple threads from processing the same document,
                # Thereby avoiding potential database insertion deadlocks
                document_groups: list[list[Document]] = [[] for _ in range(max_workers)]
                for document in documents:
                    hash = helper.generate_text_hash(document.page_content)
                    group_index = int(hash, 16) % max_workers
                    document_groups[group_index].append(document)
                for chunk_documents in document_groups:
                    if len(chunk_documents) == 0:
                        continue
                    futures.append(
                        executor.submit(
                            self._process_chunk,
                            current_app._get_current_object(),  # type: ignore
                            index_processor,
                            chunk_documents,
                            dataset,
                            dataset_document,
                            embedding_model_instance,
                        )
                    )

                for future in futures:
                    tokens += future.result()
```

**解读**：
- 第 2 行：`ThreadPoolExecutor(max_workers=10)`——10 个线程并发处理文档
- 第 8-12 行：**按 hash 分片**——相同内容的文档总落到同一线程，避免插入死锁（同一文档被多线程插入会触发主键冲突）
- 第 13-19 行：每个线程处理一个文档组，调用 `_process_chunk`（含 embedding 调用，I/O 密集）
- 第 21-22 行：等待所有 future 完成，累计 token 数
- **为什么用线程池而非异步**：dify 的 embedding 调用库（如 transformers）是同步的，包成异步很麻烦；用线程池简单直接

### 3.2 Celery 任务内部并发

**文件位置**：`/Users/xu/code/github/dify/api/tasks/rag_pipeline/rag_pipeline_run_task.py`
**核心代码**（行 37-75）：

```python
@shared_task(queue="pipeline")
def rag_pipeline_run_task(
    rag_pipeline_invoke_entities_file_id: str,
    tenant_id: str,
):
    """
    Async Run rag pipeline task using regular priority queue.

    :param rag_pipeline_invoke_entities_file_id: File ID containing serialized RAG pipeline invoke entities
    :param tenant_id: Tenant ID for the pipeline execution
    """
    # run with threading, thread pool size is 10

    try:
        start_at = time.perf_counter()
        rag_pipeline_invoke_entities_content = FileService(db.engine).get_file_content(
            rag_pipeline_invoke_entities_file_id
        )
        rag_pipeline_invoke_entities = json.loads(rag_pipeline_invoke_entities_content)

        logger.info("tenant %s received %d rag pipeline invoke entities", tenant_id, len(rag_pipeline_invoke_entities))

        # Get Flask app object for thread context
        flask_app = current_app._get_current_object()  # type: ignore

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for rag_pipeline_invoke_entity in rag_pipeline_invoke_entities:
                # Submit task to thread pool with Flask app
                future = executor.submit(run_single_rag_pipeline_task, rag_pipeline_invoke_entity, flask_app)
                futures.append(future)

            # Wait for all tasks to complete
            for future in futures:
                try:
                    future.result()  # This will raise any exceptions that occurred in the thread
                except Exception:
                    logging.exception("Error in pipeline task")
```

**解读**：
- 第 1 行：`@shared_task(queue="pipeline")`——Celery 任务，外部排队
- 第 19 行：`time.perf_counter()`——高精度计时器，记录整个任务耗时
- 第 23 行：`current_app._get_current_object()`——Flask app 对象**必须显式传入线程**，因为 Flask 的 `current_app` 是 `LocalProxy`，跨线程不工作
- 第 27 行：10 线程并发跑多个 RAG pipeline 调用（每个调用包含多次 I/O：embedding、检索、LLM）
- 第 31 行：`future.result()`——阻塞直到线程完成，并把异常传播到主线程
- **架构组合**：Celery（进程级并发）+ ThreadPoolExecutor（线程级并发）= 多层并发模型

## 4. 关键要点总结

- **CPU 密集型**用 `ProcessPoolExecutor`；**I/O 密集型**用 `ThreadPoolExecutor` 或 `asyncio`
- GIL 限制多线程不能并行 CPU 任务，但 I/O 等待时会释放 GIL
- `concurrent.futures` 提供统一的「池」接口（`submit` / `map` / `as_completed`）
- dify 大量用 `ThreadPoolExecutor` 处理**含 I/O 的并发任务**（embedding 调用、HTTP 请求）
- 多层并发模型常见：Celery（进程）→ ThreadPoolExecutor（线程）→ 业务调用

## 5. 练习题

### 练习 1：基础（必做）

用 `ThreadPoolExecutor` 并发请求 10 个 URL（用 `requests`），统计总耗时。

```python
from concurrent.futures import ThreadPoolExecutor
import requests, time

urls = [f"https://httpbin.org/delay/{i}" for i in range(1, 11)]

def fetch(url):
    return requests.get(url).status_code

start = time.perf_counter()
with ThreadPoolExecutor(max_workers=10) as pool:
    statuses = list(pool.map(fetch, urls))
print(f"耗时: {time.perf_counter() - start:.2f}s, 状态码: {statuses}")
```

### 练习 2：进阶

阅读 `api/core/repositories/sqlalchemy_workflow_node_execution_repository.py` 第 548 行附近的代码，理解 dify 在什么场景下用 `ThreadPoolExecutor`（提示：可能是批量数据库插入）。

### 练习 3：挑战（选做）

实现一个 `RateLimitedThreadPool`：在线程池外面加一层信号量（`threading.Semaphore`），限制同时只能有 N 个线程运行（模拟 API rate limit）。要求：用 `concurrent.futures` 包装。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/indexing_runner.py`（第 608-637 行）
- `/Users/xu/code/github/dify/api/tasks/rag_pipeline/rag_pipeline_run_task.py`
- Python 官方文档 concurrent.futures：https://docs.python.org/3/library/concurrent.futures.html
- Real Python 并发教程：https://realpython.com/python-concurrency/

---

**文档版本**：v1.0
**最后更新**：2026-07-13