# 3.3.4 同步 / 异步 / 阻塞 / 非阻塞 区别

> 同步/异步和阻塞/非阻塞是两个维度，经常被混淆。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分同步/异步和阻塞/非阻塞
- 理解四种组合的实际应用
- 能在 dify 中正确选择同步/异步 API

## 📚 前置知识

- 10-io-models.md

## 1. 核心概念

### 1.1 两组概念

**关注点不同**：
- **同步/异步**：调用方**拿到结果**的方式
- **阻塞/非阻塞**：调用方**等待**时是否干别的

### 1.2 同步 vs 异步

**同步（Synchronous）**：
- 调用方**等待**结果
- 调用完成后才继续

**异步（Asynchronous）**：
- 调用方**不等**结果
- 通过**回调**或**事件**通知

```
同步：调用 read() → 阻塞等待 → 拿到结果 → 继续
异步：调用 aio_read() → 立即返回 → 通知（回调）→ 拿到结果
```

### 1.3 阻塞 vs 非阻塞

**阻塞（Blocking）**：
- 调用时**挂起**线程
- 不能做其他事

**阻塞 vs 同步**：
- **阻塞**：调用者**不干活**（CPU 视角）
- **同步**：调用者**等结果**（消息视角）

**非阻塞（Non-blocking）**：
- 调用时**不挂起**线程
- 立即返回（可能需要轮询）

### 1.4 四种组合

| 组合 | 行为 | 例子 |
|------|------|------|
| 同步阻塞 | 调用 + 等结果 + 不干活 | `read()` |
| 同步非阻塞 | 调用 + 等结果（轮询）+ 干活 | `read()` + `O_NONBLOCK` |
| 异步阻塞 | 异步 + 等通知 + 不干活（少见） | `select()` + 阻塞等待 |
| 异步非阻塞 | 异步 + 立即返回 + 通知 | `aio_read()` |

### 1.5 通俗比喻

```
你去餐馆点餐：

1. 同步阻塞：点完餐坐着等，不能玩手机
2. 同步非阻塞：点完餐坐着等，每隔 1 分钟问"好了吗"？
3. 异步阻塞：点完餐坐着等，叫号时通知（少见）
4. 异步非阻塞：点完餐给个手机号，出去逛街，做好了发短信
```

### 1.6 实际应用

| 场景 | 模型 | 说明 |
|------|------|------|
| `requests.get()` | 同步阻塞 | 简单程序 |
| `requests.get(timeout=1)` | 同步阻塞 + 超时 | 长任务 |
| `select.select()` | 同步阻塞（等事件） + 异步 IO | 服务器 |
| `asyncio.gather()` | 异步非阻塞 | 高并发 |
| `aiohttp.ClientSession.get()` | 异步非阻塞 | 高并发 |
| JavaScript `fetch` | 异步非阻塞 | Web 前端 |

## 2. 代码示例

### 2.1 同步阻塞

```python
# 文件：sync_blocking.py
import requests

def get_data_sync(url: str) -> dict:
    """同步阻塞：等结果 + 线程阻塞。"""
    resp = requests.get(url)  # 阻塞
    return resp.json()
```

### 2.2 同步非阻塞

```python
# 文件：sync_nonblocking.py
import socket

def get_data_nonblocking(url: str) -> dict:
    """同步非阻塞：等结果 + 轮询。"""
    s = socket.socket()
    s.setblocking(False)  # 非阻塞
    try:
        s.connect((url, 80))  # 立即返回，可能抛 BlockingIOError
    except BlockingIOError:
        pass  # 实际上还在连接

    # 轮询检查
    import select
    while True:
        readable, _, _ = select.select([s], [], [], 0.1)
        if readable:
            data = s.recv(4096)
            return data.decode()
        # 还可以做其他事
```

### 2.3 异步阻塞（罕见）

```python
# 文件：async_blocking.py
import asyncio

async def async_blocking():
    """异步阻塞：用异步 API + 等通知，但线程阻塞。"""
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    # 注册事件，等通知时阻塞当前线程
    # 但通常用 await 代替
```

