# 7.1.2 文档加载：多格式解析（PDF / Word / Markdown / HTML）

> 理解 RAG 管道第一步——文档加载，了解 dify 如何支持 10+ 种文档格式。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出常见的文档格式及其解析难点
- 使用 dify 的 `ExtractProcessor` 加载任意支持格式的文档
- 看懂 dify 中 extractor 的策略模式设计

## 📚 前置知识

- Python 基础与文件 I/O
- RAG 全流程概览（详见 [RAG 概览](./01-rag-overview.md)）

## 1. 核心概念

### 1.1 文档格式与解析难点

| 格式 | 解析工具 | 难点 |
|------|----------|------|
| PDF | pypdf, unstructured | 表格、扫描件、公式 |
| Word | python-docx | 样式、图片、批注 |
| Markdown | markdown-it, mistune | 简单，几乎纯文本 |
| HTML | beautifulsoup4 | 标签清理、保留语义 |
| Excel | openpyxl, pandas | 多 sheet、合并单元格 |
| CSV | csv, pandas | 编码、分隔符 |
| Notion | notion API | 嵌套块、附件 |
| 网页 | firecrawl, jina | JS 渲染、反爬 |

### 1.2 解析器模式（Extractor Pattern）

dify 采用**策略模式**，每种格式对应一个 `Extractor`：

```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self) -> list[Document]:
        pass
```

`ExtractProcessor` 作为"调度器"，根据文件类型选择对应 extractor。

## 2. 代码示例

### 2.1 用 ExtractProcessor 加载 PDF

```python
from core.rag.extractor.extract_processor import ExtractProcessor
from models.model import UploadFile

def load_pdf_to_documents(upload_file: UploadFile):
    """加载 PDF 文件并返回 Document 列表"""
    documents = ExtractProcessor.load_from_upload_file(
        upload_file=upload_file,
        return_text=False,  # 返回 Document 对象列表
    )
    return documents

# 使用示例
# docs = load_pdf_to_documents(my_pdf_file)
# for doc in docs:
#     print(f"[{doc.metadata.get('page', '?')}] {doc.page_content[:80]}")
```

### 2.2 自己实现一个简易 Markdown 解析器

```python
import re
from typing import List

class MarkdownDocument:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


def parse_markdown(md_text: str) -> List[MarkdownDocument]:
    """极简 Markdown 解析：按二级标题切片"""
    # 用正则按 ## 分割
    sections = re.split(r'\n## ', md_text)
    documents = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        # 第一段是标题前的部分
        title_match = re.match(r'# (.+)', section)
        title = title_match.group(1) if title_match else f"section_{i}"
        documents.append(MarkdownDocument(
            page_content=section.strip(),
            metadata={"title": title, "section_index": i},
        ))
    return documents


# 测试
md = """# 标题

引言内容

## 第一章

第一章内容

## 第二章

第二章内容
"""
docs = parse_markdown(md)
for d in docs:
    print(f"[{d.metadata['title']}] {d.page_content[:30]}...")
```

## 3. 关键要点总结

- dify 支持 10+ 种文档格式（PDF/Word/Excel/HTML/CSV/Notion/网页/Markdown/PPT/...）
- 每种格式对应一个独立的 Extractor 类，实现统一的 `extract()` 接口
- `ExtractProcessor` 是调度器，根据 datasource_type 选择对应 extractor
- 统一的数据结构是 `Document{page_content, metadata}`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
