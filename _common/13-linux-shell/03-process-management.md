# 1.3.3 进程管理：`ps` / `top` / `kill` / `systemctl`

> 掌握 Linux 进程查看、监控、终止与服务管理，能诊断 dify 后端的运行状态。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `ps` / `top` / `htop` 查看进程信息
- 用 `kill` 发送信号终止进程
- 用 `systemctl` 管理 systemd 服务
- 诊断 dify 后端进程的常见问题（CPU 高、内存泄漏、僵尸进程）

## 📚 前置知识

- 命令行基础
- [Shell 脚本](./02-shell-scripting.md)

## 1. 核心概念

### 1.1 什么是进程？

进程是**运行中的程序实例**，Linux 中每个进程都有：
- **PID**（Process ID）：唯一标识
- **PPID**（Parent PID）：父进程 ID
- **状态**：运行（R）、睡眠（S）、僵尸（Z）、停止（T）
- **资源占用**：CPU、内存、文件描述符

### 1.2 `ps`：进程快照

```bash
# 显示当前终端的所有进程
ps

# 显示所有进程（常用）
ps aux

# 输出列说明：
# USER  PID  %CPU %MEM  VSZ   RSS  TTY  STAT  START  TIME  COMMAND

# 按进程名过滤
ps aux | grep celery

# 显示进程树（PPID 关系）
ps auxf   # 或 pstree -p

# 按 CPU / 内存排序
ps aux --sort=-%cpu | head -10
ps aux --sort=-%mem | head -10

# 查看特定 PID 的详细信息
ps -p 1234 -o pid,ppid,user,cmd
```

### 1.3 `top` / `htop`：实时监控

```bash
# 实时显示所有进程（默认按 CPU 排序）
top

# top 内交互命令：
# P: 按 CPU 排序
# M: 按内存排序
# k: 杀进程（输入 PID）
# q: 退出

# htop 是 top 的增强版（彩色、鼠标友好）
htop
```

`top` 输出解读：

```
top - 10:30:45 up 30 days,  1 user,  load average: 0.52, 0.48, 0.45
Tasks: 234 total,   1 running, 233 sleeping
%Cpu(s): 12.3 us,  2.1 sy,  0.0 ni, 85.6 id   ← CPU 使用率
MiB Mem :  16000 total,   8000 free,   4000 used,   4000 buff/cache
MiB Swap:   2000 total,   1000 free,   1000 used
```

- **load average**：1/5/15 分钟平均负载（> CPU 核数说明过载）
- **id（idle）**：CPU 空闲率，< 20% 说明 CPU 紧张

### 1.4 `kill`：发送信号

Linux 信号机制：
- **进程间通信**：内核通知进程"发生了什么"
- 常用信号：
  - `SIGTERM`（15）：优雅终止（默认）
  - `SIGKILL`（9）：强制终止（不可捕获）
  - `SIGHUP`（1）：重载配置
  - `SIGINT`（2）：Ctrl+C 同效

```bash
# 优雅终止（推荐）
kill 1234             # 发 SIGTERM
kill -15 1234         # 等价

# 强制终止（最后手段）
kill -9 1234          # 发 SIGKILL

# 按进程名终止
pkill celery
pkill -f "celery worker"

# 重载配置（dify 不太常用）
kill -HUP 1234
```

### 1.5 后台进程：`&` / `nohup` / `disown`

```bash
# 后台运行
python api.py &

# 不挂起（即使关闭终端也继续运行）
nohup python api.py > /tmp/api.log 2>&1 &

# nohup 详解：
# > /tmp/api.log    重定向 stdout 到文件
# 2>&1              把 stderr 也重定向到 stdout
# &                 后台运行

# jobs / fg / bg
jobs                 # 查看当前 shell 的后台任务
fg %1                # 把任务 1 调到前台
bg %1                # 继续后台运行任务 1
```

### 1.6 `systemctl`：管理 systemd 服务

systemd 是现代 Linux 的服务管理器：

```bash
# 查看服务状态
systemctl status dify-api

# 启动 / 停止 / 重启
sudo systemctl start dify-api
sudo systemctl stop dify-api
sudo systemctl restart dify-api

# 启用开机自启
sudo systemctl enable dify-api

# 查看日志
sudo journalctl -u dify-api -f          # 实时跟踪
sudo journalctl -u dify-api --since "1 hour ago"

# 查看所有失败的服务
systemctl --failed
```

## 2. 代码示例

### 2.1 排查 dify CPU 占用过高

```bash
# 步骤 1：找出 CPU 最高的进程
top -b -n 1 | head -20

# 步骤 2：定位到具体进程
ps aux | grep dify

# 步骤 3：查看进程的线程（哪个线程占用高）
ps -eLf | grep <PID> | head

# 步骤 4：用 py-spy dump Python 栈
py-spy dump --pid <PID>
```

