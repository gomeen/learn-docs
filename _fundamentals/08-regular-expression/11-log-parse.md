# 3.2 日志解析：Nginx / Apache 日志

> 日志解析是正则的经典应用。本文以 Nginx 和 Apache 日志为例。

## 🎯 学习目标

完成本文档后，你将能够：
- 解析 Nginx/Apache 访问日志
- 提取关键字段（IP、时间、状态码、URL）
- 用命名组让解析更清晰
- 在 dify/ruoyi 中应用日志解析

## 📚 前置知识

- 01-05 正则基础
- 04-group.md（命名组）

## 1. 核心概念

### 1.1 Nginx 访问日志格式

```
192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users?id=1 HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
```

字段：
- 远程 IP
- 用户标识
- 用户名
- 时间
- 请求行（方法、URL、协议）
- 状态码
- 响应大小
- Referer
- User-Agent

### 1.2 Apache 通用日志格式（CLF）

```
127.0.0.1 - frank [10/Oct/2023:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
```

## 2. 代码示例

### 2.1 Nginx 日志解析

```python
import re
from dataclasses import dataclass

@dataclass
class NginxLog:
    ip: str
    time: str
    method: str
    path: str
    status: int
    size: int
    user_agent: str


# Nginx combined 日志格式
NGINX_PATTERN = r"""
^(?P<ip>\S+)\s+                # 远程 IP
\S+\s+                          # 用户标识
\S+\s+                          # 用户名
\[(?P<time>[^\]]+)\]\s+         # 时间
"(?P<method>\S+)\s+             # 方法
(?P<path>\S+)\s+                # URL
[^"]+"\s+                       # 协议
(?P<status>\d+)\s+              # 状态码
(?P<size>\d+)\s+                # 响应大小
"[^"]*"\s+                      # Referer
"(?P<user_agent>[^"]*)"         # User-Agent
"""

log_line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users?id=1 HTTP/1.1" 200 1234 "-" "Mozilla/5.0"'

m = re.match(NGINX_PATTERN, log_line, re.X)
if m:
    log = NginxLog(
        ip=m.group("ip"),
        time=m.group("time"),
        method=m.group("method"),
        path=m.group("path"),
        status=int(m.group("status")),
        size=int(m.group("size")),
        user_agent=m.group("user_agent"),
    )
    print(log)
```

### 2.2 Apache 日志解析

```python
APACHE_PATTERN = r"""
^(?P<ip>\S+)\s+                # IP
\S+\s+                          # 用户标识
(?P<user>\S+)\s+                # 用户
\[(?P<time>[^\]]+)\]\s+         # 时间
"(?P<request>[^"]+)"\s+         # 请求
(?P<status>\d+)\s+              # 状态
(?P<size>\S+)                   # 响应大小
"""

line = '127.0.0.1 - frank [10/Oct/2023:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326'

m = re.match(APACHE_PATTERN, line, re.X)
if m:
    print(m.groupdict())
```

### 2.3 日志分析（统计）

```python
import re
from collections import Counter

log_lines = """\
192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla"
192.168.1.2 - - [10/Oct/2023:13:55:37 +0000] "POST /api/login HTTP/1.1" 401 567 "-" "Mozilla"
192.168.1.1 - - [10/Oct/2023:13:55:38 +0000] "GET /api/users/1 HTTP/1.1" 200 890 "-" "Chrome"
192.168.1.3 - - [10/Oct/2023:13:55:39 +0000] "GET /static/style.css HTTP/1.1" 404 234 "-" "Safari"
192.168.1.1 - - [10/Oct/2023:13:55:40 +0000] "GET /api/posts HTTP/1.1" 200 5678 "-" "Mozilla"
"""

status_pattern = r'" (?P<status>\d{3}) '
statuses = [int(m.group("status")) for m in re.finditer(status_pattern, log_lines)]
print(f"Status distribution: {Counter(statuses)}")

# IP 访问次数
ip_pattern = r"^(?P<ip>\S+)"
ips = [m.group("ip") for m in re.finditer(ip_pattern, log_lines, re.M)]
print(f"IP counts: {Counter(ips)}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的日志格式

**位置**：`/Users/xu/code/github/dify/api/core/logging/`
**核心代码**：

```python
import re
from datetime import datetime

# dify 的日志格式（简化）
LOG_PATTERN = r"""
(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,]\d+)
\s+\[(?P<level>\w+)\]\s+
(?P<logger>[\w.]+):
\s+(?P<message>.*)
"""

def parse_dify_log(line: str) -> dict | None:
    """解析 dify 日志"""
    m = re.match(LOG_PATTERN, line, re.X)
    if not m:
        return None
    return {
        "timestamp": m.group("timestamp"),
        "level": m.group("level"),
        "logger": m.group("logger"),
        "message": m.group("message"),
    }


# 测试
line = "2026-07-13 10:30:45,123 [INFO] api.services.workflow: Workflow started"
print(parse_dify_log(line))
```

**解读**：
- 用命名组让解析结果易读
- 适合 dify 日志分析工具

### 3.2 dify/ruoyi 中无直接 Nginx 解析

**说明**：dify/ruoyi 通常用 ELK、Loki 等日志系统，但核心解析逻辑也是基于正则。

## 4. 关键要点总结

- Nginx 日志：IP + 时间 + 请求 + 状态 + 大小 + UA
- Apache 日志类似但字段略少
- 用命名组让正则更易维护
- 多行模式 `re.M` 用于解析多行日志
- dify 日志格式：时间戳 + 级别 + logger + 消息

## 5. 练习题

### 练习 1：基础
用正则解析一行 Nginx 日志，提取所有字段。

### 练习 2：进阶
写一个日志分析脚本：统计每分钟的请求数、错误率、Top 10 IP。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/logging/`
- Nginx 日志格式：http://nginx.org/en/docs/http/ngx_http_log_module.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13