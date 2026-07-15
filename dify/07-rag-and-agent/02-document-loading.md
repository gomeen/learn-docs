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

## 3. dify 仓库源码解读

### 3.1 ExtractProcessor 调度器

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/extractor/extract_processor.py`
**核心代码**（行 42-90）：

```python
class ExtractProcessor:
    @overload
    @classmethod
    def load_from_upload_file(
        cls, upload_file: UploadFile, return_text: Literal[True], is_automatic: bool = False
    ) -> str: ...

    @overload
    @classmethod
    def load_from_upload_file(
        cls, upload_file: UploadFile, return_text: Literal[False] = False, is_automatic: bool = False
    ) -> list[Document]: ...

    @classmethod
    def load_from_upload_file(
        cls, upload_file: UploadFile, return_text: bool = False, is_automatic: bool = False
    ) -> list[Document] | str:
        extract_setting = ExtractSetting(
            datasource_type=DatasourceType.FILE, upload_file=upload_file, document_model="text_model"
        )
        text_docs = ExtractProcessor.extract(extract_setting, is_automatic=is_automatic)
```

**解读**：
- 使用 `@overload` 装饰器支持两种返回类型（`str` 或 `list[Document]`）
- `ExtractSetting` 把所有解析需要的参数封装成一个对象，便于在多个 extractor 间传递
- 这是"参数对象模式"，避免长参数列表

### 3.2 Extractor 基类

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/extractor/extractor_base.py`
**核心代码**（行 1-30）：

```python
from abc import ABC, abstractmethod
from typing import Optional

from core.rag.models.document import Document


class BaseExtractor(ABC):
    """所有文档解析器的基类。"""

    def __init__(self, tenant_id: str, file_path: str, file_name: str, **kwargs):
        self.tenant_id = tenant_id
        self.file_path = file_path
        self.file_name = file_name

    @abstractmethod
    def extract(self) -> list[Document]:
        """子类必须实现：返回 Document 列表"""
        raise NotImplementedError

    def _extract_file_metadata(self) -> dict:
        return {
            "source_file": self.file_name,
            "file_path": self.file_path,
        }
```

**解读**：
- `ABC` + `@abstractmethod` 强制子类实现 `extract`
- 统一接口让 `ExtractProcessor` 可以用同一种方式调度所有 extractor
- 解析器只关心"把文件变 Document"，不关心后续切片、向量化

## 4. 关键要点总结

- dify 支持 10+ 种文档格式（PDF/Word/Excel/HTML/CSV/Notion/网页/Markdown/PPT/...）
- 每种格式对应一个独立的 Extractor 类，实现统一的 `extract()` 接口
- `ExtractProcessor` 是调度器，根据 datasource_type 选择对应 extractor
- 统一的数据结构是 `Document{page_content, metadata}`

## 5. 练习题

### 练习 1：基础（必做）

写一个 `PlainTextExtractor`，继承 `BaseExtractor`，实现读取 `.txt` 文件并返回 `list[Document]`。

### 练习 2：进阶

阅读 `csv_extractor.py`、`excel_extractor.py`，总结 CSV 和 Excel 解析的差异（编码处理、多 sheet 处理）。

### 练习 3：挑战（选做）

实现一个 `HTMLCleaner`，去除 HTML 标签但保留段落结构（用 `<p>` 作为分块边界）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/extractor/extract_processor.py`
- `/Users/xu/code/github/dify/api/core/rag/extractor/extractor_base.py`
- `/Users/xu/code/github/dify/api/core/rag/extractor/pdf_extractor.py`
- `/Users/xu/code/github/dify/api/core/rag/extractor/notion_extractor.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13