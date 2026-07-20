# 10.4.3 On-Call 与故障响应

> 故障不可避免，如何建立高效的 On-Call 机制和标准化的故障响应流程是 SRE 的核心能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 On-Call 文化与最佳实践
- 掌握标准化的故障响应流程
- 知道如何在 dify 部署中建立 On-Call 机制
- 学习故障复盘（Post-Mortem）的写法

## 📚 前置知识

- 10.4.2 告警策略（`11-alerting.md`）
- DevOps 基础知识
- 团队协作工具（Slack / PagerDuty / 钉钉）

## 1. 核心概念

### 1.1 On-Call 的本质

**On-Call** = 团队成员轮流值班，随时响应生产告警。

**目标**：
1. **快速响应**：MTTR（Mean Time To Repair）最小化
2. **公平轮换**：避免某个人长期值班导致 burnout
3. **知识沉淀**：通过值班积累对系统的理解

### 1.2 On-Call 文化（Google SRE 原则）

**核心原则**：
1. **值班补偿**：值班时间应得到补偿（调休或加班费）
2. **值班有上限**：每人每周不超过一定时长
3. **可持续性**：避免疲劳值班导致判断力下降
4. **值班即责任**：值班期间有最高优先级响应权

### 1.3 故障响应流程（Incident Response）

```
┌─────────────────┐
│ 1. Detection    │ ← 告警触发 / 用户反馈
└────────┬────────┘
         ↓
┌─────────────────┐
│ 2. Triage       │ ← 5 分钟内确认严重程度
└────────┬────────┘
         ↓
┌─────────────────┐
│ 3. Mobilization │ ← 召集响应小组
└────────┬────────┘
         ↓
┌─────────────────┐
│ 4. Mitigation   │ ← 止血（不是根因修复）
└────────┬────────┘
         ↓
┌─────────────────┐
│ 5. Resolution   │ ← 完整修复
└────────┬────────┘
         ↓
┌─────────────────┐
│ 6. Post-Mortem  │ ← 48 小时内完成复盘
└─────────────────┘
```

### 1.4 Incident Commander（事件指挥官）

每次故障指定一个 IC，统一指挥：
- 不一定是最懂技术的人，但要是最有协调能力的人
- 负责决策、调度、对外沟通
- 其他成员专注技术修复

### 1.5 故障分级

| 级别 | 影响 | 响应 | 沟通 |
|------|------|------|------|
| **SEV-1** | 核心功能完全不可用 | 全员响应 | 公开声明 + 高管 |
| **SEV-2** | 核心功能部分受损 | On-Call + 后端 | 状态页 + 客服 |
| **SEV-3** | 非核心功能受损 | On-Call | 内部通告 |
| **SEV-4** | 轻微问题 | 下个工作日 | 无 |

## 2. 代码示例

### 2.1 PagerDuty 值班排班

```yaml
# pagerduty-schedule.yaml
schedules:
  - name: dify-oncall-primary
    teams: [dify-backend]
    layers:
      - name: primary
        users:
          - { user: alice, rotation: weekly }
          - { user: bob, rotation: weekly }
          - { user: carol, rotation: weekly }
        start: 2026-01-01T00:00:00Z
        restrictions:
          - type: daily
            start_time: "09:00"
            duration: 8h
```

### 2.2 故障通告模板

```markdown
# 🚨 故障通告：[SEV-1] API 服务不可用

**开始时间**：2026-07-13 14:30 UTC
**当前状态**：调查中（investigating）
**影响范围**：所有用户无法访问 dify API

## 当前进展
- 14:30：告警触发（5xx 错误率 > 50%）
- 14:32：IC 已接手（@alice）
- 14:35：定位到 Redis 集群故障
- 14:40：开始切换到备用 Redis

## 临时方案
- 用户可继续使用，响应延迟 2-5 秒

## 下一步
- 14:50：完整恢复后更新本通告
```

### 2.3 Post-Mortem 模板

```markdown
# 故障复盘：[SEV-1] Redis 集群故障导致 API 不可用

## 摘要
2026-07-13 14:30-15:00，dify API 因 Redis 集群故障完全不可用 30 分钟。

## 影响
- 受影响用户：~5000
- 受影响请求：~50,000
- 收入损失：~¥50,000

## 时间线
- 14:25：Redis 主节点 OOM
- 14:30：客户端开始报连接错误
- 14:30：Prometheus 告警触发
- 14:32：值班 @alice 接手
- 14:40：切换到备用 Redis
- 15:00：完全恢复

## 根因
Redis 集群的 maxmemory 配置过低（4GB），在一次大模型调用缓存写入时触发 OOM，主从切换耗时 8 分钟。

## 改进措施
| 措施 | 负责人 | 截止日期 |
|------|--------|----------|
| 提高 Redis maxmemory 到 16GB | @bob | 2026-07-20 |
| 增加 Redis 内存使用率告警（>80%） | @carol | 2026-07-15 |
| 实施 Redis 客户端重试 + 熔断 | @alice | 2026-07-25 |
```

