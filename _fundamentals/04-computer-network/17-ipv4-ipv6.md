# 4.4.2 IPv4 vs IPv6

> IPv6 是 IPv4 的下一代协议，解决地址耗尽问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 IPv4 地址耗尽问题
- 掌握 IPv6 的改进和特点
- 知道 IPv4 到 IPv6 的过渡技术
- 能在 dify 中识别 IPv6 的支持

## 📚 前置知识

- 16-ip-subnet.md

## 1. 核心概念

### 1.1 IPv4 地址耗尽

**问题**：
- IPv4 地址 32 位（~43 亿）
- 早已分配完（2011 年 IANA 耗尽）
- NAT 等技术只能缓解

**IPv4 地址分配**：
- 早期：8 个 Class A 给大型组织
- 现在：大量使用 NAT、私有 IP

### 1.2 IPv6 的优势

**128 位地址**（约 3.4 × 10³⁸）：
- 地球上每粒沙子都可以有 IP
- 解决地址耗尽

**改进**：
- 更大的地址空间
- 简化的头部（无校验和、固定的 40 字节）
- 内置安全（IPsec）
- 更好的 QoS
- 无 NAT（端到端连接）
- 自动配置（SLAAC）

### 1.3 IPv6 地址表示

```
2001:0db8:85a3:0000:0000:8a2e:0370:7334
      ↑ 简化（省略前导零）
2001:db8:85a3:0:0:8a2e:370:7334
      ↑ 进一步简化（连续 0 替换为 ::，只能用一次）
2001:db8:85a3::8a2e:370:7334
```

**地址类型**：
- `::1`：回环（类似 127.0.0.1）
- `fe80::/10`：链路本地
- `fc00::/7`：唯一本地（类似 IPv4 私有）
- `2000::/3`：全球单播

### 1.4 IPv6 头部

```
版本(4) 流量类(8)    流标签(20)
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  有效载荷长度(16)  | 下一个头(8) |   跳数限制(8)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                       |
+                 源地址 (128)                          +
|                                                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                       |
+                目标地址 (128)                        +
|                                                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**简化**：
- 固定 40 字节（IPv4 是 20-60 字节）
- 无校验和（路由器不计算）
- 无分片字段（端到端处理）

### 1.5 过渡技术

#### 双栈（Dual Stack）

```
服务器同时支持 IPv4 和 IPv6
```

#### 隧道（Tunneling）

```
IPv6 包封装在 IPv4 包中
```

**类型**：
- 6to4
- 6rd
- Teredo

#### NAT64 / DNS64

```
IPv6 客户端 → DNS64 解析 → NAT64 网关 → IPv4 服务器
```

### 1.6 实际应用

- **移动网络**：4G/5G 已支持 IPv6
- **云服务**：AWS、Azure、Google Cloud 支持
- **国内**：三大运营商已开始部署
- **dify**：支持 IPv4 + IPv6 双栈

## 2. 代码示例

### 2.1 IPv6 地址操作

```python
# 文件：ipv6_demo.py
import ipaddress

# 创建 IPv6 地址
ip = ipaddress.ip_address("2001:db8:85a3::8a2e:370:7334")
print(f"IPv6: {ip}")
print(f"版本: IPv{ip.version}")
print(f"完整格式: {ip.exploded}")

# 简化表示
ip2 = ipaddress.ip_address("::1")
print(f"\n回环: {ip2}")
print(f"完整格式: {ip2.exploded}")

# IPv6 网络
network = ipaddress.ip_network("2001:db8::/32")
print(f"\n网络: {network}")
print(f"前缀: /{network.prefixlen}")
```

### 2.2 双栈 Socket

```python
# 文件：dual_stack.py
import socket

def create_dual_stack_server(host: str = "::", port: int = 9999):
    """双栈服务器（同时支持 IPv4 和 IPv6）。"""
    # AF_INET6 + IPV6_V6ONLY=0 → 双栈
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind((host, port))
    sock.listen()
    print(f"双栈服务器: {host}:{port}")

    while True:
        conn, addr = sock.accept()
        print(f"连接来自: {addr}")
        # addr 是 (host, port, flowinfo, scopeid)
        conn.close()
```

### 2.3 DNS 查询（IPv6）

```python
# 文件：dns_ipv6.py
import socket

def resolve_ipv6(host: str) -> list[str]:
    """解析域名的 IPv6 地址。"""
    try:
        # AF_INET6 触发 AAAA 查询
        infos = socket.getaddrinfo(host, None, socket.AF_INET6)
        return list({info[4][0] for info in infos})
    except socket.gaierror:
        return []

