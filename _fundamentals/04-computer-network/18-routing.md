# 4.4.3 路由原理：静态路由 / 动态路由

> 路由是网络层的核心，决定数据包如何转发。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解路由的基本原理
- 区分静态路由和动态路由
- 知道常见路由协议（OSPF、BGP）

## 📚 前置知识

- 16-ip-subnet.md

## 1. 核心概念

### 1.1 路由是什么？

**路由**：决定数据包从源到目的地的**路径**。

**类比**：寄快递时选择走哪条路。

### 1.2 路由表

每个路由器维护一张**路由表**：

```
目标网络      子网掩码          网关        接口        跃点数
0.0.0.0       0.0.0.0          192.168.1.1  eth0       1     ← 默认路由
10.0.0.0      255.0.0.0        0.0.0.0      eth1       0     ← 直连
192.168.1.0   255.255.255.0    0.0.0.0      eth0       0     ← 直连
```

**最长前缀匹配**：选择最具体的路由。

### 1.3 路由的分类

**按目标**：
- **直连路由**：直接连接的网络
- **静态路由**：手动配置
- **动态路由**：路由协议自动学习

**按范围**：
- **内部网关协议（IGP）**：自治系统内（OSPF、RIP）
- **外部网关协议（EGP）**：自治系统间（BGP）

### 1.4 静态路由 vs 动态路由

| 维度 | 静态路由 | 动态路由 |
|------|----------|----------|
| 配置 | 手动 | 自动 |
| 维护 | 复杂 | 简单 |
| 资源 | 几乎无开销 | CPU/带宽 |
| 适用 | 小型网络 | **大型网络** |
| 收敛 | 无需 | 需要时间 |
| 适应性 | 差 | **好** |

### 1.5 常见路由协议

| 协议 | 类型 | 算法 | 适用 |
|------|------|------|------|
| **RIP** | IGP | 距离向量 | 小型网络 |
| **OSPF** | IGP | 链路状态 | **大型企业网** |
| **IS-IS** | IGP | 链路状态 | ISP |
| **BGP** | EGP | 路径向量 | **互联网骨干** |

### 1.6 路由转发过程

```
源主机 192.168.1.10
   ↓
目标 IP 8.8.8.8
   ↓
查路由表：
1. 匹配直连网段？不匹配
2. 匹配默认路由 → 网关 192.168.1.1
   ↓
发送到网关（路由器）
   ↓
路由器 1 查自己的路由表 → 路由器 2 → ... → 目标
```

### 1.7 数据包转发 vs 路由控制

- **转发（Forwarding）**：根据路由表发送包（快）
- **路由控制（Routing）**：计算路由表（慢）

### 1.8 路由环路

**问题**：路由不一致导致循环转发。

**防护**：
- **TTL（Time To Live）**：每跳减 1，归零丢弃
- **水平分割**：不从学习的接口发回
- **路由毒化**：故障路由标记为无穷大

## 2. 代码示例

### 2.1 Python 查看路由表

```python
# 文件：routing_table.py
import subprocess

def get_routing_table():
    """获取系统路由表。"""
    if subprocess.os.name == "posix":  # Linux/macOS
        result = subprocess.run(
            ["netstat", "-rn"], capture_output=True, text=True
        )
        return result.stdout
    else:  # Windows
        result = subprocess.run(
            ["route", "print"], capture_output=True, text=True
        )
        return result.stdout

print(get_routing_table())
```

### 2.2 路由追踪

```python
# 文件：traceroute.py
import subprocess
import socket

def traceroute(host: str, max_hops: int = 30) -> list[str]:
    """路由追踪 - 显示到目标的路径。"""
    ips = []

    for ttl in range(1, max_hops + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        sock.settimeout(3)
        try:
            sock.sendto(b"x", (host, 33434))
            data, addr = sock.recvfrom(1024)
            ips.append(addr[0])
            if addr[0] == host:
                break
        except socket.timeout:
            ips.append("*")
        finally:
            sock.close()

    return ips

# 测试
# hops = traceroute("8.8.8.8")
# print(f"路径：{' → '.join(hops)}")
```

