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
- [并发模型](./30-concurrency.md)（推荐）
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
| `__slots__` 节省内存（见 [29-memory-management](./32-memory-management.md)） | ~30% 内存 |
| `lru_cache` 缓存重复计算（见 [26-functools](./29-functools.md)） | 数量级加速 |
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

## 3. 关键要点总结

- **测量优先于猜测**——先 profile，找到瓶颈再优化
- `time.perf_counter()` 是推荐的高精度计时器
- `timeit.timeit()` 做微基准测试，自动多次取最小值
- `cProfile.Profile()` 记录函数级 CPU 耗时，关注 `cumtime`
- dify 用 `time.perf_counter()` 记录索引耗时、Celery 任务耗时，写入 DB 或日志
- **常见优化**：列表推导、`__slots__`、`lru_cache`、C 扩展（numpy）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
