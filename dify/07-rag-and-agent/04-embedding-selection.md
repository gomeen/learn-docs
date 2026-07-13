# 7.1.4 Embedding 模型选型

> 理解 Embedding 模型在 RAG 中的作用，掌握 dify 中的 Embedding 调用与缓存机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Embedding 模型的工作原理
- 列举主流 Embedding 模型及其适用场景
- 理解 dify 的 `CacheEmbedding` 缓存策略
- 看懂 dify 中 Embedding 与切片的协同（token 计算）

## 📚 前置知识

- 06-llm-and-ai 中关于 Embedding 基础
- 07-rag-and-agent/03-chunking-strategies.md

## 1. 核心概念

### 1.1 什么是 Embedding？

Embedding 是把文本映射为**稠密向量**（dense vector）的过程：

```
"你好世界"  →  [0.12, -0.34, 0.56, ..., 0.78]   (维度通常 384/768/1024/1536)
```

语义相近的文本在向量空间中距离近：

```
"猫" → [0.8, 0.1, ...]
"狗" → [0.7, 0.2, ...]   ← 距离近
"汽车" → [-0.3, 0.9, ...] ← 距离远
```

### 1.2 主流 Embedding 模型对比

| 模型 | 维度 | 语言 | 特点 |
|------|------|------|------|
| OpenAI text-embedding-3-small | 1536 | 多语言 | 性价比高 |
| OpenAI text-embedding-3-large | 3072 | 多语言 | 精度高 |
| BGE-M3 | 1024 | 多语言 | 开源、支持长文本 |
| M3E | 1024 | 中文 | 中文社区主流 |
| Cohere embed-v3 | 1024 | 多语言 | Rerank 一体 |

### 1.3 为什么 dify 要缓存 Embedding？

Embedding 调用**极贵**（一次 1000 个 token 约 $0.0001，量大时很贵）。同一段文本反复调用是浪费。dify 通过数据库缓存避免重复计算。

## 2. 代码示例

### 2.1 用 sentence-transformers 加载本地 Embedding

```python
from sentence_transformers import SentenceTransformer

# 加载本地模型
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

# 编码文本
texts = ["Dify 是一个开源平台", "RAG 是检索增强生成"]
embeddings = model.encode(texts)
print(embeddings.shape)  # (2, 512) - 2 个向量，每个 512 维

# 计算余弦相似度
import numpy as np
sim = np.dot(embeddings[0], embeddings[1]) / (
    np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
)
print(f"相似度: {sim:.4f}")  # 越接近 1 越相似
```

### 2.2 自己实现一个极简 Embedding 缓存

```python
import hashlib
from typing import List, Dict


class SimpleEmbeddingCache:
    def __init__(self):
        self._cache: Dict[str, List[float]] = {}

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get_or_compute(self, text: str, compute_fn) -> List[float]:
        key = self._hash(text)
        if key in self._cache:
            print(f"[CACHE HIT] {text[:20]}")
            return self._cache[key]
        print(f"[CACHE MISS] {text[:20]}")
        vec = compute_fn(text)
        self._cache[key] = vec
        return vec


# 模拟 Embedding
def mock_embed(text: str) -> List[float]:
    return [hash(text) % 100 / 100.0] * 384


cache = SimpleEmbeddingCache()
text = "Dify 是开源平台"
v1 = cache.get_or_compute(text, mock_embed)  # MISS
v2 = cache.get_or_compute(text, mock_embed)  # HIT
```

### 2.3 常见错误：忘记 batch

```python
# ❌ 错误：逐条调用 embedding，效率低
for text in texts:
    vec = client.embed(text)

# ✅ 正确：批量调用
vectors = client.embed_batch(texts, batch_size=64)
```

## 3. dify 仓库源码解读

### 3.1 CacheEmbedding 缓存实现

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/embedding/cached_embedding.py`
**核心代码**（行 24-50）：

```python
class CacheEmbedding(Embeddings):
    def __init__(self, model_instance: ModelInstance):
        self._model_instance = model_instance

    @override
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed search docs in batches of 10."""
        # use doc embedding cache or store if not exists
        text_embeddings: list[Any] = [None for _ in range(len(texts))]
        embedding_queue_indices = []
        for i, text in enumerate(texts):
            hash = helper.generate_text_hash(text)
            embedding = db.session.scalar(
                select(Embedding)
                .where(
                    Embedding.model_name == self._model_instance.model_name,
                    Embedding.hash == hash,
                    Embedding.provider_name == self._model_instance.provider,
                )
                .limit(1)
            )
            if embedding:
                text_embeddings[i] = embedding.get_embedding()
            else:
                embedding_queue_indices.append(i)
```

**解读**：
- 第 30 行：先分配一个 `None` 列表占位
- 第 34-44 行：遍历每个文本，先查数据库的 `Embedding` 表
- 第 45-48 行：如果数据库里有缓存，直接用；否则加入"待计算队列"
- 这是经典的"先查后算"模式，最大限度复用历史 Embedding

### 3.2 Embedding 与切片的协同

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/splitter/fixed_text_splitter.py`
**核心代码**（行 15-45）：

```python
class EnhanceRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    """
    This class is used to implement from_gpt2_encoder, to prevent using of tiktoken
    """

    @classmethod
    def from_encoder[T: EnhanceRecursiveCharacterTextSplitter](
        cls: type[T],
        embedding_model_instance: ModelInstance | None,
        allowed_special: Literal["all"] | AbstractSet[str] = frozenset(),
        disallowed_special: Literal["all"] | AbstractSet[str] = "all",
        **kwargs: Any,
    ) -> T:
        def _token_encoder(texts: list[str]) -> list[int]:
            if not texts:
                return []
            if embedding_model_instance:
                return embedding_model_instance.get_text_embedding_num_tokens(texts=texts)
            else:
                return [GPT2Tokenizer.get_num_tokens(text) for text in texts]
```

**解读**：
- 让切片器使用**与 Embedding 模型一致的 tokenizer** 来计数长度
- 这样切片大小精确匹配 Embedding 模型的最大输入长度
- 防止"切片后超出模型限制被截断"

## 4. 关键要点总结

- Embedding 模型把文本变稠密向量，相似文本向量距离近
- dify 通过数据库缓存（`Embedding` 表）避免重复计算
- Embedding 与切片器必须协同：用 Embedding 模型的 tokenizer 计算长度
- 批量调用效率远高于逐条调用

## 5. 练习题

### 练习 1：基础（必做）

用 sentence-transformers 加载 `BAAI/bge-small-zh-v1.5`，对 5 条中文句子做 Embedding，计算两两余弦相似度。

### 练习 2：进阶

阅读 `cached_embedding.py` 完整实现，回答：如果 Embedding 模型升级了（比如从 `text-embedding-3-small` 升级到 `text-embedding-3-large`），旧缓存会失效吗？怎么改进？

### 练习 3：挑战（选做）

实现一个 Embedding 缓存的两级缓存（内存 LRU + 数据库），给出接口设计。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/embedding/cached_embedding.py`
- `/Users/xu/code/github/dify/api/core/rag/embedding/embedding_base.py`
- `/Users/xu/code/github/dify/api/core/rag/splitter/fixed_text_splitter.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13