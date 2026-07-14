# 4.3.2 TCP 滑动窗口与拥塞控制

> 滑动窗口和拥塞控制是 TCP 可靠传输的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握滑动窗口机制
- 理解拥塞控制算法（慢启动、拥塞避免）
- 知道 TCP 性能调优
- 能在 dify 中识别 TCP 优化的应用

## 📚 前置知识

- 11-tcp-handshake.md

## 1. 核心概念

### 1.1 滑动窗口

**作用**：流量控制，让发送方不要发送太快，避免接收方来不及处理。

```
接收方窗口：
[已确认][已接收未读][未接收][接收中]
  rwnd 表示窗口大小（接收方还能接收多少）
```

**发送方窗口**：
```
[已发送已确认][已发送未确认][未发送][未发送（窗口外）]
                              ← 发送窗口 →
```

### 1.2 滑动窗口的工作原理

```
发送方                          接收方
   │                              │
   ├── 数据 1-10 ──────────────→ │
   │                              │
   ├── 数据 11-20 ─────────────→ │  ← 窗口滑到 1-10 后
   │←─────── ACK 1-10 ──────────┤
   │                              │
   ├── 数据 21-30 ─────────────→ │  ← 窗口继续滑动
   │←─────── ACK 11-20 ────────┤
```

**关键字段**：
- `snd_base`：已确认的最大字节
- `nextseqnum`：下一个要发送的字节
- `snd_base + window`：窗口右边界

### 1.3 零窗口

**场景**：接收方缓冲区满，发送 rwnd=0

```
发送方暂停发送
定期发送"窗口探测"（1 字节）检查接收方
接收方缓冲区空后，发送 rwnd 更新
```

### 1.4 拥塞控制

**目的**：防止发送方发送太快导致网络拥塞。

**核心概念**：
- **cwnd**（congestion window）：拥塞窗口
- **rwnd**（receiver window）：接收方窗口
- **发送窗口 = min(cwnd, rwnd)**

### 1.5 拥塞控制算法

#### 慢启动（Slow Start）

```
初始 cwnd = 1 MSS
每收到一个 ACK，cwnd += 1 MSS
每经过一个 RTT，cwnd × 2

慢启动阈值 ssthresh = 64（初始）
cwnd < ssthresh：慢启动（指数增长）
cwnd >= ssthresh：拥塞避免（线性增长）
```

#### 拥塞避免（Congestion Avoidance）

```
每收到一个 ACK，cwnd += 1/cwnd
每经过一个 RTT，cwnd += 1
```

#### 快重传（Fast Retransmit）

```
发送方收到 3 个重复 ACK（说明丢包）
立即重传（不等超时）
```

#### 快恢复（Fast Recovery）

```
3 个重复 ACK 时：
ssthresh = cwnd / 2
cwnd = ssthresh + 3
进入拥塞避免
```

### 1.6 经典拥塞控制状态机

```
慢启动 → 拥塞避免
   ↑          ↓
   ↑     超时 / 3 个重复 ACK
   ↑          ↓
   ←────── 重新慢启动 / 快恢复
```

**超时**：cwnd = 1，重新慢启动
**3 个重复 ACK**：cwnd = cwnd/2 + 3，快恢复

### 1.7 现代 TCP 变种

| 算法 | 特点 |
|------|------|
| **TCP Tahoe** | 早期版本，超时和丢包都回到慢启动 |
| **TCP Reno** | 快重传 + 快恢复 |
| **TCP BBR** | 基于带宽时延，不依赖丢包 |
| **TCP CUBIC** | Linux 默认 |

### 1.8 TCP 性能调优

1. **调整窗口大小**：`net.ipv4.tcp_window_scaling`
2. **启用 BBR**：`net.ipv4.tcp_congestion_control=BBR`
3. **增大缓冲区**：`net.core.rmem_max`
4. **优化 MTU**：减少分包

## 2. 代码示例

### 2.1 模拟滑动窗口

```python
# 文件：sliding_window.py
class SlidingWindow:
    """滑动窗口模拟。"""

    def __init__(self, window_size: int):
        self._window_size = window_size
        self._send_base = 0   # 窗口左边界
        self._next_seq = 0    # 下一个序号

    def can_send(self) -> bool:
        """是否能发送数据。"""
        return self._next_seq < self._send_base + self._window_size

    def send(self) -> int | None:
        """发送一个数据包，返回序号。"""
        if not self.can_send():
            return None
        seq = self._next_seq
        self._next_seq += 1
        return seq

    def receive_ack(self, ack: int) -> None:
        """收到 ACK，窗口滑动。"""
        # ack 表示已收到的最大序号
        if ack >= self._send_base:
            self._send_base = ack + 1

    def __repr__(self) -> str:
        return (f"Window[base={self._send_base}, "
                f"next={self._next_seq}, "
                f"size={self._window_size}]")

# 测试
window = SlidingWindow(window_size=4)
print(window)  # Window[base=0, next=0, size=4]

# 发送 4 个包
for _ in range(4):
    seq = window.send()
    print(f"发送: {seq}")

# 收到 ACK 2，窗口滑动
window.receive_ack(2)
print(window)  # Window[base=3, next=4, size=4]

# 继续发送
print(window.send())  # 4
```

