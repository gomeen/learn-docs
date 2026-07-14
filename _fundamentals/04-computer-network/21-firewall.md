# 4.5.2 防火墙与 ACL

> 防火墙是网络安全的第一道防线。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解防火墙的工作原理
- 区分不同类型的防火墙
- 知道 ACL 规则的设计
- 能在 dify 中识别网络隔离的应用

## 📚 前置知识

- 16-ip-subnet.md

## 1. 核心概念

### 1.1 防火墙是什么？

**防火墙**：控制网络流量的设备或软件，根据规则允许/拒绝数据包。

**位置**：
- 边界（企业网 ↔ 互联网）
- 内部（不同子网间）
- 主机（个人电脑）

### 1.2 防火墙的类型

#### 包过滤防火墙（Packet Filter）

**第 3 层**，检查 IP 头、TCP/UDP 头。

```
规则示例：
- 允许 192.168.1.0/24 → 任何地方的 80 端口
- 允许任何地方 → 192.168.1.0/24 的 22 端口
- 拒绝其他所有
```

**特点**：简单、快、不检查应用层内容

#### 状态检测防火墙（Stateful Inspection）

**第 3-4 层**，跟踪连接状态。

```
状态：
- NEW：新建连接
- ESTABLISHED：已建立
- RELATED：相关连接（如 FTP 数据通道）
- INVALID：无效

规则：
- 允许 ESTABLISHED 连接的响应（默认）
- 允许新建的出站连接
- 拒绝新建的入站连接（默认）
```

#### 应用层防火墙（Application Firewall / WAF）

**第 7 层**，检查 HTTP 内容。

```
WAF 规则：
- 检测 SQL 注入关键字（UNION SELECT）
- 检测 XSS 攻击（<script>）
- 检测恶意文件上传
- 速率限制（防 DDoS）
```

#### 下一代防火墙（NGFW）

**综合**：包过滤 + 状态检测 + 应用识别 + IPS

### 1.3 Linux iptables

**iptables 是 Linux 内置的包过滤防火墙**。

**表（tables）**：
- `filter`：过滤（默认）
- `nat`：地址转换
- `mangle`：修改包

**链（chains）**：
- `INPUT`：入站
- `OUTPUT`：出站
- `FORWARD`：转发
- `PREROUTING`：路由前
- `POSTROUTING`：路由后

**规则示例**：
```bash
# 允许 SSH（22）
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP（80）
iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 默认拒绝入站
iptables -A INPUT -j DROP
```

### 1.4 ACL（访问控制列表）

**ACL**：路由器/交换机上的流量控制规则。

**类型**：
- **标准 ACL**：只匹配源 IP（1-99）
- **扩展 ACL**：匹配 IP、端口、协议（100-199）

**示例**：
```
! Cisco IOS
access-list 100 permit tcp 192.168.1.0 0.0.0.255 any eq 80
access-list 100 permit tcp 192.168.1.0 0.0.0.255 any eq 443
access-list 100 deny ip any any

interface FastEthernet 0/0
  ip access-group 100 in
```

### 1.5 防火墙 vs ACL

| 特性 | 防火墙 | ACL |
|------|--------|-----|
| 层级 | 3-7 层 | 3-4 层 |
| 性能 | 较慢 | 快 |
| 功能 | 复杂（状态、DPI） | 简单（规则匹配） |
| 部署 | 独立设备 | 路由器功能 |

### 1.6 防火墙的最佳实践

1. **默认拒绝**：拒绝所有，允许特定
2. **最小权限**：只开放必需端口
3. **状态检测**：跟踪连接状态
4. **日志审计**：记录所有拒绝的流量
5. **分层防御**：边界 + 内部 + 主机

## 2. 代码示例

### 2.1 iptables 规则管理

```bash
# 文件：iptables_rules.sh

# 1. 清空现有规则
iptables -F
iptables -X

# 2. 默认策略
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 3. 允许回环
iptables -A INPUT -i lo -j ACCEPT

# 4. 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 5. 允许 SSH（限制来源 IP）
iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 22 -j ACCEPT

# 6. 允许 HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 7. 允许 ping（限制速率）
iptables -A INPUT -p icmp --icmp-type 8 -m limit --limit 1/s -j ACCEPT

# 8. 防止 SYN 洪泛
iptables -A INPUT -p tcp --syn -m limit --limit 1/s --limit-burst 3 -j ACCEPT

# 9. 保存规则（Debian/Ubuntu）
iptables-save > /etc/iptables.rules
```

