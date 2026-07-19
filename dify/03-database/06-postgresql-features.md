# 3.1.6 PostgreSQL 特有功能：JSON / 数组 / GIN 索引

> 在关系结构之外安全使用 JSONB、数组和 GIN，同时保持字段可查询、可约束和可演进。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 JSON 与 JSONB 的存储和查询特点
- 使用 JSONB 与数组运算符
- 理解 GIN 的倒排索引模型
- 识别 dify 对跨数据库 JSON 类型和 GIN 的处理

## 📚 前置知识

- [3.1.3 索引原理](./03-sql-index.md)
- JSON 基础：[`../01-fundamentals/27-json-processing.md`](../01-fundamentals/27-json-processing.md)

## 1. 核心概念

### 1.1 JSONB 不是“免设计”

`jsonb` 以分解后的二进制形式存储，支持包含、键存在和路径查询，通常比 `json` 更适合检索。稳定且高频过滤的字段仍应建成普通列，以获得类型约束、统计信息和清晰索引。

### 1.2 数组

PostgreSQL 数组适合“单行内的小型同类值集合”，例如标签。`@>` 表示包含，`&&` 表示有交集。需要频繁连接、携带额外属性或独立更新的成员，应规范化成子表（范式与反范式详见 [数据库规范化](./07-database-normalization.md)）。

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

## 3. dify 仓库源码解读

### 3.1 文档 JSON 字段的跨库抽象

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`  
**核心代码**（行 497-506）：

```python
class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="document_pkey"),
        sa.Index("document_dataset_id_idx", "dataset_id"),
        sa.Index("document_is_paused_idx", "is_paused"),
        sa.Index("document_tenant_idx", "tenant_id"),
        adjusted_json_index("document_metadata_idx", "doc_metadata"),
    )

```

**解读**：
- `doc_metadata` 使用项目自定义 `AdjustedJSON`，让模型层表达统一语义。
- `adjusted_json_index(...)` 根据数据库能力选择合适索引实现。
- 同一表还为租户和数据集的标量过滤保留普通 B-tree 索引。

### 3.2 迁移中显式创建 JSONB GIN

**文件位置**：`/Users/xu/code/github/dify/api/migrations/versions/2025_02_27_0917-d20049ed0af6_add_metadata_function.py`  
**核心代码**（行 90-102）：

```python
    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('built_in_field_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    if _is_pg(conn):
        with op.batch_alter_table('documents', schema=None) as batch_op:
            batch_op.alter_column('doc_metadata',
                   existing_type=postgresql.JSON(astext_type=sa.Text()),
                   type_=postgresql.JSONB(astext_type=sa.Text()),
                   existing_nullable=True)
            batch_op.create_index('document_metadata_idx', ['doc_metadata'], unique=False, postgresql_using='gin')
    else:
        pass
    # ### end Alembic commands ###
```

**解读**：
- 迁移只在 PostgreSQL 分支把 `JSON` 改成 `JSONB`。
- 第 99 行用 `postgresql_using="gin"` 创建元数据倒排索引。
- 非 PostgreSQL 分支跳过该特有操作，体现方言差异必须显式处理。

## 4. 关键要点总结

- JSONB 适合半结构化数据，但不替代关系建模
- 数组适合小型同类值集合，复杂成员应拆表
- GIN 服务包含与成员检索，B-tree 服务标量排序和范围
- 跨数据库项目需要在类型与迁移层隔离方言差异

## 5. 练习题

### 练习 1：基础（必做）

建立 JSONB 列并分别用 `->`、`->>`、`@>` 查询。

### 练习 2：进阶

为标签数组创建 GIN，比较建索引前后的执行计划。

### 练习 3：挑战（选做）

阅读 `AdjustedJSON` 实现，说明 PostgreSQL 和其他数据库的差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/dataset.py`
- `/Users/xu/code/github/dify/api/migrations/versions/2025_02_27_0917-d20049ed0af6_add_metadata_function.py`
- PostgreSQL JSON：https://www.postgresql.org/docs/current/datatype-json.html
- PostgreSQL 数组：https://www.postgresql.org/docs/current/arrays.html
- PostgreSQL GIN：https://www.postgresql.org/docs/current/gin.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
