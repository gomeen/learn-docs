# 10 - 可观测性

> 生产环境的「眼睛」：日志、指标、链路追踪。LLM 应用还需要专门的 LLM 可观测性。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定 |
|------|----------|------------|
| 日志级别 / 结构化日志 / 指标 / 追踪 / 告警 | [`_common/19-observability`](../../_common/19-observability/) | Python logging、LLM 可观测、`*-in-dify` |

## 前置依赖

- `04-cache-and-queue` 基础
- `08-devops` 的部署基础

## 模块 10.1 结构化日志

- [ ] [1.1 日志级别：DEBUG / INFO / WARNING / ERROR](../../_common/19-observability/01-log-levels.md)
- [ ] [1.2 Python `logging` 模块与 Logger 层级](./01-python-logging.md)
- [ ] [1.3 结构化日志：JSON 格式](../../_common/19-observability/02-structured-logging.md)
- [ ] [1.4 日志上下文：trace_id / tenant_id](./02-log-context.md)
- [ ] [1.5 dify 的日志体系分析](./03-logging-in-dify.md)

## 模块 10.2 指标监控

- [ ] [2.1 指标类型：Counter / Gauge / Histogram / Summary](../../_common/19-observability/03-metric-types.md)
- [ ] [2.2 Prometheus 基础](../../_common/19-observability/04-prometheus.md)
- [ ] [2.3 Grafana 仪表盘](../../_common/19-observability/05-grafana.md)
- [ ] [2.4 应用指标：QPS / 延迟 / 错误率](../../_common/19-observability/06-app-metrics.md)
- [ ] [2.5 业务指标：DAU / 转化率 / LLM Token 用量](./04-business-metrics.md)

## 模块 10.3 链路追踪

- [ ] [3.1 链路追踪概念：Trace / Span / Context](../../_common/19-observability/07-tracing-concepts.md)
- [ ] [3.2 OpenTelemetry 标准](../../_common/19-observability/08-opentelemetry.md)
- [ ] [3.3 Jaeger / Zipkin 实战](../../_common/19-observability/09-jaeger-zipkin.md)
- [ ] [3.4 dify 的链路追踪实现](./05-tracing-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [06-*-logging-metrics-tracing: 日志 · 指标 · 链路追踪](./06-*-logging-metrics-tracing.md)
  - 覆盖：01-python-logging.md, 02-log-context.md, 03-logging-in-dify.md, 04-business-metrics.md, 05-tracing-in-dify.md


## 模块 10.4 错误追踪与告警

- [ ] [4.1 Sentry 错误追踪集成](../../_common/19-observability/10-sentry.md)
- [ ] [4.2 告警策略：阈值 / 异常检测](../../_common/19-observability/11-alerting.md)
- [ ] [4.3 On-Call 与故障响应](../../_common/19-observability/12-oncall.md)

## 模块 10.5 LLM 应用可观测性

- [ ] [5.1 LLM 调用追踪：Prompt / Response / Token](./07-llm-tracing.md)
- [ ] [5.2 Token 用量与成本分析](./08-llm-cost.md)
- [ ] [5.3 响应质量评估：人工反馈 / 自动评估](./09-llm-quality.md)
- [ ] [5.4 Langfuse / Helicone 等 LLM 专用工具](./10-llm-observability-tools.md)
- [ ] [5.5 dify 的 LLM 监控实现](./11-llm-obs-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [12-*-llm-observability: LLM 可观测性与成本](./12-*-llm-observability.md)
  - 覆盖：07-llm-tracing.md, 08-llm-cost.md, 09-llm-quality.md, 10-llm-observability-tools.md, 11-llm-obs-in-dify.md


## 🎯 dify 仓库对应位置

- 日志配置：`/Users/xu/code/github/dify/api/extensions/ext_logging.py`
- 错误处理：`/Users/xu/code/github/dify/api/libs/logging.py`
- 工作流追踪：`/Users/xu/code/github/dify/api/core/workflow/trigger/`
- LLM 用量：`/Users/xu/code/github/dify/api/services/feature_service.py`
