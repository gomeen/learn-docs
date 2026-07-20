# 14 - API 与应用层协议（工程向）

> 接口设计与实时通信的**工程用法**。  
> HTTP/TCP 协议栈与报文语义的 **Mastery** 在 [`../../_fundamentals/04-computer-network/`](../../_fundamentals/04-computer-network/)。

## 📐 分层

| 内容 | 归属 |
|------|------|
| OSI/TCP、HTTP 版本演进、状态码/Header 全解、HTTPS 握手、WebSocket 协议细节 | `_fundamentals/04-computer-network` |
| REST 设计、SSE 流式、gRPC 选型与用法；HTTP 工程速查 | **本分类** |

## 知识点

- [ ] [1.1 HTTP/HTTPS 工程速查](./01-http-protocol.md) · 深入见 [计算机网络 · HTTP](../../_fundamentals/04-computer-network/)
- [ ] [1.2 REST API 设计规范与最佳实践](./02-rest-api-design.md) ← **本层 Mastery**
- [ ] [1.3 WebSocket（工程）](./03-websocket.md) · 协议细节见 [fundamentals WebSocket](../../_fundamentals/04-computer-network/09-websocket.md)
- [ ] [1.4 Server-Sent Events（SSE）与流式响应](./04-sse.md) ← **本层 Mastery**
- [ ] [1.5 gRPC 与 Protocol Buffers 入门](./05-grpc-protobuf.md) ← **本层 Mastery**

## 🔗 项目特定实现

- **dify（Python）**：LLM 流式 [`../../dify/06-llm-and-ai/`](../../dify/06-llm-and-ai/)；Flask 路由 [`../../dify/02-backend/`](../../dify/02-backend/)

## 🔗 相关分类

- 命令行调试：[`../13-linux-shell/04-network-commands.md`](../13-linux-shell/04-network-commands.md)
- 认证：[`../07-authentication/`](../07-authentication/)
