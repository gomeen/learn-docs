# 4.4.1 IP 地址与子网掩码

> IP 地址和子网划分是网络基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 IPv4 地址结构和分类
- 掌握子网掩码和 CIDR
- 能在 dify 中识别 IP 验证的应用（SSRF 防护）

## 📚 前置知识

- 02-tcp-ip.md

## 1. 核心概念

### 1.1 IPv4 地址

**32 位**地址，通常用**点分十进制**表示：
```
11000000.10101000.00000001.00000001
   192    .  168   .   1    .   1
```

**范围**：0.0.0.0 ~ 255.255.255.255（共约 43 亿）

### 1.2 IP 地址分类

| 类别 | 范围 | 用途 |
|------|------|------|
| **A 类** | 1.0.0.0 - 126.255.255.255 | 大型网络（/8） |
| **B 类** | 128.0.0.0 - 191.255.255.255 | 中型网络（/16） |
| **C 类** | 192.0.0.0 - 223.255.255.255 | 小型网络（/24） |
| **D 类** | 224.0.0.0 - 239.255.255.255 | 多播 |
| **E 类** | 240.0.0.0 - 255.255.255.255 | 保留 |

### 1.3 私有 IP 地址（RFC 1918）

```
A 类：10.0.0.0/8        （10.x.x.x）
B 类：172.16.0.0/12     （172.16-31.x.x）
C 类：192.168.0.0/16    （192.168.x.x）
```

**特殊地址**：
- `127.0.0.1`：本机回环（localhost）
- `0.0.0.0`：本机所有 IP / 未分配
- `255.255.255.255`：广播
- `169.254.0.0/16`：链路本地（AWS metadata 是 169.254.169.254）

### 1.4 子网掩码

**子网掩码**：区分网络号和主机号

```
IP:      192.168.1.100
掩码:    255.255.255.0
─────────────────────
网络号:   192.168.1.0
主机号:             100

按位：
IP:   11000000.10101000.00000001.01100100
掩码: 11111111.11111111.11111111.00000000
与:   11000000.10101000.00000001.00000000
```

### 1.5 CIDR 表示法

**CIDR（Classless Inter-Domain Routing）**：

```
192.168.1.0/24
         ↑
       网络前缀长度（24 位）
```

**示例**：
- `10.0.0.0/8`：8 位网络号（255.0.0.0）
- `192.168.1.0/24`：24 位网络号（255.255.255.0）
- `172.16.0.0/12`：12 位网络号（255.240.0.0）

### 1.6 子网划分

**需求**：把 `192.168.1.0/24` 划分成 4 个子网

```
192.168.1.0/24 → 256 个地址
划成 4 个 /26 子网：
- 192.168.1.0/26    （64 个：.0 - .63）
- 192.168.1.64/26   （64 个：.64 - .127）
- 192.168.1.128/26  （64 个：.128 - .191）
- 192.168.1.192/26  （64 个：.192 - .255）
```

### 1.7 公网 vs 私网 IP

**公网 IP**：
- 全球唯一
- 可路由
- 需要 ISP 分配

**私网 IP**：
- 内部使用
- 不可路由
- 通过 NAT 访问公网

## 2. 代码示例

### 2.1 Python IP 地址操作

```python
# 文件：ip_demo.py
import ipaddress

# 创建 IP 对象
ip = ipaddress.ip_address("192.168.1.1")
print(f"IP: {ip}")
print(f"版本: IPv{ip.version}")
print(f"是否私有: {ip.is_private}")
print(f"是否回环: {ip.is_loopback}")
print(f"是否多播: {ip.is_multicast}")

# 创建网络对象
network = ipaddress.ip_network("192.168.1.0/24")
print(f"\n网络: {network}")
print(f"网络地址: {network.network_address}")
print(f"广播地址: {network.broadcast_address}")
print(f"子网掩码: {network.netmask}")
print(f"前缀长度: {network.prefixlen}")
print(f"地址数: {network.num_addresses}")
print(f"可用地址: {list(network.hosts())[:5]}...")
```

### 2.2 CIDR 计算

```python
# 文件：cidr_demo.py
import ipaddress

def cidr_to_subnet_mask(prefix_len: int) -> str:
    """CIDR 前缀 → 子网掩码。"""
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    return ".".join(str((mask >> i) & 0xFF) for i in (24, 16, 8, 0))

# 测试
for prefix in [8, 16, 24, 26, 30]:
    print(f"/{prefix} → {cidr_to_subnet_mask(prefix)}")
# /8  → 255.0.0.0
# /16 → 255.255.0.0
# /24 → 255.255.255.0
# /26 → 255.255.255.192
# /30 → 255.255.255.252
```

