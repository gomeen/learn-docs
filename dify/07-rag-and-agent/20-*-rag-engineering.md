# 小验证：RAG 评估与工程实践

> 覆盖：
> - [13-rag-evaluation](./15-rag-evaluation.md)
> - [14-context-management](./16-context-management.md)
> - [15-multimodal-rag](./17-multimodal-rag.md)
> - [16-rag-failure-modes](./18-rag-failure-modes.md)
> - [17-rag-in-dify](./19-rag-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

上线后要会评估与裁剪上下文。验证：做迷你评估集 + 上下文裁剪函数，并对照 dify 实现。

## 需求

1. 构造 5 条「问题-应含关键词/金句」评估集；你的假 retrieve 返回固定候选，计算命中率。
2. 实现 `fit_context(chunks, max_chars)`：按相关性优先塞入，保证不超预算。
3. `NOTES.md`：列 4 种失败模式（空检索、噪声、过期文档、权限泄漏）及对应日志/指标该怎么看。
4. 对照 `17-rag-in-dify` 相关源码路径做批注。

## 提示

- 评估不必上 LLM-as-judge
- 上下文裁剪稳定排序：score desc + 稳定二次键

## 验收标准

- [ ] 评估脚本输出命中率
- [ ] fit_context 超限时丢弃低分块
- [ ] 失败模式笔记完整
- [ ] 有仓库路径锚点

## 延伸（选做）

为评估集增加「应拒答」样本。
