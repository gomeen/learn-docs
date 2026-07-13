# 07 - RAG 与 Agent

> Dify 的核心差异化能力：RAG 知识库 + Agent 工作流编排。

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

## 模块 7.2 检索优化

- [ ] [2.1 相似度检索：余弦 / 欧氏 / 点积](./07-similarity-search.md)
- [ ] [2.2 混合检索：BM25 + 向量检索](./08-hybrid-search.md)
- [ ] [2.3 重排序（Rerank）模型](./09-rerank.md)
- [ ] [2.4 查询改写与 HyDE](./10-query-rewriting.md)
- [ ] [2.5 元数据过滤与多条件检索](./11-metadata-filter.md)
- [ ] [2.6 dify 的检索管道（Retrieval Pipeline）](./12-retrieval-pipeline.md)

## 模块 7.3 RAG 工程实践

- [ ] [3.1 RAG 评估体系：召回率 / 准确率 / 人工评估](./13-rag-evaluation.md)
- [ ] [3.2 上下文窗口管理与截断](./14-context-management.md)
- [ ] [3.3 多模态 RAG：图片、表格、音频](./15-multimodal-rag.md)
- [ ] [3.4 RAG 的常见失败模式与对策](./16-rag-failure-modes.md)
- [ ] [3.5 dify 的 RAG 实现源码分析](./17-rag-in-dify.md)

## 模块 7.4 Agent 基础

- [ ] [4.1 Agent 概念：感知-决策-行动循环](./18-agent-concepts.md)
- [ ] [4.2 ReAct 模式深入](./19-react-deep-dive.md)
- [ ] [4.3 Plan-and-Execute 模式](./20-plan-execute.md)
- [ ] [4.4 Reflection 自我反思](./21-reflection.md)
- [ ] [4.5 Toolformer / ReWOO 等前沿模式](./22-advanced-agent.md)
- [ ] [4.6 dify 的 Agent 节点实现](./23-agent-in-dify.md)

## 模块 7.5 工作流编排（Dify 核心）

- [ ] [5.1 工作流引擎原理：节点 + 边 + 状态机](./24-workflow-engine.md)
- [ ] [5.2 节点类型：开始 / 结束 / LLM / 工具 / 条件 / 循环](./25-workflow-nodes.md)
- [ ] [5.3 变量系统：全局 / 会话 / 节点变量](./26-workflow-variables.md)
- [ ] [5.4 条件分支、循环、并行](./27-workflow-control-flow.md)
- [ ] [5.5 工作流的执行与状态管理](./28-workflow-execution.md)
- [ ] [5.6 工作流 DSL 规范（YAML 格式）](./29-workflow-dsl.md)
- [ ] [5.7 自定义节点开发](./30-custom-nodes.md)
- [ ] [5.8 dify 工作流执行器源码分析](./31-workflow-in-dify.md)

## 模块 7.6 多 Agent 协作

- [ ] [6.1 多 Agent 架构：Supervisor / Swarm / Hierarchical](./32-multi-agent.md)
- [ ] [6.2 Agent 间通信协议](./33-agent-communication.md)
- [ ] [6.3 任务分发与负载均衡](./34-task-distribution.md)
- [ ] [6.4 dify 的 Chatflow vs Workflow 对比](./35-chatflow-vs-workflow.md)

## 🎯 dify 仓库对应位置

- 工作流引擎：`/Users/xu/code/github/dify/api/core/workflow/`
- 工作流节点：`/Users/xu/code/github/dify/api/core/workflow/nodes/`
- 工作流执行：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
- RAG 核心：`/Users/xu/code/github/dify/api/core/rag/`
- 文档提取：`/Users/xu/code/github/dify/api/core/rag/extractor/`
- 文档切片：`/Users/xu/code/github/dify/api/core/rag/splitter/`
- 检索器：`/Users/xu/code/github/dify/api/core/rag/retrieval/`
- Agent 实现：`/Users/xu/code/github/dify/api/core/agent/`
