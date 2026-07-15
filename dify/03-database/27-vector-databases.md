# 3.5.3 专用向量库：Milvus / Weaviate / Qdrant

> 比较三类专用向量库的数据模型、过滤、混合检索与运维特征，并理解 dify 如何统一使用它们。

## 🎯 学习目标

完成本文档后，你将能够：
- 比较三种后端的核心模型
- 理解 collection、payload/property 与索引
- 识别混合检索和过滤能力
- 从 dify 适配器选择后端

## 📚 前置知识

- [3.5.1 向量检索基础](./25-vector-search.md)
- PostgreSQL 内嵌向量方案对照（详见 [pgvector](./26-pgvector.md)）
- 分布式系统和 HTTP/gRPC 基础

## 1. 核心概念

### 1.1 侧重点

| 后端 | 数据抽象 | 代表特点 |
|---|---|---|
| Milvus | Collection / Field | 大规模向量、稀疏 BM25 |
| Weaviate | Collection / Property | schema 属性、BM25 + 向量 |
| Qdrant | Collection / Point / Payload | 强 payload 过滤、REST/gRPC |

### 1.2 选择维度

除 QPS 和数据量，还要比较过滤、混合检索、备份、多租户、SDK、索引时间和成本。基准必须使用真实维度、top_k 和过滤比例。

### 1.3 共同设计

三者都保存向量和业务 metadata。Dify 统一保存 `doc_id`、`document_id` 等字段，删除和过滤才能定位记录；索引创建用 Redis 锁避免并发重复（分布式锁详见 [Redis Redlock](../../_common/04-distributed-locks/02-redis-redlock.md)；Redis 在 dify 中的用法见 [Redis in dify](../04-cache-and-queue/13-redis-in-dify.md)）。

## 2. 代码示例

### 2.1 用统一协议模拟多向量库

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Hit:
    doc_id: str
    score: float

class VectorBackend(Protocol):
    def upsert(
        self,
        doc_id: str,
        vector: list[float],
        metadata: dict[str, str],
    ) -> None: ...

    def search(
        self,
        vector: list[float],
        *,
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[Hit]: ...


def retrieve(backend: VectorBackend, query: list[float]) -> list[str]:
    hits = backend.search(query, top_k=5)
    return [hit.doc_id for hit in hits if hit.score >= 0.7]
```

**说明**：调用方依赖统一协议，后端负责翻译过滤和分数语义。

## 3. dify 仓库源码解读

### 3.1 Milvus 批量插入

**文件位置**：`/Users/xu/code/github/dify/api/providers/vdb/vdb-milvus/src/dify_vdb_milvus/milvus_vector.py`  
**核心代码**（行 140-167）：

```python
    @override
    def add_texts(self, documents: list[Document], embeddings: list[list[float]], **kwargs):
        """
        Add texts and their embeddings to the collection.
        """
        insert_dict_list = []
        for i in range(len(documents)):
            insert_dict = {
                # Do not need to insert the sparse_vector field separately, as the text_bm25_emb
                # function will automatically convert the native text into a sparse vector for us.
                Field.CONTENT_KEY: documents[i].page_content,
                Field.VECTOR: embeddings[i],
                Field.METADATA_KEY: documents[i].metadata,
            }
            insert_dict_list.append(insert_dict)
        # Total insert count
        total_count = len(insert_dict_list)
        pks: list[str] = []

        for i in range(0, total_count, 1000):
            # Insert into the collection.
            batch_insert_list = insert_dict_list[i : i + 1000]
            try:
                ids = self._client.insert(collection_name=self._collection_name, data=batch_insert_list)
                pks.extend(ids)
            except MilvusException as e:
                logger.exception("Failed to insert batch starting at entity: %s/%s", i, total_count)
                raise e
```

**解读**：
- 文本、向量和 metadata 组织成统一字段。
- 每 1000 条批量插入。
- 异常记录批次位置。

### 3.2 Qdrant 集合与 HNSW 配置

**文件位置**：`/Users/xu/code/github/dify/api/providers/vdb/vdb-qdrant/src/dify_vdb_qdrant/qdrant_vector.py`  
**核心代码**（行 127-149）：

```python
            if collection_name not in all_collection_name:
                from qdrant_client.http import models as rest

                vectors_config = rest.VectorParams(
                    size=vector_size,
                    distance=rest.Distance[self._distance_func],
                )
                hnsw_config = HnswConfigDiff(
                    m=0,
                    payload_m=16,
                    ef_construct=100,
                    full_scan_threshold=10000,
                    max_indexing_threads=0,
                    on_disk=False,
                )

                self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=vectors_config,
                    hnsw_config=hnsw_config,
                    timeout=int(self._client_config.timeout),
                    replication_factor=self._client_config.replication_factor,
                    write_consistency_factor=self._client_config.write_consistency_factor,
```

**解读**：
- 集合指定向量维度与距离函数。
- HNSW 参数控制图结构与全扫描阈值。
- 复制与写一致性参数来自配置。

## 4. 关键要点总结

- 选择同时考虑检索、过滤、运维和成本
- metadata 是删除与过滤关键
- 批量写入和并发建索引保护是共同需求
- 统一接口要处理分数语义差异

## 5. 练习题

### 练习 1：基础（必做）

制作三后端能力比较表。

### 练习 2：进阶

给协议添加全文搜索并处理能力缺失。

### 练习 3：挑战（选做）

设计真实数据基准测试。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/providers/vdb/vdb-milvus/src/dify_vdb_milvus/milvus_vector.py`
- `/Users/xu/code/github/dify/api/providers/vdb/vdb-qdrant/src/dify_vdb_qdrant/qdrant_vector.py`
- `/Users/xu/code/github/dify/api/providers/vdb/vdb-weaviate/src/dify_vdb_weaviate/weaviate_vector.py`
- Milvus：https://milvus.io/docs
- Weaviate：https://docs.weaviate.io/
- Qdrant：https://qdrant.tech/documentation/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
