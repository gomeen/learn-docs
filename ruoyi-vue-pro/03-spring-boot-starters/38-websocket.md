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

## 3. ruoyi 仓库源码解读

### 3.1 YudaoWebSocketAutoConfiguration

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/src/main/java/cn/iocoder/yudao/framework/websocket/config/YudaoWebSocketAutoConfiguration.java`

**核心代码**（节选）：

```java
@AutoConfiguration
public class YudaoWebSocketAutoConfiguration {

    @Bean
    public WebSocketMessageSender webSocketMessageSender(RedisMQTemplate redisMQTemplate) {
        return new RedisWebSocketMessageSender(redisMQTemplate);
    }
}
```

### 3.2 RedisWebSocketMessageSender

```java
public class RedisWebSocketMessageSender extends AbstractWebSocketMessageSender {
    private final RedisMQTemplate redisMQTemplate;

    @Override
    public void send(Long userId, String messageType, String message) {
        // 1. 构造消息
        RedisWebSocketMessage msg = new RedisWebSocketMessage()
                .setUserId(userId)
                .setMessageType(messageType)
                .setMessage(message);
        // 2. 通过 Redis Pub/Sub 发送
        redisMQTemplate.send(msg);
    }
}
```

### 3.3 WebSocketMessageListener

```java
@Component
public class WebSocketMessageListener extends AbstractRedisChannelMessageListener<RedisWebSocketMessage> {
    @Override
    public void onMessage(RedisWebSocketMessage message) {
        // 1. 找到本节点的 session
        WebSocketSession session = sessionManager.getSession(message.getUserId());
        if (session != null && session.isOpen()) {
            // 2. 推送到客户端
            session.sendMessage(new TextMessage(message.getMessage()));
        }
    }
}
```

**解读**：
- 所有节点**订阅同一个 Redis Channel**
- 消息来了之后，**本节点**判断 session 是否在本节点
- 是 → 直接推；否 → 忽略

### 3.4 流程图

```
用户 A 发送消息
  ↓
Node 1 收到请求
  ↓
Node 1 通过 redisMQTemplate.send 发送
  ↓
Redis Pub/Sub 广播到所有节点
  ↓
所有 Node 收到消息
  ↓
每个 Node 检查：用户 A 的 session 在我这里吗？
  ↓
Node 2 命中（用户 A 连的是 Node 2）
  ↓
Node 2 推送 WebSocket 消息给用户 A
```

## 4. 关键要点总结

- **WebSocket 集群 = Redis Pub/Sub + 每个节点监听**
- **性能优化**：通过 userId 路由，只让目标节点推
- **yudao 抽象** `WebSocketMessageSender` 接口
- **支持** 在线用户、广播、单播

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中实现"系统通知"功能：管理员发通知 → 推送给所有在线用户。

### 练习 2：进阶

实现"私聊"功能：用户 A 发消息给用户 B。

### 练习 3：挑战（选做）

实现"在线用户列表"：实时展示当前在线用户数和名单。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-websocket/`
- Spring WebSocket 文档：https://docs.spring.io/spring-framework/reference/web/websocket.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
