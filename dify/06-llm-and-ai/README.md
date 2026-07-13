# 06 - LLM 应用开发

> Dify 的核心是 LLM 应用平台，理解模型、Prompt、Tool Use 是构建 AI 应用的基础。

## 前置依赖

- `01-fundamentals` 全部
- HTTP 协议基础

## 模块 6.1 LLM 基础概念

- [ ] [1.1 主流大模型对比：Claude / GPT / Gemini / 开源模型](./01-llm-overview.md)
- [ ] [1.2 Transformer 架构概述](./02-transformer.md)
- [ ] [1.3 Token、上下文窗口与计费](./03-tokens-context.md)
- [ ] [1.4 模型参数：temperature / top_p / top_k / max_tokens](./04-model-parameters.md)
- [ ] [1.5 模型能力边界与幻觉问题](./05-llm-limitations.md)
- [ ] [1.6 Embedding 模型原理与选型](./06-embedding-models.md)

## 模块 6.2 Prompt 工程

- [ ] [2.1 Prompt 基础：指令、上下文、输出格式](./07-prompt-basics.md)
- [ ] [2.2 Few-shot Prompting：示例驱动](./08-few-shot.md)
- [ ] [2.3 Chain-of-Thought（CoT）：思维链](./09-cot.md)
- [ ] [2.4 ReAct：推理 + 行动](./10-react.md)
- [ ] [2.5 Prompt 调优与评估方法](./11-prompt-evaluation.md)
- [ ] [2.6 Prompt 模板与变量替换](./12-prompt-template.md)
- [ ] [2.7 dify 的 Prompt 模板系统分析](./13-prompt-in-dify.md)

## 模块 6.3 Function Calling / Tool Use

- [ ] [3.1 Function Calling 原理与调用流程](./14-function-calling.md)
- [ ] [3.2 工具定义：JSON Schema 规范](./15-tool-schema.md)
- [ ] [3.3 多工具编排与路由](./16-multi-tool-routing.md)
- [ ] [3.4 错误处理：工具调用失败与重试](./17-tool-error-handling.md)
- [ ] [3.5 并行工具调用](./18-parallel-tool-calls.md)
- [ ] [3.6 dify 的工具系统：Tool / ToolProvider](./19-tools-in-dify.md)

## 模块 6.4 MCP（Model Context Protocol）

- [ ] [4.1 MCP 协议概述与架构](./20-mcp-overview.md)
- [ ] [4.2 MCP Server 开发（Python）](./21-mcp-server.md)
- [ ] [4.3 MCP Client 集成](./22-mcp-client.md)
- [ ] [4.4 MCP 与传统 Function Calling 的对比](./23-mcp-vs-function-calling.md)
- [ ] [4.5 dify 与 MCP 的集成](./24-mcp-in-dify.md)

## 模块 6.5 LLM API 实战

- [ ] [5.1 Anthropic Claude API 使用（Messages API）](./25-anthropic-api.md)
- [ ] [5.2 OpenAI API 使用](./26-openai-api.md)
- [ ] [5.3 流式输出：SSE 协议实现](./27-streaming-sse.md)
- [ ] [5.4 dify 的模型适配层：`model_runtime`](./28-model-runtime.md)
- [ ] [5.5 dify 的供应商系统：ModelProvider 抽象](./29-model-provider.md)

## 模块 6.6 成本与性能优化

- [ ] [6.1 Token 用量统计与计费](./30-token-tracking.md)
- [ ] [6.2 Prompt Caching（提示词缓存）](./31-prompt-caching.md)
- [ ] [6.3 模型路由与降级策略](./32-model-routing.md)
- [ ] [6.4 限流、配额管理与用户余额](./33-rate-limit-quota.md)
- [ ] [6.5 dify 的账单系统分析](./34-billing-in-dify.md)

## 🎯 dify 仓库对应位置

- 模型运行时：`/Users/xu/code/github/dify/api/core/model_runtime/`
- 模型供应商：`/Users/xu/code/github/dify/api/core/model_runtime/model_providers/`
- 工具系统：`/Users/xu/code/github/dify/api/core/tools/`
- Prompt 模板：`/Users/xu/code/github/dify/api/core/prompt_template.py`
- LLM 调用：`/Users/xu/code/github/dify/api/core/llm_generator/`
- 计费服务：`/Users/xu/code/github/dify/api/services/billing_service.py`
