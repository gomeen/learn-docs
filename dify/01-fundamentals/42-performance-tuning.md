# 1.1.26 Python 性能调优：`cProfile` / `timeit` / `perf_counter`

> 掌握 Python 性能分析工具，能精准定位代码瓶颈，做有数据支撑的优化。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `time.perf_counter` / `timeit` 做微基准测试
- 用 `cProfile` 做函数级 CPU profiling
- 解读 cProfile 的 pstats 输出（`cumtime` / `tottime`）
- 在 dify 中识别 `time.perf_counter()` 等计时模式

## 📚 前置知识

- Python 基础：函数、模块
- 01-fundamentals/39-concurrency.md（推荐）
- 操作系统的「CPU 时间 vs 墙钟时间」概念

## 1. 核心概念

### 1.1 性能调优的原则

> **不要猜测，要测量。** —— Rob Pike

调优步骤：
1. **测量 baseline**（当前耗时）
2. **找到瓶颈**（profiling）
3. **优化瓶颈**
4. **再次测量**，验证有效

### 1.2 三种计时工具对比

| 工具 | 精度 | 用途 |
| --- | --- | --- |
| `time.time()` | ~微秒 | 跨平台通用，但可能受系统时间调整影响 |
| `time.perf_counter()` | ~纳秒 | **推荐**：高精度单调时钟 |
| `time.process_time()` | ~微秒 | CPU 时间（不计 sleep） |
| `timeit.timeit()` | 纳秒 | 微基准测试，自动多跑取平均 |

> 永远优先用 `time.perf_counter()` 测「墙钟时间」。

### 1.3 `cProfile`：函数级 CPU profiling

`cProfile` 是 C 实现的 profiler，开销低，记录每个函数被调用多少次、花了多少时间：

```bash
python -m cProfile -s cumtime my_script.py
```

或在代码中：
```python
import cProfile, pstats

with cProfile.Profile() as pr:
    main()

stats = pstats.Stats(pr).sort_stats('cumtime')
stats.print_stats(20)  # 打印前 20 行
```

**关键字段**：
- `ncalls`：调用次数
- `tottime`：**本函数**总耗时（不含子函数）
- `cumtime`：**本函数 + 子函数**总耗时
- `percall`：每次调用的平均耗时

### 1.4 `timeit`：微基准测试

```python
import timeit

# 单行语句
t = timeit.timeit('"-".join(str(n) for n in range(100))', number=10000)
print(t)  # 总耗时

# 多行（用 ; 分隔或传 setup）
t = timeit.timeit(
    'lst = [n**2 for n in range(100)]',
    setup='pass',
    number=10000,
)

# 命令行
python -m timeit '"-".join(str(n) for n in range(100))'
```

`timeit` 自动跑多次取最小值，避免被其他进程干扰。

### 1.5 常见优化技巧

| 优化 | 效果 |
| --- | --- |
| 列表推导代替循环 append | ~10-30% |
| `dict.get()` 代替 `try/except KeyError` | ~3x |
| 局部变量代替全局变量 | ~10-20% |
| `__slots__` 节省内存 | ~30% 内存 |
| `lru_cache` 缓存重复计算 | 数量级加速 |
| 用 C 扩展（numpy、pandas） | 10x-100x |

> **永远先 profile，再优化**——大多数优化的「直觉」都是错的。

## 2. 代码示例

### 2.1 用 `time.perf_counter` 计时

```python
import time

start = time.perf_counter()
result = sum(range(1_000_000))
end = time.perf_counter()

print(f"耗时: {end - start:.6f} 秒")
```

### 2.2 用 `timeit` 比较两种写法

```python
import timeit

# 写法 A：for 循环
t1 = timeit.timeit(
    'result = []\nfor i in range(1000): result.append(str(i))',
    number=10000,
)

# 写法 B：列表推导
t2 = timeit.timeit(
    '[str(i) for i in range(1000)]',
    number=10000,
)

print(f"for loop:    {t1:.4f}s")
print(f"list comp:   {t2:.4f}s")
print(f"加速比: {t1/t2:.2f}x")
```

### 2.3 用 `cProfile` 分析程序

```python
import cProfile, pstats, io

def slow_function():
    total = 0
    for i in range(10_000_000):
        total += i
    return total

def main():
    for _ in range(3):
        slow_function()

# 运行 profiler
pr = cProfile.Profile()
pr.enable()
main()
pr.disable()

# 打印统计
s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumtime')
ps.print_stats(10)
print(s.getvalue())
```

输出类似：
```
   ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
        3    0.450    0.150    0.450    0.150  example.py:3(slow_function)
        1    0.001    0.001    0.451    0.451  example.py:8(main)
```

### 2.4 常见错误：用 `time.time()` 测短任务

```python
import time

# ❌ 错误：time.time() 精度只到微秒，测 100ns 任务会显示 0
start = time.time()
result = 1 + 1
print(time.time() - start)  # 0.0（看不清）

# ✅ 正确：用 time.perf_counter()，精度到纳秒
start = time.perf_counter()
result = 1 + 1
print(time.perf_counter() - start)
```

