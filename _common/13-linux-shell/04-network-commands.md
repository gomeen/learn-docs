# 1.3.4 网络命令：`curl` / `wget` / `netstat` / `ss`

> 掌握常用网络命令，能用 curl 调用 dify API、用 ss 诊断端口占用、用 wget 下载资源。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `curl` 调用 dify REST API（设计规范见 [REST API 设计](../14-api-protocols/02-rest-api-design.md)）并调试响应
- 用 `ss` 替代 `netstat` 诊断端口和连接
- 用 `wget` 下载文件或镜像
- 用 `ping` / `traceroute` / `dig` 排查网络问题

## 📚 前置知识

- HTTP 基础（GET/POST、状态码）
- [Linux 常用命令](./01-linux-commands.md)

## 1. 核心概念

### 1.1 `curl`：HTTP 调试利器

curl 是命令行 HTTP 客户端，是开发者调试 API 的核心工具：

```bash
# 基本 GET 请求
curl https://api.dify.ai/v1/health

# 显示完整响应（含头）
curl -i https://api.dify.ai/v1/health

# 只显示头
curl -I https://api.dify.ai/v1/health

# POST JSON
curl -X POST https://api.dify.ai/v1/workflows/run \
    -H "Authorization: Bearer app-xxx" \
    -H "Content-Type: application/json" \
    -d '{"inputs": {"query": "hello"}}'

# 保存响应到文件
curl -o response.json https://api.dify.ai/v1/health

# 跟随重定向
curl -L https://bit.ly/some-link

# 详细输出（看握手过程）
curl -v https://api.dify.ai/v1/health

# 上传文件
curl -F "file=@/tmp/upload.txt" https://api.dify.ai/v1/files/upload

# 设置超时
curl --connect-timeout 5 --max-time 30 https://api.dify.ai/v1/health
```

### 1.2 `wget`：下载文件

```bash
# 下载单个文件
wget https://example.com/file.zip

# 指定保存文件名
wget -O myfile.zip https://example.com/file.zip

# 后台下载
wget -b https://example.com/large-file.zip

# 断点续传
wget -c https://example.com/large-file.zip

# 镜像整个站点（谨慎使用）
wget -m -p -k https://docs.dify.ai
```

### 1.3 `ss`：网络连接诊断

`ss` 是 `netstat` 的现代替代品，速度快 10 倍：

```bash
# 显示所有 TCP 连接
ss -t

# 显示所有监听端口
ss -tlnp
# -t: TCP
# -l: 监听
# -n: 数字端口（不解析服务名）
# -p: 显示进程

# 显示所有 UDP 连接
ss -u

# 显示 Unix 域套接字
ss -x

# 显示 Socket 统计
ss -s

# 按状态过滤
ss -t state established
ss -t state time-wait | wc -l   # 统计 TIME_WAIT 数（可能过多）

# 查看特定端口
ss -tlnp | grep 5001
```

### 1.4 `ping` / `traceroute` / `dig`

```bash
# ping（测试连通性）
ping api.dify.ai
ping -c 4 api.dify.ai          # 只发 4 个包

# traceroute（路由追踪）
traceroute api.dify.ai
mtr api.dify.ai                # 实时路由监控（推荐）

# DNS 查询
dig api.dify.ai
dig api.dify.ai +short         # 只显示结果
dig api.dify.ai MX             # 查询邮件记录
nslookup api.dify.ai
```

### 1.5 `tcpdump`：网络抓包

```bash
# 抓取特定端口的包
sudo tcpdump -i any port 5001 -w /tmp/capture.pcap

# 抓取特定主机
sudo tcpdump -i any host 192.168.1.10

# 抓取 HTTP 请求（明文）
sudo tcpdump -i any -A port 80 | grep -i "GET\|POST"
```

## 2. 代码示例

### 2.1 调用 dify API 进行调试

```bash
# 1. 测试健康检查
curl -s http://localhost:5001/health | jq .

# 2. 上传文件
curl -X POST http://localhost:5001/v1/files/upload \
    -H "Authorization: Bearer app-xxxxxxxx" \
    -F "file=@/tmp/document.pdf" \
    -F "user=user-001"

# 3. 发起工作流运行
curl -X POST http://localhost:5001/v1/workflows/run \
    -H "Authorization: Bearer app-xxxxxxxx" \
    -H "Content-Type: application/json" \
    -d '{
        "inputs": {"query": "什么是 LLM？"},
        "user": "user-001"
    }' | jq .
```

