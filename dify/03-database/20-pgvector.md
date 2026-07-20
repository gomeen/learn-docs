# 3.5.2 pgvector：PostgreSQL 向量检索插件

> 在 PostgreSQL 中用 vector 类型和 HNSW 索引保存 embedding，同时复用事务、JSONB 元数据与 SQL 过滤能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 安装并启用 pgvector 扩展
- 理解 vector 列与距离运算符
- 使用 HNSW 余弦索引
- 读懂 dify PGVector 实现

## 📚 前置知识

- [3.5.1 向量检索基础](./19-vector-search.md)
- [3.1.6 PostgreSQL 特有功能](./01-postgresql-features.md)

## 1. 核心概念

### 1.1 类型与运算符

pgvector 提供 `vector(n)` 类型。`<->` 是欧氏距离、`<#>` 是负内积、`<=>` 是余弦距离。余弦相似度通常换算为 `1 - cosine_distance`。

### 1.2 HNSW

`USING hnsw (embedding vector_cosine_ops)` 为余弦距离建立 ANN 索引。`m` 控制连接数，`ef_construction` 影响构建质量和成本。

### 1.3 边界

pgvector 适合已有 PostgreSQL、数据量中等且需要关系过滤/事务一致性的场景（事务语义详见 [事务与隔离级别](../../_common/21-sql/04-sql-transaction.md)）。极大规模与独立弹性可能更适合专用向量库（详见 [专用向量库](./21-vector-databases.md)）。

## 2. 代码示例

### 2.1 创建向量表和余弦索引

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(3) NOT NULL
);

CREATE INDEX knowledge_embedding_hnsw_idx
ON knowledge_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

INSERT INTO knowledge_chunks
    (id, document_id, content, embedding)
VALUES
    ('00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000010',
     'SQL basics', '[0.9,0.1,0.0]');

SELECT id, content, 1 - (embedding <=> '[1,0,0]') AS score
FROM knowledge_chunks
ORDER BY embedding <=> '[1,0,0]'
LIMIT 5;
```

**说明**：ORDER BY 与索引 opclass 使用同一余弦距离；显示时再转成相似度。

## 3. 关键要点总结

- 维度必须与 embedding 模型一致
- 索引 opclass 与查询距离一致
- 余弦相似度可用 1-distance
- pgvector 复用 PostgreSQL 但受单库边界约束

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
