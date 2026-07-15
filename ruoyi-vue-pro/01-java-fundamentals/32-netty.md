# 1.4.9 Netty 网络编程

> 理解 Netty 的核心组件与 Reactor 模型，能读懂 Redisson、Dubbo 等基于 Netty 的框架源码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Reactor 线程模型（单线程 / 多线程 / 主从多线程）
- 掌握 Netty 的核心组件：Bootstrap、Channel、ChannelHandler、EventLoop
- 能写一个简单的 Netty Echo 服务器
- 在 ruoyi-vue-pro 中识别 Netty 的间接使用（Redisson、Vert.x、Spring WebFlux 客户端）

## 📚 前置知识

- [21-thread.md](./21-thread.md)：线程基础
- [22-thread-pool.md](./22-thread-pool.md)：线程池
- [18-jvm-memory.md](./18-jvm-memory.md)：JVM 内存
- Java NIO（Buffer、Channel、Selector）

> **重要**：ruoyi-vue-pro 当前 `master` 分支是 **JDK 8 / Spring Boot 2.7**，**业务代码不直接使用 Netty**，但 `yudao-module-iot-gateway` 通过 **Vert.x MQTT**（底层 Netty）实现了 IoT 设备协议网关，同时 `yudao-module-ai` 的 WebClient（底层 reactor-netty）也间接依赖 Netty。本节结合 IoT 网关源码讲解。

## 1. 核心概念

### 1.1 传统 BIO 的问题

```
传统 BIO 模型：一个连接一个线程

Client1 ─┐
Client2 ─┼─→ ServerSocket ─→ Thread1 (阻塞 read)
Client3 ─┤                  Thread2 (阻塞 read)
...      │                  Thread3 (阻塞 read)
ClientN ─┘                  ...
                            ↑ N 个连接 = N 个线程 = OOM
```

**Netty 的解决方案**：基于 **NIO + Reactor 模式**，用一个（或少量）线程处理成千上万的连接。

### 1.2 Reactor 模型演进

#### 单线程 Reactor

```
                  Single Thread
                  ┌──────────────────────┐
                  │  Selector            │
                  │  Dispatcher (run)    │
Client ──→ Acceptor ──→ Read ──→ Process ──→ Write
                  └──────────────────────┘
                          ↑
                  1 个线程处理所有 I/O + 业务逻辑
                  适合：业务极快（微秒级）的场景
```

#### 主从多线程 Reactor（Netty 默认）

```
                ┌──── Main Reactor (1 thread) ────┐
                │  Selector (Accept)              │
                │  Acceptor                       │
                └─────────┬───────────────────────┘
                          │ 新连接 → 注册到 Sub Reactor
                          ↓
       ┌──────────┬──────────┬──────────┐
       ↓          ↓          ↓          ↓
    Sub1        Sub2        Sub3        Sub4 ...  (N = CPU 核数 * 2)
   Selector    Selector    Selector    Selector
   Read/Write  Read/Write  Read/Write  Read/Write
       ↓
   业务处理（可丢到业务线程池）
```

### 1.3 Netty 核心组件

| 组件 | 职责 |
|------|------|
| **Channel** | 网络连接（一个连接一个 Channel） |
| **EventLoop** | 处理 Channel I/O 的线程（绑定到 Selector） |
| **ChannelHandler** | 业务逻辑（如编解码、心跳、业务处理） |
| **ChannelPipeline** | 链式容器，按顺序执行多个 Handler |
| **Bootstrap / ServerBootstrap** | 启动引导类，配置 Channel、Handler 等 |
| **ByteBuf** | Netty 自定义的字节容器，比 NIO ByteBuffer 更易用 |
| **ChannelFuture** | 异步操作的结果（Netty 所有 I/O 异步） |

### 1.4 Netty vs JDK NIO