### 2.3 实现简单的距离向量路由

```python
# 文件：distance_vector.py
from collections import defaultdict

class DistanceVectorRouter:
    """简化的距离向量路由（类似 RIP）。"""

    def __init__(self, name: str):
        self.name = name
        # 路由表：目标 → (距离, 下一跳)
        self._table: dict[str, tuple[int, str]] = {}
        # 邻居
        self._neighbors: dict[str, int] = {}
        # 邻居的路由表
        self._neighbor_tables: dict[str, dict] = {}

    def add_neighbor(self, name: str, cost: int) -> None:
        """添加邻居。"""
        self._neighbors[name] = cost
        # 直接连接的距离为 cost
        self._table[name] = (cost, name)

    def update_from_neighbor(self, neighbor: str, table: dict) -> None:
        """从邻居学习路由。"""
        self._neighbor_tables[neighbor] = table
        # Bellman-Ford 算法
        for dest, (dist, _) in table.items():
            new_dist = dist + self._neighbors[neighbor]
            if dest not in self._table or new_dist < self._table[dest][0]:
                self._table[dest] = (new_dist, neighbor)

    def get_table(self) -> dict:
        """返回当前路由表。"""
        return self._table

# 模拟小型网络
r1 = DistanceVectorRouter("R1")
r2 = DistanceVectorRouter("R2")
r3 = DistanceVectorRouter("R3")

# 网络拓扑：R1 - R2 - R3
r1.add_neighbor("R2", 1)
r2.add_neighbor("R1", 1)
r2.add_neighbor("R3", 1)
r3.add_neighbor("R2", 1)

# 交换路由表
r2.update_from_neighbor("R1", {"R3": (1, "R3")})
r1.update_from_neighbor("R2", r2.get_table())
r3.update_from_neighbor("R2", r2.get_table())

print(f"R1 路由表: {r1.get_table()}")
print(f"R2 路由表: {r2.get_table()}")
print(f"R3 路由表: {r3.get_table()}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的网络连接（间接涉及路由）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 40-60）：

```python
import socket

class NetworkManager:
    """dify 的网络连接管理。

    路由相关：
    1. dify 不直接管理路由
    2. 但每个 HTTP 请求都依赖路由
    3. 内部服务（DB、Redis）走内网
    4. 外部 API（OpenAI）走公网

    路由选择：
    - 默认路由：所有出站流量
    - 特定路由：自定义网段走特定网关（如内网服务）
    """

    async def connect_to_service(self, host: str, port: int):
        """连接到服务（内部或外部）。"""
        # 系统自动选择路由
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

        # 内网服务（如 PostgreSQL）走内网路由（快）
        # 外网服务（如 OpenAI）走默认路由（公网）

        # dify 部署时的网络配置：
        # /etc/hosts：
        # 192.168.1.10  postgres
        # 192.168.1.11  redis
        #
        # /etc/resolv.conf：
        # nameserver 8.8.8.8  ← 外部 DNS
        #
        # 路由表（自动）：
        # 192.168.1.0/24 → eth0（内网）
        # default → 192.168.1.1（默认网关，公网）

        return sock
```

**解读**：
- 第 28-34 行：依赖系统路由表
- **设计意图**：dify 不管理路由，依赖操作系统和基础设施

## 4. 关键要点总结

- **路由表**：目标网络 → 网关
- **静态 vs 动态**：小型用静态，大型用动态
- **OSPF**：企业内部常用
- **BGP**：互联网骨干
- **TTL**：防止路由环路
- dify 依赖系统路由表

## 5. 练习题

### 练习 1：基础（必做）

用 `traceroute` 或 `tracepath` 命令追踪到 `8.8.8.8` 的路径。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何需要在内网部署时配置特殊路由。

### 练习 3：挑战（选做）

实现简单的距离向量路由算法，模拟 3 个路由器学习彼此路由。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 2453：RIP
- RFC 2328：OSPF
- 《计算机网络：自顶向下方法》第 5 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13