### 2.2 Python iptables 操作

```python
# 文件：iptables_python.py
import subprocess

def iptables_add_rule(rule: str) -> None:
    """添加 iptables 规则。"""
    subprocess.run(
        f"iptables -A {rule}",
        shell=True, check=True,
    )

def iptables_list_rules() -> str:
    """列出所有规则。"""
    result = subprocess.run(
        "iptables -L -n -v",
        shell=True, capture_output=True, text=True,
    )
    return result.stdout

# 示例
# iptables_add_rule("INPUT -p tcp --dport 22 -j ACCEPT")
# print(iptables_list_rules())
```

### 2.3 Web 应用防火墙（Flask 简化版）

```python
# 文件：simple_waf.py
from flask import Flask, request, abort
import re

app = Flask(__name__)

# WAF 规则
WAF_RULES = {
    "sql_injection": [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b.*=.*)",
        r"('.*--)",
    ],
    "xss": [
        r"<script.*?>",
        r"javascript:",
        r"onerror\s*=",
    ],
    "path_traversal": [
        r"\.\./",
        r"\.\.\\",
    ],
}

def check_request() -> bool:
    """WAF 检查。"""
    # 检查所有参数
    for key, value in request.args.items():
        if not check_value(value):
            return False

    # 检查请求体
    if request.data:
        if not check_value(request.data.decode("utf-8", errors="ignore")):
            return False

    return True

def check_value(value: str) -> bool:
    """检查值是否包含恶意内容。"""
    value_lower = value.lower()
    for category, patterns in WAF_RULES.items():
        for pattern in patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                abort(403, description=f"WAF: {category}")
    return True

@app.before_request
def waf():
    if not check_request():
        abort(403)

@app.route("/api/data")
def api():
    return {"data": "value"}
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Docker 网络隔离

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（简化）：

```yaml
# dify 的 Docker 网络配置

networks:
  dify-network:
    driver: bridge
    # 内部网络（不暴露到主机）
    internal: false  # Nginx 需要外部访问
    ipam:
      config:
        - subnet: 192.168.1.0/24  # 自定义子网

services:
  # 暴露公网的 Nginx
  nginx:
    image: nginx
    networks:
      - dify-network
    ports:
      - "80:80"

  # 仅内网的 API
  api:
    image: dify-api
    networks:
      - dify-network
    # 不暴露端口（只能通过 Nginx 访问）

  # 仅内网的数据库
  db:
    image: postgres
    networks:
      - dify-network
    # 不暴露端口（只能通过 API 访问）

  # 仅内网的 Redis
  redis:
    image: redis
    networks:
      - dify-network
    # 不暴露端口
```

**解读**：
- 第 8-13 行：自定义 Docker 网络（类似内网）
- 第 17 行：Nginx 暴露公网
- 第 26、35、44 行：内部服务不暴露端口
- **设计意图**：网络隔离，只暴露必要的服务

### 3.2 dify 的容器安全

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（简化）：

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: dify123456  # 应改为 secret
    volumes:
      - ./volumes/db/data:/var/lib/postgresql/data
    # 禁用特权模式
    privileged: false
    # 限制资源
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
    # 只读文件系统（除必要目录）
    read_only: true
    tmpfs:
      - /tmp
      - /run
    # 禁用新的 privileges
    security_opt:
      - no-new-privileges:true
```

**解读**：
- 第 11 行：限制资源（防止 DoS）
- 第 16-17 行：只读文件系统
- 第 22 行：禁用新权限
- **设计意图**：容器安全最佳实践

## 4. 关键要点总结

- **防火墙**：包过滤、状态检测、WAF、NGFW
- **iptables**：Linux 内置防火墙
- **ACL**：路由器上的流量控制
- **最佳实践**：默认拒绝、最小权限、分层防御
- dify 用 Docker 网络隔离 + 容器安全

## 5. 练习题

### 练习 1：基础（必做）

用 iptables 配置规则：只允许 192.168.1.0/24 网段访问本机的 22 端口。

### 练习 2：进阶

阅读 `docker/docker-compose.yaml`，说明 dify 为何用 Docker 网络隔离服务。

### 练习 3：挑战（选做）

用 Flask 实现一个简单的 WAF，检测 SQL 注入和 XSS 攻击。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- iptables 文档：man iptables
- 《网络攻防实战》第 3 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13