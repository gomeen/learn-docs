# 07 - RAG 与 Agent

> Dify 的核心差异化能力：RAG 知识库 + Agent 工作流编排。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 前置依赖

- `06-llm-and-ai` 全部
- `03-database` 中的向量数据库基础

## 模块 7.1 RAG 基础

- [ ] [1.1 RAG 概述：为什么需要检索增强](./01-rag-overview.md)
- [ ] [1.2 文档加载：多格式解析（PDF / Word / Markdown / HTML）](./02-document-loading.md)
- [ ] [1.3 文本切片策略：固定长度 / 语义 / 递归](./03-chunking-strategies.md)
- [ ] [1.4 Embedding 模型选型](./04-embedding-selection.md)
- [ ] [1.5 向量数据库与索引类型](./05-vector-db-index.md)
- [ ] [1.6 dify 的知识库架构分析](./06-knowledge-base-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-rag-basics: RAG 基础管线](./07-*-rag-basics.md)
  - 覆盖：01-rag-overview.md, 02-document-loading.md, 03-chunking-strategies.md, 04-embedding-selection.md, 05-vector-db-index.md, 06-knowledge-base-in-dify.md


## 模块 7.2 检索优化

- [ ] [2.1 相似度检索：余弦 / 欧氏 / 点积](./08-similarity-search.md)
- [ ] [2.2 混合检索：BM25 + 向量检索](./09-hybrid-search.md)
- [ ] [2.3 重排序（Rerank）模型](./10-rerank.md)
- [ ] [2.4 查询改写与 HyDE](./11-query-rewriting.md)
- [ ] [2.5 元数据过滤与多条件检索](./12-metadata-filter.md)
- [ ] [2.6 dify 的检索管道（Retrieval Pipeline）](./13-retrieval-pipeline.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [14-*-retrieval: 检索优化与 Retrieval Pipeline](./14-*-retrieval.md)
  - 覆盖：08-similarity-search.md, 09-hybrid-search.md, 10-rerank.md, 11-query-rewriting.md, 12-metadata-filter.md, 13-retrieval-pipeline.md


## 模块 7.3 RAG 工程实践

- [ ] [3.1 RAG 评估体系：召回率 / 准确率 / 人工评估](./15-rag-evaluation.md)
- [ ] [3.2 上下文窗口管理与截断](./16-context-management.md)
- [ ] [3.3 多模态 RAG：图片、表格、音频](./17-multimodal-rag.md)
- [ ] [3.4 RAG 的常见失败模式与对策](./18-rag-failure-modes.md)
- [ ] [3.5 dify 的 RAG 实现源码分析](./19-rag-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [20-*-rag-engineering: RAG 评估与工程实践](./20-*-rag-engineering.md)
  - 覆盖：15-rag-evaluation.md, 16-context-management.md, 17-multimodal-rag.md, 18-rag-failure-modes.md, 19-rag-in-dify.md


## 模块 7.4 Agent 基础

- [ ] [4.1 Agent 概念：感知-决策-行动循环](./21-agent-concepts.md)
- [ ] [4.2 ReAct 模式深入](./22-react-deep-dive.md)
- [ ] [4.3 Plan-and-Execute 模式](./23-plan-execute.md)
- [ ] [4.4 Reflection 自我反思](./24-reflection.md)
- [ ] [4.5 Toolformer / ReWOO 等前沿模式](./25-advanced-agent.md)
- [ ] [4.6 dify 的 Agent 节点实现](./26-agent-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [27-*-agent: Agent 模式与 dify Agent 节点](./27-*-agent.md)
  - 覆盖：21-agent-concepts.md, 22-react-deep-dive.md, 23-plan-execute.md, 24-reflection.md, 25-advanced-agent.md, 26-agent-in-dify.md


## 模块 7.5 工作流编排（Dify 核心）

- [ ] [5.1 工作流引擎原理：节点 + 边 + 状态机](./28-workflow-engine.md)
- [ ] [5.2 节点类型：开始 / 结束 / LLM / 工具 / 条件 / 循环](./29-workflow-nodes.md)
- [ ] [5.3 变量系统：全局 / 会话 / 节点变量](./30-workflow-variables.md)
- [ ] [5.4 条件分支、循环、并行](./31-workflow-control-flow.md)
- [ ] [5.5 工作流的执行与状态管理](./32-workflow-execution.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [33-*-workflow: 工作流引擎 · 节点 · 变量 · 控制流 · 执行](./33-*-workflow.md)
  - 覆盖：28-workflow-engine.md, 29-workflow-nodes.md, 30-workflow-variables.md, 31-workflow-control-flow.md, 32-workflow-execution.md


- [ ] [5.6 工作流 DSL 规范（YAML 格式）](./34-workflow-dsl.md)
- [ ] [5.7 自定义节点开发](./35-custom-nodes.md)
- [ ] [5.8 dify 工作流执行器源码分析](./36-workflow-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [37-*-workflow-dsl-nodes: 工作流 DSL、自定义节点与 dify 执行器](./37-*-workflow-dsl-nodes.md)
  - 覆盖：34-workflow-dsl.md, 35-custom-nodes.md, 36-workflow-in-dify.md


## 模块 7.6 多 Agent 协作

- [ ] [6.1 多 Agent 架构：Supervisor / Swarm / Hierarchical](./38-multi-agent.md)
- [ ] [6.2 Agent 间通信协议](./39-agent-communication.md)
- [ ] [6.3 任务分发与负载均衡](./40-task-distribution.md)
- [ ] [6.4 dify 的 Chatflow vs Workflow 对比](./41-chatflow-vs-workflow.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [42-*-multi-agent-chatflow: 多 Agent 与 Chatflow/Workflow](./42-*-multi-agent-chatflow.md)
  - 覆盖：38-multi-agent.md, 39-agent-communication.md, 40-task-distribution.md, 41-chatflow-vs-workflow.md


## 🎯 dify 仓库对应位置

- 工作流引擎：`/Users/xu/code/github/dify/api/core/workflow/`
- 工作流节点：`/Users/xu/code/github/dify/api/core/workflow/nodes/`
- 工作流执行：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
- RAG 核心：`/Users/xu/code/github/dify/api/core/rag/`
- 文档提取：`/Users/xu/code/github/dify/api/core/rag/extractor/`
- 文档切片：`/Users/xu/code/github/dify/api/core/rag/splitter/`
- 检索器：`/Users/xu/code/github/dify/api/core/rag/retrieval/`
- Agent 实现：`/Users/xu/code/github/dify/api/core/agent/`
