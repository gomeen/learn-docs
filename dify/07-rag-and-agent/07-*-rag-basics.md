# 小验证：RAG 基础管线

> 覆盖：
> - [01-rag-overview](./01-rag-overview.md)
> - [02-document-loading](./02-document-loading.md)
> - [03-chunking-strategies](./03-chunking-strategies.md)
> - [04-embedding-selection](./04-embedding-selection.md)
> - [05-vector-db-index](./05-vector-db-index.md)
> - [06-knowledge-base-in-dify](./06-knowledge-base-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

知识库从文档到可检索块是 RAG 的前半段。验证：本地切分 + 对照 dify 知识库架构。

## 需求

1. 本地实现 `chunk_text(text, size, overlap)`，对一篇 ≥1KB 样例 Markdown 切片；打印每片长度与前 40 字符。
2. 比较 `overlap=0` vs `overlap=size//5` 的边界句子完整性（人工看 2 例）。
3. 阅读 `api/core/rag/` 下 extractor/splitter 入口，`NOTES.md` 描述 dify 知识库主流程文件。

## 提示

- `api/core/rag/extractor/`、`splitter/`
- 切片不要在句子中间硬切得太狠（可用简单段落优先）

## 验收标准

- [ ] 切片覆盖全文无死循环
- [ ] overlap 对比有结论
- [ ] NOTES 含知识库主路径
- [ ] 样例文件不含敏感数据

## 延伸（选做）

增加按 Markdown 标题二次切分。