| 维度 | JDK NIO | Netty |
|------|---------|-------|
| API 复杂度 | 高（Selector/Buffer 繁琐） | 简洁（Builder + Handler） |
| 线程模型 | 需自己实现 | 内置主从 Reactor |
| 协议支持 | 需自己实现 | 内置 HTTP/WebSocket/Protobuf 等 |
| 内存管理 | ByteBuffer（需手动 flip/clear） | ByteBuf（引用计数，零拷贝） |
| 性能调优 | 需自己摸索 | 经过大规模生产验证 |

### 1.5 ByteBuf 的设计亮点

```
ByteBuf 由 readerIndex / writerIndex 两个指针划分：

+-------------------+----------------+----------------+
| discardable bytes |  readable bytes|  writable bytes |
+-------------------+----------------+----------------+
                   ↑                ↑
              readerIndex      writerIndex

对比 JDK ByteBuffer：单一 position 指针，flip() 切换读写模式易出错
```

**Reference Count（引用计数）**：基于池化的 ByteBuf 通过 `refCnt()` 防止内存泄漏，`release()` 必须调用。

### 1.6 ChannelPipeline 的责任链

> 📌 **Sighting**：责任链模式完整讲解见 [责任链](../../_fundamentals/06-design-patterns/17-chain.md)。此处只看 Netty 里「Handler 串行处理入站/出站事件」的用法。

```
Inbound（入站）：网络 → 应用
  ByteToMessageDecoder → MessageDecoder → BusinessHandler → ...
  
Outbound（出站）：应用 → 网络
  MessageEncoder → MessageToByteEncoder → ...

入站从 head 向 tail 传播；出站从 tail 向 head 传播
```

## 2. 代码示例

### 2.1 Netty Echo 服务器

```java
// 文件：NettyEchoServer.java
import io.netty.bootstrap.ServerBootstrap;
import io.netty.buffer.ByteBuf;
import io.netty.channel.*;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;

public class NettyEchoServer {
    public static void main(String[] args) throws InterruptedException {
        // bossGroup：负责接收连接（1 个线程足够）
        NioEventLoopGroup bossGroup = new NioEventLoopGroup(1);
        // workerGroup：负责处理 I/O（默认 2 * CPU 核数）
        NioEventLoopGroup workerGroup = new NioEventLoopGroup();

        try {
            ServerBootstrap b = new ServerBootstrap();
            b.group(bossGroup, workerGroup)
             .channel(NioServerSocketChannel.class)
             .childHandler(new ChannelInitializer<SocketChannel>() {
                 @Override
                 protected void initChannel(SocketChannel ch) {
                     ch.pipeline().addLast(new EchoServerHandler());
                 }
             })
             .option(ChannelOption.SO_BACKLOG, 128)
             .childOption(ChannelOption.SO_KEEPALIVE, true);

            // 绑定端口，同步等待
            ChannelFuture f = b.bind(8080).sync();
            System.out.println("Echo 服务器启动，端口 8080");
            f.channel().closeFuture().sync();  // 阻塞直到 Channel 关闭
        } finally {
            workerGroup.shutdownGracefully();
            bossGroup.shutdownGracefully();
        }
    }

    // 业务 Handler
    static class EchoServerHandler extends ChannelInboundHandlerAdapter {
        @Override
        public void channelRead(ChannelHandlerContext ctx, Object msg) {
            ByteBuf in = (ByteBuf) msg;
            System.out.println("Server received: " + in.toString(io.netty.util.CharsetUtil.UTF_8));
            // 回写数据
            ctx.write(in);
        }

        @Override
        public void channelReadComplete(ChannelHandlerContext ctx) {
            ctx.writeAndFlush(Unpooled.EMPTY_BUFFER);  // 一次性 flush
        }

        @Override
        public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
            cause.printStackTrace();
            ctx.close();
        }
    }
}
```

### 2.2 Netty HTTP 服务器

