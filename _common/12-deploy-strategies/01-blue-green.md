# 12.1 蓝绿部署（Blue-Green Deployment）

> 学习蓝绿部署的核心思想：**两套完全相同的环境交替上线**，能做到零停机回滚。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释蓝绿部署的"两套完全等价环境"思想
- 绘制蓝绿部署切换流程图
- 列举蓝绿部署的优点与局限
- 对比 dify 与 ruoyi 实际部署中的"等效"做法

## 📚 前置知识

- [Docker Compose](../09-containerization/04-compose.md)
- [Jenkins 流水线](../11-cicd/04-jenkins.md)
- Docker / K8s 基本概念（[容器化](../09-containerization/01-concepts.md)）

## 1. 核心概念

### 1.1 蓝绿部署的核心思想

```
          旧版本 (Blue)                新版本 (Green)
   ┌─────────────────────┐    ┌─────────────────────┐
   │  v1 API 实例 (3 pods) │    │  v2 API 实例 (3 pods) │
   └──────────┬──────────────┘    └──────────┬──────────────┘
              │                              │
              │       ┌──────────────┐       │
              └──────►│  路由器(LB)   │◄──────┘
                      └──────┬───────┘
                             │
                       用户流量
```

**关键特点**：
- 同时存在**两套完全等价的部署环境**
- 切换时**瞬间**把流量从一个切到另一个
- 回滚 = 把流量切回上一个环境（**秒级**）
- **数据库**：通常升级到兼容的 schema，所有版本都能跑

### 1.2 标准切换流程

```
                        正常状态                  切换中                    完成后
                      ┌──────────┐           ┌──────────┐            ┌──────────┐
        用户流量 ────►│   100% ─────►Blue│  10%→Blue │  90%→Green │    0%→Blue │
                      │                       10%→Green│   100%→Green│    0%→Blue │
                      │                          │       │             │
                      │                          ▼       ▼             │
                      │                     [观察期]              销毁 Blue 或留作备份
```

**核心步骤**：
1. 部署 Green v2 版本（不接流量）
2. 健康检查 / 业务验证（流量小或用 staging 流量）
3. Router/LB 把流量切到 Green
4. Blue 实例保留若干分钟作为"可立即回滚"的备用
5. 销毁 Blue 实例

### 1.3 优缺点

| 优点 | 缺点 |
|------|------|
| 零停机切换（瞬间） | 部署期间需要 **2× 资源**（两套环境都在跑）|
| 回滚极快（切回旧版就完事） | 数据库 schema 变更要前后兼容（**双向兼容最难**）|
| 部署 / 切流量是两个独立动作 | 状态服务（session、缓存）需要在两套环境间共享 |
| 适合高频发版 | 不适合需要"渐进式观察"的产品 |

### 1.4 蓝绿 vs 滚动 vs 灰度

| 策略 | 切换速度 | 资源开销 | 回滚粒度 | 风险 |
|------|----------|---------|---------|------|
| **蓝绿** | 秒级（瞬时切换）| 2× | 秒级 | 切换失败必须立即切回 |
| **滚动** | 数分钟（按 batch 替换） | 1× | 数分钟 | 旧版、新版共存 |
| **灰度** | 数小时（逐步放量） | 1.5x | 立即中断灰度 | 适合大规模版本验证 |

## 2. 代码示例

### 2.1 Docker Compose 蓝绿部署

```yaml
# 文件：docker-compose.blue-green.yaml
# 蓝色 v1 旧版本
services:
  api-blue:
    image: myapp:v1
    ports:
      - "5001:5001"
    environment:
      VERSION: blue

# 绿色 v2 新版本
  api-green:
    image: myapp:v2
    ports:
      - "5002:5001"
    environment:
      VERSION: green
```

```bash
# 1. 部署两个版本（互不干扰）
docker compose up -d api-blue
docker compose up -d api-green

# 2. Nginx upstream 配置切换
# 把 upstream 改成只指向 api-green
nginx -s reload

# 3. 观察一段时间后，销毁 api-blue
docker compose stop api-blue
docker compose rm api-blue
```

### 2.2 K8s 中用 Service Selector 切换

```bash
# 1. 部署 v1（标签 app=api，version=blue）
kubectl apply -f api-blue.yaml
# Deployment api-blue:
#   spec:
#     template:
#       metadata:
#         labels:
#           version: blue

# 2. 部署 v2（标签 version=green）
kubectl apply -f api-green.yaml

# 3. 修改 Service selector（瞬时切换！）
kubectl patch service api-svc -p '{"spec":{"selector":{"version":"green"}}}'

# 4. 验证：流量全部转到 green
kubectl get endpoints api-svc
# 显示 green pod IP

# 5. 回滚（如有需要）
kubectl patch service api-svc -p '{"spec":{"selector":{"version":"blue"}}}'
```

### 2.3 常见错误：未考虑 session 共享

```yaml
# ❌ 错误：用户在 Blue 创建了 session，流量切到 Green 后 session 没了
services:
  api-blue: { ... }
  api-green: { ... }

# ✅ 正确：session 存在共享外部存储（Redis / 数据库）
services:
  redis:                           # 共享 session
    image: redis:7-alpine
  api-blue:
    environment:
      REDIS_URL: redis://redis:6379
  api-green:
    environment:
      REDIS_URL: redis://redis:6379
```

