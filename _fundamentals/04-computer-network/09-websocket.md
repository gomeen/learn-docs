# 4.2.6 WebSocket 协议

> WebSocket 是浏览器与服务器全双工通信的标准协议。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 WebSocket 与 HTTP 的关系
- 掌握 WebSocket 的握手和帧格式
- 能在 dify 中识别 WebSocket 的应用（流式响应）

## 📚 前置知识

- 04-http-versions.md
- 02-tcp-ip.md

## 1. 核心概念

### 1.1 什么是 WebSocket？

**WebSocket** 是 HTML5 引入的协议，提供浏览器与服务器**全双工**通信。

**特点**：
- 基于 TCP
- 全双工（同时读写）
- 持久连接
- 低延迟（无 HTTP 头开销）

### 1.2 WebSocket vs HTTP

| 特性 | [HTTP](./04-http-versions.md) | WebSocket |
|------|------|-----------|
| 连接 | 短连接 / 持久 | **持久** |
| 通信方向 | 单向（请求-响应） | **双向** |
| 头部开销 | 每次请求 | 仅握手时 |
| 实时性 | 差（轮询） | **好**（推送） |
| 适用 | 普通 Web 请求 | 实时通信 |

### 1.3 WebSocket 握手

**本质：HTTP Upgrade 请求**

```http
GET /chat HTTP/1.1
Host: example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: https://example.com

HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**Sec-WebSocket-Accept 计算**：
```
1. Sec-WebSocket-Key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
2. SHA-1
3. Base64
```

### 1.4 WebSocket 帧格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - + - - - - - - - - - - - - - - - +
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
```

**字段**：
- **FIN**：是否最后一帧
- **opcode**：0x1 文本、0x2 二进制、0x8 关闭、0x9 Ping、0xA Pong
- **MASK**：是否掩码（客户端必须掩码）
- **Payload length**：数据长度

### 1.5 WebSocket 的应用

1. **即时聊天**：微信网页版、Slack
2. **实时协作**：Google Docs、Figma
3. **股票行情**：实时报价
4. **在线游戏**：多人游戏同步
5. **实时监控**：Grafana、Web 控制台

### 1.6 dify 中的 WebSocket / SSE

**dify 用 SSE（Server-Sent Events）实现流式响应**：
- LLM 生成 token → 推送给前端
- 基于 HTTP（单向）
- 浏览器原生 EventSource API 支持

**SSE vs WebSocket**：
- SSE：单向（服务器推），HTTP，文本
- WebSocket：双向，独立协议

## 2. 代码示例

### 2.1 Python WebSocket 客户端

```python
# 文件：websocket_client.py
import asyncio
import websockets

async def chat_client():
    """WebSocket 客户端示例。"""
    uri = "wss://example.com/chat"
    async with websockets.connect(uri) as websocket:
        # 接收欢迎消息
        welcome = await websocket.recv()
        print(f"服务器: {welcome}")

        # 发送消息
        await websocket.send("Hello, WebSocket!")

        # 接收回复
        for _ in range(3):
            response = await websocket.recv()
            print(f"服务器: {response}")

# 运行
# asyncio.run(chat_client())
```

### 2.2 Python WebSocket 服务器

```python
# 文件：websocket_server.py
import asyncio
import websockets

async def echo_handler(websocket, path):
    """回显服务器。"""
    async for message in websocket:
        # 接收客户端消息
        print(f"收到: {message}")
        # 发送回复
        await websocket.send(f"Echo: {message}")

async def main():
    async with websockets.serve(echo_handler, "127.0.0.1", 8765):
        print("WebSocket 服务器启动")
        await asyncio.Future()  # 永久运行

# asyncio.run(main())
```

### 2.3 SSE（Server-Sent Events）