```java
// 文件：NettyHttpServer.java
import io.netty.bootstrap.ServerBootstrap;
import io.netty.buffer.Unpooled;
import io.netty.channel.*;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.http.*;
import java.nio.charset.StandardCharsets;

public class NettyHttpServer {
    public static void main(String[] args) throws InterruptedException {
        NioEventLoopGroup boss = new NioEventLoopGroup(1);
        NioEventLoopGroup worker = new NioEventLoopGroup();
        try {
            ServerBootstrap b = new ServerBootstrap();
            b.group(boss, worker)
             .channel(NioServerSocketChannel.class)
             .childHandler(new ChannelInitializer<SocketChannel>() {
                 @Override
                 protected void initChannel(SocketChannel ch) {
                     ch.pipeline().addLast(new HttpServerCodec());         // HTTP 编解码
                     ch.pipeline().addLast(new HttpObjectAggregator(1024 * 1024)); // 聚合为 FullHttpRequest
                     ch.pipeline().addLast(new SimpleHttpHandler());
                 }
             });
            ChannelFuture f = b.bind(8080).sync();
            f.channel().closeFuture().sync();
        } finally {
            boss.shutdownGracefully();
            worker.shutdownGracefully();
        }
    }

    static class SimpleHttpHandler extends SimpleChannelInboundHandler<FullHttpRequest> {
        @Override
        protected void channelRead0(ChannelHandlerContext ctx, FullHttpRequest req) {
            String response = "{\"code\":0,\"msg\":\"OK\",\"data\":\"Hello Netty\"}";
            FullHttpResponse resp = new DefaultFullHttpResponse(
                    HttpVersion.HTTP_1_1, HttpResponseStatus.OK,
                    Unpooled.copiedBuffer(response, StandardCharsets.UTF_8));
            resp.headers().set(HttpHeaderNames.CONTENT_TYPE, "application/json");
            resp.headers().set(HttpHeaderNames.CONTENT_LENGTH, response.length());
            ctx.writeAndFlush(resp);
        }
    }
}
```

### 2.3 自定义协议编解码

```java
// 文件：CustomMessage.java + CustomCodec.java
// 自定义消息格式：[长度(4B)][魔数(4B)][类型(1B)][数据(N)]

public class CustomMessage {
    public static final int MAGIC = 0xCAFEBABE;
    private byte type;
    private byte[] data;

    public CustomMessage(byte type, byte[] data) {
        this.type = type;
        this.data = data;
    }

    // getters/setters
}
```

```java
// 文件：CustomMessageDecoder.java
import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.ByteToMessageDecoder;

import java.util.List;

public class CustomMessageDecoder extends ByteToMessageDecoder {
    private static final int HEADER_LENGTH = 4 + 4 + 1;

    @Override
    protected void decode(ChannelHandlerContext ctx, ByteBuf in, List<Object> out) {
        if (in.readableBytes() < HEADER_LENGTH) return;

        in.markReaderIndex();
        int length = in.readInt();
        int magic = in.readInt();
        if (magic != CustomMessage.MAGIC) {
            ctx.close();  // 协议错误，关闭连接
            return;
        }
        if (in.readableBytes() < length) {
            in.resetReaderIndex();
            return;
        }
        byte type = in.readByte();
        byte[] data = new byte[length - 1];
        in.readBytes(data);
        out.add(new CustomMessage(type, data));
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

> ruoyi-vue-pro **未直接使用 Netty**，但通过 Redisson、Vert.x、OkHttp 等三方库间接依赖 Netty。理解 Netty 有助于排查这些库的底层问题。

### 3.1 Netty 在 ruoyi-vue-pro 的依赖链

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-dependencies/pom.xml`
**核心代码**（行 97-103，BOM 引入 Netty）：

```xml
97   <dependency>
98       <groupId>io.netty</groupId>
99       <artifactId>netty-bom</artifactId>
100      <version>${netty.version}</version>
101      <type>pom</type>
102      <scope>import</scope>
103  </dependency>
```

**第 73 行**：`netty.version` 在 properties 中定义为 `4.2.15.Final`。

