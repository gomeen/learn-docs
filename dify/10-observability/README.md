# 10 - 可观测性

> 生产环境的「眼睛」：日志、指标、链路追踪。LLM 应用还需要专门的 LLM 可观测性。

## 前置依赖

- `04-cache-and-queue` 基础
- `08-devops` 的部署基础

## 模块 10.1 结构化日志

- [ ] [1.1 日志级别：DEBUG / INFO / WARNING / ERROR](./01-log-levels.md)
- [ ] [1.2 Python `logging` 模块与 Logger 层级](./02-python-logging.md)
- [ ] [1.3 结构化日志：JSON 格式](./03-structured-logging.md)
- [ ] [1.4 日志上下文：trace_id / tenant_id](./04-log-context.md)
- [ ] [1.5 dify 的日志体系分析](./05-logging-in-dify.md)

## 模块 10.2 指标监控

- [ ] [2.1 指标类型：Counter / Gauge / Histogram / Summary](./06-metric-types.md)
- [ ] [2.2 Prometheus 基础](./07-prometheus.md)
- [ ] [2.3 Grafana 仪表盘](./08-grafana.md)
- [ ] [2.4 应用指标：QPS / 延迟 / 错误率](./09-app-metrics.md)
- [ ] [2.5 业务指标：DAU / 转化率 / LLM Token 用量](./10-business-metrics.md)

## 模块 10.3 链路追踪

- [ ] [3.1 链路追踪概念：Trace / Span / Context](./11-tracing-concepts.md)
- [ ] [3.2 OpenTelemetry 标准](./12-opentelemetry.md)
- [ ] [3.3 Jaeger / Zipkin 实战](./13-jaeger-zipkin.md)
- [ ] [3.4 dify 的链路追踪实现](./14-tracing-in-dify.md)

## 模块 10.4 错误追踪与告警

- [ ] [4.1 Sentry 错误追踪集成](./15-sentry.md)
- [ ] [4.2 告警策略：阈值 / 异常检测](./16-alerting.md)
- [ ] [4.3 On-Call 与故障响应](./17-oncall.md)

## 模块 10.5 LLM 应用可观测性

- [ ] [5.1 LLM 调用追踪：Prompt / Response / Token](./18-llm-tracing.md)
- [ ] [5.2 Token 用量与成本分析](./19-llm-cost.md)
- [ ] [5.3 响应质量评估：人工反馈 / 自动评估](./20-llm-quality.md)
- [ ] [5.4 Langfuse / Helicone 等 LLM 专用工具](./21-llm-observability-tools.md)
- [ ] [5.5 dify 的 LLM 监控实现](./22-llm-obs-in-dify.md)

## 🎯 dify 仓库对应位置

- 日志配置：`/Users/xu/code/github/dify/api/extensions/ext_logging.py`
- 错误处理：`/Users/xu/code/github/dify/api/libs/logging.py`
- 工作流追踪：`/Users/xu/code/github/dify/api/core/workflow/trigger/`
- LLM 用量：`/Users/xu/code/github/dify/api/services/feature_service.py`