### 2.4 常见错误：DB Schema 不兼容

```sql
-- 蓝绿场景下，两个版本同时连同一个数据库
-- v1 期望 user 有 name 字段
-- v2 重命名 name → full_name
-- ❌ 蓝绿切换时，旧 Blue 实例查询 name 字段会失败

-- ✅ 正确做法：
--   1. 加新字段（ALTER TABLE ADD COLUMN full_name）
--   2. v2 开始写 full_name
--   3. v1 同时仍然读 name（向后兼容）
--   4. 切流量到 Green
--   5. 销毁 Blue 后，再 DROP COLUMN name
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：deploy-dev 模式是简化版蓝绿

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`

dify 的 `deploy-dev.yml` 是典型的**简化版蓝绿部署**：

```yaml
jobs:
  deploy:
    runs-on: depot-ubuntu-24.04
    if: |
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'deploy/dev'
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@0ff4204d59e8e51228ff73bce53f80d53301dee2 # v1.2.5
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            ${{ vars.SSH_SCRIPT || secrets.SSH_SCRIPT }}
```

**dify 的部署脚本（被 SSH_SCRIPT 隐藏）通常做**：
```bash
# 1. 拉取新镜像
docker compose pull api web

# 2. 启动新容器（与旧容器端口冲突，靠 docker compose 自动优雅替换）
docker compose up -d --no-deps api web

# 3. 等健康检查通过
./scripts/wait-for-health.sh

# 4. （可选）保留旧镜像 24 小时，回滚备用
```

**特点**：
- 单机部署（用 docker compose，不是 K8s）
- 蓝绿依赖 docker compose 的**端口复用**：同一端口，旧容器停了，新容器起来
- 没有显式"切换路由器"的步骤，因为是单机部署
- 保留旧镜像 → 允许快速回滚（蓝绿本质）

### 3.2 ruoyi：deploy.sh 是"停-起"型蓝绿

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 60-104，行 145-158）：

```bash
# 停止：优雅关闭之前已经启动的服务
function stop() {
    echo "[stop] 开始停止 $BASE_PATH/$SERVER_NAME"
    PID=$(ps -ef | grep $BASE_PATH/$SERVER_NAME | grep -v "grep" | awk '{print $2}')
    # 如果 Java 服务启动中，则进行关闭
    if [ -n "$PID" ]; then
        # 正常关闭
        echo "[stop] $BASE_PATH/$SERVER_NAME 运行中，开始 kill [$PID]"
        kill -15 $PID
        # 等待最大 120 秒，直到关闭完成。
        for ((i = 0; i < 120; i++))
            do
                sleep 1
                PID=$(ps -ef | grep $BASE_PATH/$SERVER_NAME | grep -v "grep" | awk '{print $2}')
                if [ -n "$PID" ]; then
                    echo -e ".\c"
                else
                    echo "[stop] 停止 $BASE_PATH/$SERVER_NAME 成功"
                    break
                fi
		    done

        # 如果正常关闭失败，那么进行强制 kill -9 进行关闭
        if [ -n "$PID" ]; then
            echo "[stop] $BASE_PATH/$SERVER_NAME 失败，强制 kill -9 $PID"
            kill -9 $PID
        fi
    # 如果 Java 服务未启动，则无需关闭
    else
        echo "[stop] $BASE_PATH/$SERVER_NAME 未启动，无需停止"
    fi
}

# 启动：启动后端项目
function start() {
    # 开启启动前，打印启动参数
    echo "[start] 开始启动 $BASE_PATH/$SERVER_NAME"
    echo "[start] JAVA_OPS: $JAVA_OPS"
    echo "[start] JAVA_AGENT: $JAVA_AGENT"
    echo "[start] PROFILES: $PROFILES_ACTIVE"

    # 开始启动
    BUILD_ID=dontKillMe nohup java -server $JAVA_OPS $JAVA_AGENT -jar $BASE_PATH/$SERVER_NAME.jar --spring.profiles.active=$PROFILES_ACTIVE &
    echo "[start] 启动 $BASE_PATH/$SERVER_NAME 完成"
}
```

```bash
# 部署
function deploy() {
    cd $BASE_PATH
    # 备份原 jar
    backup
    # 停止 Java 服务
    stop
    # 部署新 jar
    transfer
    # 启动 Java 服务
    start
    # 健康检查
    healthCheck
}

deploy
```

**解读**：

**A. ruoyi 的"伪蓝绿"——完整 4 步流程**：

| 阶段 | 对应蓝绿 | 行为 |
|------|---------|------|
| `backup` | 备份当前版本 | `cp yudao-server.jar backup/yudao-server-20260713.jar` |
| `stop` | 停止旧版本 | `kill -15`（优雅终止，120s 超时 → `kill -9`）|
| `transfer` | 复制新 jar | 用新 jar 覆盖 |
| `start` | 启动新版本 | `nohup java -jar` 后台启动 |
| `healthCheck` | 验证新版本是否健康 | `curl /actuator/health` 120 次 |

