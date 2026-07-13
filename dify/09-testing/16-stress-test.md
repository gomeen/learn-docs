# 16 压力测试与基准测试

> 区分压力测试和基准测试的目标，掌握容量规划与系统极限的探索方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解压力测试、负载测试、基准测试的区别
- 掌握压测场景设计（尖峰、持续加压、突发）
- 理解基准测试在 dify 代码级的作用
- 应用：能为 dify 关键路径设计压测方案

## 📚 前置知识

- 09-testing/15-performance-test.md
- 系统吞吐量、延迟、容量规划基础概念

## 1. 核心概念

### 1.1 性能测试的 4 种类型

| 类型 | 目标 | 典型问题 |
|------|------|----------|
| **基准测试（Benchmark）** | 测量单次性能 | "这个函数每秒能跑多少次？" |
| **负载测试（Load Test）** | 验证正常负载下的稳定性 | "100 并发用户时系统表现？" |
| **压力测试（Stress Test）** | 找到系统极限 | "系统能扛多少用户？什么时候崩溃？" |
| **尖峰测试（Spike Test）** | 验证突发流量 | "1 秒内从 10 用户涨到 1000 用户会怎样？" |

### 1.2 压力测试 vs 基准测试

**基准测试**：
- 单线程、固定负载
- 关注**吞吐量**和**延迟**
- 工具：`pytest-benchmark`、JMH（Java）

**压力测试**：
- 多线程、模拟真实用户
- 关注**系统极限**和**降级行为**
- 工具：Locust、k6、JMeter

```
基准测试：1 个用户跑 1 个请求  →  测函数速度
压力测试：1000 个用户跑请求   →  测系统极限
```

### 1.3 压力测试的常见模式

```
1. 渐进式加压
   用户数：  0 → 50 → 100 → 200 → 500
   观察：    正常  正常   正常   慢    崩溃
   
2. 尖峰测试
   0s ─────────────── 30s ──── 35s ─────── 65s
   10 用户            1000 用户   回落
                      ↑ 突发      ↑ 恢复

3. 持续高压（Soak Test）
   100 用户持续运行 24 小时
   观察：内存泄漏、连接耗尽
```

## 2. 代码示例

### 2.1 k6 渐进式加压

```javascript
// 文件：stress-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '1m', target: 50 },    // 加到 50 用户
    { duration: '3m', target: 50 },    // 维持 3 分钟（稳态）
    { duration: '1m', target: 100 },   // 加到 100
    { duration: '3m', target: 100 },
    { duration: '1m', target: 200 },   // 继续加压
    { duration: '3m', target: 200 },
    { duration: '1m', target: 0 },     // 降压
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.05'],     // 允许 5% 错误率
  },
}

export default function () {
  const res = http.get('http://localhost:5001/api/apps')
  check(res, { 'status ok': (r) => r.status === 200 })
  sleep(1)
}
```

### 2.2 k6 尖峰测试

```javascript
export const options = {
  stages: [
    { duration: '10s', target: 10 },     // 平稳 10 用户
    { duration: '5s', target: 1000 },    // 5 秒内涨到 1000（尖峰！）
    { duration: '30s', target: 1000 },   // 维持 30 秒
    { duration: '10s', target: 10 },     // 回落
    { duration: '30s', target: 10 },     // 恢复期
  ],
}
```

### 2.3 pytest-benchmark 基准测试

```python
# 文件：test_benchmark_splitter.py
import pytest


def test_chunk_split_throughput(benchmark):
    """基准测试：文本分割吞吐量。"""
    from core.rag.splitter import TextSplitter
    splitter = TextSplitter(chunk_size=500)
    text = "lorem ipsum dolor sit amet " * 1000

    # benchmark() 会自动跑多次并报告中位数
    result = benchmark(splitter.split, text)
    assert len(result) > 0


@pytest.mark.parametrize("chunk_size", [100, 500, 1000, 2000])
def test_chunk_size_comparison(benchmark, chunk_size):
    """对比不同 chunk size 的吞吐量。"""
    from core.rag.splitter import TextSplitter
    splitter = TextSplitter(chunk_size=chunk_size)
    text = "abc " * 5000
    benchmark(splitter.split, text)
```

输出：

