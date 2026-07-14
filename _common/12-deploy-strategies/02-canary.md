# 12.2 灰度发布（金丝雀发布）

> 把"全部或无"的发布改成"小流量逐步放量"，降低新版本风险。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释灰度发布的核心思想（金丝雀实例 → 1% → 10% → 100%）
- 区分灰度 vs 蓝绿 vs AB Test
- 用 Nginx / Istio 配置灰度流量切分
- 解释新版本对数据库 schema 的"扩展-收缩"两阶段迁移

## 📚 前置知识

- 12.1 蓝绿部署
- Nginx upstream / 负载均衡
- /Users/xu/code/gomeen/learn-docs/_common/10-network-proxy/02-reverse-proxy.md

## 1. 核心概念

### 1.1 金丝雀的起源

```
   矿工进矿洞前，会先放一只金丝雀进去：
   如果金丝雀死了 → 矿内有有毒气体
   如果金丝雀活着 → 矿内安全

   同理，发布新版本时：
   先让 1% 用户用新版本（"金丝雀"）
   如果新版本稳定 → 逐渐放量到 100%
   如果新版本出 bug → 这 1% 是金丝雀，撤掉即可
```

### 1.2 灰度的三阶段

```
   时间 ────────────────────────────────────►

   阶段 1          阶段 2          阶段 3
   金丝雀验证       扩容放量        全量替换

   ┌──────┐       ┌──────┐        ┌──────┐
   │ v1:5│       │ v1:3│        │ v1:0│
   │ v2:1│       │ v2:2│        │ v2:5│
   └──┬───┘       └──┬───┘        └──┬───┘
      ▼              ▼               ▼
   1% 新版         40% 新版         100% 新版
   ↓ 验证         ↓ 持续观察        ↓ 完成

   触发切换：业务关键指标（错误率 / 延迟）正常
```

### 1.3 灰度 vs 蓝绿 vs AB Test

| 维度 | 灰度 | 蓝绿 | AB Test |
|------|------|------|---------|
| **目的** | 风险控制 | 零停机 | 功能验证 |
| **流量切分** | 渐进（1% → 100%）| 瞬时（100% 切换）| 持续对比 |
| **决策依据** | 监控告警 | 切换路由器 | 业务指标 |
| **典型场景** | 大型项目、低频发布 | 中型项目、高频发布 | 营销活动、产品迭代 |

### 1.4 灰度的实现方式

| 方式 | 实现 | 灵活性 |
|------|------|--------|
| **基于权重** | Nginx `upstream` `weight` / K8s Service `sessionAffinity` | 粗粒度（30% / 70%）|
| **基于 Header / Cookie** | Nginx `if ($cookie_user = "vip")` | 单用户定向 |
| **基于 IP** | Nginx `geo` 模块 | 区域定向 |
| **基于服务网格** | Istio VirtualService | 精细化（基于权重 + header + IP）|

## 2. 代码示例

### 2.1 Nginx 基于权重的灰度

```nginx
upstream backend {
    server 10.0.0.1:5001 weight=9;    # 旧版 90%
    server 10.0.0.2:5001 weight=1;    # 新版 10%（金丝雀）
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

**调整比例**：
```nginx
# 第一阶段：1% 用户先体验
upstream backend { server 10.0.0.1:5001 weight=99; server 10.0.0.2:5001 weight=1; }

# 第二阶段：放量到 10%
upstream backend { server 10.0.0.1:5001 weight=90; server 10.0.0.2:5001 weight=10; }

# 第三阶段：全量替换
upstream backend { server 10.0.0.2:5001; }
```

### 2.2 Nginx 基于 Cookie 的灰度

```nginx
upstream backend-old { server 10.0.0.1:5001; }
upstream backend-new { server 10.0.0.2:5001; }

server {
    location / {
        # 员工定向（cookie 中带 vip=1 的走新版）
        set $backend backend-old;
        if ($cookie_user_group = "canary") {
            set $backend backend-new;
        }
        proxy_pass http://$backend;
    }
}
```

### 2.3 K8s Service 灰度

```yaml
# v1 deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-v1
spec:
  replicas: 9
  selector:
    matchLabels: { app: api, version: v1 }
  template:
    metadata:
      labels: { app: api, version: v1 }    # 注意这里有 version 标签

---
# v2 (canary)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-v2
spec:
  replicas: 1
  selector:
    matchLabels: { app: api, version: v2 }
  template:
    metadata:
      labels: { app: api, version: v2 }
```

```yaml
# Service 不区分 v1/v2，所有版本都会被路由
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  selector: { app: api }      # 只看 app，不看 version
  ports: [{ port: 5001 }]
```

**比例**：`v1:9 pods + v2:1 pod = 10%` 流量到 v2。

### 2.4 数据库两阶段迁移（关键！）

```sql
-- 阶段 1：扩展（双写，向后兼容）
ALTER TABLE users ADD COLUMN full_name VARCHAR;

-- v2 写入：同时写 name + full_name
INSERT INTO users (name, full_name) VALUES ('Alice', 'Alice');

-- v1 仍然只读 name（不会出错，因为 full_name 是新字段）

