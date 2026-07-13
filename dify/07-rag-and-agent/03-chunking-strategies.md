# 7.1.3 文本切片策略：固定长度 / 语义 / 递归

> 掌握 RAG 中最关键的预处理步骤——文本切片，理解 dify 的切片器实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释为什么 RAG 必须做切片
- 对比固定长度 / 语义 / 递归三种切片策略
- 使用 dify 的 `RecursiveCharacterTextSplitter` 切片
- 看懂 `chunk_overlap` 的作用和实现

## 📚 前置知识

- 07-rag-and-agent/01-rag-overview.md
- Python 字符串操作

## 1. 核心概念

### 1.1 为什么要切片？

LLM 有上下文长度限制（如 4K、8K、32K tokens）。把整本书一次性塞给 LLM：
1. 超出上下文长度
2. 检索时粒度太粗，召回精度低
3. Embedding 模型对长文本向量化效果差

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

## 3. dify 仓库源码解读

### 3.1 TextSplitter 基类

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/splitter/text_splitter.py`
**核心代码**（行 33-60）：

```python
class TextSplitter(BaseDocumentTransformer, ABC):
    """Interface for splitting text into chunks."""

    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Callable[[list[str]], list[int]] = lambda x: [len(x) for x in x],
        keep_separator: bool = False,
        add_start_index: bool = False,
    ):
        """Create a new TextSplitter.

        Args:
            chunk_size: Maximum size of chunks to return
            chunk_overlap: Overlap in characters between chunks
            length_function: Function that measures the length of given chunks
            keep_separator: Whether to keep the separator in the chunks
            add_start_index: If `True`, includes chunk's start index in metadata
        """
        if chunk_overlap > chunk_size:
            raise ValueError(
                f"Got a larger chunk overlap ({chunk_overlap}) than chunk size ({chunk_size}), should be smaller."
            )
```

**解读**：
- 第 53-56 行：`chunk_overlap > chunk_size` 直接抛错，避免下游死循环
- `length_function` 是可注入的，默认按字符数，也可以按 token 数
- `add_start_index` 用于追溯 chunk 在原文中的位置（前端展示高亮时很有用）

### 3.2 _merge_splits 算法核心

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/splitter/text_splitter.py`
**核心代码**（行 98-131）：

```python
def _merge_splits(self, splits: Iterable[str], separator: str, lengths: list[int]) -> list[str]:
    # We now want to combine these smaller pieces into medium size
    # chunks to send to the LLM.
    separator_len = self._length_function([separator])[0]

    docs = []
    current_doc: list[str] = []
    total = 0
    for d, _len in zip(splits, lengths):
        if total + _len + (separator_len if len(current_doc) > 0 else 0) > self._chunk_size:
            if total > self._chunk_size:
                logger.warning(
                    "Created a chunk of size %s, which is longer than the specified %s", total, self._chunk_size
                )
            if len(current_doc) > 0:
                doc = self._join_docs(current_doc, separator)
                if doc is not None:
                    docs.append(doc)
                # Keep on popping if:
                # - we have a larger chunk than in the chunk overlap
                # - or if we still have any chunks and the length is long
                while total > self._chunk_overlap or (
                    total + _len + (separator_len if len(current_doc) > 0 else 0) > self._chunk_size and total > 0
                ):
                    total -= self._length_function([current_doc[0]])[0] + (
                        separator_len if len(current_doc) > 1 else 0
                    )
                    current_doc = current_doc[1:]
        current_doc.append(d)
        total += _len + (separator_len if len(current_doc) > 1 else 0)
```

**解读**：
- `total` 跟踪当前 chunk 的累积长度
- 当 `total + next_len > chunk_size` 时，弹出已完成的 chunk
- **关键的 `while` 循环**：持续从头部弹出片段，直到 `total <= chunk_overlap`，实现 overlap 效果
- 这就是 LangChain 的经典 `_merge_splits` 算法，dify 直接复用

## 4. 关键要点总结

- 切片是 RAG 的关键预处理步骤，决定了检索粒度
- 三大策略：固定长度（简单）/ 语义（按段落）/ 递归（LangChain 默认）
- `chunk_overlap` 用于避免关键信息被切断（一般取 chunk_size 的 10-20%）
- dify 通过 `length_function` 注入支持字符数或 token 数两种长度计量

## 5. 练习题

### 练习 1：基础（必做）

用 dify 的 `RecursiveCharacterTextSplitter` 切片下面这段文本，观察输出：
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text = "第一段。\n\n第二段比较长。" * 50
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
print(splitter.split_text(text))
```

### 练习 2：进阶

修改 `_merge_splits` 算法，把 `length_function` 改为按 token 数（用 `len(text.split())` 模拟），观察输出。

### 练习 3：挑战（选做）

阅读 `fixed_text_splitter.py` 中的 `FixedRecursiveCharacterTextSplitter`，理解"固定分隔符"切片与普通递归切片的差异，并思考什么场景下要用固定分隔符。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/splitter/text_splitter.py`
- `/Users/xu/code/github/dify/api/core/rag/splitter/fixed_text_splitter.py`
- LangChain TextSplitters 文档

---

**文档版本**：v1.0
**最后更新**：2026-07-13