## 3. dify 仓库源码解读

### 3.1 RAG 索引耗时统计

**文件位置**：`/Users/xu/code/github/dify/api/core/indexing_runner.py`
**核心代码**（行 590-656）：

```python
        # chunk nodes by chunk size
        indexing_start_at = time.perf_counter()
        tokens = 0
        create_keyword_thread = None
        if (
            dataset_document.doc_form != IndexStructureType.PARENT_CHILD_INDEX
            and dataset.indexing_technique == IndexTechniqueType.ECONOMY
        ):
            ...

        max_workers = 10
        if dataset.indexing_technique == IndexTechniqueType.HIGH_QUALITY:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ... 文档处理逻辑 ...
                for future in futures:
                    tokens += future.result()
        if (
            dataset_document.doc_form != IndexStructureType.PARENT_CHILD_INDEX
            and dataset.indexing_technique == IndexTechniqueType.ECONOMY
            and create_keyword_thread is not None
        ):
            create_keyword_thread.join()
        indexing_end_at = time.perf_counter()

        # update document status to completed
        self._update_document_index_status(
            document_id=dataset_document.id,
            after_indexing_status=IndexingStatus.COMPLETED,
            extra_update_params={
                DatasetDocument.tokens: tokens,
                DatasetDocument.completed_at: naive_utc_now(),
                DatasetDocument.indexing_latency: indexing_end_at - indexing_start_at,
                DatasetDocument.error: None,
            },
        )
```

**解读**：
- 第 2 行：`indexing_start_at = time.perf_counter()`——开始计时
- 第 45 行：`indexing_end_at = time.perf_counter()`——结束计时
- 第 52 行：`indexing_latency: indexing_end_at - indexing_start_at`——把**索引耗时写入数据库**
- **业务价值**：dify 记录每次文档索引的耗时，用户能在 UI 上看到「这个文档花了多久处理」
- **为什么用 `perf_counter`**：索引可能跨分钟、小时，必须用高精度单调时钟

### 3.2 Celery 任务墙钟时间记录

**文件位置**：`/Users/xu/code/github/dify/api/tasks/rag_pipeline/rag_pipeline_run_task.py`
**核心代码**（行 50-80）：

```python
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
        end_at = time.perf_counter()
        logging.info(
            click.style(
                f"tenant_id: {tenant_id}, Rag pipeline run completed. Latency: {end_at - start_at}s", fg="green"
            )
        )
```

**解读**：
- 第 2 行：`start_at = time.perf_counter()`——Celery 任务开始计时
- 第 24 行：`end_at = time.perf_counter()`——任务结束计时
- 第 26-30 行：把耗时写到日志（带颜色），方便运维定位慢任务
- **为什么用 `perf_counter`**：Celery 任务可能涉及多个子 pipeline，整体耗时可能几分钟，必须用单调时钟避免系统时间跳变干扰
- **日志记录而非数据库**：长任务用日志记录即可，频繁写 DB 会拖慢任务

## 4. 关键要点总结

- **测量优先于猜测**——先 profile，找到瓶颈再优化
- `time.perf_counter()` 是推荐的高精度计时器
- `timeit.timeit()` 做微基准测试，自动多次取最小值
- `cProfile.Profile()` 记录函数级 CPU 耗时，关注 `cumtime`
- dify 用 `time.perf_counter()` 记录索引耗时、Celery 任务耗时，写入 DB 或日志
- **常见优化**：列表推导、`__slots__`、`lru_cache`、C 扩展（numpy）

## 5. 练习题

### 练习 1：基础（必做）

用 `timeit` 对比三种列表创建方式：

```python
import timeit

t1 = timeit.timeit('[]', number=1_000_000)
t2 = timeit.timeit('list()', number=1_000_000)
t3 = timeit.timeit('[i for i in range(10)]', number=1_000_000)
print(f"[]: {t1:.4f}s, list(): {t2:.4f}s, listcomp: {t3:.4f}s")
```

### 练习 2：进阶

写一个慢函数（用两层 for 循环累加），然后：
1. 用 `cProfile.Profile()` 跑 100 次
2. 打印 `sort_stats('cumtime')` 的前 10 行
3. 用列表推导或 `sum()` 重写，对比耗时

### 练习 3：挑战（选做）

实现一个 `profile_decorator`：装饰一个函数后，每次调用都打印耗时，并把超过 100ms 的调用记录到日志文件。

```python
import functools, time, logging

def profile_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        # TODO: 超过 100ms 时打 warning
        return result
    return wrapper
```

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/indexing_runner.py`（第 590-656 行）
- `/Users/xu/code/github/dify/api/tasks/rag_pipeline/rag_pipeline_run_task.py`
- Python 官方文档 profile：https://docs.python.org/3/library/profile.html
- Python 官方文档 timeit：https://docs.python.org/3/library/timeit.html
- 「Python 高性能编程」：https://www.oreilly.com/library/view/high-performance-python/9781492055013/

---

**文档版本**：v1.0
**最后更新**：2026-07-13