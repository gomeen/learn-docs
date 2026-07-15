# 12.3 滚动发布与 A/B 测试

> 掌握**滚动发布**（用 K8s 自动滚替）和**A/B 测试**（用分流对比业务指标），理解两者与灰度的差别。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释滚动发布的"按 batch 替换"机制
- 用 K8s Deployment 配置 `RollingUpdate` 策略
- 解释 A/B 测试与灰度的本质区别
- 给出两个项目（A/B 测试 vs 滚动发布）的适用场景

## 📚 前置知识

- [12.1 蓝绿部署](./01-blue-green.md)
- [12.2 灰度发布](./02-canary.md)
- K8s 基本概念（Deployment / Service / Pod）

## 1. 核心概念

### 1.1 滚动发布（Rolling Update）

```
   时间 ────────────────────────────────────►

   ┌─────┬─────┬─────┐
   │  v1 │ v1 │ v1 │   初始：3 个 v1 pod
   │ p1  │ p2  │ p3  │
   └─────┴─────┴─────┘

   第一批替换
   ┌─────┬─────┬─────┬─────┐
   │ v2  │ v1 │ v1 │ v1│   ← 加一个 v2、等到旧 v1 p1 删掉
   │ p1  │ p2  │ p3  │ p4│
   └─────┴─────┴─────┴─────┘

   最后一批替换
   ┌─────┬─────┬─────┬─────┐
   │ v2  │ v2 │ v2 │ v1 │  ← 替换最后一个 v1
   └─────┴─────┴─────┴─────┘

   全部完成
   ┌─────┬─────┬─────┬─────┐
   │ v2  │ v2 │ v2 │ v2 │
   └─────┴─────┴─────┴─────┘
```

**特点**：
- **渐进**替换，每次替换一个 batch（默认 K8s 是 25% 一次）
- **资源占用 1×**（不出新实例，旧实例被销毁）
- **滚动过程服务不中断**（新旧共存）
- **失败可回滚**（`kubectl rollout undo`）

### 1.2 滚动发布关键参数

| 参数 | 含义 | 默认 |
|------|------|------|
| `maxUnavailable` | 滚动时允许不可用 pod 数 | 25% |
| `maxSurge` | 滚动时允许超出 pod 数 | 25% |
| `minReadySeconds` | 启动后等待多少秒才视为就绪 | 0 |
| `terminationGracePeriodSeconds` | 优雅终止等待 | 30 |

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2           # 最多同时 2 个新 pod
      maxUnavailable: 0     # 滚动过程不能少可用 pod（保证零停机）
```

### 1.3 A/B 测试与灰度的区别

| 维度 | 灰度（金丝雀）| A/B 测试 |
|------|--------------|----------|
| **核心目标** | 风险控制（稳定性）| 业务指标（功能验证）|
| **何时切换流量** | 验证稳定性 | 达到统计显著性 |
| **流量分配** | 渐增（1% → 100%）| **固定**（50/50，长期）|
| **失败回滚** | **是必须** | 通常不回滚 |
| **决策依据** | 错误率、延迟 | 转化率、留存、收入 |
| **典型时长** | 数小时 ~ 数天 | 数天 ~ 数周 |

**关键差异**：灰度是"上线决策"（发不发），A/B 测试是"产品决策"（哪个版本好）。

### 1.4 A/B 测试实现方式

| 方式 | 实现 | 适合 |
|------|------|------|
| **前端硬编码** | JS 根据 cookie 切换样式 | 简单 UI 改动 |
| **Nginx 头部** | 通过 `X-AB-Group` 区分 | 流式比较 |
| **后端 Feature Flag** | 代码内 AB 系统 | 复杂业务逻辑 |
| **功能开关平台** | Unleash / LaunchDarkly | 企业级 |

## 2. 代码示例

### 2.1 K8s Deployment 滚动发布

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                # 每次滚动最多加 1 个新 pod
      maxUnavailable: 0          # 整个滚动过程可用 pod 数必须 ≥ 4
  template:
    spec:
      containers:
      - name: api
        image: myapp:v2
        readinessProbe:           # 就绪探针：失败就不接流量
          httpGet: { path: /health, port: 8080 }
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:            # 存活探针：失败就重启容器
          httpGet: { path: /health, port: 8080 }
          initialDelaySeconds: 30
          periodSeconds: 10
```

