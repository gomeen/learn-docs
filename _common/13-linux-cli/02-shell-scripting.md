# 13.2 Shell 脚本：变量、条件、循环、函数

> 掌握 Bash 脚本编程基础，能阅读和编写常见运维脚本（启动、健康检查、日志分析等）。

## 🎯 学习目标

完成本文档后，你将能够：
- 编写带变量、条件、循环、函数的 Bash 脚本
- 理解 `$?`、`$$`、`$@` 等特殊变量
- 调试 Bash 脚本（`set -e`、`set -x`）
- 看懂项目中的 `.sh` 运维脚本

## 📚 前置知识

- 命令行基础（cd、ls、pwd）
- [13.1 Linux 常用命令](./01-linux-commands.md)

## 1. 核心概念

### 1.1 第一个 Shell 脚本

```bash
#!/bin/bash
# 注释以 # 开头
# 第一行 shebang 告诉系统用哪个解释器

echo "Hello, World!"
```

```bash
# 赋予执行权限并运行
chmod +x hello.sh
./hello.sh
```

### 1.2 变量

```bash
# 定义（注意：= 两边不能有空格！）
name="dify"
version="1.16.0"

# 使用（必须加 $）
echo "App: $name, Version: $version"
echo "App: ${name}_api"   # 花括号用于边界

# 命令替换
current_dir=$(pwd)
today=$(date +%Y-%m-%d)

# 只读变量
readonly MAX_RETRIES=3

# 环境变量
export API_KEY="secret"
```

### 1.3 特殊变量

| 变量 | 含义 |
|---|---|
| `$0` | 脚本名 |
| `$1`, `$2`... | 位置参数 |
| `$@` | 所有参数（推荐使用） |
| `$#` | 参数个数 |
| `$?` | 上一个命令的退出码 |
| `$$` | 当前进程 PID |
| `!!` | 上一条命令（交互式） |

```bash
#!/bin/bash
echo "Script: $0"
echo "First arg: $1"
echo "All args: $@"
echo "Total args: $#"

# 上一个命令是否成功
if grep -q "error" /var/log/app.log; then
    echo "Errors found"
fi
```

### 1.4 条件判断

```bash
# if 语句
if [ "$1" = "start" ]; then
    echo "Starting..."
elif [ "$1" = "stop" ]; then
    echo "Stopping..."
else
    echo "Usage: $0 {start|stop}"
fi

# 文件测试
if [ -f "/tmp/config.yaml" ]; then
    echo "Config exists"
fi
if [ -d "/tmp/data" ]; then
    echo "Data dir exists"
fi

# 数值比较（注意用 -eq / -lt / -gt，不是 == < >）
if [ "$count" -gt 10 ]; then
    echo "Too many"
fi

# 字符串比较
if [ -z "$name" ]; then
    echo "Name is empty"
fi

# 推荐用 [[ ]]（Bash 扩展，更安全）
if [[ "$name" == "dify" ]]; then
    echo "Welcome, dify"
fi
```

### 1.5 循环

```bash
# for 循环
for i in 1 2 3 4 5; do
    echo "Number: $i"
done

# for 遍历文件
for file in /tmp/*.txt; do
    echo "Processing $file"
done

# C 风格 for
for ((i=0; i<10; i++)); do
    echo "$i"
done

# while 循环
count=0
while [ $count -lt 5 ]; do
    echo "$count"
    ((count++))
done

# 遍历命令行参数
for arg in "$@"; do
    echo "Arg: $arg"
done
```

### 1.6 函数

```bash
# 定义
greet() {
    local name="$1"   # local 声明局部变量
    echo "Hello, $name"
}

# 调用
greet "Alice"

# 返回值（只能返回 0-255 的整数）
is_file() {
    if [ -f "$1" ]; then
        return 0   # 成功
    else
        return 1   # 失败
    fi
}

if is_file "/etc/passwd"; then
    echo "Exists"
fi

# 用 echo 返回字符串
get_version() {
    cat version.txt
}
version=$(get_version)
```

### 1.7 调试：`set -e` / `set -x`

```bash
#!/bin/bash
set -euo pipefail   # 推荐放在脚本开头

# -e: 命令失败立即退出
# -u: 使用未定义变量报错
# -o pipefail: 管道中任何命令失败都算失败

set -x   # 打印执行的每个命令（调试用）
```

## 2. 代码示例

### 2.1 部署脚本

```bash
#!/bin/bash
set -euo pipefail

APP_NAME="dify-api"
DEPLOY_DIR="/opt/dify"
BACKUP_DIR="/opt/dify/backups"

# 函数：备份当前版本
backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    echo "Backing up to ${BACKUP_DIR}/${APP_NAME}_${timestamp}.tar.gz"
    tar -czf "${BACKUP_DIR}/${APP_NAME}_${timestamp}.tar.gz" -C "$DEPLOY_DIR" "$APP_NAME"
}

# 函数：拉取最新代码
pull_code() {
    cd "$DEPLOY_DIR/$APP_NAME"
    git pull origin main
}

# 函数：重启服务
restart_service() {
    systemctl restart "$APP_NAME"
    sleep 3
    if systemctl is-active --quiet "$APP_NAME"; then
        echo "Service started successfully"
    else
        echo "Service failed to start"
        exit 1
    fi
}

# 主流程
backup
pull_code
restart_service
echo "Deploy complete"
```

