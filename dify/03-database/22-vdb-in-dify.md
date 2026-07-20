# 3.5.4 dify 的向量库适配层

> 从 BaseVector 契约、Factory、entry point 注册到 Vector 门面，理解 dify 如何隔离多种向量后端。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 BaseVector、Factory、Vector 的职责
- 理解 entry point 发现与缓存
- 追踪 dataset.index_struct 的后端选择
- 能审查一个 VDB provider

## 📚 前置知识

- [3.5.3 专用向量库](./21-vector-databases.md)
- 工厂与适配器模式（详见 [策略与工厂](../02-backend/21-strategy-factory.md)、[适配器模式](../02-backend/20-adapter-pattern.md)；经典定义亦可参考 [工厂方法](../../_fundamentals/06-design-patterns/02-factory-method.md)、[适配器](../../_fundamentals/06-design-patterns/06-adapter.md)）
- Python entry point 基础

## 1. 核心概念

### 1.1 四层结构

```text
业务服务 → Vector 门面 → AbstractVectorFactory → BaseVector 适配器
```

Vector 门面负责 embedding、批处理和追踪；Factory 按 Dataset 初始化；BaseVector 把统一方法翻译成具体 SDK。

### 1.2 后端发现

provider 包在 `dify.vector_backends` 组注册 `vector_type → Factory`。Registry 延迟加载并缓存类，核心包不静态导入所有第三方 SDK。

### 1.3 数据集绑定

新数据集读取全局 `VECTOR_STORE`；已有数据集优先使用 `index_struct_dict['type']`，保证配置切换后旧索引仍路由到原后端。

### 1.4 统一不抹平差异

过滤能力、阈值语义、错误类型仍由适配器翻译。新增后端还要提供依赖、entry point、配置和测试。

## 2. 代码示例

### 2.1 实现内存版适配器骨架

```python
from core.rag.datasource.vdb.vector_base import BaseVector
from core.rag.models.document import Document

class MemoryVector(BaseVector):
    def __init__(self, collection_name: str):
        super().__init__(collection_name)
        self._docs: dict[str, Document] = {}

    def get_type(self) -> str:
        return "memory"

    def create(self, texts, embeddings, **kwargs):
        return self.add_texts(texts, embeddings)

    def add_texts(self, documents, embeddings, **kwargs):
        ids = [doc.metadata["doc_id"] for doc in documents if doc.metadata]
        self._docs.update(zip(ids, documents))
        return ids

    def text_exists(self, id: str) -> bool:
        return id in self._docs

    def delete_by_ids(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)
```

**说明**：示例省略其余抽象方法；完整 provider 必须实现两类搜索、metadata 删除和集合删除。

## 3. 关键要点总结

- Vector 负责 embedding，BaseVector 负责 SDK 翻译
- Factory 根据 Dataset 初始化
- entry point 隔离可选依赖
- 统一接口仍需明确分数、过滤和错误语义

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
