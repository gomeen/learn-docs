# 15 性能测试：Locust / k6 / JMeter

> 理解性能测试的目标和主流工具，能用 Locust 或 k6 测试 dify API 的吞吐量与延迟。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解性能测试的核心指标（RPS、P95、错误率）
- 掌握 Locust 和 k6 的基本用法
- 知道如何选择合适的性能测试工具
- 应用：能为 dify 的 API 编写性能测试脚本

## 📚 前置知识

- HTTP 基础
- 09-testing/01-testing-pyramid.md

## 1. 核心概念

### 1.1 性能测试的目标

性能测试不是验证"功能正确"，而是回答：

- **吞吐量**：每秒能处理多少请求（RPS, Requests Per Second）
- **延迟**：请求耗时多少（平均、P50、P95、P99）
- **稳定性**：长时间运行是否出现内存泄漏
- **容量**：并发 N 个用户时，系统表现如何

### 1.2 性能测试的核心指标

```
┌──────────────────────────────────────────────────────┐
│ P50（50% 请求在此时间内完成）         中位数          │
│ P95（95% 请求在此时间内完成）         95% 用户体验    │
│ P99（99% 请求在此时间内完成）         1% 极端情况     │
│ 错误率（5xx 响应占比）                系统稳定性      │
└──────────────────────────────────────────────────────┘
```

**为什么 P95 比平均值重要？**
- 平均值被极端值拉偏
- P95 告诉你"95% 用户的体验"
- 业务上，P95 超过 SLO 就触发告警

### 1.3 主流性能测试工具对比

| 工具 | 语言 | 学习曲线 | 分布式 | 协议 |
|------|------|----------|--------|------|
| **Locust** | Python | 低 | ✓ | HTTP |
| **k6** | JavaScript (Go runtime) | 中 | ✓ | HTTP, WebSocket, gRPC |
| **JMeter** | Java | 高 | ✓ | HTTP, FTP, JDBC |
| **wrk** | C | 高 | ✗ | HTTP |
| **Vegeta** | Go | 中 | ✓ | HTTP |

dify 早期使用 Locust，当前 pyproject 已移除（兼容性原因）。

## 2. 代码示例

### 2.1 Locust 基础脚本

```python
# 文件：locustfile.py
from locust import HttpUser, task, between


class DifyUser(HttpUser):
    wait_time = between(1, 3)  # 每个任务间隔 1-3 秒

    @task(3)  # 权重 3，被执行概率更高
    def list_apps(self):
        self.client.get("/api/apps")

    @task(1)
    def create_app(self):
        self.client.post("/api/apps", json={
            "name": "Load Test App",
            "mode": "chat",
        })

    def on_start(self):
        """每个虚拟用户启动时执行一次（登录等）。"""
        response = self.client.post("/api/auth/login", json={
            "email": "test@dify.ai",
            "password": "secret",
        })
        self.token = response.json()["access_token"]

    def on_stop(self):
        """每个虚拟用户结束时执行。"""
        self.client.post("/api/auth/logout")
```

运行：

```bash
$ locust -f locustfile.py --host=http://localhost:5001 \
    --users 100 --spawn-rate 10 --run-time 60s
```

### 2.2 k6 脚本

```javascript
// 文件：script.js
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // 30 秒内加压到 50 用户
    { duration: '1m', target: 100 },   // 1 分钟内加到 100 用户
    { duration: '30s', target: 0 },    // 30 秒内降到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // P95 < 500ms
    http_req_failed: ['rate<0.01'],    // 错误率 < 1%
  },
}

export default function () {
  const res = http.get('http://localhost:5001/api/apps')
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  })
  sleep(1)
}
```

运行：

```bash
$ k6 run script.js
```

### 2.3 性能测试报告解读

```
     ✓ status is 200
     ✓ response time < 500ms

     checks.........................: 100.00% ✓ 12000  ✗ 0
     data_received..................: 1.2 MB  20 kB/s
     data_sent......................: 240 kB  4.0 kB/s
   ✓ http_req_duration..............: avg=125ms  min=50ms  med=110ms  max=480ms  p(90)=220ms  p(95)=280ms
     http_req_failed................: 0.00%   ✓ 0      ✗ 12000
     http_reqs......................: 12000   200/s
```

**关键解读**：
- `http_reqs: 12000` —— 总请求数
- `http_req_duration p(95)=280ms` —— 95% 请求在 280ms 内完成
- `http_req_failed: 0.00%` —— 错误率 0%

## 3. dify 仓库源码解读

### 3.1 dify 的性能测试依赖

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
- 第 181 行：`# "locust>=2.40.4"` 被注释，注释说明"Temporarily removed due to compatibility issues"
- dify **未来可能**会用 Locust，但当前不用
- **设计意图**：注释保留依赖证据，方便未来恢复

### 3.2 dify 的性能基准测试入口

**文件位置**：`/Users/xu/code/github/dify/Makefile`
**核心代码**（通过 grep 查找 pytest-benchmark 相关）：

```makefile
test:
	@echo "🧪 Running backend unit tests..."
	...
	uv run --project api --dev pytest -p no:benchmark --timeout "$${PYTEST_TIMEOUT:-20}" -n auto \
		api/tests/unit_tests \
		...
```

**解读**：
- CI 中 `-p no:benchmark` —— 默认**禁用** benchmark 插件
- 本地调试时可去掉 `-p no:benchmark` 跑性能基准
- dify 通过 `pytest-benchmark` 提供"性能测试"能力（区别于压测工具）

### 3.3 pytest-benchmark 实战

**文件位置**：`/Users/xu/code/github/dify/api/tests/unit_tests/core/rag/splitter/test_text_splitter.py`

```python
# pytest-benchmark 自动收集基准
def test_text_splitter_performance(benchmark):
    """基准测试：文本分割函数的吞吐量。"""
    from core.rag.splitter import TextSplitter
    splitter = TextSplitter(chunk_size=500, overlap=50)
    long_text = "lorem ipsum " * 10000  # ~120KB

    result = benchmark(splitter.split, long_text)

    assert len(result) > 0
```

运行：

```bash
$ pytest test_text_splitter.py --benchmark-only
text_splitter_performance  1000 rounds: 12.50ms/round
```

## 4. 关键要点总结

- 性能测试关注**吞吐量、延迟、稳定性、容量**四大维度
- P95 比平均值更能反映用户体验
- Locust（Python）和 k6（JS）是目前最主流的压测工具
- dify 通过 `pytest-benchmark` 做代码级基准测试，Locust 暂时移除
- 压测报告应包含：P50/P95/P99、错误率、吞吐量

## 5. 练习题

### 练习 1：基础（必做）

写一个 k6 脚本，对 dify 的 `/api/health` 端点做 30 秒压测，验证：
- P95 响应时间 < 100ms
- 错误率 < 0.1%

### 练习 2：进阶

本地运行 `cd api && uv run --project api --dev pytest api/tests/unit_tests/core/rag/splitter/ --benchmark-only`，观察不同 chunk size 下的吞吐量差异。

### 练习 3：挑战（选做）

写一个 Locust 脚本，模拟 dify 的对话流程：登录 → 创建 Chatbot 应用 → 发送对话消息 → 接收响应。统计 P95 延迟，并对比单用户 vs 100 并发用户时的性能差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/pyproject.toml`（性能测试依赖）
- `/Users/xu/code/github/dify/Makefile`（`make test` 用 `-p no:benchmark`）
- Locust 文档：https://docs.locust.io/
- k6 文档：https://k6.io/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13