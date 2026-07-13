# 1.1.6 Embedding 模型原理与选型

> 理解文本如何映射到向量空间，并从语义质量、维度、语言、成本和迁移风险选择 Embedding 模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Embedding 向量如何表达文本的语义相似性
- 使用余弦相似度比较查询与文档向量
- 区分 Embedding、生成式 LLM 与 Rerank 模型的职责
- 从维度、上下文长度、语言、领域和成本评估模型
- 能看懂 dify 如何区分 `LLM`、`TEXT_EMBEDDING` 和 `RERANK` 模型类型

## 📚 前置知识

- [01-llm-overview.md](./01-llm-overview.md)
- [02-transformer.md](./02-transformer.md)
- [03-tokens-context.md](./03-tokens-context.md)
- 外部基础：向量、点积、范数、余弦相似度和基本检索概念

## 1. 核心概念

### 1.1 从文本到语义向量

Embedding 模型把文本 $x$ 映射为固定维向量 $f(x)\in\mathbb{R}^d$。训练目标会让语义相近的文本在向量空间中更接近，让不相关文本更远。检索时先离线计算文档向量，再计算查询向量，通过近似最近邻索引找候选文档。

常用余弦相似度为：

$$
\operatorname{cos}(a,b)=\frac{a\cdot b}{\|a\|\|b\|}
$$

若向量已归一化，余弦相似度就等于点积。Embedding 擅长快速召回，但它把整段文本压缩成一个向量，细粒度条件可能丢失。因此 RAG 常采用“两阶段检索”：Embedding 从大量文档中召回候选，Rerank 模型再同时阅读 query-document 对并精排。

### 1.2 模型选型与生命周期

选型不能只看排行榜，需要匹配实际数据：

| 维度 | 要问的问题 |
| --- | --- |
| 语义质量 | 在自有 query-document 标注集上 Recall@K、MRR 如何？ |
| 语言/领域 | 是否覆盖中文、代码、法律、医疗等真实语料？ |
| 上下文长度 | 文档块是否会被截断？长块是否真的提升召回？ |
| 向量维度 | 存储、索引内存和检索延迟是否可接受？ |
| 成本/吞吐 | 批量建库和在线查询的价格与速率如何？ |
| 可运维性 | 是否支持批处理、私有部署、版本固定与监控？ |

同一索引中的文档向量和查询向量必须来自同一模型、同一版本与同一预处理方案。更换模型后，旧向量与新向量不在同一个坐标空间，通常需要全量重建索引。模型迁移应采用双写、回填、离线评测、灰度切流，而不是只替换模型名称。

## 2. 代码示例

### 2.1 用余弦相似度完成一个最小检索器

```python
# 文件：vector_search.py
import math


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def search(
    query_vector: list[float], documents: dict[str, list[float]], limit: int = 2
) -> list[tuple[str, float]]:
    scored = [
        (document_id, cosine_similarity(query_vector, vector))
        for document_id, vector in documents.items()
    ]
    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


document_vectors = {
    "refund": [0.95, 0.05, 0.10],
    "password": [0.05, 0.95, 0.10],
    "invoice": [0.75, 0.10, 0.45],
}
print(search([0.90, 0.08, 0.15], document_vectors))
```

**说明**：向量数值在真实系统中由 Embedding 模型生成。示例只展示检索阶段；大规模场景会使用向量数据库的近似最近邻索引，而不是遍历所有文档。

## 3. dify 仓库源码解读

### 3.1 模型运行时区分 Embedding 与 Rerank

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/model_entities.py`  
**核心代码**（行 9-19）：

```python
class ModelType(Enum):
    """
    Enum class for model type.
    """

    LLM = "llm"
    TEXT_EMBEDDING = "text-embedding"
    RERANK = "rerank"
    SPEECH2TEXT = "speech2text"
    MODERATION = "moderation"
    TTS = "tts"
```

**解读**：
- 第 14-16 行：生成、向量召回与精排是三种不同模型能力，不能互相替代。
- 第 17-19 行：同一运行时还统一描述语音、审核和合成模型。
- 整体设计意图：上层业务按能力选择模型，而不是把所有 AI 请求都塞进 LLM 接口。

### 3.2 Embedding 响应包含二维向量列表与用量

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/text_embedding_entities.py`  
**核心代码**（行 7-28）：

```python
class EmbeddingUsage(ModelUsage):
    """
    Model class for embedding usage.
    """

    tokens: int
    total_tokens: int
    unit_price: Decimal
    price_unit: Decimal
    total_price: Decimal
    currency: str
    latency: float


class TextEmbeddingResult(BaseModel):
    """
    Model class for text embedding result.
    """

    model: str
    embeddings: list[list[float]]
    usage: EmbeddingUsage
```

**解读**：
- 第 12-18 行：Embedding 同样记录 token、价格和延迟，便于评估批量建库成本。
- 第 26-28 行：一次调用可返回多个文本对应的二维向量列表，并绑定具体模型和 usage。
- 整体设计意图：对不同供应商输出建立统一结果类型，让知识库流程不依赖专有 SDK。

## 4. 关键要点总结

- Embedding 把文本映射到向量空间，用距离近似语义相关性
- 余弦相似度适合比较方向；归一化向量时可直接使用点积
- Embedding 负责高效召回，Rerank 负责对少量候选做更精细判断
- 选型必须使用自有语料评测，并权衡维度、成本、语言和上下文长度
- 更换 Embedding 模型通常需要重建全部文档向量和索引

## 5. 练习题

### 练习 1：基础（必做）

手算向量 `[1, 0]` 与 `[1, 1]` 的余弦相似度，并解释为什么它不等于 1。

**参考答案**：见 `solutions/06-embedding-models.md`

### 练习 2：进阶

扩展示例，加入文档元数据过滤与相似度阈值；当没有候选超过阈值时返回“无可靠资料”，而不是强行返回最近文档。

### 练习 3：挑战（选做）

为 dify 知识库设计 Embedding 模型迁移方案：包含双索引、全量回填、Recall@K 对比、灰度切换、回滚和旧索引清理步骤。

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/model_entities.py`
- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/text_embedding_entities.py`
- Sentence-BERT：https://arxiv.org/abs/1908.10084
- BEIR Benchmark：https://arxiv.org/abs/2104.08663
- Faiss：https://faiss.ai/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