### 2.2 日志分析脚本

```bash
#!/bin/bash
# 分析 dify 后端的错误日志

LOG_FILE="${1:-/var/log/dify/api.log}"
ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE" || true)
WARN_COUNT=$(grep -c "WARNING" "$LOG_FILE" || true)

echo "=== Log Summary ==="
echo "ERROR:   $ERROR_COUNT"
echo "WARNING: $WARN_COUNT"

echo ""
echo "=== Top 5 errors ==="
grep "ERROR" "$LOG_FILE" | awk -F'ERROR' '{print $2}' | sort | uniq -c | sort -rn | head -5
```

### 2.3 常见错误：未引号包裹变量

```bash
# ❌ 错误：变量含空格时会拆成多个参数
file="my document.txt"
rm $file  # 会变成 rm my document.txt（删除 my 和 document.txt）

# ✅ 正确：用双引号包裹
rm "$file"  # 删除 "my document.txt"
```

## 3. dify 仓库源码解读

### 3.1 dify 的容器入口脚本

**文件位置**：`/Users/xu/code/github/dify/api/cnt_base.sh`
**核心代码**（行 1-30）：

```bash
#!/bin/bash
set -euo pipefail

# 等待依赖服务（PostgreSQL、Redis）就绪
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"
    local max_retries=30
    local retry=0

    echo "Waiting for $service at $host:$port..."
    while ! nc -z "$host" "$port"; do
        retry=$((retry + 1))
        if [ $retry -ge $max_retries ]; then
            echo "$service not available after $max_retries attempts"
            exit 1
        fi
        sleep 2
    done
    echo "$service is ready"
}

# 主流程
wait_for_service "${DB_HOST:-db}" "${DB_PORT:-5432}" "PostgreSQL"
wait_for_service "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"

echo "Starting dify API..."
exec gunicorn ...
```

**解读**：
- 第 2 行：`set -euo pipefail` 是生产级脚本的标配
- 第 5-20 行：定义 `wait_for_service` 函数，封装"等待依赖服务"的通用逻辑
- 第 14 行：`nc -z` 是 netcat 的端口探测模式
- 第 26 行：`${DB_HOST:-db}` 用 `${VAR:-default}` 语法提供默认值
- **关键设计**：通过函数封装重复逻辑，提高脚本可读性和可维护性

### 3.2 dify 的健康检查脚本

**文件位置**：`/Users/xu/code/github/dify/api/celery_healthcheck.py`
**核心代码**（行 1-20）：

```python
#!/usr/bin/env python3
"""Celery worker 健康检查脚本。"""

import sys
from celery_app import celery_app

# 检查 Celery worker 是否在线
inspect = celery_app.control.inspect()
active = inspect.active()
if active is None:
    print("No workers found")
    sys.exit(1)
else:
    print(f"Workers: {list(active.keys())}")
    sys.exit(0)
```

对应的 docker-compose 用法：

```bash
# 在 docker-compose.yaml 中
healthcheck:
  test: ["CMD", "python", "celery_healthcheck.py"]
  interval: 30s
  timeout: 10s
  retries: 3
```

**解读**：
- 健康检查脚本用 `sys.exit(0)` / `sys.exit(1)` 报告状态
- Docker 据此判断容器是否健康
- **关键设计**：健康检查脚本必须**快速、幂等**，避免副作用

## 4. 关键要点总结

- 变量赋值 `=` 两边**不能有空格**
- 字符串变量**必须用双引号**包裹（防空格、防 glob）
- 条件判断：文件用 `-f`/`-d`，数值用 `-eq`/`-gt`，字符串用 `=`/`==`
- 推荐 `[[ ]]` 替代 `[ ]`，更安全更强大
- `set -euo pipefail` 是脚本开头必备
- 函数用 `local` 声明局部变量，返回值只能 0-255
- dify 用 shell 脚本封装容器启动逻辑，等待依赖服务

## 5. 练习题

### 练习 1：基础（必做）

写一个脚本 `count_files.sh`，接受一个目录路径参数，统计该目录下 `.py` 文件数量和总行数。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/cnt_base.sh`，列出所有函数，理解每个函数的作用。

### 练习 3：挑战（选做）

写一个 `dify_migrate.sh` 脚本：接受 `--check` / `--apply` / `--rollback` 三个子命令，分别执行"检查待执行迁移"/"应用迁移"/"回滚最后一次迁移"。提示：用 `alembic` 命令。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/cnt_base.sh`
- `/Users/xu/code/github/dify/api/celery_healthcheck.py`
- Bash 官方手册：https://www.gnu.org/software/bash/manual/
- ShellCheck（脚本 lint）：https://www.shellcheck.net/

---

**文档版本**：v1.0
**最后更新**：2026-07-13