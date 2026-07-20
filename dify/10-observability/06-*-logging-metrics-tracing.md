# 小验证：日志 · 指标 · 链路追踪

> 覆盖：
> - [01-python-logging](./01-python-logging.md)
> - [02-log-context](./02-log-context.md)
> - [03-logging-in-dify](./03-logging-in-dify.md)
> - [04-business-metrics](./04-business-metrics.md)
> - [05-tracing-in-dify](./05-tracing-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

没有日志字段与追踪 id，线上不可排障。验证：结构化日志 + context，对照 dify 日志扩展。

## 需求

1. 本地实现 JSON logger filter：自动注入 `request_id`（contextvars）。
2. 模拟 2 个并发请求，确认日志行 request_id 不串。
3. 阅读 `api/extensions/ext_logging.py` 与相关 libs，`NOTES.md` 记录级别、格式、租户字段。
4. （可选）在调试端点日志中增加安全的业务字段（禁止 PII/密钥）。

## 提示

- contextvars 比全局变量更安全
- 指标：至少在 NOTES 定义 QPS/延迟/错误率怎么取

## 验收标准

- [ ] 并发下 request_id 不串
- [ ] JSON 日志可被 `json.loads` 解析
- [ ] NOTES 对照仓库配置
- [ ] 无敏感字段入日志

## 延伸（选做）

手写一个 Prometheus counter 示例（本地）。
