# 7.2.2 混合检索：BM25 + 向量检索

> 理解混合检索的设计思想：把传统关键词检索（BM25）和向量检索结合，取长补短。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 BM25 算法的核心思想
- 对比 BM25 和向量检索的优劣
- 理解 Reciprocal Rank Fusion（RRF）等融合策略
- 看懂 dify 中混合检索的实现

## 📚 前置知识

- 向量相似度检索（详见 [相似度检索](./07-similarity-search.md)）

## 1. 核心概念

### 1.1 为什么需要混合检索？

| 方法 | 强项 | 弱项 |
|------|------|------|
| **BM25**（关键词） | 精确匹配（人名、产品型号） | 无法理解同义词 |
| **向量检索** | 语义匹配 | 容易"飘"（找到不精确相关的） |

混合检索 = 两者结合，兼顾精确匹配和语义匹配。

### 1.2 BM25 算法

BM25（Best Matching 25）是一种基于词频的排序函数：

$$\text{BM25}(q, d) = \sum_{i=1}^{n} \text{IDF}(q_i) \cdot \frac{f(q_i, d) \cdot (k_1 + 1)}{f(q_i, d) + k_1 \cdot (1 - b + b \cdot \frac{|d|}{avgdl})}$$

- $f(q_i, d)$：词 $q_i$ 在文档 $d$ 中出现的频率
- IDF：逆文档频率（罕见的词权重高）
- $k_1, b$：调节参数

核心思想：**某词在某文档中频繁出现，且在所有文档中较少出现，则该词对该文档有强区分力**。

### 1.3 结果融合：RRF

Reciprocal Rank Fusion：

$$\text{RRF}(d) = \sum_{r \in \text{ranks}} \frac{1}{k + r(d)}$$

- $r(d)$：文档 $d$ 在某个排序中的位置
- $k$：常数（一般取 60）
- 把多个排序结果按位置倒数相加，得分最高的就是最终 top-K

## 2. 代码示例

### 2.1 手写一个简单 BM25

```python
import math
from collections import Counter
from typing import List, Dict


class SimpleBM25:
    def __init__(self, corpus: List[str]):
        self.corpus = [doc.lower().split() for doc in corpus]
        self.N = len(self.corpus)
        self.avgdl = sum(len(doc) for doc in self.corpus) / self.N
        # IDF
        self.df: Dict[str, int] = Counter()
        for doc in self.corpus:
            for word in set(doc):
                self.df[word] += 1

    def _idf(self, word: str) -> float:
        return math.log((self.N - self.df[word] + 0.5) / (self.df[word] + 0.5) + 1)

    def score(self, query: str, doc_idx: int, k1=1.5, b=0.75) -> float:
        doc = self.corpus[doc_idx]
        doc_len = len(doc)
        tf = Counter(doc)
        score = 0.0
        for word in query.lower().split():
            if word not in tf:
                continue
            f = tf[word]
            idf = self._idf(word)
            score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * doc_len / self.avgdl))
        return score

    def search(self, query: str, top_k: int = 5) -> List[int]:
        scored = [(i, self.score(query, i)) for i in range(self.N)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [i for i, s in scored[:top_k] if s > 0]


# 测试
corpus = [
    "Dify is an open source LLM platform",
    "RAG is retrieval augmented generation",
    "Python is a programming language",
    "Vector database stores embeddings",
]
bm25 = SimpleBM25(corpus)
results = bm25.search("LLM platform", top_k=3)
print(f"Top-3: {results}")
```

### 2.2 RRF 融合

```python
def reciprocal_rank_fusion(rankings: List[List[int]], k: int = 60) -> List[int]:
    """rankings: 多个排序结果，每个是 doc_id 列表"""
    scores: Dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


# 测试
bm25_ranking = [0, 2, 3, 1]   # BM25 排序
vector_ranking = [1, 0, 3, 2]  # 向量检索排序
fused = reciprocal_rank_fusion([bm25_ranking, vector_ranking])
print(f"融合结果: {fused}")
```

## 3. dify 仓库源码解读

### 3.1 WeightRerank 中的混合打分

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
**核心代码**（行 59-75）：

```python
query_scores = self._calculate_keyword_score(query, documents)
query_vector_scores = self._calculate_cosine(self.tenant_id, query, documents, self.weights.vector_setting)

rerank_documents = []
for document, query_score, query_vector_score in zip(documents, query_scores, query_vector_scores):
    score = (
        self.weights.vector_setting.vector_weight * query_vector_score
        + self.weights.keyword_setting.keyword_weight * query_score
    )
```

**解读**：
- 同时计算关键词分数（BM25）和向量相似度（Cosine）
- 按用户配置的权重相加，得到最终分数
- 这是最直接的"加权和"融合，比 RRF 更直观、可调

### 3.2 关键词表构建

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/keyword/jieba/jieba_keyword_table_handler.py`（节选）
**核心代码**：

```python
import jieba
from collections import Counter


class JiebaKeywordTableHandler:
    """中文关键词提取，使用 jieba 分词"""

    def extract_keywords(self, text: str, top_k: int = 10) -> list[tuple[str, float]]:
        """用 jieba.analyse 提取关键词"""
        import jieba.analyse
        return jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)

    def build_keyword_table(self, documents: list[str]) -> dict[str, list[str]]:
        """建立关键词 → 文档的倒排索引"""
        table: dict[str, list[str]] = {}
        for doc_id, text in enumerate(documents):
            keywords = self.extract_keywords(text, top_k=20)
            for keyword, _ in keywords:
                table.setdefault(keyword, []).append(str(doc_id))
        return table
```

**解读**：
- dify 用 jieba（中文分词）+ TF-IDF 提取关键词
- 关键词表是 BM25 的基础数据结构
- 倒排索引：`keyword → [doc_id, doc_id, ...]`

## 4. 关键要点总结

- BM25 擅长精确匹配，向量检索擅长语义匹配
- 混合检索结合两者：互补短板
- 融合方式：加权和（直观可调）或 RRF（无需调参）
- dify 通过 `WeightRerank` 让用户配置两者权重

## 5. 练习题

### 练习 1：基础（必做）

用 `rank_bm25` 库对一组中文文档建索引，对一个查询做 BM25 检索，比较纯 BM25 和混合检索的结果差异。

### 练习 2：进阶

阅读 `weight_rerank.py` 完整代码，回答：如何根据业务场景调整 `vector_weight` 与 `keyword_weight`？

### 练习 3：挑战（选做）

实现一个 RRF 融合函数，对比"加权和"与 RRF 在一组测试查询上的差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
- `/Users/xu/code/github/dify/api/core/rag/datasource/keyword/jieba/jieba_keyword_table_handler.py`
- BM25 原论文：Robertson, S. 2009

---

**文档版本**：v1.0
**最后更新**：2026-07-13