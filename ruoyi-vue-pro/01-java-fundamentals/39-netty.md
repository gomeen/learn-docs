# 1.4.9 Netty 网络编程

> 理解 Netty 的核心组件与 Reactor 模型，能读懂 Redisson、Dubbo 等基于 Netty 的框架源码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Reactor 线程模型（单线程 / 多线程 / 主从多线程）
- 掌握 Netty 的核心组件：Bootstrap、Channel、ChannelHandler、EventLoop
- 能写一个简单的 Netty Echo 服务器
- 在 ruoyi-vue-pro 中识别 Netty 的间接使用（Redisson、Vert.x、Spring WebFlux 客户端）

## 📚 前置知识

- [25-thread.md](./25-thread.md)：线程基础
- [26-thread-pool.md](./26-thread-pool.md)：线程池
- [22-jvm-memory.md](./22-jvm-memory.md)：JVM 内存
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

## 3. 关键要点总结

- **Netty** 是基于 **Reactor 主从多线程模型** 的高性能 NIO 框架
- **三大核心**：Channel（连接）/ EventLoop（线程）/ ChannelHandler（业务逻辑）
- **ByteBuf**：比 JDK ByteBuffer 更易用，支持零拷贝、引用计数
- **ChannelPipeline**：责任链模式，inbound 自 head → tail，outbound 自 tail → head
- ruoyi-vue-pro **业务代码不直接用 Netty**，但通过 Redisson、Vert.x MQTT、reactor-netty（WebClient 底层）间接使用
- **IoT 网关**（`yudao-module-iot-gateway`）直接 import Netty 的 MQTT 枚举（MqttQoS、MqttConnectReturnCode、MqttTopicSubscription）—— 是少有的 Netty 直接使用场景
- **应用场景**：Redis 客户端、RPC 框架（Dubbo/gRPC）、IoT 网关、游戏服务器

---

**文档版本**：v1.0
**最后更新**：2026-07-13