**B. 与真正蓝绿的区别**：

| 对比项 | dify / ruoyi 简化版 | 真正蓝绿 |
|--------|---------------------|----------|
| 同时保留两套环境 | 否（先停后启）| 是 |
| 切换耗时 | 30 秒 ~ 5 分钟（停 + 启动） | 1 ~ 5 秒（切路由器） |
| 资源占用 | 1× | 2× |
| 回滚速度 | 重新 `transfer` 旧 jar | 切回路由器 |
| 部署期间服务状态 | **短暂不可用** | 始终可用 |

**C. 优雅停止的细节**：

```bash
# 第 67 行：先尝试 kill -15（SIGTERM）
kill -15 $PID

# 第 70-79 行：等 120 秒（120 次 × 1 秒），每 1 秒检查一次
for ((i = 0; i < 120; i++))
    do
        sleep 1
        PID=$(ps -ef | grep $BASE_PATH/$SERVER_NAME | grep -v "grep" | awk '{print $2}')
        if [ -n "$PID" ]; then
            echo -e ".\c"      # 还在跑（显示一个点）
        else
            echo "[stop] 停止成功"
            break
        fi
    done

# 第 83-85 行：超时未停，再 SIGKILL
if [ -n "$PID" ]; then
    kill -9 $PID
fi
```

**SIGTERM (15) vs SIGKILL (9)**：
- `-15` 给应用机会做清理（关闭连接、刷数据、写状态）
- `-9` 强制终止，**只用于救命**
- ruoyi 的 120 秒等待是给 JVM 做 GC flush、Tomcat 关连接、合理退出时间

**D. 健康检查的设计**：

```bash
function healthCheck() {
    if [ -n "$HEALTH_CHECK_URL" ]; then
        for ((i = 0; i < 120; i++))
            do
                result=`curl -I -m 10 -o /dev/null -s -w %{http_code} $HEALTH_CHECK_URL || echo "000"`
                if [ "$result" == "200" ]; then
                    echo "[healthCheck] 健康检查通过"
                    break
                else
                    sleep 1
                fi
            done

        # 健康检查不通过 → 部署失败！
        if [ ! "$result" == "200" ]; then
            tail -n 10 nohup.out
            exit 1
        else
            tail -n 10 nohup.out
        fi
    fi
}
```

**关键点**：
- `curl -I` 只取 HTTP 头（快）
- `-m 10`：单次请求最多 10 秒
- `-w %{http_code}`：只输出状态码
- 状态码 `200` 才算通过
- 不通过 → `exit 1`，CI 部署失败报警（隐式）

## 4. 关键要点总结

- **蓝绿核心**：两套等价环境 + 秒级路由器切换 + 保留旧版一段时间
- **dify 简化版**：单机 docker compose 用端口替换实现蓝绿
- **ruoyi 简化版**：停-起-健康检查，部署期间短暂不可用
- **JVM 优雅停机**：先 SIGTERM，等 120 秒才 SIGKILL
- **健康检查是关键**：HTTP 200 才算部署成功
- **数据库兼容性**：蓝绿前后兼容 schema 是最大难点

## 5. 练习题

### 练习 1：基础（必做）

写一份简化版 ruoyi `deploy.sh`，包含：
1. `backup()`：复制当前 jar 到 backup/
2. `stop()`：`kill -15`，120 秒后 `kill -9`
3. `start()`：nohup 启动
4. `healthCheck()`：curl 200 才算成功

**参考答案**：见 `solutions/01-deploy-script.md`

### 练习 2：进阶

阅读 `ruoyi-vue-pro/script/shell/deploy.sh` 第 102 行：
```bash
BUILD_ID=dontKillMe nohup java -server $JAVA_OPS $JAVA_AGENT -jar $BASE_PATH/$SERVER_NAME.jar --spring.profiles.active=$PROFILES_ACTIVE &
```

回答：
1. **`BUILD_ID=dontKillMe`** 这个变量的作用是什么？（提示：和 Jenkins / nohup 有关）
2. `&` 把进程放后台，为什么还需要 `nohup`？
3. 为什么用 `--spring.profiles.active=$PROFILES_ACTIVE` 而非环境变量 `SPRING_PROFILES_ACTIVE`？

### 练习 3：挑战（选做）

设计"完整蓝绿"版本的 ruoyi 部署：
1. 同时启动 v1 + v2（监听不同端口：48080 + 48081）
2. Nginx upstream 默认指向 v1
3. 启动 v2 后，让 Nginx 切到 v2（修改 upstream + reload）
4. 验证 v2 正常后，停 v1
5. 如果 v2 不健康，**自动回滚**到 v1

写出关键 shell 脚本。

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- Blue/Green Deployment（Martin Fowler）：https://martinfowler.com/bliki/BlueGreenDeployment.html
- K8s 蓝绿：https://kubernetes.io/docs/concepts/cluster-administration/manage-deployment/#blue-green-deployments

---

**文档版本**：v1.0
**最后更新**：2026-07-13
