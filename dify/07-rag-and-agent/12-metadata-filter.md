# 7.2.5 元数据过滤与多条件检索

> 掌握元数据过滤（Metadata Filtering）在 RAG 中的作用，理解 dify 的元数据模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释元数据过滤的价值
- 设计一个文档的元数据 schema
- 用 LLM 把自然语言转换为结构化过滤条件
- 看懂 dify 中元数据过滤的实现

## 📚 前置知识

- 查询改写（详见 [Query Rewriting](./11-query-rewriting.md)）
- SQL WHERE 子句基础（详见 [SQL 基础](../../_common/21-sql/01-sql-basics.md)）
- Pydantic 校验（详见 [Pydantic 基础](../02-backend/12-pydantic-basics.md)）

## 1. 核心概念

### 1.1 什么是元数据？

元数据是描述文档属性的结构化信息：

```python
Document(
    page_content="Dify 是一个开源 LLM 平台...",
    metadata={
        "source": "official_docs.pdf",
        "category": "产品介绍",
        "author": "Dify Team",
        "created_at": "2024-01-15",
        "version": "1.0",
        "language": "zh",
    }
)
```

### 1.2 元数据过滤 vs 向量检索

| 维度 | 元数据过滤 | 向量检索 |
|------|-----------|---------|
| 匹配方式 | 精确（值相等/范围） | 模糊（语义相似） |
| 速度 | 快（可建索引） | 较慢（向量计算） |
| 适用 | 结构化条件 | 语义查询 |

最佳实践：**先元数据过滤缩小范围 → 再向量检索**。

### 1.3 常见元数据字段

```
文档级：source_file, file_type, created_at, author, language
业务级：category, tags, department, product_line, region
权限级：access_level, owner_tenant
```

## 2. 代码示例

### 2.1 简单元数据过滤

```python
from typing import List


class Document:
    def __init__(self, content: str, metadata: dict):
        self.content = content
        self.metadata = metadata


def filter_documents(docs: List[Document], conditions: dict) -> List[Document]:
    """简单元数据过滤：所有条件 AND 连接"""
    results = []
    for doc in docs:
        if all(doc.metadata.get(k) == v for k, v in conditions.items()):
            results.append(doc)
    return results


# 测试
docs = [
    Document("Dify 介绍", {"category": "产品", "language": "zh"}),
    Document("Dify API", {"category": "技术", "language": "en"}),
    Document("RAG 教程", {"category": "技术", "language": "zh"}),
]

filtered = filter_documents(docs, {"category": "技术", "language": "zh"})
print([d.content for d in filtered])  # ["RAG 教程"]
```

### 2.2 用 LLM 提取过滤条件

```python
import json


class MetadataFilterExtractor:
    """用 LLM 从自然语言查询中提取结构化过滤条件"""

    PROMPT = """从用户查询中提取元数据过滤条件。

可用的元数据字段：
{catalog}

支持的比较运算符：is, is not, contains, does not contain, is empty, is not empty,
                  >, <, =, ≠, before, after

用户查询：{query}

输出 JSON：
{{
    "metadata_conditions": [
        {{"name": "category", "comparison_operator": "is", "value": "技术"}}
    ]
}}
"""

    def __init__(self, llm, metadata_catalog: dict):
        self.llm = llm
        self.catalog = metadata_catalog

    def extract(self, query: str) -> dict:
        catalog_str = "\n".join(f"- {k}: {v}" for k, v in self.catalog.items())
        prompt = self.PROMPT.format(catalog=catalog_str, query=query)
        response = self.llm.invoke(prompt)
        return json.loads(response)
```

### 2.3 常见错误：元数据过滤后做语义匹配

```python
# ❌ 错误：先语义检索再过滤，结果可能为空
results = vector_store.semantic_search(query, top_k=20)
filtered = [r for r in results if r.metadata["year"] == 2024]  # 可能全过滤掉

# ✅ 正确：先过滤缩小范围，再做语义检索
candidates = vector_store.filter({"year": 2024})  # 元数据索引快速筛
results = vector_store.semantic_search_in(query, candidates, top_k=5)
```

## 3. 关键要点总结

- 元数据过滤先于向量检索，提升精度和效率
- 用 LLM 把自然语言转换为结构化过滤条件
- 支持的操作符：is / contains / > / < / before / after
- dify 用 Pydantic 定义过滤条件，自带校验

---

**文档版本**：v1.0
**最后更新**：2026-07-13