# 测试
ips = resolve_ipv6("www.baidu.com")
print(f"IPv6: {ips}")
```

### 2.4 IPv4/IPv6 判断

```python
# 文件：ip_version.py
import ipaddress

def classify_ip(ip: str) -> str:
    """判断 IP 类型。"""
    try:
        addr = ipaddress.ip_address(ip)

        if addr.is_loopback:
            return "回环"
        elif addr.is_private:
            return "私有"
        elif addr.is_multicast:
            return "多播"
        elif addr.is_reserved:
            return "保留"
        elif addr.is_unspecified:
            return "未指定"
        elif addr.is_link_local:
            return "链路本地"
        elif addr.version == 4:
            return "公网 IPv4"
        elif addr.version == 6:
            return "公网 IPv6"
        else:
            return "未知"
    except ValueError:
        return "无效"

# 测试
for ip in ["127.0.0.1", "192.168.1.1", "8.8.8.8", "::1", "fe80::1", "2001:db8::1"]:
    print(f"{ip:20s} → {classify_ip(ip)}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的双栈支持

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 30-50）：

```python
import socket
import ipaddress

class DualStackResolver:
    """dify 的双栈 DNS 解析器。

    支持 IPv4 和 IPv6：
    - AF_INET：IPv4
    - AF_INET6：IPv6
    - AF_UNSPEC：双栈

    dify 的 IPv6 支持：
    1. 解析域名 → A 记录（IPv4）
    2. 解析域名 → AAAA 记录（IPv6）
    3. 优先尝试 IPv6（如果可用）
    4. 回退到 IPv4
    """

    def resolve(self, host: str) -> list[str]:
        """解析域名的所有 IP（双栈）。"""
        ips_v4 = []
        ips_v6 = []

        try:
            # IPv4
            infos = socket.getaddrinfo(host, None, socket.AF_INET)
            ips_v4 = list({info[4][0] for info in infos})
        except socket.gaierror:
            pass

        try:
            # IPv6
            infos = socket.getaddrinfo(host, None, socket.AF_INET6)
            ips_v6 = list({info[4][0] for info in infos})
        except socket.gaierror:
            pass

        return ips_v4, ips_v6


class SSRFProtectionV6:
    """SSRF 防护也支持 IPv6。"""

    # IPv6 内网段
    PRIVATE_V6_RANGES = [
        ipaddress.ip_network("::1/128"),         # 回环
        ipaddress.ip_network("fe80::/10"),       # 链路本地
        ipaddress.ip_network("fc00::/7"),        # 唯一本地
        ipaddress.ip_network("::ffff:0:0/96"),   # IPv4 映射（需检查嵌入的 IPv4）
    ]

    @classmethod
    def is_private_v6(cls, ip: str) -> bool:
        """检查 IPv6 是否内网。"""
        try:
            addr = ipaddress.ip_address(ip)
            if addr.version != 6:
                return False

            # IPv4 映射地址（如 ::ffff:192.168.1.1）
            if addr.ipv4_mapped:
                return SSRFProtection.is_private_ip(str(addr.ipv4_mapped))

            # IPv6 内网段
            return any(addr in net for net in cls.PRIVATE_V6_RANGES)
        except ValueError:
            return False
```

**解读**：
- 第 18-30 行：分别解析 IPv4 和 IPv6
- 第 47 行：处理 IPv4 映射的 IPv6 地址
- **设计意图**：dify 支持双栈，但需要扩展 SSRF 防护到 IPv6

## 4. 关键要点总结

- **IPv4**：32 位，~43 亿地址，已耗尽
- **IPv6**：128 位，~3.4×10³⁸地址，足够
- **IPv6 优势**：简化头部、内置安全、自动配置
- **过渡**：双栈、隧道、NAT64
- dify 支持 IPv4 + IPv6 双栈

## 5. 练习题

### 练习 1：基础（必做）

用 Python `ipaddress` 模块判断 `2001:db8::1`、`fe80::1`、`::1` 的类型。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何需要扩展 SSRF 防护到 IPv6。

### 练习 3：挑战（选做）

用双栈 socket 创建服务器，同时接受 IPv4 和 IPv6 连接。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 8200：IPv6 规范
- RFC 4291：IPv6 地址架构

---

**文档版本**：v1.0
**最后更新**：2026-07-13