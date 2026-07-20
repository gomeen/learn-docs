# 小验证：检索优化与 Retrieval Pipeline

> 覆盖：
> - [07-similarity-search](./08-similarity-search.md)
> - [08-hybrid-search](./09-hybrid-search.md)
> - [09-rerank](./10-rerank.md)
> - [10-query-rewriting](./11-query-rewriting.md)
> - [11-metadata-filter](./12-metadata-filter.md)
> - [12-retrieval-pipeline](./13-retrieval-pipeline.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

检索质量决定 RAG 上限。验证：实现最小 hybrid 打分，并读懂 dify retrieval 管道。

## 需求

1. 本地：对小语料实现 `bm25_like_score`（可极简 TF）+ 向量分（伪向量）线性融合 `alpha`。
2. 实现 `apply_metadata_filter(docs, filters)`：支持 `equals` 与 `in`。
3. 阅读 `api/core/rag/retrieval/`，`NOTES.md` 画出 pipeline 步骤（rewrite → retrieve → rerank…以代码为准）。
4. （可选）为某过滤条件补测试或修正边界 bug（小改动）。

## 提示

- 融合分数要归一或说明量纲
- 仓库 retrieval 目录

## 验收标准

- [ ] top-k 融合排序可运行
- [ ] metadata 过滤单测/断言 ≥3
- [ ] pipeline 步骤与文件对应
- [ ] 可选改动不扩大召回越权（租户/权限）

## 延伸（选做）

增加简单 query rewrite：同义词表替换。
