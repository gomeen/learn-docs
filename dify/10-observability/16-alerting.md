# 10.4.2 告警策略：阈值 / 异常检测

> 合理的告警策略是 SRE 的核心能力——既不"狼来了"，也不错过关键问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握告警策略的设计原则
- 区分阈值告警、同比/环比告警、异常检测
- 能为 dify 设计分级告警规则
- 知道告警疲劳的成因和缓解方法

## 📚 前置知识

- 10.2.4 应用指标（`09-app-metrics.md`）
- 10.2.2 Prometheus 基础（`07-prometheus.md`）
- 统计学基础（平均值、标准差、分位数）

## 1. 核心概念

### 1.1 告警的本质

告警 = **"系统在不可接受的偏差下运行"**。好的告警应该：
1. **可操作**：收到后能立即采取行动
2. **及时**：问题发生后尽快通知
3. **准确**：低误报、低漏报
4. **分级**：区分紧急程度

### 1.2 告警三大类

#### 阈值告警（Threshold Alerting）

最简单：指标超过阈值就告警。

```yaml
- alert: HighErrorRate
  expr: error_rate > 0.05
  for: 2m  # 持续 2 分钟才告警（避免抖动）
```

**适用**：SLA 明确的指标（错误率、延迟、CPU%）

#### 同比 / 环比告警（Comparative Alerting）

与历史值对比，发现"异常变化"。

```promql
# 当前流量比昨天同时段下降 50%
sum(rate(http_requests_total[5m]))
  <
sum(rate(http_requests_total[5m] offset 1d)) * 0.5
```

**适用**：业务流量、用户活跃度

#### 异常检测（Anomaly Detection）

用机器学习检测异常模式（如突增、突降）。

```promql
# 需要启用 recording rule
predict_linear(metric[1h], 4*3600) < 0
```

**适用**：季节性强的指标（如电商周末流量）

### 1.3 告警分级

| 级别 | 含义 | 通知方式 | 响应时间 SLA |
|------|------|----------|--------------|
| **P0 / Critical** | 服务不可用 | 电话 + 短信 + 钉钉 | 15 分钟 |
| **P1 / High** | 功能受损 | 钉钉 + Slack | 1 小时 |
| **P2 / Medium** | 性能下降 | Slack / Email | 4 小时 |
| **P3 / Low** | 优化建议 | Email / 周报 | 下一个迭代 |

### 1.4 告警疲劳（Alert Fatigue）

**症状**：团队开始忽略告警，关键告警被淹没。

**成因**：
1. 阈值设置不合理（过低导致抖动）
2. 没有分级（所有告警都是 P0）
3. 没有抑制规则（相关告警一起触发）
4. 没有行动指南（告警后不知做什么）

**缓解方法**：
- 设置合理的 `for` 持续时间
- 用 `inhibit_rules` 抑制重复告警
- 给每个告警写明 `summary` 和 `description`
- 定期 review 并淘汰无效告警

## 2. 代码示例

### 2.1 dify 的告警规则示例

```yaml
# alerts.yml
groups:
  - name: dify_api
    interval: 30s
    rules:
      # P0 - 5xx 错误率超过 5%
      - alert: DifyHighErrorRate
        expr: |
          sum(rate(http_server_response_count{status_class=~"5xx"}[5m]))
            /
          sum(rate(http_server_response_count[5m]))
            > 0.05
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "dify API 5xx 错误率超过 5%"
          description: "过去 5 分钟错误率为 {{ $value | humanizePercentage }}"

      # P1 - P99 延迟超过 3 秒
      - alert: DifyHighLatency
        expr: |
          histogram_quantile(0.99,
            sum by (route, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          ) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.route }} P99 延迟超过 3 秒"

      # P2 - 流量突降（环比）
      - alert: DifyTrafficDrop
        expr: |
          (
            sum(rate(http_server_response_count[15m]))
            /
            sum(rate(http_server_response_count[15m] offset 1d))
          ) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "流量比昨天同时段下降 50%"
```

### 2.2 告警路由与抑制

```yaml
# alertmanager.yml
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

inhibit_rules:
  # 整体服务不可用时，抑制单独组件的告警
  - source_match:
      alertname: 'DifyServiceDown'
    target_match:
      severity: 'warning'
    equal: ['cluster']
```

### 2.3 常见错误：告警太多

```yaml
# ❌ 错误：所有告警都标 critical
- alert: DiskUsage
  expr: node_filesystem_used_percent > 80
  labels:
    severity: critical  # 80% 就 critical，团队会被淹没

# ✅ 正确：分级 + 持续时间
- alert: DiskUsageCritical
  expr: node_filesystem_used_percent > 90
  for: 30m
  labels:
    severity: critical
- alert: DiskUsageWarning
  expr: node_filesystem_used_percent > 80
  for: 2h
  labels:
    severity: warning
```