### 2.2 优雅重启 dify worker

```bash
# 找到 worker 主进程
ps aux | grep "celery worker" | grep -v grep | awk '{print $2}'

# 发 SIGTERM（Celery 会等待当前任务完成后退出）
pkill -TERM -f "celery worker"

# 等待 5 秒，检查是否退出
sleep 5
ps aux | grep "celery worker" | grep -v grep

# 如果还在，强杀
pkill -9 -f "celery worker"
```

### 2.3 用 nohup 启动 dify 后台

```bash
# 在生产环境启动 dify（脱离终端）
cd /opt/dify/api
nohup uv run gunicorn dify_app:app \
    --bind 0.0.0.0:5001 \
    --workers 4 \
    > /var/log/dify/api.log 2>&1 &

# 立即返回，不阻塞 shell
echo "Started PID: $!"
```

### 2.4 常见错误：直接 kill -9

```bash
# ❌ 错误：直接 kill -9，导致 Celery 任务中断、数据库连接泄漏
kill -9 1234

# ✅ 正确：先 SIGTERM，给进程 30 秒优雅退出
kill 1234
sleep 30
if kill -0 1234 2>/dev/null; then
    echo "Still running, force kill"
    kill -9 1234
fi
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Gunicorn 配置

**文件位置**：`/Users/xu/code/github/dify/api/gunicorn.conf.py`
**核心代码**（行 1-30）：

```python
"""Gunicorn 生产服务器配置。"""

# 监听端口
bind = "0.0.0.0:5001"

# Worker 进程数（推荐 2 * CPU 核数 + 1）
workers = 4
worker_class = "gevent"   # 协程 worker，适合 I/O 密集

# 超时
timeout = 3600            # 1 小时（LLM 调用可能很慢）

# 优雅退出
graceful_timeout = 60     # 收到 SIGTERM 后等待 60 秒
keepalive = 5

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名
proc_name = "dify-api"
```

**解读**：
- 第 7 行：`worker_class = "gevent"` 用协程 worker 提升 I/O 并发
- 第 10 行：`timeout = 3600` 给 LLM 慢响应留足时间
- 第 13 行：`graceful_timeout = 60` 让 worker 收到 SIGTERM 后能完成当前请求
- **关键设计**：通过配置文件而非命令行参数管理进程行为，便于版本控制

### 3.2 dify 的 Celery 入口

**文件位置**：`/Users/xu/code/github/dify/api/celery_entrypoint.py`
**核心代码**（行 1-25）：

```python
"""Celery worker 进程入口。"""

import os

from celery import Celery

celery_app = Celery("dify")

# 从环境变量加载 broker / backend
celery_app.conf.update(
    broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    task_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,  # 防止大任务阻塞小任务
)

# 启动命令：
# celery -A celery_entrypoint.celery_app worker --loglevel=info --concurrency=4
```

**解读**：
- 第 9-10 行：broker 和 backend 都用 Redis
- 第 14 行：`task_track_started=True` 让任务状态包含"已启动"
- 第 15 行：`worker_prefetch_multiplier=1` 每次只预取 1 个任务，避免长任务饿死短任务
- **关键设计**：通过环境变量注入配置（12-Factor），同一镜像可在多环境运行

## 4. 关键要点总结

- `ps aux` 查看进程快照，`top` / `htop` 实时监控
- 信号机制：`SIGTERM`（15）优雅退出，`SIGKILL`（9）强制终止
- **永远先 SIGTERM，再 SIGKILL**，给进程清理资源的时间
- `nohup cmd > log 2>&1 &` 是后台运行的标准模式
- `systemctl` 管理 systemd 服务，`journalctl` 看日志
- dify 用 Gunicorn + gevent 运行 API，用 Celery + Redis 跑异步任务

## 5. 练习题

### 练习 1：基础（必做）

用 `ps aux` 列出你本机所有 `python` 进程，然后用 `top` 实时监控 10 秒，按 CPU 排序。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/gunicorn.conf.py`，解释每个配置项的作用，重点关注 `worker_class="gevent"` 的设计意图。

### 练习 3：挑战（选做）

写一个 `restart_dify.sh` 脚本：找到当前 dify-api 主进程，发 SIGTERM，等待 30 秒，如果还在则 SIGKILL，最后启动新的进程。要求用 `systemctl` 或自定义进程管理。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/gunicorn.conf.py`
- `/Users/xu/code/github/dify/api/celery_entrypoint.py`
- Gunicorn 文档：https://docs.gunicorn.org/en/stable/
- systemd 文档：https://www.freedesktop.org/software/systemd/man/systemctl.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13