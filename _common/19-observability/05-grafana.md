# 10.2.3 Grafana 仪表盘

> 用 Grafana 把 Prometheus 数据可视化为直观的图表和仪表盘，建立可观测性的"驾驶舱"。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Grafana 的数据源、面板、仪表盘三层结构
- 掌握常用可视化（折线图、柱状图、Stat、Table）
- 能为 dify 设计核心业务仪表盘
- 知道 dify 中暂未直接集成 Grafana 的现状

## 📚 前置知识

- 10.2.2 Prometheus 基础（`04-prometheus.md`）
- 10.2.1 指标类型（`03-metric-types.md`）

## 1. 核心概念

### 1.1 Grafana 架构

```
┌─────────────────────────────────────┐
│            Dashboard                │
│  ┌─────────┬─────────┬──────────┐   │
│  │  Panel  │  Panel  │  Panel   │   │
│  │ (QPS)   │ (P99)   │ (Errors) │   │
│  └─────────┴─────────┴──────────┘   │
│           ↓ PromQL ↓                │
│      ┌──────────────────┐           │
│      │  Datasource:     │           │
│      │  Prometheus      │           │
│      └──────────────────┘           │
└─────────────────────────────────────┘
```

### 1.2 三层结构

| 层级 | 作用 |
|------|------|
| **Data source** | 数据后端（Prometheus / Loki / Elasticsearch） |
| **Panel** | 单个图表（折线、柱状、Stat、Table） |
| **Dashboard** | 多个 Panel 的集合，保存为 JSON 可导入导出 |

### 1.3 常用可视化类型

| 类型 | 用途 | 指标举例 |
|------|------|----------|
| **Time series** | 时序数据 | QPS、CPU%、在线人数 |
| **Stat** | 单值大数字 | 当前总用户、P99 延迟 |
| **Bar gauge** | 进度条 | 磁盘使用率、SLA 达成率 |
| **Table** | 列表 | Top 10 慢查询、Top 错误端点 |
| **Heatmap** | 热力图 | 请求延迟分布 |

### 1.4 仪表盘设计原则

1. **黄金信号先行**：QPS、错误率、延迟、饱和度
2. **业务分层**：基础设施 → 应用 → 业务
3. **关联 trace_id**：指标异常时能跳转到 trace
4. **告警阈值可见**：直接画出 P99 阈值线

## 2. 代码示例

### 2.1 dify 的核心业务仪表盘（JSON）

```json
{
  "title": "Dify API Overview",
  "panels": [
    {
      "title": "QPS",
      "type": "timeseries",
      "targets": [{
        "expr": "sum(rate(http_server_response_count[1m]))",
        "legendFormat": "{{method}} {{status_class}}"
      }]
    },
    {
      "title": "P99 Latency",
      "type": "stat",
      "targets": [{
        "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))"
      }],
      "fieldConfig": {
        "thresholds": {
          "steps": [
            {"color": "green", "value": null},
            {"color": "yellow", "value": 1.0},
            {"color": "red", "value": 3.0}
          ]
        },
        "unit": "s"
      }
    },
    {
      "title": "Error Rate",
      "type": "timeseries",
      "targets": [{
        "expr": "sum(rate(http_server_response_count{status_class=~\"5xx\"}[5m])) / sum(rate(http_server_response_count[5m]))",
        "legendFormat": "error rate"
      }],
      "fieldConfig": {
        "unit": "percentunit",
        "min": 0,
        "max": 1
      }
    }
  ]
}
```

### 2.2 业务指标面板：LLM 用量

```json
{
  "title": "LLM Token Usage (Hourly)",
  "type": "barchart",
  "targets": [{
    "expr": "sum by (model) (increase(llm_tokens_total[1h]))",
    "legendFormat": "{{model}}"
  }],
  "options": {
    "orientation": "horizontal",
    "xTickLabelRotation": 0
  }
}
```

### 2.3 异常查询：Top 10 慢端点

```json
{
  "title": "Top 10 Slowest Endpoints",
  "type": "table",
  "targets": [{
    "expr": "topk(10, histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route)))",
    "format": "table",
    "instant": true
  }]
}
```

## 3. dify 仓库源码解读