**操作**：
```bash
# 滚动更新镜像
kubectl set image deployment/api api=myapp:v2

# 看滚动状态
kubectl rollout status deployment/api

# 暂停 / 继续
kubectl rollout pause deployment/api
kubectl rollout resume deployment/api

# 回滚到上一版本
kubectl rollout undo deployment/api
```

### 2.2 A/B 测试 Nginx 配置（基于 Cookie）

```nginx
# 利用 set $upstream_name 实现 AB 测试分流
split_clients "cookie${cookie_ab_group}" $ab_upstream {
    50% backend-a;       # 50% 流量到 A 版本
    50% backend-b;       # 50% 流量到 B 版本
}

upstream backend-a { server 10.0.0.1:5001; }
upstream backend-b { server 10.0.0.2:5001; }

server {
    listen 80;
    location / {
        proxy_pass http://$ab_upstream;
        proxy_set_header X-AB-Group $cookie_ab_group;
    }
}
```

**关键：通过 cookie 保证用户级别一致性**：
- 用户访问时 Set-Cookie: ab_group=A
- 下次同 cookie 命中同一后端（避免用户看到的内容"闪变"）

### 2.3 Feature Flag 实现（A/B 测试"硬核"方案）

```python
# Python 示例：基于用户 ID 决定显示哪个 UI 版本
import random
import hashlib

def get_ab_group(user_id: str) -> str:
    """稳定哈希：同 user_id 总命中同一组"""
    h = hashlib.md5(user_id.encode()).hexdigest()
    bucket = int(h, 16) % 100
    if bucket < 50:
        return "A"
    else:
        return "B"

@app.route("/dashboard")
def dashboard():
    user_id = current_user.id
    group = get_ab_group(user_id)
    if group == "A":
        return render_template("dashboard_v1.html")
    else:
        return render_template("dashboard_v2.html")
```

### 2.4 常见错误：滚动发布没有 readinessProbe

```yaml
# ❌ 错误：滚动时新 pod 还没初始化完就被压流量，导致 502
spec:
  template:
    spec:
      containers:
      - name: api
        image: myapp:v2

# ✅ 正确：加 readinessProbe，确认健康才接收流量
spec:
  template:
    spec:
      containers:
      - name: api
        image: myapp:v2
        readinessProbe:
          httpGet: { path: /health, port: 8080 }
          initialDelaySeconds: 5
          periodSeconds: 3
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：滚动发布的"自然发生"

**事实**：dify 主要使用 **docker-compose（单实例）+ GitHub Actions**部署。**没有显式的滚动发布策略**。

但在 K8s 部署场景下（dify 提供 helm chart），会用 K8s 默认的 RollingUpdate：

```yaml
# 简化版 helm chart api deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0        # 滚动过程零停机
  template:
    spec:
      containers:
      - name: api
        image: langgenius/dify-api:1.6.0
        readinessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 10
          periodSeconds: 5
```

**特点**：
- `maxUnavailable: 0`：滚动期间 pod 数不变（保证可访问）
- `maxSurge: 1`：最多同时 1 个新 pod 启动
- `readinessProbe`：新 pod 启动后要通过健康检查才接流量（关键）

**dify 仓库自身**：
- 单实例部署时不需要滚动（因为只有 1 个 pod）
- 但 helm chart 允许用户部署多 replicas，自动滚动

### 3.2 ruoyi：单机停-起式部署（无滚动）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 60-91）：

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
```