**解读**：
- Netty 通过 BOM 统一管理版本，所有子模块自动获得一致的 Netty 版本
- **BOM（Bill of Materials）**：Spring Boot / Redisson / Vert.x 都依赖 Netty，通过 BOM 强制版本对齐

### 3.2 Redisson 中的 Netty 应用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/pom.xml`

```xml
18  <dependencies>
19      <dependency>
20          <groupId>cn.iocoder.boot</groupId>
21          <artifactId>yudao-common</artifactId>
22      </dependency>
24      <!-- DB 相关 -->
25      <dependency>
26          <groupId>org.redisson</groupId>
27          <artifactId>redisson-spring-boot-starter</artifactId>
28      </dependency>
29      <dependency>
30          <groupId>org.redisson</groupId>
31          <artifactId>redisson-spring-data-27</artifactId>
32      </dependency>
```

**Redisson → Netty 链路**：

```
ruoyi-vue-pro → Redisson Client → Redis 通信
                              ↓
                          Netty（异步 I/O 客户端）
                              ↓
                          Redis Server
```

**解读**：
- Redisson 用 Netty 作为底层网络客户端，所以 ruoyi 的所有 Redis 调用（分布式锁、分布式限流、分布式集合）都走 Netty
- **诊断价值**：遇到 Redis 连接问题时（如 ConnectionTimeoutException），需要懂 Netty 才能看懂堆栈
- **典型 Netty 异常**：`io.netty.channel.ConnectTimeoutException`、`io.netty.handler.timeout.ReadTimeoutException`

### 3.3 Vert.x MQTT Broker 中的 Netty 应用（EMQX 直连模式）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/emqx/IotEmqxProtocol.java`
**核心代码**（行 16, 512-520）：

```java
16  import io.netty.handler.codec.mqtt.MqttQoS;

// ...

512 public void publishMessage(String topic, byte[] payload) {
513     if (mqttClient == null || !mqttClient.isConnected()) {
514         log.warn("[publishMessage][IoT EMQX 协议 {} MQTT Client 未连接, 无法发布消息]", getId());
515         return;
516     }
517     MqttQoS qos = MqttQoS.valueOf(emqxConfig.getMqttQos());
518     mqttClient.publish(topic, Buffer.buffer(payload), qos, false, false)
519             .onFailure(e -> log.error("[publishMessage][IoT EMQX 协议 {} 发布失败, topic: {}]", getId(), topic, e));
520 }
```

**解读**：
- **第 16 行**：直接 import Netty 的 `MqttQoS` 枚举（用于 QoS 等级定义：AT_MOST_ONCE / AT_LEAST_ONCE / EXACTLY_ONCE）
- **第 518 行**：`mqttClient.publish(...)` 返回 Vert.x 的 `Future<Void>`（异步），通过 `.onFailure(...)` 链式处理失败
- **链路**：ruoyi-vue-pro IoT 模块 → Vert.x MQTT 客户端 → Netty MQTT 编解码 → TCP → EMQX Broker
- **Vert.x 内部用 Netty 实现 TCP/MQTT 编解码**，所以 Netty 是 ruoyi-vue-pro IoT 设备的底层网络栈
- **设计意图**：MQTT QoS 等级用 Netty 枚举，避免重复定义

### 3.4 IoT MQTT Server 模式：处理设备连接和 ACL 订阅

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/mqtt/IotMqttProtocol.java`
**核心代码**（行 22-23, 218-268）：

```java
22  import io.netty.handler.codec.mqtt.MqttConnectReturnCode;
23  import io.netty.handler.codec.mqtt.MqttTopicSubscription;

// ...

