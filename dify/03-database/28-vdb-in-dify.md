# 3.5.4 dify 的向量库适配层

> 从 BaseVector 契约、Factory、entry point 注册到 Vector 门面，理解 dify 如何隔离多种向量后端。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 BaseVector、Factory、Vector 的职责
- 理解 entry point 发现与缓存
- 追踪 dataset.index_struct 的后端选择
- 能审查一个 VDB provider

## 📚 前置知识

- [3.5.3 专用向量库](./27-vector-databases.md)
- 工厂与适配器模式（详见 [策略与工厂](../02-backend/23-strategy-factory.md)、[适配器模式](../02-backend/22-adapter-pattern.md)；经典定义亦可参考 [工厂方法](../../_fundamentals/06-design-patterns/02-factory-method.md)、[适配器](../../_fundamentals/06-design-patterns/06-adapter.md)）
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

## 3. dify 仓库源码解读

### 3.1 BaseVector 后端契约

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_base.py`  
**核心代码**（行 17-45）：

```python

class BaseVector(ABC):
    def __init__(self, collection_name: str):
        self._collection_name = collection_name

    @abstractmethod
    def get_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def create(self, texts: list[Document], embeddings: list[list[float]], **kwargs) -> list[str] | None:
        raise NotImplementedError

    @abstractmethod
    def add_texts(self, documents: list[Document], embeddings: list[list[float]], **kwargs) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def text_exists(self, id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_by_ids(self, ids: list[str]) -> None:
        raise NotImplementedError

    def get_ids_by_metadata_field(self, key: str, value: str):
        raise NotImplementedError

    @abstractmethod
```

**解读**：
- 基类保存 collection_name。
- 创建、追加、存在和删除有固定签名。
- 能力缺口在开发期暴露。

### 3.2 entry point 延迟发现与缓存

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_backend_registry.py`  
**核心代码**（行 74-86）：

```python

def get_vector_factory_class(vector_type: str) -> type[AbstractVectorFactory]:
    """Resolve :class:`AbstractVectorFactory` for a :class:`~VectorType` string value."""
    if vector_type in _VECTOR_FACTORY_CACHE:
        return _VECTOR_FACTORY_CACHE[vector_type]

    plugin_cls = _load_plugin_factory(vector_type)
    if plugin_cls is not None:
        _VECTOR_FACTORY_CACHE[vector_type] = plugin_cls
        return plugin_cls

    cls = _load_builtin_factory(vector_type)
    _VECTOR_FACTORY_CACHE[vector_type] = cls
```

**解读**：
- 先查缓存。
- 优先加载插件 Factory。
- 没有插件才尝试内建目标。

## 4. 关键要点总结

- Vector 负责 embedding，BaseVector 负责 SDK 翻译
- Factory 根据 Dataset 初始化
- entry point 隔离可选依赖
- 统一接口仍需明确分数、过滤和错误语义

## 5. 练习题

### 练习 1：基础（必做）

画出 search_by_vector 调用链。

### 练习 2：进阶

补全 MemoryVector 并测试。

### 练习 3：挑战（选做）

核对一个 provider 的 entry point、Factory、配置和测试。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_base.py`
- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_backend_registry.py`
- `/Users/xu/code/github/dify/api/providers/vdb/vdb-pgvector/pyproject.toml`
- Python entry points：https://packaging.python.org/en/latest/specifications/entry-points/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