-- 阶段 2：收缩（v1 下线后才执行）
-- 把 name 的数据迁移到 full_name
UPDATE users SET full_name = name WHERE full_name IS NULL;
-- 切换读写都走 full_name
-- 最后 DROP COLUMN name
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：deploy-agent 是更细粒度的灰度

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/deploy-agent.yml`

dify 有专门的 `deploy-agent.yml`——和 `deploy-dev.yml` 分开。**这本身就是一种"灰度思路"**：先部署新功能到 agent，验证后再部署到主应用。

具体细节由于 deploy-agent.yml 内容本次未读取，我们重点关注多 deployment 模式的设计意图。

### 3.2 dify：基于 build tag 的灰度（隐式机制）

dify 通过 GitHub Actions 的 `workflow_run` 触发不同环境的部署：

```
push tag: v1.6.0       → 触发 deploy-enterprise.yml（企业版）
push to main           → 触发 main-ci.yml（CI 测试）
push to deploy/dev     → 触发 deploy-dev.yml
push to deploy/staging → (可类似配置触发 staging)
```

这种"基于分支 / tag"的发布，本质上是**人肉灰度**——用户通过 PR 流程在不同分支验证不同版本。

### 3.3 ruoyi：单机部署无内建灰度

ruoyi 的 `deploy.sh` 是**单机停-起型部署**，没有内置灰度能力。原因：
1. **单机部署**（一台服务器跑单实例），无法"部分流量"
2. **中国中小企业实践**：通常直接停-起，依赖人工验证
3. **JVM 内存占用大**：双实例都跑对内存压力大

**如果要让 ruoyi 支持灰度，需要的改造**：
1. **前置负载均衡**：在服务器前加 Nginx / SLB
2. **双实例部署**：在同一台机器启动 2 个端口（48080 + 48081）
3. **Nginx 灰度配置**：
   ```nginx
   upstream yudao {
       server 127.0.0.1:48080 weight=9;     # 旧
       server 127.0.0.1:48081 weight=1;     # 新
   }
   ```
4. **监控指标**：观察 `/actuator/health` 和 `/actuator/prometheus`

### 3.4 三个发布策略对比表（针对两个项目）

| 维度 | 蓝绿 | 灰度（金丝雀）| 滚动 |
|------|------|--------------|------|
| **dify 现状** | 近似实现（SSH 单机部署）| 多 workflow 分阶段 | K8s Helm chart 支持 |
| **ruoyi 现状** | 简化停-起（`deploy.sh`）| 不支持（需手工加 Nginx）| 不支持 |
| **实现难度** | 中 | 高（需要双实例）| 低 |
| **风险** | 切换瞬时没机会发现 | 全程可控 | 滚动批次无问题可继续 |
| **资源开销** | 2× | 1.5x | 1× |

### 3.5 一个生产级灰度架构图

```
        ┌──────────────────────────────────┐
        │   生产流量入口（Nginx / K8s Service）│
        └──────────────┬───────────────────┘
                       │
       ┌───────────────┴───────────────────┐
       │             灰度路由器            │
       │   根据权重 / 用户分桶分流         │
       └────┬───────────────────────┬─────┘
            │                       │
   ┌────────▼─────────┐    ┌────────▼─────────┐
   │  v1（stable）     │    │  v2（canary）     │
   │  90% 流量          │    │  10% 流量         │
   │  9 pods           │    │  1 pod           │
   │                   │    │                  │
   │  监控：           │    │  监控：           │
   │   - 错误率 < 0.1% │    │   - 错误率 < 0.1% │
   │   - p99 < 200ms   │    │   - p99 < 200ms  │
   └───────────────────┘    └──────────────────┘
            │                       │
            ▼                       ▼
   ┌──────────────────────────────────────────┐
   │   共享数据库（schema 必须兼容！）         │
   └──────────────────────────────────────────┘
```

## 4. 关键要点总结

- **金丝雀**：1% 流量先验证 → 增加到 10% → 50% → 100%
- **Nginx 实现**：通过 `weight` 调整 upstream 比例
- **K8s 实现**：通过 deployment `replicas` 比例（共享 Service selector）
- **DB 兼容**：两阶段迁移（扩展 → 切换 → 收缩）
- **dify 现状**：用多 workflow 实现"分阶段发布"
- **ruoyi 现状**：单机部署，需手工加前置 Nginx 改造才能灰度

## 5. 练习题

### 练习 1：基础（必做）

设计一份 Nginx 灰度配置（基于权重）：
- 90% 流量到 v1
- 10% 流量到 v2（金丝雀）
- 实现两个阶段（扩容 v2）的硬切换

**参考答案**：见 `solutions/01-canary-nginx.md`

### 练习 2：进阶

设计一个**数据库 schema 扩展迁移**：
1. `users` 表原 `name` 字段要改名为 `full_name`
2. 列出 3 步迁移（每一步两个版本都能跑）
3. 解释为什么不能直接 `ALTER TABLE ... RENAME COLUMN`

### 练习 3：挑战（选做）

为 dify 设计一份完整的灰度发布流程：
1. K8s Helm chart 部署 v1，replicas=10
2. 部署 v2，replicas=1
3. 用 Prometheus 监控错误率：
   - 错误率 > 5% 自动回滚
   - 错误率正常自动扩容 v2 到 10
4. 用 Argo Rollouts 实现全自动

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- `/Users/xu/code/github/dify/.github/workflows/deploy-agent.yml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- Canary Release（ThoughtWorks）：https://martinfowler.com/bliki/CanaryRelease.html
- Istio 灰度：https://istio.io/latest/docs/concepts/traffic-management/
- Argo Rollouts：https://argoproj.github.io/argo-rollouts/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