218 private void handleEndpoint(MqttEndpoint endpoint) {
219     // 1. 如果是注册请求，注册待认证连接；否则走正常认证流程
220     String clientId = endpoint.clientIdentifier();
221     if (StrUtil.endWith(clientId, AUTH_TYPE_REGISTER)) {
222         registerHandler.handleRegister(endpoint);
223         return;
224     } else {
225         if (!authHandler.handleAuthenticationRequest(endpoint)) {
226             endpoint.reject(MqttConnectReturnCode.CONNECTION_REFUSED_BAD_USER_NAME_OR_PASSWORD);
227             return;
228         }
229     }
230
231     // 2.1 设置异常和关闭处理器
232     endpoint.exceptionHandler(ex -> {
233         log.warn("[handleEndpoint][连接异常...]", ...);
234         endpoint.close();
235     });
236
237     // 3.1 设置消息处理器
238     endpoint.publishHandler(message -> processMessage(endpoint, message));
239
240     // 4.1 设置订阅处理器（带 ACL 校验）
241     endpoint.subscribeHandler(subscribe -> {
242         List<MqttQoS> grantedQoSLevels = new ArrayList<>();
243         for (MqttTopicSubscription sub : subscribe.topicSubscriptions()) {
244             String topicName = sub.topicName();
245             if (connectionInfo != null && IotMqttTopicUtils.isTopicSubscribeAllowed(
246                     topicName, connectionInfo.getProductKey(), connectionInfo.getDeviceName())) {
247                 grantedQoSLevels.add(sub.qualityOfService());
248             } else {
249                 log.warn("[handleEndpoint][订阅被拒绝，客户端 ID: {}，主题: {}]", clientId, topicName);
250                 grantedQoSLevels.add(MqttQoS.FAILURE);
251             }
252         }
253         endpoint.subscribeAcknowledge(subscribe.messageId(), grantedQoSLevels);
254     });
255 }
```

**解读**：
- **第 22-23 行**：直接 import Netty 的 `MqttConnectReturnCode`（连接拒绝原因枚举）和 `MqttTopicSubscription`（订阅主题模型）
- **第 226 行**：用 Netty 的 `MqttConnectReturnCode.CONNECTION_REFUSED_BAD_USER_NAME_OR_PASSWORD` 作为拒绝连接的错误码（标准 MQTT 协议值）
- **第 244-251 行**：**关键 ACL 校验** —— 设备只能订阅自己有权限的主题，否则用 `MqttQoS.FAILURE`（值为 0x80）告诉客户端订阅被拒
- **第 238 行**：`publishHandler` 是 Vert.x 的回调式 API（底层是 Netty ChannelInboundHandler）
- **架构角色**：这是 **MQTT Broker 模式**（不是 3.3 的 Client 模式）—— ruoyi 自己作为 Broker 接收设备的 MQTT 连接
- **业务场景**：物联网设备成千上万，每个设备的 Topic 必须按 productKey/deviceName 隔离，否则可能越权订阅

### 3.5 IoT 模块的 Vert.x + Netty 依赖

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/pom.xml`
**核心代码**（行 43-53）：

```xml
43 <!-- 工具类相关 -->
44 <dependency>
45     <groupId>io.vertx</groupId>
46     <artifactId>vertx-web</artifactId>
47 </dependency>
48
49 <!-- MQTT 相关 -->
50 <dependency>
51     <groupId>io.vertx</groupId>
52     <artifactId>vertx-mqtt</artifactId>
53 </dependency>
```

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-dependencies/pom.xml`（properties 段）

```xml
73  <netty.version>4.2.15.Final</netty.version>
74  <mqtt.version>1.2.5</mqtt.version>
75  <vertx.version>4.5.26</vertx.version>
```

**解读**：
- **第 45、51 行**：Vert.x 提供 MQTT/Web 支持（Vert.x 内部基于 Netty）
- **`vertx.version = 4.5.26`**：与 Netty 4.2.x 版本配套
- **依赖链**：ruoyi-vue-pro → vertx-mqtt → Netty（MQTT codec + TCP transport）
- **无显式 `netty-*` 依赖**：因为 Vert.x 已经传递依赖，所有 Netty 类都可通过 Vert.x 的 API 间接使用
- **常见 Netty 调优点**（即使不直接用也要懂）：
  - `CONNECT_TIMEOUT_MILLIS`：MQTT 连接超时
  - `SO_KEEPALIVE`：TCP Keep-Alive
  - `TCP_NODELAY`：禁用 Nagle 算法（低延迟）
  - `WRITE_BUFFER_HIGH_WATER_MARK` / `WRITE_BUFFER_LOW_WATER_MARK`：流量控制

### 3.6 业务代码不直接用 Netty

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`（典型 Web 异常处理）