### 3.1 dify 中的 OTEL 指标 → Prometheus 导出

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
**核心代码**（行 104-129）：

```python
def init_flask_instrumentor(app: DifyApp) -> None:
    meter = get_meter("http_metrics", version=dify_config.project.version)
    _http_response_counter = meter.create_counter(
        "http.server.response.count",
        description="Total number of HTTP responses by status code, method and target",
        unit="{response}",
    )

    def response_hook(span: Span, status: str, response_headers: list) -> None:
        if span and span.is_recording():
            try:
                if status.startswith("2"):
                    span.set_status(StatusCode.OK)
                else:
                    span.set_status(StatusCode.ERROR, status)

                status = status.split(" ")[0]
                status_code = int(status)
                status_class = f"{status_code // 100}xx"
                attributes: dict[str, str | int] = {"status_code": status_code, "status_class": status_class}
                request = flask.request
                if request and request.url_rule:
                    attributes[HTTP_ROUTE] = str(request.url_rule.rule)
                if request and request.method:
                    attributes[HTTP_REQUEST_METHOD] = str(request.method)
                _http_response_counter.add(1, attributes)
```

**解读**：
- 第 3-7 行：定义指标 `http.server.response.count`，单位 `{response}`
- 第 16-19 行：把状态码分组为 `2xx/3xx/4xx/5xx`，便于 Grafana 分组聚合
- 第 24-26 行：附加 `HTTP_ROUTE`（路由模板而非实际 URL，避免基数爆炸）和 `HTTP_REQUEST_METHOD`
- **关键设计**：使用路由模板而不是 URL，避免 `/users/123`、`/users/456` 被当成不同 label

### 3.2 Trace → Grafana Tempo 的关联

**文件位置**：`/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
**核心代码**（行 22-30）：

```python
def setup_context_propagation() -> None:
    set_global_textmap(
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
                B3MultiFormat(),
            ]
        )
    )
```

**解读**：
- 第 2-7 行：设置全局 propagator，支持 W3C TraceContext 和 B3 两种格式
- **Grafana Tempo 关联**：当 OTEL trace 推送到 Tempo，Grafana 面板可以点击 `trace_id` 跳转到 trace 详情

### 3.3 dify 中 Grafana 的现状

> **dify 中暂未直接集成 Grafana**，需要自行部署。但 dify 的指标设计完全兼容 Prometheus + Grafana：
> - 指标命名遵循 OTEL 语义约定（`http.server.response.count`）
> - 支持 OTLP 协议，可以推到 Grafana Cloud / 自建 Tempo
> - HTTP 标签使用路由模板（`HTTP_ROUTE`）避免高基数

## 4. 关键要点总结

- Grafana = Data source + Panel + Dashboard 三层结构
- 核心面板：QPS（折线）、P99（Stat）、错误率（折线）、饱和度（Bar gauge）
- 标签设计要控制基数：用路由模板而不是 URL
- 通过 trace_id 关联面板和 trace 详情
- dify 通过 OTEL → Tempo → Grafana 实现 trace 可视化
- 业务面板设计：LLM Token 用量、工作流执行情况、租户活跃度

## 5. 练习题

### 练习 1：基础（必做）

设计一个"Dify API 健康仪表盘"，至少包含 4 个面板：QPS、P99 延迟、错误率、当前活跃连接数。画出面板布局草图。

### 练习 2：进阶

阅读 `api/extensions/otel/instrumentation.py` 中的 `ExceptionLoggingHandler`，解释为什么 dify 把错误信息记录到 span 而不是单独定义一个 `errors_total` Counter？

### 练习 3：挑战（选做）

为 dify 设计一个"LLM 成本监控仪表盘"：按模型（GPT-4 / Claude / Gemini）、租户、时间维度统计 Token 用量和估算成本。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/otel/instrumentation.py`
- `/Users/xu/code/github/dify/api/extensions/otel/runtime.py`
- `/Users/xu/code/github/dify/api/extensions/ext_otel.py`
- Grafana 官方文档：https://grafana.com/docs/grafana/latest/
- Grafana Dashboard 仓库：https://grafana.com/grafana/dashboards/

---

**文档版本**：v1.0
**最后更新**：2026-07-13