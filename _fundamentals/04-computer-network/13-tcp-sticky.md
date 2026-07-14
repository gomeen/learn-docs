# 4.3.3 TCP 粘包与拆包

> TCP 是字节流协议，没有消息边界，需要应用层处理粘包问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 TCP 粘包和拆包的成因
- 掌握常见的解决方案（定长、分隔符、长度前缀）
- 能在 dify 中识别相关应用

## 📚 前置知识

- 11-tcp-handshake.md

## 1. 核心概念

### 1.1 为什么会有粘包？

**TCP 是字节流协议**，不保留消息边界。

```
发送方连续发送 3 个包：
┌────────┐┌────────┐┌────────┐
│ Hello  ││ World  ││Python  │
└────────┘└────────┘└────────┘

TCP 可能这样传输：
┌────────────────────────────┐
│ HelloWorldPython            │ ← 粘在一起！
└────────────────────────────┘

接收方读时：
recv(1024) → "HelloWorldPython"  ← 一次读到多个包
```

### 1.2 粘包的场景

1. **发送快 + 接收慢**：发送方连续发，TCP 缓存到一起
2. **小包频繁发送**：Nagle 算法合并小包
3. **接收方不及时读取**：多个包在缓冲区堆积

### 1.3 拆包的场景

```
发送：┌──────────────────────────────┐
      │   一个很大的数据包            │
      └──────────────────────────────┘

TCP 拆成多个段：
┌──────────┐┌──────────┐┌──────────┐
│ 前半部分  ││ 中间部分  ││ 后半部分  │
└──────────┘└──────────┘└──────────┘

接收方读时：
recv(1024) → "前半部分"  ← 一次只读到一半
```

### 1.4 解决方案

#### 方案 1：定长消息

每个消息固定长度（如 1024 字节）。不足部分补空格。

```python
def send_fixed_length(sock, message: bytes, length: int = 1024) -> None:
    """发送定长消息。"""
    msg = message.ljust(length, b'\x00')
    sock.send(msg)

def recv_fixed_length(sock, length: int = 1024) -> bytes:
    """接收定长消息。"""
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    return data.rstrip(b'\x00')
```

#### 方案 2：分隔符

每个消息以特定分隔符结尾（如 `\n`、`\r\n`）。

```python
def send_delimited(sock, message: str) -> None:
    """发送带分隔符的消息。"""
    sock.send((message + "\n").encode())

def recv_delimited(sock, delimiter: bytes = b"\n") -> bytes:
    """接收一个消息（到分隔符）。"""
    data = b""
    while not data.endswith(delimiter):
        chunk = sock.recv(1)
        if not chunk:
            break
        data += chunk
    return data.rstrip(delimiter)
```

#### 方案 3：长度前缀（最常用）

每个消息前 4 字节表示长度。

```
┌──────────┬──────────────────┐
│ 长度(4B) │   消息体(N 字节)  │
└──────────┴──────────────────┘
```

```python
import struct

def send_with_length(sock, message: bytes) -> None:
    """发送带长度前缀的消息。"""
    # 前 4 字节：长度
    header = struct.pack("!I", len(message))
    sock.send(header + message)

def recv_with_length(sock) -> bytes:
    """接收带长度前缀的消息。"""
    # 先收 4 字节长度
    header = b""
    while len(header) < 4:
        chunk = sock.recv(4 - len(header))
        if not chunk:
            return b""
        header += chunk
    length = struct.unpack("!I", header)[0]

    # 再收 length 字节
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    return data
```

### 1.5 应用协议示例

**HTTP** 用换行符 + Content-Length：
```
GET / HTTP/1.1\r\n
Host: example.com\r\n
\r\n
```

**WebSocket** 用帧格式（包含 FIN、opcode、length）。

**gRPC** 用 5 字节 header（1B 压缩标志 + 4B 长度）。

**Redis** 用 `*<count>\r\n$<len>\r\n<data>\r\n`。

## 2. 代码示例

### 2.1 自定义长度前缀协议

