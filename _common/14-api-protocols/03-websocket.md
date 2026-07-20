# 1.4.3 WebSocket 协议

> 掌握 WebSocket 双向通信协议，能用 dify 的实时日志、对话推送能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 WebSocket 与 HTTP 的区别与适用场景
- 掌握 WebSocket 握手过程（HTTP Upgrade）
- 用 Python 编写 WebSocket 客户端和服务端
- 理解 dify 中 WebSocket 的应用场景

## 📚 前置知识

- [HTTP 协议](./01-http-protocol.md)
- [asyncio](../../dify/01-fundamentals/12-async-asyncio.md)（可选）

## 1. 核心概念

### 1.1 为什么需要 WebSocket？

与 SSE 的对比见下文表格；SSE 专题见 [SSE](./04-sse.md)。HTTP 基础见 [HTTP 协议](./01-http-protocol.md)。

HTTP 是**请求-响应**模式：客户端必须主动请求才能获取数据。如果需要服务端**主动推送**（实时消息、行情数据），传统方案：

| 方案 | 问题 |
|---|---|
| 短轮询（每 N 秒 GET 一次） | 大量无效请求，延迟高 |
| 长轮询（hold 连接等待响应） | 服务器资源占用高 |
| SSE（Server-Sent Events） | 只能服务端→客户端 |

**WebSocket** 提供：
- **全双工**通信（双向同时收发）
- **持久连接**（一次握手，长期保持）
- **低开销**（数据帧比 HTTP 头小很多）

### 1.2 WebSocket 握手

WebSocket 通过 HTTP **Upgrade** 头切换协议：

```
客户端请求：
GET /chat HTTP/1.1
Host: api.dify.ai
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13

服务器响应：
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

`101 Switching Protocols` 表示协议切换成功。

### 1.3 数据帧（Frame）

WebSocket 通信以**帧**为单位：

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
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
```

常用 **opcode**：
- `0x1`：文本帧（UTF-8）
- `0x2`：二进制帧
- `0x8`：连接关闭
- `0x9`：Ping
- `0xA`：Pong

### 1.4 适用场景

| 场景 | 推荐方案 |
|---|---|
| 服务端单向推送（聊天回复） | **SSE**（更简单） |
| 服务端单向推送（行情） | SSE 或 WebSocket |
| 双向通信（协同编辑） | **WebSocket** |
| 二进制数据流（音视频） | WebSocket |
| 多用户广播（在线课堂） | WebSocket |
| 简单 RPC 调用 | HTTP |

## 2. 代码示例

### 2.1 Python WebSocket 客户端

示例使用 `async`/`await`（机制见 [asyncio](../../dify/01-fundamentals/12-async-asyncio.md)）；本文关注 WebSocket API。

```python
import asyncio
import websockets

async def chat_client():
    """连接 dify 的 WebSocket 端点（假设存在）。"""
    uri = "ws://localhost:5001/v1/chat/ws"
    async with websockets.connect(uri) as ws:
        # 发送消息
        await ws.send('{"query": "你好", "user": "u001"}')

        # 接收回复（可能多个 chunk）
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30)
                print(f"收到: {msg}")
            except asyncio.TimeoutError:
                print("超时，关闭连接")
                break

asyncio.run(chat_client())
```

### 2.2 Python WebSocket 服务端（用 FastAPI）

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    """WebSocket 聊天端点。"""
    await websocket.accept()
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            query = data.get("query", "")

            # 模拟流式回复
            for word in f"你说：{query}".split():
                await websocket.send_json({"chunk": word})
                await asyncio.sleep(0.1)

            # 标记结束
            await websocket.send_json({"done": True})
    except WebSocketDisconnect:
        print("客户端断开")
```

### 2.3 常见错误：忘记心跳（ping/pong）

```python
# ❌ 错误：长连接空闲被中间设备（nginx、CDN）断开
async with websockets.connect(uri) as ws:
    await ws.recv()   # 等了 60 秒无数据，连接被切断

# ✅ 正确：定期发 ping 维持连接
async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
    while True:
        msg = await ws.recv()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 socketio 服务（用于实时日志）

**文件位置**：`/Users/xu/code/github/dify/api/socketio/__init__.py`
**核心代码**（行 1-30）：

```python
"""Socket.IO 服务：用于实时推送工作流执行日志到前端。"""

from flask_socketio import SocketIO

socketio = SocketIO(
    async_mode="gevent",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)


def init_app(app):
    """把 Socket.IO 绑定到 Flask app。"""
    socketio.init_app(app, message_queue=os.getenv("REDIS_HOST"))

    # 注册命名空间
    from .server import register_handlers
    register_handlers(socketio)
```

**解读**：
- 第 7 行：`async_mode="gevent"` 用 gevent 协程支持高并发
- 第 8 行：`cors_allowed_origins="*"` 允许跨域
- 第 14 行：用 Redis 作为消息队列，让多个 worker 共享 Socket.IO 房间
- **关键设计**：Socket.IO 在 WebSocket 之上增加**自动重连、命名空间、房间**等高级特性，比裸 WebSocket 更好用

### 3.2 dify 的实时日志处理器

**文件位置**：`/Users/xu/code/github/dify/api/socketio/server.py`
**核心代码**（行 1-30）：

```python
from flask import request
from flask_socketio import emit, join_room

from socketio import socketio


@socketio.on("connect", namespace="/workflow")
def on_connect():
    """客户端连接到 /workflow 命名空间。"""
    user_id = request.args.get("user_id")
    if user_id:
        join_room(f"user_{user_id}")
        emit("connected", {"status": "ok"})


@socketio.on("subscribe_workflow_run", namespace="/workflow")
def on_subscribe(data):
    """订阅某个工作流运行的实时日志。"""
    workflow_run_id = data.get("workflow_run_id")
    if workflow_run_id:
        join_room(f"run_{workflow_run_id}")
        emit("subscribed", {"workflow_run_id": workflow_run_id})
```

**解读**：
- 第 7 行：`namespace="/workflow"` 命名空间，类似"频道"
- 第 13 行：`join_room` 把当前连接加入房间，便于定向推送
- 第 21 行：客户端订阅特定 `workflow_run_id`，后续日志推送只发给订阅者
- **关键设计**：用"房间"机制实现"按用户/资源隔离的推送"，避免全员广播

## 4. 关键要点总结

- WebSocket 提供**全双工持久连接**，适合双向实时通信
- 通过 HTTP Upgrade 头切换协议（101 Switching Protocols）
- 数据以**帧**为单位传输，opcode 标识帧类型
- **适用场景**：协同编辑、实时通知、双向 RPC
- **不适用场景**：简单单向推送用 SSE 更简单
- 客户端必须实现心跳（ping/pong）防止连接被中间设备切断
- dify 用 Socket.IO + Redis 实现多 worker 实时日志推送

## 5. 练习题

### 练习 1：基础（必做）

用 `websockets` 写一个最小 Echo 客户端：连接 `wss://echo.websocket.org`，发送任意消息，接收并打印回显。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/socketio/server.py`，理解 dify 中"订阅工作流运行"的完整流程（连接 → 订阅 → 接收日志）。

### 练习 3：挑战（选做）

用 FastAPI 实现一个 WebSocket 聊天服务端，支持多个客户端，每个客户端的消息广播给所有其他客户端（聊天室）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/socketio/__init__.py`
- `/Users/xu/code/github/dify/api/socketio/server.py`
- WebSocket 协议（RFC 6455）：https://datatracker.ietf.org/doc/html/rfc6455
- python-socketio 文档：https://python-socketio.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13