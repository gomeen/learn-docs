# 6.7 WebSocket 集群：Redis Pub/Sub

> 掌握 yudao 基于 Redis Pub/Sub 的 WebSocket 集群方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 WebSocket 集群的核心问题
- 掌握 yudao 的 Redis Pub/Sub 方案
- 能在 yudao 中开发 WebSocket
- 了解 STOMP 与原生 WebSocket 的差异

## 📚 前置知识

- WebSocket 基础
- Redis Pub/Sub（详见 [Redis Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)）
- Spring Messaging

## 1. 核心概念

### 1.1 WebSocket 集群的挑战

WebSocket 是**长连接**，每个客户端只连接到一台服务器。
- 消息发送方在 A 服务器
- 接收方在 B 服务器
- **A 不知道怎么推到 B**

### 1.2 解决方案

| 方案 | 原理 |
|------|------|
| 消息广播 | 用 Redis Pub/Sub 中转 |
| Session 共享 | 用 Redis 存 session |
| 一致性哈希 | 路由到固定节点 |

yudao 用 **Redis Pub/Sub**。

## 2. 代码示例

### 2.1 WebSocket 配置

```java
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(myWebSocketHandler(), "/ws/notice")
                .addInterceptors(handshakeInterceptor())
                .setAllowedOrigins("*");
    }
}
```

### 2.2 发送消息

```java
@Resource
private WebSocketMessageSender webSocketMessageSender;

public void notifyUser(Long userId, String message) {
    webSocketMessageSender.send(userId, WebSocketMessageTypeEnum.NOTICE, message);
}
```

## 3. 关键要点总结

- **WebSocket 集群 = Redis Pub/Sub + 每个节点监听**
- **性能优化**：通过 userId 路由，只让目标节点推
- **yudao 抽象** `WebSocketMessageSender` 接口
- **支持** 在线用户、广播、单播

---

**文档版本**：v1.0
**最后更新**：2026-07-13