### 2.4 常见错误：值班疲劳

```python
# ❌ 错误：一个人连续值班 7 天
schedule:
  - alice: 7_days

# ✅ 正确：每周轮换 + 备班
schedule:
  primary:
    - alice: 1_day
    - bob: 1_day
    - carol: 1_day
  secondary:
    - dave: 7_days  # 备班，主值班未响应时升级
```

## 3. dify 仓库源码解读

### 3.1 dify 的故障检测机制

dify 通过 Sentry + OTEL 实现故障自动检测：

**Sentry 检测**：`api/extensions/ext_sentry.py`
- 捕获未处理异常 → Sentry 自动告警
- 通过 `before_send` 过滤噪音
- 通过 `release` 标识版本，识别新引入的 bug

**OTEL 检测**：`api/extensions/ext_otel.py`
- 记录 HTTP 响应状态 → 用于 PromQL 告警
- 异常日志 hook（`ExceptionLoggingHandler`）→ 把错误信息记录到 OTEL span

### 3.2 dify 的企业版 On-Call 能力

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1500-1503）：

```python
from core.telemetry.gateway import is_enterprise_telemetry_enabled

self._enterprise_telemetry_enabled = is_enterprise_telemetry_enabled()
if trace_manager_timer is None:
    self.start_timer()
```

**解读**：
- dify 企业版提供更完善的遥测和告警能力
- 社区版用户需要自建 On-Call 机制（基于 Sentry / OTEL 后端）

### 3.3 dify 的故障恢复设计

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1517-1524）：

```python
def collect_tasks(self):
    global trace_manager_queue
    tasks: list[TraceTask] = []
    while len(tasks) < trace_manager_batch_size and not trace_manager_queue.empty():
        task = trace_manager_queue.get_nowait()
        tasks.append(task)
        trace_manager_queue.task_done()
    return tasks
```

**解读**：
- 第 4-7 行：批量处理任务，避免单点故障
- 第 5 行：`trace_manager_batch_size` 默认 100，防止 OOM
- **设计意图**：故障隔离——trace 系统故障不影响主业务

## 4. 关键要点总结

- **On-Call** = 团队轮流值班，随时响应告警
- 标准化流程：Detection → Triage → Mobilization → Mitigation → Resolution → Post-Mortem
- **Incident Commander**（IC）统一指挥
- 四级故障：**SEV-1 / SEV-2 / SEV-3 / SEV-4**
- 值班必须公平轮换，避免疲劳
- **Post-Mortem 关注系统改进，不追究个人责任**（Blameless）
- dify 通过 Sentry + OTEL 实现故障检测，企业版提供更完整的 On-Call 能力

## 5. 练习题

### 练习 1：基础（必做）

为你的 dify 团队设计 On-Call 值班表：
- 团队 3 人（A / B / C）
- 每周轮换
- 工作时间 9:00-18:00
- 主值班 + 备班机制

### 练习 2：进阶

阅读 `api/extensions/ext_sentry.py`，设计一个 dify 故障的应急响应 Runbook：
- 触发条件：Sentry 收到 P0 异常
- 5 分钟内：On-Call 接手 + 初步定位
- 30 分钟内：止血方案 + 状态页更新
- 48 小时内：Post-Mortem

### 练习 3：挑战（选做）

为 dify 实现一个 `IncidentStatusPage`：用 Flask + WebSocket 实时展示当前故障状态（investigating / identified / monitoring / resolved），前端自动订阅。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_sentry.py`
- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- Google SRE Book 第 11-13 章：https://sre.google/sre-book/
- PagerDuty On-Call 最佳实践：https://www.pagerduty.com/resources/learn/on-call/
- Atlassian Incident Handbook：https://www.atlassian.com/incident-management/handbook
- Blameless Post-Mortem 模板：https://blameless.com/blog/the-blameless-postmortem-and-better-after-action-reviews/

---

**文档版本**：v1.0
**最后更新**：2026-07-13