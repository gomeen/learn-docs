# 3.6 全文索引：倒排索引

> 全文索引（Full-Text Index）用于高效的文本搜索，核心数据结构是**倒排索引**（Inverted Index）。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解倒排索引的原理
- 掌握全文索引 vs LIKE 查询的区别
- 知道 PostgreSQL 的 tsvector / tsquery
- 在 dify 中识别全文检索的应用

## 📚 前置知识

- 10-index-basics.md
- 字符串匹配基础

## 1. 核心概念

### 1.1 倒排索引原理

```
文档（正向）：
doc1: "Dify is an AI platform"
doc2: "Dify supports RAG"
doc3: "RAG uses vector database"

倒排索引（反向）：
"dify"   → [doc1, doc2]
"rag"    → [doc2, doc3]
"vector" → [doc3]
```

### 1.2 倒排索引的组成

1. **词项词典（Term Dictionary）**：所有唯一词
2. **倒排列表（Posting List）**：每个词对应的文档列表（及位置信息）

### 1.3 PostgreSQL 全文检索

PostgreSQL 用 `tsvector` + `tsquery`：
- `tsvector`：文档的标准化表示（词项 + 位置）
- `tsquery`：查询条件
- `ts_rank`：相关性评分

```sql
-- 创建全文索引
CREATE INDEX idx_articles_content ON articles USING GIN(to_tsvector('english', content));

-- 查询
SELECT * FROM articles
WHERE to_tsvector('english', content) @@ to_tsquery('dify & rag');
```

### 1.4 MySQL FULLTEXT 索引

- MySQL 5.6+ InnoDB 支持 FULLTEXT
- 默认最小词长 4（`innodb_ft_min_token_size`）
- 中文需要 ngram 解析器：`WITH PARSER ngram`

## 2. 代码示例

### 2.1 倒排索引简化实现

```python
import re
from collections import defaultdict

class InvertedIndex:
    """倒排索引"""

    def __init__(self):
        self.index: dict[str, set[int]] = defaultdict(set)
        self.documents: dict[int, str] = {}

    def _tokenize(self, text: str) -> list[str]:
        # 简化：按空格分词，转小写
        return re.findall(r"\w+", text.lower())

    def add_document(self, doc_id: int, text: str) -> None:
        self.documents[doc_id] = text
        for token in self._tokenize(text):
            self.index[token].add(doc_id)

    def search(self, query: str) -> set[int]:
        """单词查询"""
        tokens = self._tokenize(query)
        if not tokens:
            return set()
        result = self.index.get(tokens[0], set())
        for token in tokens[1:]:
            result &= self.index.get(token, set())  # AND
        return result

    def search_or(self, query: str) -> set[int]:
        tokens = self._tokenize(query)
        result = set()
        for token in tokens:
            result |= self.index.get(token, set())
        return result


idx = InvertedIndex()
idx.add_document(1, "Dify is an AI platform")
idx.add_document(2, "Dify supports RAG")
idx.add_document(3, "RAG uses vector database")

print(idx.search("dify rag"))     # {2}——AND
print(idx.search_or("dify rag"))  # {1, 2, 3}——OR
```

### 2.2 对比 LIKE 查询

```sql
-- ❌ LIKE 全表扫描，无法走索引
SELECT * FROM articles WHERE content LIKE '%dify%';

-- ✅ 全文索引（毫秒级）
SELECT * FROM articles
WHERE to_tsvector('english', content) @@ to_tsquery('dify');
```

## 3. dify 仓库源码解读

### 3.1 dify 的 RAG 与向量检索

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
**核心代码**（行 1-50）：

```python
from typing import Any

class Vector:
    """向量检索（不是倒排索引，但是另一种相似度搜索）"""
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id

    def search_by_vector(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        """基于向量的相似度搜索（ANN 算法）"""
        # 实际使用 pgvector、ChromaDB、Qdrant 等
        ...
```

**解读**：
- dify 用**向量检索**（pgvector）做 RAG，不是倒排索引
- **相似度搜索**比传统倒排索引更智能（语义匹配）
- 倒排索引（全文索引）dify/ruoyi 中无直接示例

### 3.2 difi 的关键词搜索（兜底）

**文件位置**：`/Users/xu/code/github/dify/api/services/dataset_service.py`
**核心代码**（行 30-60）：

```python
def keyword_search(query: str, dataset_id: str) -> list[dict]:
    """关键词搜索——使用 PostgreSQL ILIKE 或全文检索"""
    with Session(db.engine) as session:
        # 简化版用 ILIKE（不依赖全文索引）
        stmt = select(Document).where(
            Document.dataset_id == dataset_id,
            Document.name.ilike(f"%{query}%"),
        )
        return list(session.scalars(stmt).all())
```

**解读**：
- dify 的兜底关键词搜索用 `ILIKE`（不依赖全文索引）
- RAG 主路径走**向量检索**（更智能）

## 4. 关键要点总结

- 倒排索引是全文检索的核心数据结构
- PostgreSQL `tsvector` + `tsquery` 支持英文全文检索
- 中文需要专门的 ngram / IK 解析器
- dify 用向量检索（pgvector）做 RAG，不依赖倒排索引
- dify/ruoyi 中无直接倒排索引示例

## 5. 练习题

### 练习 1：基础
用上面的 InvertedIndex 实现，添加"按词频排序"功能。

### 练习 2：进阶
在 PostgreSQL 中为 `articles` 表创建全文索引（GIN），并测试 `@@` 查询。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
- `/Users/xu/code/github/dify/api/services/dataset_service.py`
- PostgreSQL 全文检索：https://www.postgresql.org/docs/current/textsearch.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13