### 2.2 诊断端口占用

```bash
# 场景：dify 启动失败，提示 "port 5001 already in use"

# 步骤 1：找出占用 5001 的进程
ss -tlnp | grep :5001
# 输出：tcp LISTEN 0  128  0.0.0.0:5001  *  users:(("python",pid=1234,fd=5))

# 步骤 2：确认是哪个进程
ps -p 1234 -o pid,user,cmd

# 步骤 3：杀掉（如果可以）
kill 1234
```

### 2.3 流式调用（SSE）调试

SSE 协议本身见 [SSE](../14-api-protocols/04-sse.md)；本节只练 `curl -N` 调试手法。

```bash
# dify 支持流式响应，用 curl 调试
curl -N -X POST http://localhost:5001/v1/chat-messages \
    -H "Authorization: Bearer app-xxx" \
    -H "Content-Type: application/json" \
    -d '{
        "inputs": {},
        "query": "讲个笑话",
        "user": "user-001",
        "response_mode": "streaming"
    }'

# -N 禁用缓冲，实时显示数据
```

### 2.4 常见错误：忘记 `-N` 看 SSE

```bash
# ❌ 错误：curl 默认缓冲，看不到流式数据
curl -X POST http://localhost:5001/v1/chat-messages ...

# ✅ 正确：用 -N 禁用缓冲
curl -N -X POST http://localhost:5001/v1/chat-messages ...
```

## 3. dify 仓库源码解读

### 3.1 dify 健康检查端点

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/health.py`
**核心代码**（行 1-30）：

```python
from flask_restx import Namespace, Resource

health_ns = Namespace("health", description="Health check")


@health_ns.route("/")
class HealthCheck(Resource):
    """健康检查端点。

    用于：
    1. Docker 健康检查
    2. Kubernetes liveness probe
    3. 负载均衡器健康探测
    """

    def get(self):
        """返回服务状态。"""
        return {"status": "ok", "version": "1.16.0"}
```

**调用方式**：

```bash
curl -s http://localhost:5001/health
# {"status": "ok", "version": "1.16.0"}
```

**解读**：
- 健康检查端点必须**快速、无副作用**（不查 DB、不发邮件）
- 返回简单 JSON 即可，被 K8s / Docker / LB 解析
- **关键设计**：用 `/health` 路径作为行业约定

### 3.2 dify 的 SSRF 防护：HTTP 代理

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 1-30）：

```python
"""SSRF 安全的 HTTP 代理：dify 后端调用外部 API 时通过此代理转发。

防止攻击者让服务器访问内部地址（如 127.0.0.1、169.254.169.254）。
"""

import os

# 内部代理地址（通过环境变量配置）
HTTP_PROXY = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "")

# 调试：测试代理是否生效
# curl -x http://proxy.internal:8080 https://api.dify.ai/v1/health
```

**解读**：
- dify 通过 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量配置代理
- 所有外部 HTTP 请求都通过代理转发，便于审计和过滤
- **调试技巧**：用 `curl -x` 测试代理是否生效

## 4. 关键要点总结

- `curl` 是 HTTP 调试核心，`-i`/`-I`/`-v` 控制输出详细程度
- 用 `jq` 格式化 JSON 响应：`curl ... | jq .`
- `ss -tlnp` 查看监听端口和占用进程（替代 `netstat`）
- 流式响应必须用 `curl -N` 禁用缓冲
- `dig` / `nslookup` 查 DNS，`mtr` 实时路由监控
- dify `/health` 端点用于 K8s/Docker 健康检查

## 5. 练习题

### 练习 1：基础（必做）

用 `curl` 调用本机 dify 健康检查（如未运行则用 https://api.dify.ai/v1/health 公开 demo），并用 `jq` 格式化输出。

### 练习 2：进阶

用 `ss -tlnp` 列出本机所有监听端口，找出哪些是 dify / 数据库 / Redis 相关的端口。

### 练习 3：挑战（选做）

写一个 `dify_api_test.sh` 脚本：读取 API_KEY 和 BASE_URL 环境变量，自动测试 5 个常见端点（/health、/v1/workspaces、/v1/apps 等），用 curl + jq 输出格式化的测试报告。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/health.py`
- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- curl 官方文档：https://curl.se/docs/
- iproute2 文档（ss）：https://man7.org/linux/man-pages/man8/ss.8.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13