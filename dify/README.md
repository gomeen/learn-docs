# Dify 全栈后端学习路径

本目录是基于 [dify](https://github.com/langgenius/dify) 仓库的全栈后端学习索引。**不含前端知识**。

## 🎯 使用方式

每个知识点对应一份待生成的学习文档，文件命名格式：`./<序号>-<主题>.md`。

### 让 AI 生成学习文档的 Prompt 模板

```
根据 /Users/xu/code/gomeen/learn-docs/dify/<分类>/README.md 中的目录，
请为「<知识点名称>」生成学习文档，
保存到 /Users/xu/code/gomeen/learn-docs/dify/<分类>/<序号>-<主题>.md

要求：
1. 理论讲解（概念、原理、适用场景、与同类方案对比）
2. 代码示例（Python 为主，必要时附 TypeScript/SQL/Shell）
3. 结合 dify 仓库实际代码（/Users/xu/code/github/dify）
4. 列出参考代码文件和行号
5. 2-3 个练习题
```

## 📚 知识分类总览

| 分类 | 主题 | 目录 |
|------|------|------|
| **01** | 编程语言与基础工具 | [`01-fundamentals/`](./01-fundamentals/) |
| **02** | 后端架构与框架 | [`02-backend/`](./02-backend/) |
| **03** | 数据库与 ORM | [`03-database/`](./03-database/) |
| **04** | 缓存与消息队列 | [`04-cache-and-queue/`](./04-cache-and-queue/) |
| **05** | 认证与安全 | [`05-auth-and-security/`](./05-auth-and-security/) |
| **06** | LLM 应用开发 | [`06-llm-and-ai/`](./06-llm-and-ai/) |
| **07** | RAG 与 Agent | [`07-rag-and-agent/`](./07-rag-and-agent/) |
| **08** | DevOps 与部署 | [`08-devops/`](./08-devops/) |
| **09** | 测试与质量保障 | [`09-testing/`](./09-testing/) |
| **10** | 可观测性 | [`10-observability/`](./10-observability/) |
| **11** | 工程实践与协作 | [`11-engineering/`](./11-engineering/) |

## 📖 推荐学习顺序

> 编号顺序 ≠ 严格学习顺序。同一分类内的知识通常有依赖，跨分类可并行。

```
01-fundamentals（基础） 
    ↓
02-backend（架构） + 03-database（数据库）
    ↓
04-cache-and-queue（缓存队列） + 05-auth-and-security（安全）
    ↓
06-llm-and-ai（LLM 基础）
    ↓
07-rag-and-agent（RAG 与 Agent）
    ↓
08-devops（部署） + 09-testing（测试） + 10-observability（监控）
    ↓
11-engineering（工程实践贯穿始终）
```

## 🔗 参考资源

- dify 仓库：`/Users/xu/code/github/dify`
- dify 官方文档：https://docs.dify.ai
- 后端架构指南：`/Users/xu/code/github/dify/api/AGENTS.md`
