# 14.5 gRPC 与 Protocol Buffers 入门

> 了解 gRPC 与 Protobuf 的基本概念，能阅读涉及 gRPC 的代码，理解 dify 中可能用到的场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 gRPC 与 REST 的差异
- 掌握 Protobuf 语法（message、service）
- 理解 gRPC 的四种通信模式（一元、服务端流、客户端流、双向流）
- 知道 dify 中 gRPC 的使用现状

## 📚 前置知识

- _common/14-api-protocols/01-http-protocol.md
- 命令行基础

## 1. 核心概念

### 1.1 为什么需要 gRPC？

REST + JSON 是 Web API 主流（REST 见 [22-rest-api-design](./02-rest-api-design.md)，JSON 见 [17-json-processing](../../dify/01-fundamentals/27-json-processing.md)），但有局限：

| 问题 | gRPC 的解决方案 |
|---|---|
| JSON 体积大 | Protobuf 二进制编码，体积小 3-10 倍 |
| HTTP/1.1 队头阻塞 | 基于 HTTP/2 多路复用 |
| 无强类型契约 | `.proto` 文件即契约，自动生成代码 |
| 流式支持弱 | 原生支持四种流模式 |
| 性能 | HTTP/2 + Protobuf，性能远超 REST |

**适用场景**：
- **内部服务间通信**（微服务）
- **移动端与后端**（省流量）
- **实时流式数据**
- **强类型 API 契约**

### 1.2 Protobuf 基础

**`.proto` 文件定义数据结构和服务**：

```protobuf
syntax = "proto3";

package dify.v1;

import "google/protobuf/timestamp.proto";

// 消息定义（数据结构）
message WorkflowRun {
  string id = 1;                                       // 字段编号（不是默认值）
  string workflow_id = 2;
  WorkflowStatus status = 3;
  google.protobuf.Timestamp created_at = 4;
  map<string, string> labels = 5;                       // map 类型
  repeated string tags = 6;                             // 数组
}

enum WorkflowStatus {
  WORKFLOW_STATUS_UNSPECIFIED = 0;                      // 0 保留为未指定值
  WORKFLOW_STATUS_PENDING = 1;
  WORKFLOW_STATUS_RUNNING = 2;
  WORKFLOW_STATUS_SUCCEEDED = 3;
  WORKFLOW_STATUS_FAILED = 4;
}

// 服务定义（RPC 方法）
service WorkflowService {
  // 一元调用
  rpc GetWorkflow(GetWorkflowRequest) returns (WorkflowRun);

  // 服务端流
  rpc StreamWorkflowRuns(StreamRequest) returns (stream WorkflowRun);

  // 客户端流
  rpc BatchCreate(stream WorkflowRun) returns (BatchResponse);

  // 双向流
  rpc Chat(stream ChatMessage) returns (stream ChatReply);
}
```

**字段编号**（=1, =2）：不是默认值，是 Protobuf 二进制编码用的**标识符**，**一旦确定不能修改**。

### 1.3 gRPC 四种通信模式

```
1. Unary（一元）
   Client ──Request──> Server
   Client <──Response── Server

2. Server Streaming（服务端流）
   Client ──Request──> Server
   Client <──Chunk1─── Server
   Client <──Chunk2─── Server
   Client <──Chunk3─── Server

3. Client Streaming（客户端流）
   Client ──Chunk1──> Server
   Client ──Chunk2──> Server
   Client ──Chunk3──> Server
   Client <──Response─ Server

4. Bidirectional Streaming（双向流）
   Client ──Chunk1──> Server
   Client <──Chunk1── Server
   Client ──Chunk2──> Server
   Client <──Chunk2── Server
```

### 1.4 代码生成

```bash
# 安装 protoc 编译器
# Mac: brew install protobuf

# 定义 .proto 文件 workflow.proto

# 生成 Python 代码
python -m grpc_tools.protoc \
    --python_out=. \
    --grpc_python_out=. \
    workflow.proto

# 生成 Go 代码
protoc --go_out=. --go-grpc_out=. workflow.proto
```

生成后的代码包含：
- 数据类（`WorkflowRun`）
- 客户端 stub（同步/异步）
- 服务端接口（继承实现）

## 2. 代码示例

### 2.1 定义 `.proto` 文件

```protobuf
syntax = "proto3";

package dify.v1;

service ChatService {
  // 一元调用：发送消息得到完整回复
  rpc SendMessage(MessageRequest) returns (MessageReply);

  // 服务端流：发送消息得到流式回复
  rpc StreamMessage(MessageRequest) returns (stream MessageChunk);
}

message MessageRequest {
  string query = 1;
  string user_id = 2;
}

message MessageReply {
  string answer = 1;
}

message MessageChunk {
  string delta = 1;
  bool done = 2;
}
```

### 2.2 gRPC 服务端实现（Python）

```python
import grpc
from concurrent import futures

import chat_pb2
import chat_pb2_grpc


class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """实现 .proto 中定义的服务。"""

    def SendMessage(self, request, context):
        """一元调用实现。"""
        return chat_pb2.MessageReply(
            answer=f"你说：{request.query}",
        )

    def StreamMessage(self, request, context):
        """服务端流实现：逐 token 输出（`yield` 生成器见 [14-generator](../../dify/01-fundamentals/14-generator.md)）。"""
        for word in f"你说：{request.query}".split():
            yield chat_pb2.MessageChunk(delta=word, done=False)
        yield chat_pb2.MessageChunk(delta="", done=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
```

### 2.3 gRPC 客户端调用