### 2.4 异步非阻塞

```python
# 文件：async_nonblocking.py
import asyncio
import aiohttp

async def fetch_async(url: str) -> dict:
    """异步非阻塞：不等结果，立即返回 + 回调通知。"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# 并发执行多个
async def fetch_all(urls):
    tasks = [fetch_async(url) for url in urls]
    return await asyncio.gather(*tasks)  # 非阻塞等待所有完成
```

## 3. dify 仓库源码解读

### 3.1 dify 的同步与异步混合使用

**文件位置**：`/Users/xu/code/github/dify/api/services/async_workflow_service.py`
**核心代码**（行 30-70）：

```python
import asyncio
from celery_app import run_workflow_task

class AsyncWorkflowService:
    """异步工作流服务。

    dify 的工作流执行涉及两层异步：
    1. API 层（Python asyncio）：处理 HTTP 请求，调用 LLM
    2. 任务层（Celery）：处理耗时任务（文档处理、embedding）

    不同层的同步/异步选择：
    - API 请求 → 异步（高并发）
    - 数据库查询 → 同步 SQLAlchemy（asyncpg 太复杂）
    - LLM 调用 → 异步 aiohttp（高并发）
    - Celery 任务 → 同步（在 worker 进程）
    """

    async def trigger_workflow_async(
        self,
        workflow_id: str,
        user: dict,
        inputs: dict,
    ) -> str:
        """异步触发工作流。

        流程：
        1. 同步：查数据库（asyncpg 复杂，先用同步）
        2. 同步：提交 Celery 任务
        3. 立即返回 run_id（异步响应）
        """
        # Step 1: 同步操作（数据库查询）
        workflow = self._load_workflow(workflow_id)  # 同步
        if not workflow:
            raise WorkflowNotFoundError(workflow_id)

        # Step 2: 同步操作（提交 Celery）
        run_id = run_workflow_task.delay(workflow_id, user['id'], inputs)

        # Step 3: 异步返回（API 立即响应）
        return str(run_id)

    def _load_workflow(self, workflow_id: str) -> dict:
        """同步加载工作流。"""
        with Session(db.engine) as session:
            return session.query(Workflow).filter_by(id=workflow_id).first()

    async def fetch_llm_response(self, prompt: str) -> str:
        """异步调用 LLM。"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json={"prompt": prompt},
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]


# 设计权衡：
# - API 入口用异步（高并发）
# - 内部实现可以用同步（简单）
# - I/O 密集用异步（高并发）
# - CPU 密集用同步 + 多进程（避免 GIL）
```

**解读**：
- 第 25 行：`async def` 但内部用同步 DB（取舍）
- 第 50 行：`_load_workflow` 同步数据库查询
- 第 55 行：`fetch_llm_response` 异步 LLM 调用
- **设计意图**：根据场景选择最合适的模型（不要过度异步化）

## 4. 关键要点总结

- **同步/异步**：拿到结果的方式
- **阻塞/非阻塞**：等待时是否干别的
- **四种组合**：同步阻塞、同步非阻塞、异步阻塞、异步非阻塞
- **最常见**：同步阻塞（简单）、异步非阻塞（高性能）
- dify API 层用异步，内部按场景选最合适模型

## 5. 练习题

### 练习 1：基础（必做）

用同步阻塞和异步非阻塞两种方式抓取 10 个 URL，对比耗时。

### 练习 2：进阶

阅读 `api/services/async_workflow_service.py`，说明 dify 为何 API 用异步、内部 DB 查询用同步。

### 练习 3：挑战（选做）

用 `asyncio` + `aiohttp` 实现一个并发爬虫，抓取 100 个 URL 并统计耗时。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/async_workflow_service.py`
- 《UNIX 网络编程》第 6 章 IO 模型

---

**文档版本**：v1.0
**最后更新**：2026-07-13