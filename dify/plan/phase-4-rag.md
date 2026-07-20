# Phase 4 — RAG / 知识库

← [索引](../LEARNING-PLAN.md) · 上一 → [Phase 2](./phase-2-main-paths.md) · 下一 → [Phase 5](./phase-5-workflow-agent.md)

**量级：** 2–4 周 · **入学：** Phase 2 总毕业  

---

## 目标

竖切：**上传/索引 → 检索 →（可选）注入提示 → 回答**。

---

## 必读（按序）

1. [`../07-rag-and-agent/01-rag-overview.md`](../07-rag-and-agent/01-rag-overview.md)  
2. [`../07-rag-and-agent/02-document-loading.md`](../07-rag-and-agent/02-document-loading.md)  
3. [`../07-rag-and-agent/03-chunking-strategies.md`](../07-rag-and-agent/03-chunking-strategies.md)  
4. [`../07-rag-and-agent/06-knowledge-base-in-dify.md`](../07-rag-and-agent/06-knowledge-base-in-dify.md)  
5. [`../07-rag-and-agent/08-similarity-search.md`](../07-rag-and-agent/08-similarity-search.md)  
6. [`../07-rag-and-agent/13-retrieval-pipeline.md`](../07-rag-and-agent/13-retrieval-pipeline.md)  
7. [`../07-rag-and-agent/19-rag-in-dify.md`](../07-rag-and-agent/19-rag-in-dify.md)  
8. 向量够用：[`../03-database/19-vector-search.md`](../03-database/19-vector-search.md) + [`22-vdb-in-dify.md`](../03-database/22-vdb-in-dify.md)

**验证：** [`07-*-rag-basics`](../07-rag-and-agent/07-*-rag-basics.md)、[`14-*-retrieval`](../07-rag-and-agent/14-*-retrieval.md) 中可执行部分  

**卡壳再读：** hybrid / rerank / query-rewriting 单篇  
**延后：** multimodal、评测全集、全部向量库  

---

## 源码（从 API 逆推）

- `controllers/console/datasets/`  
- dataset / document 相关 `services/`  
- `core/rag/` · `core/indexing_runner.py`  
- `tasks/document_indexing_task.py`  
- `models/dataset.py`  

---

## 毕业验收

- [ ] 口述：chunk → embedding → 索引  
- [ ] 口述：提问检索如何影响回答  
- [ ] 索引是否异步 + 任务文件  
- [ ] 一条知识库问答跟读路径笔记  

→ [Phase 5 Workflow + Agent](./phase-5-workflow-agent.md)
