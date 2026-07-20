# 1.4.4 Server-Sent Events（SSE）与流式响应

> 掌握 SSE 协议，能用 dify 的流式响应能力，让前端实时看到 LLM 生成的每个 token。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SSE 与 WebSocket 的区别与适用场景
- 掌握 SSE 协议格式（data: ... \n\n）
- 在 Flask / FastAPI 中实现 SSE 端点
- 看懂 dify 中流式响应的完整链路

## 📚 前置知识

- [HTTP 协议](./01-http-protocol.md)
- [生成器](../../dify/01-fundamentals/14-generator.md)

## 1. 核心概念

### 1.1 SSE 是什么？

**Server-Sent Events**（SSE）是 HTML5 规范定义的**服务端单向推送**协议：

- 基于 HTTP（普通 HTTP 连接）
- 服务端可以**持续发送**多个事件
- 自动重连机制
- 浏览器原生 `EventSource` API 支持

### 1.2 SSE vs WebSocket

WebSocket 专题见 [WebSocket](./03-websocket.md)。

| 特性 | SSE | WebSocket |
|---|---|---|
| 通信方向 | 服务端 → 客户端（单向） | 双向 |
| 协议基础 | HTTP | WebSocket |
| 自动重连 | 浏览器原生支持 | 需手动实现 |
| 数据格式 | 文本（UTF-8） | 文本 / 二进制 |
| 适用场景 | LLM 流式输出、行情、通知 | 协同编辑、双向 RPC |

**dify 的流式对话用 SSE**，因为 LLM 回复是单向推送，无需客户端频繁发消息。

### 1.3 SSE 协议格式

SSE 事件以 `data: ...\n\n` 形式发送：

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"chunk": "你好"}

data: {"chunk": "，"}

data: {"chunk": "世界"}

: heartbeat（注释行，以 : 开头，客户端忽略）

data: {"done": true}

```

**关键字段**：
- `data:`：消息内容
- `event:`：事件类型（自定义）
- `id:`：事件 ID（用于断线重连恢复）
- `: comment`：注释（心跳）
- `\n\n`：消息结束（**两个换行符**）

### 1.4 SSE 完整流程

```
1. 客户端：GET /v1/chat-messages?stream=true
2. 服务器：200 OK, Content-Type: text/event-stream
3. 服务器：持续发送 data: {...}\n\n
4. 服务器：发送 data: [DONE]\n\n 或关闭连接
5. 客户端：EventSource 自动处理，调用回调函数
```

## 2. 代码示例

### 2.1 Flask SSE 端点

流式输出依赖**生成器** `yield`（详见 [生成器](../../dify/01-fundamentals/14-generator.md)）；本文关注 SSE 协议格式。

```python
from flask import Flask, Response, stream_with_context
import time

app = Flask(__name__)


@app.route("/sse/chat")
def sse_chat():
    """流式回复端点。"""
    def generate():
        # 模拟 LLM 逐 token 输出
        for word in ["你好", "，", "世界", "！"]:
            yield f"data: {{'chunk': '{word}'}}\n\n"
            time.sleep(0.3)

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
```

### 2.2 JavaScript 客户端

```javascript
// 浏览器原生 EventSource
const source = new EventSource("/v1/chat-messages?user=u001");

source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.done) {
        source.close();
        return;
    }
    console.log("收到 chunk:", data.chunk);
    // 追加到聊天界面
};

source.onerror = (event) => {
    console.error("SSE 错误", event);
};

// 关闭连接
source.close();
```

### 2.3 FastAPI SSE 端点

异步版本使用 `async`/`await`（详见 [asyncio](../../dify/01-fundamentals/12-async-asyncio.md)）与异步生成器（生成器见上文链接）。

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


async def chat_stream():
    """异步流式生成器。"""
    for word in ["Hello", ",", " world", "!"]:
        yield f"data: {word}\n\n"
        await asyncio.sleep(0.3)
    yield "data: [DONE]\n\n"


@app.get("/v1/chat")
async def chat():
    return StreamingResponse(
        chat_stream(),
        media_type="text/event-stream",
    )
```

### 2.4 常见错误：nginx 缓冲

```bash
# ❌ 问题：nginx 默认缓冲 SSE，导致客户端看不到流式输出
# 现象：所有 chunk 一次性到达，丢失"流式"效果

# ✅ 解决 1：response header 加 X-Accel-Buffering: no
# ✅ 解决 2：nginx 配置
location /v1/chat-messages {
    proxy_buffering off;
    proxy_cache off;
}
```

## 3. dify 仓库源码解读

### 3.1 dify 的流式响应 Controller

**文件位置**：`/Users/xu/code/github/dify/api/controllers/service_api/app/completion.py`
**核心代码**（行 1-35）：

