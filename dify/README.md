# Dify 后端学习（learn-docs）

基于本地仓库 [`/Users/xu/code/github/dify`](file:///Users/xu/code/github/dify) 的后端学习材料。**不含前端 `web/` 精读。**

## 从这里开始

### 主路径（唯一推荐顺序）

→ **[`LEARNING-PLAN.md`](./LEARNING-PLAN.md)**（索引）  
→ 分册在 [`plan/`](./plan/)：先 [`00-guide`](./plan/00-guide.md)，再只开当前 Phase（如 [`phase-0-docker`](./plan/phase-0-docker.md)）

按 Phase 0 → 6 推进：Docker → Python 够用 + 地图 → 主链路竖切 → 贡献 → RAG → Workflow/Agent → 广覆盖。

- 有阶段**毕业门禁**；未毕业不进入下一 Phase  
- 文档是**点菜**，不是 01→11 通读  
- 进度勾选：[`plan/progress.md`](./plan/progress.md)  
- 通用后端会/不会：[`../CHECKLIST-understand.md`](../CHECKLIST-understand.md)（阶段末回填）

### 三层知识库

| 层 | 目录 | 何时用 |
|----|------|--------|
| 学科基础 | [`../_fundamentals/`](../_fundamentals/) | 机制卡壳时下钻 |
| 工程公共 | [`../_common/`](../_common/) | Docker / HTTP / 鉴权 / SQL / Redis… |
| 项目实战 | **本目录** | Python + Flask + Dify 源码向 |

归属与 Sighting：[`../_common/SIGHTING.md`](../_common/SIGHTING.md)。

---

## 目录角色（扩展库，服从主计划）

下列分类是**素材库**。是否阅读、读哪几篇，以 [`LEARNING-PLAN.md`](./LEARNING-PLAN.md) 的「必读 / 卡壳再读 / 延后」为准。

| 目录 | 内容 | 在主计划中的位置 |
|------|------|------------------|
| [`01-fundamentals/`](./01-fundamentals/) | Python 语言 | Phase 1 必读子集；后半多延后 |
| [`02-backend/`](./02-backend/) | Flask / 分层 / 多租户 | Phase 2.1、2.3 |
| [`03-database/`](./03-database/) | SQLAlchemy / 向量 | Phase 2.6、4 |
| [`04-cache-and-queue/`](./04-cache-and-queue/) | Redis / Celery | Phase 2.7、2.8 |
| [`05-auth-and-security/`](./05-auth-and-security/) | 鉴权与安全（Dify） | Phase 2.2、3+ |
| [`06-llm-and-ai/`](./06-llm-and-ai/) | LLM / 流式 / provider | Phase 2.4、2.5；provider 只跟 1 条 |
| [`07-rag-and-agent/`](./07-rag-and-agent/) | RAG / Agent / Workflow | Phase 4–5 |
| [`08-devops/`](./08-devops/) | Docker 等 | Phase 0 |
| [`09-testing/`](./09-testing/) | pytest | Phase 3 |
| [`10-observability/`](./10-observability/) | 日志等 | Phase 3、6 |
| [`11-engineering/`](./11-engineering/) | 协作 / PR | Phase 3、6 |

生成单篇时的模板：[`_template.md`](./_template.md)。

---

## 单篇约定（写新文档时）

- 知识点：`NN-<主题>.md`  
- 章节小验证：`NN-*-<主题>.md`（插在对应组后）  
- 结构见 [`_template.md`](./_template.md)；Sighting 见 [`../_common/SIGHTING.md`](../_common/SIGHTING.md)  
- **不要**在计划未要求时批量新增「全书覆盖」型目录  

### 生成文档 Prompt（精简）

```
按 /Users/xu/code/gomeen/learn-docs/dify/LEARNING-PLAN.md 当前 Phase 需要，
为「<知识点>」写一篇快扫文档到 dify/<分类>/，遵循 _template.md 与 Sighting。
只服务主计划竖切；不要写超长源码精读；练习放 NN-*-*.md。
```

### 生成 checkpoint Prompt（精简）

```
按 LEARNING-PLAN 当前切片，为「<小组>」写 NN-*-slug.md：
背景 / 可执行需求 / 提示 / 验收标准。优先改 dify 仓库小点或本地可跑脚本。禁止「请总结」。
```

---

## 上游参考

- 源码：`/Users/xu/code/github/dify`  
- API 协作约定：`/Users/xu/code/github/dify/api/AGENTS.md`  
- 官方文档：https://docs.dify.ai  
