# 3.1.6 PostgreSQL 特有功能：JSON / 数组 / GIN 索引

> 在关系结构之外安全使用 JSONB、数组和 GIN，同时保持字段可查询、可约束和可演进。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 JSON 与 JSONB 的存储和查询特点
- 使用 JSONB 与数组运算符
- 理解 GIN 的倒排索引模型
- 识别 dify 对跨数据库 JSON 类型和 GIN 的处理

## 📚 前置知识

- [3.1.3 索引原理](../../_common/21-sql/03-sql-index.md)
- JSON 基础：[`../01-fundamentals/20-json-processing.md`](../01-fundamentals/20-json-processing.md)

## 1. 核心概念

### 1.1 JSONB 不是“免设计”

`jsonb` 以分解后的二进制形式存储，支持包含、键存在和路径查询，通常比 `json` 更适合检索。稳定且高频过滤的字段仍应建成普通列，以获得类型约束、统计信息和清晰索引。

### 1.2 数组

PostgreSQL 数组适合“单行内的小型同类值集合”，例如标签。`@>` 表示包含，`&&` 表示有交集。需要频繁连接、携带额外属性或独立更新的成员，应规范化成子表（范式与反范式详见 [数据库规范化](../../_common/21-sql/06-normalization.md)）。

### 1.3 GIN

GIN 是倒排索引：一个键对应多行，适合 JSONB 键值、数组元素和全文词项。其读取能力强，但写放大和索引体积通常高于 B-tree。

| 数据 | 常见操作 | 索引 |
|---|---|---|
| JSONB | `@>`、`?`、路径 | GIN |
| 数组 | `@>`、`&&` | GIN |
| 标量范围 | `=`, `<`, `ORDER BY` | B-tree |

## 2. 代码示例

### 2.1 查询 JSONB 元数据和数组标签

```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    metadata JSONB NOT NULL DEFAULT '{}',
    tags TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX document_metadata_gin_idx
ON documents USING GIN (metadata);
CREATE INDEX document_tags_gin_idx
ON documents USING GIN (tags);

INSERT INTO documents (metadata, tags) VALUES
    ('{"source":"upload","lang":"zh"}', ARRAY['rag', 'database']),
    ('{"source":"api","lang":"en"}', ARRAY['agent']);

SELECT id, metadata->>'lang' AS language
FROM documents
WHERE metadata @> '{"source":"upload"}'
  AND tags && ARRAY['rag', 'sql'];
```

**说明**：两个包含/交集谓词都能利用 GIN；若经常按 `lang` 排序，应考虑表达式 B-tree 索引或独立列。

## 3. 关键要点总结

- JSONB 适合半结构化数据，但不替代关系建模
- 数组适合小型同类值集合，复杂成员应拆表
- GIN 服务包含与成员检索，B-tree 服务标量排序和范围
- 跨数据库项目需要在类型与迁移层隔离方言差异

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