```python
# 文件：sse_demo.py
from flask import Flask, Response
import time

app = Flask(__name__)

@app.route("/stream")
def stream():
    """SSE 流式响应。"""
    def generate():
        for i in range(10):
            # SSE 格式：data: <message>\n\n
            yield f"data: 消息 {i}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")

# 客户端 JavaScript：
# const eventSource = new EventSource('/stream');
# eventSource.onmessage = (e) => console.log(e.data);
```

### 2.4 WebSocket 握手实现

```python
# 文件：ws_handshake.py
import socket
import hashlib
import base64

def compute_websocket_accept(key: str) -> str:
    """计算 WebSocket 握手的 Sec-WebSocket-Accept。"""
    # WebSocket 魔数
    magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    # SHA-1 + Base64
    accept = base64.b64encode(
        hashlib.sha1((key + magic).encode()).digest()
    ).decode()
    return accept

# 测试
key = "dGhlIHNhbXBsZSBub25jZQ=="
print(f"Accept: {compute_websocket_accept(key)}")
# 输出：s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

## 3. dify 仓库源码解读

### 3.1 dify 的流式响应（SSE 思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
**核心代码**（行 100-140）：

```python
from flask import Response, stream_with_context
import json

class WorkflowStreamResponse:
    """dify 的工作流流式响应。

    dify 用 SSE（Server-Sent Events）实现流式响应：
    - LLM 生成 token → 立即推送给前端
    - 用户看到"打字机效果"
    - 类似 ChatGPT 的响应方式

    SSE vs WebSocket 的选择：
    - SSE：单向（服务器推），HTTP/1.1 兼容
    - WebSocket：双向，需要额外协议

    dify 选 SSE：
    - 简单（基于 HTTP）
    - 浏览器原生支持（EventSource）
    - 自动重连
    - 适合 LLM 流式生成（单向）
    """

    def stream_workflow_events(self, workflow_run_id: str):
        """生成工作流事件流。"""
        queue_manager = AppQueueManager(workflow_run_id)

        # SSE 格式：data: <json>\n\n
        while True:
            event = queue_manager.get_event(timeout=30)
            if event is None:
                # 心跳（保持连接）
                yield ": heartbeat\n\n"
                continue

            yield f"data: {json.dumps(event)}\n\n"

            # 结束条件
            if event.get("type") == "workflow_finished":
                break

    def make_response(self, workflow_run_id: str) -> Response:
        """创建 SSE 响应。"""
        return Response(
            stream_with_context(self.stream_workflow_events(workflow_run_id)),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            },
        )


# 前端使用：
# const eventSource = new EventSource('/workflow/123/stream');
# eventSource.onmessage = (e) => {
#   const event = JSON.parse(e.data);
#   // 处理事件（如显示 token）
# };
```

**解读**：
- 第 31 行：`yield "data: <json>\n\n"` 是 SSE 格式
- 第 37 行：心跳包保持连接
- 第 50 行：`X-Accel-Buffering: no` 禁用 Nginx 缓冲
- **设计意图**：用 SSE 实现 LLM 流式响应，简单高效

## 4. 关键要点总结

- **WebSocket**：浏览器与服务器全双工通信
- **握手**：HTTP Upgrade 到 WebSocket 协议
- **帧格式**：FIN、opcode、payload length
- **应用**：聊天、协作、实时数据
- **SSE**：单向流式响应（dify 用）
- dify 用 SSE 实现 LLM 流式响应

## 5. 练习题

### 练习 1：基础（必做）

用 Python `websockets` 库实现一个 echo 服务器和客户端。

### 练习 2：进阶

阅读 `api/core/app/apps/base_app_queue_manager.py`，说明 dify 为何选 SSE 而非 WebSocket。

### 练习 3：挑战（选做）

用 Flask 实现 SSE 流式响应，前端用 EventSource 接收并显示。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
- RFC 6455：WebSocket 协议
- MDN WebSocket：https://developer.mozilla.org/zh-CN/docs/Web/API/WebSocket

---

**文档版本**：v1.0
**最后更新**：2026-07-13