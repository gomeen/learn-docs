# 5.3 流式输出：SSE 协议实现

> 理解 Server-Sent Events 的文本帧格式、断线行为与 dify 的流式响应编码。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 SSE 与普通 JSON 响应、WebSocket 的差异
- 正确生成 `text/event-stream` 响应并解析事件
- 处理心跳、缓冲、断线重连与错误事件
- 看懂 dify 如何把 Python 生成器转换为 SSE 数据帧

## 📚 前置知识

- SSE 协议基础（详见 [SSE](../../_common/14-api-protocols/04-sse.md)）——本篇侧重 LLM 流式与 dify 编码
- [Python 异步编程](../01-fundamentals/14-async-asyncio.md)
- [OpenAI API 使用](./31-openai-api.md)
- HTTP 响应头、生成器和 JSON（详见 [HTTP 协议](../../_common/14-api-protocols/01-http-protocol.md)、[生成器](../01-fundamentals/16-generator.md)、[JSON](../01-fundamentals/20-json-processing.md)）

## 1. 核心概念

### 1.1 SSE 是什么

SSE（Server-Sent Events）是在一个长连接 HTTP 响应上，由服务器持续向客户端发送文本事件的协议。响应媒体类型是 `text/event-stream`，事件之间用空行分隔：

```text
event: message
id: 42
data: {"answer":"你好"}

```

常用字段：

| 字段 | 含义 |
| --- | --- |
| `data` | 事件负载，可出现多行 |
| `event` | 事件类型；省略时默认为 `message` |
| `id` | 事件 ID，重连时可通过 `Last-Event-ID` 续传 |
| `retry` | 建议客户端等待多少毫秒再重连 |
| `:` | 注释行，常用于心跳 |

JSON 只是 `data` 的常见编码，并不是 SSE 协议本身。

### 1.2 SSE 与 WebSocket

| 维度 | SSE | WebSocket（详见 [WebSocket](../../_common/14-api-protocols/03-websocket.md)） |
| --- | --- | --- |
| 方向 | 服务器到客户端 | 双向 |
| 协议 | 普通 HTTP 流 | HTTP Upgrade 后的帧协议 |
| 浏览器 API | `EventSource` | `WebSocket` |
| 自动重连 | 原生支持 | 应用自行实现 |
| LLM 增量文本 | 非常适合 | 可用但通常更重 |

聊天生成大多是“请求一次、服务器持续返回”，因此 SSE 足够简单。需要客户端频繁实时上行或二进制帧时，再考虑 WebSocket。

### 1.3 生产环境中的关键问题

1. **代理缓冲**：反向代理可能攒够数据才发送，应关闭响应缓冲。
2. **心跳**：长时间没有 token 时发送注释或 ping 事件，避免空闲连接关闭。
3. **断线**：服务器应取消下游模型请求并释放资源。
4. **错误语义**：HTTP 头发出后很难修改，流内错误应使用独立事件。
5. **完整性**：客户端要区分内容、错误与结束，不能把控制事件拼进答案。

## 2. 代码示例

### 2.1 Flask 生成 SSE 响应

```python
# 文件：sse_server.py
import json
import time
from collections.abc import Generator

from flask import Flask, Response

app = Flask(__name__)


def generate() -> Generator[str, None, None]:
    for index, word in enumerate(["SSE", " 让", "答案", "逐步", "到达"]):
        payload = json.dumps({"delta": word}, ensure_ascii=False)
        yield f"event: message\nid: {index}\ndata: {payload}\n\n"
        time.sleep(0.3)
    yield 'event: done\ndata: {"finish_reason":"stop"}\n\n'


@app.get("/stream")
def stream() -> Response:
    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(port=5000, threaded=True)
```

**说明**：启动后执行 `curl -N http://127.0.0.1:5000/stream`。`-N` 禁用 curl 输出缓冲；每个事件必须以两个换行结尾。

### 2.2 浏览器消费自定义事件

```html
<!-- 文件：sse_client.html -->
<pre id="answer"></pre>
<script>
  const answer = document.querySelector('#answer')
  const source = new EventSource('http://127.0.0.1:5000/stream')

  source.addEventListener('message', (event) => {
    const payload = JSON.parse(event.data)
    answer.textContent += payload.delta
  })

  source.addEventListener('done', (event) => {
    console.log('completed', JSON.parse(event.data))
    source.close()
  })

  source.onerror = () => {
    console.error('stream disconnected')
    source.close()
  }
</script>
```

**说明**：命名事件要用 `addEventListener` 监听。显式 `close()` 可阻止完成后继续自动重连。

## 3. 关键要点总结

- SSE 是基于 HTTP 的服务器单向文本事件流，事件由空行分隔。
- `data`、`event`、`id`、`retry` 各有职责，多行 `data` 需按规范合并。
- LLM 流式输出应显式区分内容增量、结束与错误事件。
- 代理缓冲、空闲超时、客户端断线和资源取消是上线前必须验证的问题。
- dify 通过生成器保持惰性传输，再将领域事件编码为 SSE 帧。

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
