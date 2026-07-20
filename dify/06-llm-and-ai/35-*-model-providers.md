# 小验证：模型 API · 流式 · Provider 抽象

> 覆盖：
> - [25-anthropic-api](./30-anthropic-api.md)
> - [26-openai-api](./31-openai-api.md)
> - [27-streaming-sse](./32-streaming-sse.md)
> - [28-model-runtime](./33-model-runtime.md)
> - [29-model-provider](./34-model-provider.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

model_runtime 把多家模型厂商收成统一接口。验证：读懂适配层，并实现/改动一处流式或 provider 细节。

## 需求

1. 阅读 `api/core/model_runtime/` 树，画「Provider → Model → invoke」三级（或实际层级）到 `NOTES.md`。
2. 本地写一个 SSE 生成器：`data: {"delta":...}\n\n`，用任意测试客户端逐块读（http.server 或 Flask 皆可）。
3. 小改动选一：为某 provider 错误映射补一种状态；或为流式 chunk 增加单测用的假 provider；默认配置不破坏现网。

## 提示

- `api/core/model_runtime/model_providers/`
- SSE：注意心跳与结束标记
- 无真实 API Key 也可用 mock

## 验收标准

- [ ] 层级图与真实目录对应
- [ ] SSE demo 可被客户端按块消费
- [ ] 有 mock/假 provider 或错误映射改动说明
- [ ] 不提交密钥

## 延伸（选做）

比较 OpenAI 与 Anthropic 消息格式差异如何被 runtime 抹平。