```java
/**
 * Web 全局异常处理
 * ruoyi 业务代码用 Spring MVC（Tomcat Servlet），不直接接触 Netty
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ServiceException.class)
    public CommonResult<?> handleServiceException(ServiceException ex) {
        log.error("[业务异常]", ex);
        return CommonResult.error(ex.getCode(), ex.getMessage());
    }

    @ExceptionHandler(Exception.class)
    public CommonResult<?> handleException(Exception ex) {
        log.error("[系统异常]", ex);
        return CommonResult.error(GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR);
    }
}
```

**解读**：
- ruoyi 业务代码运行在 **Tomcat 之上**（Servlet 阻塞模型）
- 不直接接触 Netty，但底层 Tomcat 也用 NIO Selector（Java NIO）
- 真正直接用 Netty 的是 **IoT 网关模块**（MQTT 编解码）和 **AI 模块**（WebClient / reactor-netty HTTP 客户端）
- 如果未来想换成 Spring WebFlux + Netty，可参考：[33-reactive.md](./33-reactive.md)

## 4. 关键要点总结

- **Netty** 是基于 **Reactor 主从多线程模型** 的高性能 NIO 框架
- **三大核心**：Channel（连接）/ EventLoop（线程）/ ChannelHandler（业务逻辑）
- **ByteBuf**：比 JDK ByteBuffer 更易用，支持零拷贝、引用计数
- **ChannelPipeline**：责任链模式，inbound 自 head → tail，outbound 自 tail → head
- ruoyi-vue-pro **业务代码不直接用 Netty**，但通过 Redisson、Vert.x MQTT、reactor-netty（WebClient 底层）间接使用
- **IoT 网关**（`yudao-module-iot-gateway`）直接 import Netty 的 MQTT 枚举（MqttQoS、MqttConnectReturnCode、MqttTopicSubscription）—— 是少有的 Netty 直接使用场景
- **应用场景**：Redis 客户端、RPC 框架（Dubbo/gRPC）、IoT 网关、游戏服务器

## 5. 练习题

### 练习 1：基础（必做）

用 Netty 实现一个 **Echo 客户端**：
- 启动后连接到本地 8080 端口
- 发送 "Hello Netty"
- 接收并打印服务端回显

### 练习 2：进阶

阅读 Redisson 源码 `RedissonConnectionManager`（GitHub），找出 Netty 的 `Bootstrap` 在哪里初始化，并画出 Redisson 客户端启动流程图。

### 练习 3：挑战（选做）

实现一个 Netty **心跳检测**：
- 客户端每 5 秒发送一个心跳包
- 服务端超过 10 秒未收到心跳则断开连接
- 提示：`IdleStateHandler` + `IdleStateEvent`

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-dependencies/pom.xml`（Netty BOM、版本定义）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/pom.xml`（Redisson → Netty）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/emqx/IotEmqxProtocol.java`（EMQX Client 模式，import MqttQoS）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/src/main/java/cn/iocoder/yudao/module/iot/gateway/protocol/mqtt/IotMqttProtocol.java`（MQTT Broker 模式，import MqttConnectReturnCode + MqttTopicSubscription）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-iot/yudao-module-iot-gateway/pom.xml`（vertx-mqtt 依赖）
- 《Netty 实战》（Norman Maurer 等）
- [Netty 官方文档](https://netty.io/wiki/user-guide.html)
- [Netty 4.2 API 文档](https://netty.io/4.2/api/index.html)
- [Vert.x MQTT 文档](https://vertx.io/docs/vertx-mqtt/java/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13