# 7.3.3 多模态 RAG：图片、表格、音频

> 掌握多模态 RAG：处理文档中的图片、表格、音频、视频，扩展 RAG 的能力边界。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释多模态 RAG 的必要性
- 描述图片、表格、音频的向量化方法
- 了解多模态 Embedding 模型（CLIP、ColPali）
- 看懂 dify 中多模态数据的处理

## 📚 前置知识

- Embedding 选型（详见 [Embedding 选型](./04-embedding-selection.md)）
- 多模态模型背景（详见 [主流大模型对比](../06-llm-and-ai/01-llm-overview.md)）

## 1. 核心概念

### 1.1 为什么需要多模态 RAG？

传统 RAG 只处理文本，但很多知识藏在非文本中：
- **PDF 中的图片**：产品图、架构图
- **PDF 中的表格**：财务数据、对比表
- **PPT 中的图表**
- **音频转写**：会议录音
- **视频**：教程、产品演示

### 1.2 多模态 Embedding 模型

| 模型 | 模态 | 特点 |
|------|------|------|
| CLIP | 图-文 | 经典图文对齐 |
| SigLIP | 图-文 | Google 新版 CLIP |
| ColPali | 页面-文本 | PDF 页面级检索 |
| BGE-M3 | 文 | 多语言文本 |
| Whisper | 音频 | 音频转文本 |
| GPT-4V / Claude 3.5 | 图文理解 | 用 LLM 直接理解图片 |

### 1.3 多模态 RAG 的三种路径

1. **多模态 Embedding 直接检索**：用 CLIP/ColPali 把图嵌入向量
2. **模态转换**：图片用 VLM 转文字，再走传统 RAG
3. **混合**：文本 Embedding + 图片 Embedding 混合检索

## 2. 代码示例

### 2.1 用 CLIP 做图文检索

```python
from transformers import CLIPProcessor, CLIPModel
from PIL import Image


class ImageTextRetriever:
    """用 CLIP 做图文双向检索"""

    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def encode_text(self, texts: list[str]) -> list[list[float]]:
        inputs = self.processor(text=texts, return_tensors="pt", padding=True)
        return self.model.get_text_features(**inputs).tolist()

    def encode_images(self, images: list[Image.Image]) -> list[list[float]]:
        inputs = self.processor(images=images, return_tensors="pt")
        return self.model.get_image_features(**inputs).tolist()

    def search_images(self, query: str, image_embeddings, top_k=5):
        """用文本查询检索图片"""
        import numpy as np
        q_vec = np.array(self.encode_text([query])[0])
        scores = [np.dot(q_vec, np.array(e)) for e in image_embeddings]
        return sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
```

### 2.2 用 GPT-4V 转图片为描述

```python
class ImageDescriber:
    """用多模态 LLM 把图片转为文字描述"""

    PROMPT = "请详细描述这张图片的内容，包括：场景、对象、文字、关键信息。"

    def __init__(self, vlm_client):
        self.vlm = vlm_client

    def describe(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            response = self.vlm.chat(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "data": f.read()},
                        {"type": "text", "text": self.PROMPT},
                    ],
                }]
            )
        return response
```

### 2.3 音频转文本

```python
import whisper


class AudioTranscriber:
    """用 Whisper 把音频转文本"""

    def __init__(self, model_name: str = "base"):
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio_path: str) -> str:
        result = self.model.transcribe(audio_path)
        return result["text"]
```

### 2.4 常见错误：图片直接喂给文本 Embedding

```python
# ❌ 错误：图片路径丢给 text-embedding-3
vec = client.embed(image_path)  # 只会编码路径字符串

# ✅ 正确：用 CLIP / ColPali 等多模态 Embedding
vec = clip.encode_image(image_pil)
```

## 3. 关键要点总结

- 多模态 RAG 是趋势，扩展了 RAG 的能力边界
- 主流多模态 Embedding：CLIP、ColPali、SigLIP
- 三种实现路径：多模态 Embedding / 模态转换 / 混合
- dify 用 `DocType` 枚举区分模态，对接多模态 Rerank 模型

---

**文档版本**：v1.0
**最后更新**：2026-07-13