## 3. dify 仓库源码解读

### 3.1 dify 中的告警实现

> **dify 中暂未直接使用 Prometheus Alertmanager**。dify 通过以下方式间接实现告警：
> - **Sentry**：异常告警（详见 10.4.1）
> - **OTEL 后端**：Collector 自带的告警规则（如 Grafana Alerts）
> - **企业版**：提供更完善的告警能力（`is_enterprise_telemetry_enabled`）

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1500-1502）：

```python
from core.telemetry.gateway import is_enterprise_telemetry_enabled

self._enterprise_telemetry_enabled = is_enterprise_telemetry_enabled()
if trace_manager_timer is None:
    self.start_timer()
```

**解读**：
- 第 1 行：导入企业版遥测开关
- 第 3 行：保存开关状态
- **业务含义**：dify 区分社区版和企业版，企业版提供更完整的告警能力

### 3.2 dify 的异常追踪（间接告警）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_sentry.py`
**核心代码**（行 32-47）：

```python
sentry_sdk.init(
    dsn=dify_config.SENTRY_DSN,
    integrations=[FlaskIntegration(), CeleryIntegration()],
    ignore_errors=[
        HTTPException,
        ValueError,
        FileNotFoundError,
        InvokeRateLimitError,
        _langfuse_error_response,
    ],
    traces_sample_rate=dify_config.SENTRY_TRACES_SAMPLE_RATE,
    profiles_sample_rate=dify_config.SENTRY_PROFILES_SAMPLE_RATE,
    environment=dify_config.DEPLOY_ENV,
    release=f"dify-{dify_config.project.version}-{dify_config.COMMIT_SHA}",
    before_send=before_send,
)
```

**解读**：
- Sentry 自动捕获所有非 `ignore_errors` 中的异常
- 通过 Sentry UI 的告警规则配置实现异常告警
- 通过 `environment` 字段区分环境
- 通过 `release` 字段识别"新引入的 bug"

### 3.3 dify 中的关键指标（可用于告警）

基于 dify 的 OTEL 指标（见 10.2.4），可以设计以下告警：

| 指标 | PromQL | 阈值 | 级别 |
|------|--------|------|------|
| HTTP 5xx 错误率 | `sum(rate(...{status_class=~"5xx"}[5m])) / sum(rate(...[5m]))` | > 5% 持续 2m | P0 |
| HTTP P99 延迟 | `histogram_quantile(0.99, ...)` | > 3s 持续 5m | P1 |
| 流量突降 | `rate(...) / rate(... offset 1d) < 0.5` | 持续 10m | P1 |
| Celery 队列积压 | `celery_queue_length > 1000` | 持续 10m | P1 |
| Redis 连接失败（Redis 详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)） | `rate(redis_errors_total[5m]) > 0` | 立即 | P0 |

## 4. 关键要点总结

- 三大告警类型：**阈值** / **同比** / **异常检测**
- 四级分级：**P0 Critical** / **P1 High** / **P2 Medium** / **P3 Low**
- 缓解告警疲劳：`for` 持续时间 + `inhibit_rules` 抑制 + 定期 review
- dify 通过 **Sentry** 实现异常告警，通过 **OTEL 后端** 实现指标告警
- 企业版提供更完整的告警能力
- 每个告警必须有 `summary` 和 `description`，便于理解

## 5. 练习题

### 练习 1：基础（必做）

为 dify 设计 5 条告警规则，覆盖 P0 / P1 / P2 三个级别。每条规则包含：指标、阈值、持续时间、级别、通知方式。

### 练习 2：进阶

阅读 `api/extensions/ext_sentry.py` 和 `api/core/ops/ops_trace_manager.py`，画出 dify 的告警架构图：业务异常 → Sentry / OTEL → 通知渠道 → 值班响应。

### 练习 3：挑战（选做）

设计 dify 的告警值班机制：使用 PagerDuty / OpsGenie，实现值班轮换、升级策略（5 分钟未响应升级到主管）、告警降噪（同 issue 30 分钟内合并）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_sentry.py`
- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- Prometheus Alerting：https://prometheus.io/docs/alerting/latest/overview/
- Google SRE 告警最佳实践：https://sre.google/sre-book/monitoring-distributed-systems/#xref_alerting
- Alertmanager 文档：https://prometheus.io/docs/alerting/latest/alertmanager/

---

**文档版本**：v1.0
**最后更新**：2026-07-13