**解读**：
- ruoyi 是**单实例**部署（一个 Java 进程）
- 整个部署 = `kill -15 → 停服务 → 启动新服务`
- 部署期间有几秒到几十秒的 503 不可用

**不满足滚动发布的最低条件**：
- 单实例无法做"渐进替换"
- 必须停-起
- 不算滚动发布，而是简化版停机部署

### 3.3 对比：滚动发布的工业级方案（针对 ruoyi）

**如果要让 ruoyi 支持滚动发布**，需要改造：
1. **多实例部署**：在 N 台机器上各启动一个 yudao-server.jar
2. **前置负载均衡**：Nginx upstream 配置多台机器
3. **滚动脚本**：
   ```bash
   #!/bin/bash
   SERVERS=("server1" "server2" "server3")
   for server in "${SERVERS[@]}"; do
       ssh $server "bash stop.sh; bash start.sh"   # 一次只更新一台
       sleep 30                                    # 给流量重新路由时间
   done
   ```
4. **健康检查**：返回 200 才开始下一台

### 3.4 A/B 测试在两个项目中的应用

**dify：A/B 测试特性**：
- dify 的 Web 前端（Next.js）有"实验性功能"开关——本质就是 Feature Flag
- 例如某个新 UI、新功能上线时，先对内部用户开放，再放给外部

**ruoyi：A/B 测试特性**：
- ruoyi 通常不内置 A/B 测试能力
- 但其权限系统支持多租户（芋道框架特有）——可以**把 A/B 测试做成多租户功能**
- 通过给租户打 tag，在代码内部分支

### 3.5 三种部署策略选择决策树

```
                    你的应用有几个实例？
                    ／          ＼
                单实例         多实例
                ／              ＼
         服务可以短暂停吗？      是否需要观察业务指标？
        ／        ＼          ／        ＼
       是          否        是          否
       │           │        │           │
   ruoyi 现状    滚动发布   A/B 测试    灰度发布
   （deploy.sh) (K8s default)
                              ↓
                              你能接受瞬时切换吗？
                              ／        ＼
                              是          否
                              │           │
                          蓝绿部署     滚动 + 监控
```

## 4. 关键要点总结

- **滚动发布**：渐进替换、新旧共存、零停机
- **关键参数**：`maxSurge` / `maxUnavailable` / `readinessProbe`
- **A/B 测试 ≠ 灰度**：A/B 是产品决策（哪个好），灰度是上线决策（要不要发）
- **A/B 一致性**：用 cookie / sticky session / 哈希桶让用户始终看到同一组
- **dify**：依赖 K8s RollingUpdate（helm chart）
- **ruoyi**：单机部署，本质是简化停-起，不算滚动

## 5. 练习题

### 练习 1：基础（必做）

写一份 K8s Deployment YAML：
- 4 replicas
- `maxSurge: 1`, `maxUnavailable: 0`
- 启用 readinessProbe（path=/health, port=8080）
- 启用 livenessProbe（30 秒后开始）

**参考答案**：见 `solutions/01-k8s-rolling.md`

### 练习 2：进阶

阅读 `dify/.github/workflows/docker-build.yml`：
1. 为什么 dify 的 docker 镜像构建**不是**滚动发布？
2. 为什么在 K8s 部署时 **dev/staging/prod** 通常用相同的镜像 tag（如 `1.6.0`）？
3. 这与传统的"环境不同镜像不同"差异在哪？

### 练习 3：挑战（选做）

设计一个完整的"蓝绿 + A/B 测试 + 滚动"组合系统：
1. 蓝绿：保证数据库 schema 前后兼容（两阶段迁移）
2. 滚动：用 K8s default RollingUpdate（4 pod）
3. A/B 测试：用 cookie 区分 UI v1 vs v2
4. 监控：Prometheus 抓错误率，自动化决策放量

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- K8s Rolling Deployment：https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-update-deployment
- K8s readinessProbe：https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/
- A/B Testing vs Canary：https://www.optimizely.com/insights/blog/ab-testing-vs-canary-deployments/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
