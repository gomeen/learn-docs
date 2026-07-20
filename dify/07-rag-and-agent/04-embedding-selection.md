# 7.1.4 Embedding 模型选型

> 理解 Embedding 模型在 RAG 中的作用，掌握 dify 中的 Embedding 调用与缓存机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Embedding 模型的工作原理
- 列举主流 Embedding 模型及其适用场景
- 理解 dify 的 `CacheEmbedding` 缓存策略
- 看懂 dify 中 Embedding 与切片的协同（token 计算）

## 📚 前置知识

- Embedding 原理与选型（详见 [Embedding 模型](../06-llm-and-ai/06-embedding-models.md)）
- 切片策略（详见 [Chunking 策略](./03-chunking-strategies.md)）
- 向量空间与相似度（详见 [向量检索基础](../03-database/19-vector-search.md)）

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

## 3. 关键要点总结

- Embedding 模型把文本变稠密向量，相似文本向量距离近
- dify 通过数据库缓存（`Embedding` 表）避免重复计算
- Embedding 与切片器必须协同：用 Embedding 模型的 tokenizer 计算长度
- 批量调用效率远高于逐条调用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