```
test_chunk_size_comparison[100]    500 rounds:  2.10ms/round
test_chunk_size_comparison[500]    500 rounds:  1.20ms/round
test_chunk_size_comparison[1000]   500 rounds:  0.85ms/round
test_chunk_size_comparison[2000]   500 rounds:  0.70ms/round
```

## 3. dify 仓库源码解读

### 3.1 dify 的 benchmark 工具链

**文件位置**：`/Users/xu/code/github/dify/api/pyproject.toml`
**核心代码**（行 130-135）：

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-benchmark>=5.2.3",
    "pytest-cov>=7.1.0",
    "pytest-env>=1.6.0",
    "pytest-mock>=3.15.1",
]
```

**解读**：
- `pytest-benchmark>=5.2.3` —— dify 唯一的代码级基准测试工具
- 用于发现代码级性能回归（如重构后某个函数变慢）
- 不同于压测工具的"系统级"，benchmark 是"函数级"

### 3.2 dify 的 benchmark 禁用策略

**文件位置**：`/Users/xu/code/github/dify/Makefile`
**核心代码**：

```makefile
test:
	@echo "🧪 Running backend unit tests..."
	@if [ -n "$(TARGET_TESTS)" ]; then \
		echo "Target: $(TARGET_TESTS)"; \
		uv run --project api --dev pytest $(TARGET_TESTS); \
	else \
		echo "Running backend unit tests"; \
		uv run --project api --dev pytest -p no:benchmark --timeout "$${PYTEST_TIMEOUT:-20}" -n auto \
			api/tests/unit_tests \
			...
```

**解读**：
- 第 100 行：`-p no:benchmark` —— CI 默认禁用 benchmark（避免拖慢测试）
- benchmark 跑多次取中位数，单个测试会从 100ms 变成 5 秒
- 本地开发者想跑 benchmark 时，去掉 `-p no:benchmark` 即可

### 3.3 dify 的 Locust 临时移除

**文件位置**：`/Users/xu/code/github/dify/api/pyproject.toml`
**核心代码**（行 178-185）：

```toml
[dependency-groups]
dev = [
    "mypy>=1.20.2",
    # "locust>=2.40.4",  # Temporarily removed due to compatibility issues. Uncomment when resolved.
    "pytest-timeout>=2.4.0",
    "pytest-xdist>=3.8.0",
    "pyrefly>=1.0.0",
    "xinference-client>=2.7.0",
]
```

**解读**：
- Locust 被注释保留，未来恢复
- 注释中说明原因：compatibility issues（兼容性）
- **设计意图**：性能测试基础设施在不成熟时暂时下线，但不删除依赖

## 4. 关键要点总结

- **基准测试**测单个函数的吞吐量，**压力测试**测系统极限
- 压力测试常用模式：渐进加压、尖峰、持续高压（Soak）
- k6 的 `stages` 配置可以表达各种加压曲线
- pytest-benchmark 是 Python 函数级基准测试的事实标准
- dify CI 默认禁用 benchmark（`-p no:benchmark`），开发者本地按需启用
- Locust 因兼容性问题暂时从 dify 移除，注释保留证据

## 5. 练习题

### 练习 1：基础（必做）

写一个 pytest-benchmark 测试，对比 `list.sort()` 和 `sorted(list)` 的性能差异，参数化不同列表长度（100/1000/10000）。

### 练习 2：进阶

阅读 `api/tests/unit_tests/core/rag/splitter/test_text_splitter.py`，理解 dify 现有的 splitter 基准测试是怎么写的，并尝试为本地的某个核心函数（如 `repositories/document_repo.py` 的查询方法）加一个 benchmark 测试。

### 练习 3：挑战（选做）

设计一个 dify API 的压测方案，包含：
- 目标：找出 dify 对话 API 的最大并发数
- 工具：k6
- 场景：渐进加压（10→50→100→200→500）
- 通过/失败标准：P95 < 2s，错误率 < 1%

写出完整的 k6 脚本。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pyproject.toml`（benchmark 依赖）
- `/Users/xu/code/github/dify/Makefile`（`-p no:benchmark` 配置）
- pytest-benchmark 文档：https://pytest-benchmark.readthedocs.io/
- k6 测试类型：https://k6.io/docs/test-types/

---

**文档版本**：v1.0
**最后更新**：2026-07-13