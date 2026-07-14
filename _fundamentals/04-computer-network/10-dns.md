# 4.2.7 DNS 解析过程

> DNS 是互联网的"电话簿"，把域名转换为 IP 地址。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 DNS 的查询流程
- 理解 DNS 缓存、TTL 等机制
- 能在 dify 中识别 DNS 的应用（自定义解析器）

## 📚 前置知识

- 02-tcp-ip.md

## 1. 核心概念

### 1.1 什么是 DNS？

**DNS（Domain Name System）**：把域名（如 `www.example.com`）转换为 IP（如 `93.184.216.34`）的分布式数据库。

**为什么不直接用 IP？**
- IP 难记
- 服务器迁移要换 IP
- 一个域名可以对应多个 IP（负载均衡）

### 1.2 DNS 层级结构

```
                            . （根）
                            │
              ┌─────────────┼─────────────┐
              │             │             │
            .com          .org          .net
              │
        ┌─────┴─────┐
        │           │
    example.com   google.com
        │
   ┌────┼────┐
   │    │    │
  www  api  mail
```

### 1.3 DNS 查询类型

**递归查询**：客户端 → DNS 服务器（完整解析）
**迭代查询**：DNS 服务器 → 其他 DNS 服务器（逐步查询）

```
客户端 → ISP DNS（递归）→ 根 DNS（迭代）→ .com DNS（迭代）→ example.com DNS
                                                                     │
                                                          返回 IP ←─┘
```

### 1.4 DNS 解析完整流程

```
1. 浏览器缓存
   ↓ 未命中
2. 系统 DNS 缓存（glibc nscd）
   ↓ 未命中
3. /etc/hosts 文件
   ↓ 未命中
4. 系统配置的 DNS 服务器（/etc/resolv.conf）
   ↓ 递归
5. ISP DNS 服务器
   ↓ 迭代
6. 根 DNS 服务器（返回 .com 服务器地址）
7. .com DNS 服务器（返回 example.com 服务器地址）
8. example.com DNS 服务器（返回 www 的 IP）
   ↓
返回 IP，缓存到各层
```

### 1.5 DNS 记录类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **A** | 域名 → IPv4 | `www.example.com → 93.184.216.34` |
| **AAAA** | 域名 → IPv6 | `www.example.com → 2001:db8::1` |
| **CNAME** | 别名 | `www → example.com` |
| **MX** | 邮件服务器 | `example.com → mail.example.com` |
| **NS** | DNS 服务器 | `example.com → ns1.example.com` |
| **TXT** | 文本记录 | SPF、DKIM 验证 |
| **PTR** | IP → 域名（反向） | `93.184.216.34 → www.example.com` |

### 1.6 DNS 缓存和 TTL

**TTL（Time To Live）**：缓存时间

```
example.com.   3600   IN   A   93.184.216.34
   │           │
   域名      TTL（秒）
```

**缓存层级**：
- 浏览器缓存（60 秒）
- 系统缓存（nscd）
- ISP DNS 缓存（按 TTL）

### 1.7 DNS 安全问题

**DNS 劫持**：
- 篡改 DNS 响应
- 返回假 IP

**DNS 污染**：
- 在错误的 DNS 服务器注入假记录

**防护**：
- **DNSSEC**：数字签名验证
- **DoH（DNS over HTTPS）**：加密 DNS 查询
- **DoT（DNS over TLS）**：TLS 加密 DNS

## 2. 代码示例

### 2.1 DNS 查询

```python
# 文件：dns_query.py
import socket

def dns_lookup(host: str) -> list[str]:
    """DNS 查询。"""
    try:
        # A 记录（IPv4）
        ips = socket.gethostbyname_ex(host)
        print(f"主机名: {ips[0]}")
        print(f"别名: {ips[1]}")
        print(f"IP 列表: {ips[2]}")
        return ips[2]
    except socket.gaierror as e:
        print(f"DNS 失败: {e}")
        return []

# 测试
ips = dns_lookup("www.baidu.com")
```

### 2.2 自定义 DNS 解析（防 SSRF）

