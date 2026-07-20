# 7.1.3 文本切片策略：固定长度 / 语义 / 递归

> 掌握 RAG 中最关键的预处理步骤——文本切片，理解 dify 的切片器实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释为什么 RAG 必须做切片
- 对比固定长度 / 语义 / 递归三种切片策略
- 使用 dify 的 `RecursiveCharacterTextSplitter` 切片
- 看懂 `chunk_overlap` 的作用和实现

## 📚 前置知识

- [RAG 概览](./01-rag-overview.md)
- Token 与上下文窗口（详见 [Tokens 与上下文](../06-llm-and-ai/03-tokens-context.md)）
- Python 字符串操作

## 1. 核心概念

### 1.1 为什么要切片？

LLM 有上下文长度限制（如 4K、8K、32K tokens）。把整本书一次性塞给 LLM：
1. 超出上下文长度
2. 检索时粒度太粗，召回精度低
3. Embedding 模型对长文本向量化效果差（详见 [Embedding 模型](../06-llm-and-ai/06-embedding-models.md)）

所以必须**把长文档切成短片段（chunk）**，每个片段独立 Embedding、独立检索。

### 1.2 三大切片策略

| 策略 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| **固定长度** | 按字符数 N 切 | 简单 | 可能在句子中间断开 |
| **语义切片** | 按段落、标题切 | 语义完整 | 长度不可控 |
| **递归切片** | 先按段落 → 再按句子 → 再按字符 | 兼顾长度和语义 | 实现复杂 |

### 1.3 Chunk Overlap

为了让切片**不丢失上下文**，相邻 chunk 会有部分重叠：

```
chunk_1: [   0 --- 1000   ]
chunk_2:              [   800 --- 1800   ]
                              ↑ 重叠 200 字符
```

如果切在关键信息中间，重叠可以保证关键信息至少出现在一个完整 chunk 中。

## 2. 代码示例

### 2.1 手写一个固定长度切片器

```python
def fixed_length_split(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """固定长度切片器"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# 测试
text = "Dify 是一个开源平台。" * 100  # 模拟长文本
chunks = fixed_length_split(text, chunk_size=200, overlap=20)
print(f"共切 {len(chunks)} 段")
```

### 2.2 实现递归切片器（dify 风格）

```python
from typing import List

def recursive_split(text: str, chunk_size: int = 1000, overlap: int = 100,
                    separators: List[str] = None) -> List[str]:
    """递归切片器：先按段落，再按句子，再按字符"""
    if separators is None:
        separators = ["\n\n", "\n", "。", "！", "？", " ", ""]

    # 如果当前文本已经够小，直接返回
    if len(text) <= chunk_size:
        return [text] if text else []

    # 选择第一个能切出更小片段的分隔符
    separator = separators[0]
    new_separators = separators[1:] if len(separators) > 1 else [""]

    if separator == "":
        # 已经没有可用的分隔符，按字符切
        splits = list(text)
    else:
        splits = text.split(separator)

    # 把切出来的小片段合并成 chunk
    chunks = []
    current_chunk = ""
    for split in splits:
        if len(current_chunk) + len(split) + len(separator) <= chunk_size:
            current_chunk += (separator if current_chunk else "") + split
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 如果单个 split 还超过 chunk_size，递归切
            if len(split) > chunk_size:
                chunks.extend(recursive_split(split, chunk_size, overlap, new_separators))
                current_chunk = ""
            else:
                current_chunk = split
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


# 测试
long_text = "Dify 是一个开源平台。" * 50 + "\n\n" + "RAG 是检索增强生成。" * 50
chunks = recursive_split(long_text, chunk_size=200, overlap=20)
print(f"递归切出 {len(chunks)} 段")
```

### 2.3 常见错误：Overlap 大于 Chunk Size

```python
# ❌ 错误：overlap >= chunk_size 会导致无限循环或空 chunk
chunks = fixed_length_split(text, chunk_size=100, overlap=150)  # 永远到不了 100

# ✅ 正确：overlap < chunk_size（一般 overlap 是 chunk_size 的 10-20%）
chunks = fixed_length_split(text, chunk_size=1000, overlap=100)
```

## 3. 关键要点总结

- 切片是 RAG 的关键预处理步骤，决定了检索粒度
- 三大策略：固定长度（简单）/ 语义（按段落）/ 递归（LangChain 默认）
- `chunk_overlap` 用于避免关键信息被切断（一般取 chunk_size 的 10-20%）
- dify 通过 `length_function` 注入支持字符数或 token 数两种长度计量

---

**文档版本**：v1.0
**最后更新**：2026-07-13