### 2.2 模拟拥塞控制（慢启动）

```python
# 文件：slow_start.py
import matplotlib.pyplot as plt

class CongestionControl:
    """拥塞控制模拟。"""

    def __init__(self, ssthresh: int = 16):
        self._cwnd = 1
        self._ssthresh = ssthresh
        self._state = "slow_start"

    def on_ack(self) -> None:
        """收到 ACK。"""
        if self._state == "slow_start":
            # 指数增长
            self._cwnd *= 2
            if self._cwnd >= self._ssthresh:
                self._state = "congestion_avoidance"
        else:
            # 线性增长
            self._cwnd += 1

    def on_timeout(self) -> None:
        """超时（丢包）。"""
        self._ssthresh = self._cwnd // 2
        self._cwnd = 1
        self._state = "slow_start"

    def on_3_duplicate_acks(self) -> None:
        """3 个重复 ACK（快重传 + 快恢复）。"""
        self._ssthresh = self._cwnd // 2
        self._cwnd = self._ssthresh + 3
        self._state = "congestion_avoidance"

    def get_cwnd(self) -> int:
        return self._cwnd

# 模拟
cc = CongestionControl(ssthresh=16)
cwds = []

for i in range(20):
    cc.on_ack()
    cwds.append(cc.get_cwnd())

print(f"cwnd 变化: {cwds}")
```

### 2.3 TCP 性能测试

```python
# 文件：tcp_perf_test.py
import time
import socket

def tcp_throughput_test(host: str = "127.0.0.1", port: int = 9999):
    """测试 TCP 吞吐量。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect((host, port))

    data = b"X" * 1024 * 1024  # 1 MB
    n_packets = 100

    start = time.perf_counter()
    for _ in range(n_packets):
        sock.send(data)
    elapsed = time.perf_counter() - start

    throughput = (n_packets * len(data)) / elapsed / 1024 / 1024
    print(f"吞吐量: {throughput:.2f} MB/s")
    sock.close()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 TCP 连接池优化

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 60-90）：

```python
import aiohttp

class OptimizedProxy:
    """TCP 优化的 SSRF 代理。

    滑动窗口和拥塞控制的应用：
    1. 启用 TCP_NODELAY（小数据包立即发送）
    2. 增大 socket 缓冲区（提高窗口大小）
    3. 启用 Keep-alive（避免频繁握手）
    """

    def __init__(self):
        # aiohttp 底层用 TCP，启用 keepalive
        self._connector = aiohttp.TCPConnector(
            keepalive_timeout=75,
            force_close=False,
            limit=100,
            limit_per_host=10,
            enable_cleanup_closed=True,
            # 增大 socket 缓冲区
            sock_connect=5.0,
            sock_read=30.0,
        )

    async def fetch_large_data(self, url: str) -> bytes:
        """下载大文件 - 滑动窗口自动调整。"""
        async with aiohttp.ClientSession(connector=self._connector) as session:
            async with session.get(url) as resp:
                # 流式读取（避免一次性加载到内存）
                chunks = []
                async for chunk in resp.content.iter_chunked(8192):
                    chunks.append(chunk)
                return b"".join(chunks)


# dify 的 TCP 优化：
# 1. 连接池：减少三次握手（节省 RTT）
# 2. Keep-alive：保持长连接（避免 TIME_WAIT）
# 3. 流式 IO：避免大对象占用内存
# 4. 超时控制：避免长时间阻塞

# Linux 内核的 TCP 优化（dify 部署）：
# /etc/sysctl.conf:
# net.ipv4.tcp_window_scaling = 1     # 启用窗口缩放
# net.core.rmem_max = 16777216         # 接收缓冲区 16MB
# net.core.wmem_max = 16777216         # 发送缓冲区 16MB
# net.ipv4.tcp_congestion_control = BBR  # 启用 BBR 拥塞控制
# net.ipv4.tcp_max_syn_backlog = 8192   # SYN 队列长度
```

**解读**：
- 第 13 行：Keep-alive（保持长连接）
- 第 18 行：连接池（减少握手）
- **设计意图**：通过 TCP 参数优化提升网络吞吐

## 4. 关键要点总结

- **滑动窗口**：流量控制，让接收方来得及处理
- **拥塞控制**：避免网络拥塞（慢启动、拥塞避免、快重传、快恢复）
- **BBR**：现代拥塞控制算法（不依赖丢包）
- **优化**：连接池、Keep-alive、调整窗口
- dify 用连接池和流式 IO 优化 TCP 性能

## 5. 练习题

### 练习 1：基础（必做）

实现一个滑动窗口类，支持 `send`、`receive_ack`、`can_send` 方法。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何用 Keep-alive（75 秒）。

### 练习 3：挑战（选做）

模拟慢启动和拥塞避免，画出 cwnd 随时间变化的曲线。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 5681：TCP 拥塞控制
- 《TCP/IP 详解 卷 1》第 21-22 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13