# 小验证：LLM 基础概念

> 覆盖：
> - [01-llm-overview](./01-llm-overview.md)
> - [02-transformer](./02-transformer.md)
> - [03-tokens-context](./03-tokens-context.md)
> - [04-model-parameters](./04-model-parameters.md)
> - [05-llm-limitations](./05-llm-limitations.md)
> - [06-embedding-models](./06-embedding-models.md)
>
> 预计：40～70 分钟 · 本地练习或小模块

## 背景

选型与排错前先建立 token、上下文、采样参数与 embedding 的正确心智模型。本组以本地实验为主。

## 需求

1. 写 `token_lab.py`：用任意 tokenizer（`tiktoken` 或近似：按词/字符粗估并注明误差）统计 3 段文本 token 数；计算在 8k 上下文中最多还能塞多少字的「预算表」。
2. 写函数 `clamp_params(temp, top_p, max_tokens)`：把异常参数夹到合理区间并返回告警列表。
3. 实现简易余弦相似度，对 4 句中文句子 embedding **可用伪向量**（hash 降维）演示：语义相近句是否更近（接受粗糙），重点是接口。
4. `NOTES.md`：列出 3 种幻觉触发场景与产品层缓解（检索、引用、拒答）。

## 提示

- 不必调用真实付费 API
- temperature 与 top_p 同时拉满的风险写进注释

## 验收标准

- [ ] token 预算表可读
- [ ] 参数夹取对非法输入稳定
- [ ] 相似度 demo 可运行
- [ ] 幻觉缓解点 ≥3

## 延伸（选做）

对比 embedding 维度与存储成本的粗算（1M 段文本）。