### 2.3 检查 IP 是否在网段内

```python
# 文件：ip_in_network.py
import ipaddress

def ip_in_network(ip: str, network: str) -> bool:
    """检查 IP 是否在网段内。"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        net = ipaddress.ip_network(network)
        return ip_obj in net
    except ValueError:
        return False

# 测试
print(ip_in_network("192.168.1.100", "192.168.1.0/24"))  # True
print(ip_in_network("10.0.0.1", "192.168.1.0/24"))      # False
print(ip_in_network("172.16.5.10", "172.16.0.0/12"))    # True（私有 IP）
```

### 2.4 子网划分

```python
# 文件：subnet_divide.py
import ipaddress

def divide_subnet(network: str, n: int) -> list:
    """把网段划分成 n 个子网。"""
    net = ipaddress.ip_network(network)
    # 计算新前缀长度
    new_prefix = net.prefixlen + (n - 1).bit_length()

    if new_prefix > 32:
        raise ValueError("无法划分，子网太小")

    subnets = list(net.subnets(new_prefix=new_prefix))
    return [str(subnet) for subnet in subnets[:n]]

# 测试：把 192.168.1.0/24 划分成 4 个子网
subnets = divide_subnet("192.168.1.0/24", 4)
print(f"4 个子网：")
for s in subnets:
    print(f"  {s}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的 IP 验证（SSRF 防护）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 30-60）：

```python
import ipaddress

class SSRFProtection:
    """SSRF 防护 - 通过 IP 验证。

    dify 在解析域名后会验证 IP 是否内网：
    1. 解析域名 → IP
    2. 检查 IP 是否在黑名单网段
    3. 如果是，抛异常（SSRF 防护）
    """

    # 内网 IP 网段（黑名单）
    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),       # 私有 A 类
        ipaddress.ip_network("172.16.0.0/12"),    # 私有 B 类
        ipaddress.ip_network("192.168.0.0/16"),   # 私有 C 类
        ipaddress.ip_network("127.0.0.0/8"),      # 回环
        ipaddress.ip_network("169.254.0.0/16"),   # 链路本地（AWS metadata）
        ipaddress.ip_network("0.0.0.0/8"),        # 未指定
        ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
        ipaddress.ip_network("224.0.0.0/4"),      # 多播
    ]

    @classmethod
    def is_private_ip(cls, ip: str) -> bool:
        """检查是否是内网 IP。"""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in net for net in cls.PRIVATE_RANGES)

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """验证 URL 不是内网。"""
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False

        try:
            # 解析域名
            ips = socket.gethostbyname_ex(host)[2]
        except socket.gaierror:
            return False

        # 检查每个 IP
        for ip in ips:
            if cls.is_private_ip(ip):
                return False

        return True


# dify 的 SSRF 防护层次：
# 1. URL 黑名单（协议：禁用 file://, gopher:// 等）
# 2. 域名黑名单（禁用 localhost, metadata 等）
# 3. IP 黑名单（解析后检查）
# 4. 端口限制（禁用 22, 3306, 6379 等敏感端口）
# 5. DNS Rebinding 防护（解析后再次验证）
```

**解读**：
- 第 18-26 行：私有 IP 黑名单
- 第 38 行：`ipaddress.ip_network` 用 CIDR 检查
- **设计意图**：防止 SSRF 攻击访问内网敏感服务

## 4. 关键要点总结

- **IPv4**：32 位，点分十进制
- **CIDR**：`192.168.1.0/24` 表示网络前缀
- **私有 IP**：10.x、172.16-31.x、192.168.x
- **特殊 IP**：127.0.0.1（回环）、169.254（AWS metadata）
- dify 用 IP 黑名单防 SSRF

## 5. 练习题

### 练习 1：基础（必做）

用 Python `ipaddress` 模块判断 `192.168.1.1`、`10.0.0.1`、`127.0.0.1` 是否是私有 IP。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何需要 IP 黑名单（不只是域名黑名单）。

### 练习 3：挑战（选做）

把 `192.168.1.0/24` 划分成 8 个子网，计算每个子网的地址范围。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 1918：私有 IP 地址分配
- RFC 4632：CIDR

---

**文档版本**：v1.0
**最后更新**：2026-07-13