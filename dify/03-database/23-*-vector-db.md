# 小验证：向量检索与 dify VDB 适配层

> 覆盖：
> - [15-vector-search](./19-vector-search.md)
> - [16-pgvector](./20-pgvector.md)
> - [17-vector-databases](./21-vector-databases.md)
> - [18-vdb-in-dify](./22-vdb-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

RAG 依赖向量库适配。验证：理解相似度与适配层接口，并在仓库中定位一种向量库实现。

## 需求

1. 本地纯 Python：实现余弦相似度函数，对 3 个样例向量做 top-k（k=2），不求数值库最优，求接口清楚。
2. 在 `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/` 选一种后端，阅读其 `create`/`search_by_vector`（名称以仓库为准）并写 `NOTES.md`：集合命名、top_k、过滤参数如何传递。
3. （可选改代码）为某 VDB 客户端的日志增加 debug 级「top_k / 耗时」——默认不噪音。

## 提示

- 适配层目录：`api/core/rag/datasource/vdb/`
- 先搜 `Vector` 基类/工厂

## 验收标准

- [ ] 本地 top-k 结果可复现
- [ ] `NOTES.md` 指向具体文件与方法名
- [ ] 能说明「业务代码为何不直接 import milvus SDK」
- [ ] 可选改动默认不影响生产日志量

## 延伸（选做）

对比 pgvector 与外置向量库在运维上的取舍（3 条）。