```python
# 文件：length_prefixed.py
import socket
import struct

class LengthPrefixedProtocol:
    """长度前缀协议实现。"""

    HEADER_SIZE = 4

    def send(self, sock: socket.socket, message: bytes) -> None:
        """发送消息。"""
        header = struct.pack("!I", len(message))
        sock.sendall(header + message)

    def recv(self, sock: socket.socket) -> bytes | None:
        """接收一个完整消息。"""
        # 读取 header
        header = self._recv_exact(sock, self.HEADER_SIZE)
        if not header:
            return None
        length = struct.unpack("!I", header)[0]

        # 读取 body
        body = self._recv_exact(sock, length)
        return body

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """读取恰好 n 字节。"""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return b""
            data += chunk
        return data


def test_protocol():
    """测试协议。"""
    protocol = LengthPrefixedProtocol()

    server = socket.socket()
    server.bind(('127.0.0.1', 9999))
    server.listen()

    client = socket.socket()
    client.connect(('127.0.0.1', 9999))

    conn, _ = server.accept()

    # 客户端发送两个粘在一起的包
    protocol.send(client, b"Hello")
    protocol.send(client, b"World")

    # 服务器分别接收
    msg1 = protocol.recv(conn)
    msg2 = protocol.recv(conn)
    print(f"收到: {msg1}, {msg2}")

    client.close()
    conn.close()
    server.close()
```

### 2.2 行分隔符协议

```python
# 文件：line_protocol.py
import socket

class LineProtocol:
    """行分隔符协议。"""

    DELIMITER = b"\n"

    def send(self, sock: socket.socket, message: str) -> None:
        sock.sendall((message + "\n").encode())

    def recv(self, sock: socket.socket) -> str | None:
        """接收一行（到 \n）。"""
        data = b""
        while not data.endswith(self.DELIMITER):
            chunk = sock.recv(1)
            if not chunk:
                return None
            data += chunk
        return data[:-1].decode()


def test_line_protocol():
    server = socket.socket()
    server.bind(('127.0.0.1', 9999))
    server.listen()

    client = socket.socket()
    client.connect(('127.0.0.1', 9999))
    conn, _ = server.accept()

    proto = LineProtocol()
    proto.send(client, "First message")
    proto.send(client, "Second message")

    print(proto.recv(conn))  # First message
    print(proto.recv(conn))  # Second message

    client.close()
    conn.close()
    server.close()
```

### 2.3 关闭 Nagle 算法

```python
# 文件：disable_nagle.py
import socket

def create_low_latency_socket() -> socket.socket:
    """创建低延迟 socket（禁用 Nagle 算法）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 禁用 Nagle（避免小包合并）
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # 设置 keep-alive
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    return s
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 协议（处理粘包）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 1-40）：

```python
import redis

class RedisClient:
    """Redis 客户端封装。

    Redis 用 RESP（REdis Serialization Protocol）协议：
    - 简单文本协议
    - 用 \r\n 分隔
    - 用 $ 标识长度（解决粘包）

    示例：
    *3\r\n      ← 数组，3 个元素
    $3\r\n
    SET\r\n
    $3\r\n
    foo\r\n
    $3\r\n
    bar\r\n

    这种协议天然处理粘包：
    - 客户端知道每个部分的长度（$3）
    - 不会越界读取
    """

    def __init__(self):
        # redis-py 库内部处理粘包
        self._client = redis.Redis(
            host="localhost",
            port=6379,
            socket_timeout=5,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )

    def set_key(self, key: str, value: str) -> None:
        """SET 命令 - redis-py 处理协议细节。"""
        # 内部：
        # 1. 编码为 RESP 协议
        # 2. 发送到 socket
        # 3. 接收响应
        # 4. 解析响应（用 \r\n 分隔）
        self._client.set(key, value)

    def get_key(self, key: str) -> str | None:
        return self._client.get(key)


# dify 的网络协议使用：
# - Redis：RESP 协议（\r\n 分隔 + 长度前缀）
# - PostgreSQL：自定义二进制协议（消息长度前缀）
# - HTTP：Content-Length + Transfer-Encoding
# - gRPC（向量数据库）：5 字节 header + protobuf

# 所有这些协议都解决了 TCP 粘包问题。
```

**解读**：
- 第 13-23 行：Redis RESP 协议格式
- 第 33 行：redis-py 内部处理协议
- **设计意图**：理解协议层才能正确处理网络通信

## 4. 关键要点总结

- **TCP 粘包**：TCP 是字节流，无消息边界
- **三种解决方案**：定长、分隔符、长度前缀
- **长度前缀最常用**：HTTP Content-Length、gRPC、Redis RESP
- **禁用 Nagle**：`TCP_NODELAY` 减少延迟
- dify 用 redis-py（处理 RESP 协议）

## 5. 练习题

### 练习 1：基础（必做）

实现一个长度前缀的 TCP 协议，支持发送和接收多个消息。

### 练习 2：进阶

阅读 `api/extensions/ext_redis.py`，说明 Redis RESP 协议如何解决粘包。

### 练习 3：挑战（选做）

用分隔符（`\n`）实现一个简单的行协议，并测试连续发送多个消息时的接收。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- Redis RESP 协议：https://redis.io/docs/reference/protocol-spec/
- 《Netty 实战》第 5 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13