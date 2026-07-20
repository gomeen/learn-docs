# 3.5.3 专用向量库：Milvus / Weaviate / Qdrant

> 比较三类专用向量库的数据模型、过滤、混合检索与运维特征，并理解 dify 如何统一使用它们。

## 🎯 学习目标

完成本文档后，你将能够：
- 比较三种后端的核心模型
- 理解 collection、payload/property 与索引
- 识别混合检索和过滤能力
- 从 dify 适配器选择后端

## 📚 前置知识

- [3.5.1 向量检索基础](./19-vector-search.md)
- PostgreSQL 内嵌向量方案对照（详见 [pgvector](./20-pgvector.md)）
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

三者都保存向量和业务 metadata。Dify 统一保存 `doc_id`、`document_id` 等字段，删除和过滤才能定位记录；索引创建用 Redis 锁避免并发重复（分布式锁详见 [Redis Redlock](../../_common/04-distributed-locks/02-redis-redlock.md)；Redis 在 dify 中的用法见 [Redis in dify](../04-cache-and-queue/01-redis-in-dify.md)）。

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

## 3. 关键要点总结

- 选择同时考虑检索、过滤、运维和成本
- metadata 是删除与过滤关键
- 批量写入和并发建索引保护是共同需求
- 统一接口要处理分数语义差异

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