```python
from flask_restx import Namespace, Resource

completion_ns = Namespace("completion", description="Completion API")


@completion_ns.route("/messages")
class CompletionApi(Resource):
    """Completion 消息端点，支持流式响应。"""

    def post(self):
        """发送消息，返回流式或阻塞响应。

        请求体：
        {
            "inputs": {...},
            "query": "你好",
            "user": "user-001",
            "response_mode": "streaming"   # 或 "blocking"
        }
        """
        # 1. 解析请求参数
        response_mode = request.json.get("response_mode", "blocking")

        # 2. 调用应用服务生成回复
        app_service = AppCompletionService()
        if response_mode == "streaming":
            return Response(
                app_service.stream_run(...),
                mimetype="text/event-stream",
                headers={"X-Accel-Buffering": "no"},
            )
        else:
            return app_service.blocking_run(...)
```

**解读**：
- 第 19 行：`response_mode` 决定返回流式还是阻塞响应
- 第 24-28 行：流式模式下返回 `Response` 对象 + `text/event-stream` MIME
- 第 28 行：`X-Accel-Buffering: no` 是 nginx 友好的关键 header
- **关键设计**：用同一端点支持两种模式，前端按需选择

### 3.2 dify 的流式响应生成器

**文件位置**：`/Users/xu/code/github/dify/api/services/app_generate_service.py`
**核心代码**（行 1-30）：

```python
from collections.abc import Generator

class AppGenerateService:
    """应用生成服务：把 LLM 输出转换为 SSE 流。"""

    def stream_run(self, app_model, query, user, inputs) -> Generator[str, None, None]:
        """流式生成回复（SSE 格式）。"""
        # 1. 订阅 LLM 输出流
        for chunk in self._call_llm_stream(app_model, query, user, inputs):
            # 2. 每个 chunk 转成 SSE 格式
            yield f"data: {chunk.model_dump_json()}\n\n"

        # 3. 结束事件
        yield "data: [DONE]\n\n"

    def _call_llm_stream(self, app_model, query, user, inputs) -> Generator:
        """调用 LLM 的内部流式生成器。"""
        # 实际调用 dify 的 model_runtime，流式产出
        ...
```

**解读**：
- 第 8 行：`Generator[str, None, None]`——产出 str，不接收 send，无返回值
- 第 14 行：每次 `yield` 一个 SSE 格式字符串（`data: ...\n\n`）
- 第 18 行：结束发 `[DONE]` 标记（约定）
- **关键设计**：把"生成 LLM 回复"和"序列化 SSE"两件事分离，便于测试

### 3.3 SSE 心跳保活

**文件位置**：`/Users/xu/code/github/dify/api/services/app_generate_service.py`
**核心代码**（行 30-50）：

```python
def stream_run_with_heartbeat(self, ...) -> Generator[str, None, None]:
    """带心跳的流式生成（防止长连接被切断）。"""
    last_chunk_time = time.time()

    for chunk in self._call_llm_stream(...):
        # 每 15 秒发一个心跳（注释行）
        if time.time() - last_chunk_time > 15:
            yield ": heartbeat\n\n"
            last_chunk_time = time.time()

        yield f"data: {chunk.model_dump_json()}\n\n"

    yield "data: [DONE]\n\n"
```

**解读**：
- 第 5-9 行：每 15 秒发一个 SSE 注释行（`: heartbeat\n\n`）
- 第 10 行：注释行客户端会忽略，但能维持 TCP 连接
- **关键设计**：LLM 慢响应（>30 秒）时，心跳防止 nginx/浏览器超时切断连接

## 4. 关键要点总结

- SSE 是**单向** HTTP 推送协议，适合 LLM 流式输出
- 协议格式：`data: <内容>\n\n`（**两个换行符**）
- MIME 类型必须是 `text/event-stream`
- 必须设置 `X-Accel-Buffering: no` 禁用 nginx 缓冲
- 长连接必须**定期心跳**（注释行或 ping）
- 结束标记约定：`data: [DONE]\n\n`
- dify 流式对话用 SSE，生成器负责产出 chunk，Controller 转 SSE 格式

## 5. 练习题

### 练习 1：基础（必做）

写一个 Flask SSE 端点 `/sse/counter`，每 1 秒推送递增数字，10 秒后结束。客户端用 curl `-N` 测试。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/controllers/service_api/app/completion.py`，画出"用户请求 → Controller → Service → LLM → SSE 输出"的完整时序图。

### 练习 3：挑战（选做）

实现一个异步 SSE 中间件：自动给所有 SSE 响应注入心跳（每 15 秒），并支持客户端通过 query 参数 `?heartbeat=0` 关闭。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/service_api/app/completion.py`
- `/Users/xu/code/github/dify/api/services/app_generate_service.py`
- HTML5 SSE 规范：https://html.spec.whatwg.org/multipage/server-sent-events.html
- MDN EventSource：https://developer.mozilla.org/zh-CN/docs/Web/API/EventSource

---

**文档版本**：v1.0
**最后更新**：2026-07-13