```python
# 文件：safe_dns.py
import socket
import ipaddress

class SafeDNSResolver:
    """安全的 DNS 解析器。

    dify 用自定义解析器防止 SSRF：
    - 解析域名
    - 检查返回的 IP 是否内网
    - 如果是内网，抛异常
    """

    # 内网 IP 段
    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("0.0.0.0/8"),
    ]

    @classmethod
    def is_private_ip(cls, ip: str) -> bool:
        """检查是否是内网 IP。"""
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in net for net in cls.PRIVATE_RANGES)
        except ValueError:
            return False

    @classmethod
    def safe_resolve(cls, host: str) -> str:
        """解析域名，验证不是内网。"""
        try:
            ips = socket.gethostbyname_ex(host)[2]
        except socket.gaierror:
            raise ValueError(f"DNS 解析失败: {host}")

        for ip in ips:
            if cls.is_private_ip(ip):
                raise ValueError(f"内网 IP 拒绝: {host} → {ip}")

        return ips[0]

# 测试
print(SafeDNSResolver.safe_resolve("www.baidu.com"))  # 公网 IP
# SafeDNSResolver.safe_resolve("localhost")  # 抛异常
```

### 2.3 DoH 查询

```python
# 文件：doh_query.py
import requests

def doh_query(domain: str) -> dict:
    """DoH（DNS over HTTPS）查询 - 更安全。"""
    # Cloudflare DoH
    url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=A"
    headers = {"Accept": "application/dns-json"}
    resp = requests.get(url, headers=headers, timeout=5)
    return resp.json()

# 测试
result = doh_query("www.baidu.com")
print(result)
```

## 3. dify 仓库源码解读

### 3.1 dify 的自定义 DNS 解析（SSRF 防护）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 30-50）：

```python
import socket
import ipaddress
import asyncio

class CustomSafeResolver:
    """dify 的安全 DNS 解析器。

    SSRF 攻击流程：
    1. 攻击者调用 dify 的 API，传入 URL = http://169.254.169.254/
    2. dify 解析 DNS（普通解析器）
    3. dify 请求该 URL
    4. 攻击者访问 AWS 元数据，获取凭证

    防护：
    1. 自定义 DNS 解析器
    2. 检查解析结果是否是内网 IP
    3. 如果是内网，抛异常
    """

    # 内网 IP 黑名单
    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),  # AWS metadata
        ipaddress.ip_network("0.0.0.0/8"),
    ]

    async def resolve(self, host: str) -> list[dict]:
        """异步解析域名。"""
        loop = asyncio.get_event_loop()
        # 用 getaddrinfo 解析
        infos = await loop.getaddrinfo(
            host, None,
            type=socket.SOCK_STREAM,
        )
        results = []
        for info in infos:
            ip = info[4][0]
            # 检查内网
            if self._is_private_ip(ip):
                raise ValueError(f"SSRF 防护：拒绝内网 IP {ip}")
            results.append({"hostname": host, "host": ip, "port": info[4][1]})
        return results

    def _is_private_ip(self, ip: str) -> bool:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in self.PRIVATE_RANGES)


# dify 的 SSRF 防护层次：
# 1. URL 黑名单（协议、域名）
# 2. DNS 解析层（自定义解析器）
# 3. IP 验证层（检查解析结果）
# 4. 端口限制（如禁用 22、3306 等敏感端口）
```

**解读**：
- 第 28 行：`getaddrinfo` 异步解析
- 第 36 行：检查内网 IP（防 SSRF）
- **设计意图**：阻止解析到内网 IP，防止访问云元数据等敏感服务

## 4. 关键要点总结

- **DNS**：分布式域名解析系统
- **层级**：根 → 顶级域 → 二级域 → 子域
- **记录类型**：A、AAAA、CNAME、MX、NS 等
- **TTL**：控制缓存时间
- **DoH / DoT**：加密 DNS 查询
- dify 用自定义 DNS 解析防 SSRF

## 5. 练习题

### 练习 1：基础（必做）

用 Python `socket.gethostbyname_ex` 查询 `www.baidu.com` 的所有 IP。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何自定义 DNS 解析器。

### 练习 3：挑战（选做）

实现一个简单的 DNS 解析器（递归查询根 DNS → 顶级域 DNS）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 1034、1035：DNS 规范
- 《计算机网络：自顶向下方法》第 2 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13