```python
import grpc
import chat_pb2
import chat_pb2_grpc


def main():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = chat_pb2_grpc.ChatServiceStub(channel)

        # 1. 一元调用
        reply = stub.SendMessage(
            chat_pb2.MessageRequest(query="你好", user_id="u001")
        )
        print(reply.answer)

        # 2. 流式调用
        for chunk in stub.StreamMessage(
            chat_pb2.MessageRequest(query="世界", user_id="u001")
        ):
            print(chunk.delta, end=" ")


if __name__ == "__main__":
    main()
```

### 2.4 常见错误：字段编号不能改

```protobuf
// ❌ 错误：修改了已发布字段的编号
message User {
  string name = 2;   // 原本是 1，改成 2 会破坏兼容性
}

// ✅ 正确：新增字段用新编号
message User {
  string name = 1;
  string email = 2;   // 新增
  // 删字段：保留编号，标记 reserved
  reserved 3;
  reserved "old_field";
}
```

## 3. dify 仓库源码解读

### 3.1 dify 中 gRPC 的使用现状

**dify 后端主要以 REST API + WebSocket/SSE 为主**（WebSocket 见 [23-websocket](./03-websocket.md)，SSE 见 [24-sse](./04-sse.md)）。gRPC 主要出现在以下场景：

**文件位置**：`/Users/xu/code/github/dify/api/dify_agent/`

`dify-agent` 是 dify 的独立子项目，用于管理 Agent 后端，可能用 gRPC 与主后端通信。

**当前 dify 中暂未直接使用 gRPC**——REST + WebSocket 已经能覆盖大多数场景。gRPC 更适合**内部微服务**通信，dify 当前架构是单体 Flask 应用。

### 3.2 dify 的内部 RPC 调用（基于 Celery）

实际上 dify 用 **Celery 任务队列**实现异步 RPC：

**文件位置**：`/Users/xu/code/github/dify/api/tasks/`
**核心代码**（行 1-25）：

```python
"""dify 的 Celery 任务定义（替代 gRPC 的异步 RPC）。"""
from celery import shared_task


@shared_task
def execute_workflow_professional(workflow_data: dict) -> dict:
    """异步执行专业版工作流。

    这个函数可以看作是 gRPC 风格的"远程过程调用"：
    - 调用方：celery.execute_workflow_professional.delay(data)
    - 被调用方：Celery worker 中的此函数
    - 通信媒介：Redis 队列（类似 gRPC 的网络传输）
    """
    from services.workflow.run import WorkflowRunner
    runner = WorkflowRunner(workflow_data)
    return runner.run()
```

**解读**：
- 第 9 行：函数签名是普通 Python，Celery 负责序列化/网络/重试
- **Celery 的通信模式**：
  - 调用方 `.delay(data)` → 入队 → 序列化 JSON → Redis
  - Worker 进程反序列化 → 调用函数 → 返回结果 → 入结果队列
- **与 gRPC 对比**：
  - Celery：基于消息队列（pull 模型），适合异步任务、长时间运行
  - gRPC：基于 RPC 框架（push 模型），适合同步调用、流式响应
- **dify 的选择**：工作流执行通常耗时几十秒到几分钟，Celery 的异步任务模型更合适

### 3.3 dify 的 HTTP/2 支持

**文件位置**：`/Users/xu/code/github/dify/api/gunicorn.conf.py`
**核心代码**（行 1-20）：

```python
# Gunicorn 默认使用 HTTP/1.1
# 如需 HTTP/2（gRPC 必需），需要前置 nginx 或 hypercorn

bind = "0.0.0.0:5001"
worker_class = "gevent"
```

**解读**：
- Gunicorn **不支持 HTTP/2**，dify 主后端跑在 HTTP/1.1 上
- 如果未来要引入 gRPC，需要换成支持 HTTP/2 的 ASGI 服务器（Hypercorn、Uvicorn）或用 nginx 反代
- **当前 dify 中暂未直接使用 gRPC**

## 4. 关键要点总结

- gRPC 是基于 HTTP/2 + Protobuf 的高性能 RPC 框架
- Protobuf 是强类型契约，**字段编号一旦确定不能改**
- 四种通信模式：一元、服务端流、客户端流、双向流
- gRPC 优势：性能高、流式原生、强类型
- gRPC 不适合：浏览器直接调用（需用 grpc-web）、人类调试（需用 grpcurl）
- **dify 中暂未直接使用 gRPC**，异步任务用 Celery，对外接口用 REST + WebSocket/SSE

## 5. 练习题

### 练习 1：基础（必做）

写一个 `.proto` 文件定义 `Workflow` 服务：包含一元方法 `GetWorkflow(id) returns (Workflow)` 和服务端流方法 `StreamWorkflowLogs(id) returns (stream LogEntry)`。

### 练习 2：进阶

对比 gRPC 与 Celery 的通信模型（同步 vs 异步、推 vs 拉、二进制 vs JSON），分析 dify 为什么选择 Celery 而不是 gRPC 处理工作流执行。

### 练习 3：挑战（选做）

用 `grpcio` + `grpcio-tools` 实现一个最小的 gRPC Echo 服务（一元 + 服务端流），客户端用 Python 调用测试。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/`（Celery 任务定义）
- `/Users/xu/code/github/dify/api/gunicorn.conf.py`
- gRPC 官方文档：https://grpc.io/docs/
- Protobuf 指南：https://protobuf.dev/programming-guides/proto3/
- gRPC vs REST 对比：https://www.cncf.io/blog/2020/03/30/grpc-vs-rest/

---

**文档版本**：v1.0
**最后更新**：2026-07-13