# 11.18 dify 的文档体系分析

> 从 README、CONTRIBUTING、AGENTS.md / CLAUDE.md、专题 docs 和 inline docstrings 五个层级理解 dify 如何服务不同读者与工程任务。

## 🎯 学习目标

完成本文档后，你将能够：

- 识别 dify 仓库中不同文档类型的目标读者和职责
- 理解根 README、子项目 README 与专题指南之间的导航关系
- 说明 CONTRIBUTING 如何规范 Issue、Pull Request、测试和求助流程
- 区分 AGENTS.md / CLAUDE.md 的目录约束与 inline docstrings 的局部契约
- 分析 dify 文档体系在可发现性、可执行性和同步维护方面的设计
- 根据问题类型快速定位应阅读或更新的文档层级

## 📚 前置知识

- Markdown、Git 仓库和 Pull Request 基础
- 前后端项目的目录结构常识
- 建议先学习 [技术文档写作：README / ADR / Runbook](./15-tech-writing.md)
- 建议先学习 [API 文档：OpenAPI / Swagger](./16-api-doc.md)
- 建议先学习 [架构决策记录（ADR）](./17-adr.md)

## 🧭 核心概念

### 文档体系不是一个目录

大型仓库的知识不可能全部放在根 README 中。
有效文档体系通常按照读者、任务和作用域分层：

```text
项目外部与初访者
        ↓
根 README：定位、能力、快速开始、全局导航
        ↓
CONTRIBUTING：参与规则、PR 流程、求助入口
        ↓
api/web README：子系统搭建、运行、测试
        ↓
AGENTS.md / CLAUDE.md：目录级开发约束和架构边界
        ↓
docs/ 专题指南：测试、Lint、Overlay、API Schema 等工作流
        ↓
inline docstrings/comments：模块、类、函数和局部逻辑契约
```

这些文件不是简单的“由浅到深教材”，而是面向不同任务的入口。
同一开发者在安装、编码、评审和排障时会进入不同层级。

### 根 README：项目级门面

dify 根目录的 `README.md` 面向第一次接触项目的用户和潜在贡献者。
它承担以下职责：

- 解释 Dify 是什么以及核心能力
- 提供 Docker Compose 快速启动路径
- 导航到云服务、自托管和完整产品文档
- 介绍功能、部署选项与社区入口
- 提供多语言 README 导航

根 README 的关键价值是建立全局心智模型，而不是指导每个子系统的日常开发。
例如，前端依赖安装和后端测试命令分别委托给 `web/README.md` 与 `api/README.md`。
这遵循“入口保持聚焦，细节靠链接下钻”的原则。

### CONTRIBUTING：协作协议

`CONTRIBUTING.md` 把“可以运行项目”推进到“可以安全参与项目”。
它覆盖：

- 适合开始贡献的 Issue 入口
- 插件相关变更应提交到哪个仓库
- Bug Report 和 Feature Request 需要的信息
- Issue 优先级的基本解释
- Pull Request 的提交步骤
- 前后端搭建与测试指南入口
- 遇到问题时的求助渠道

这类文档是人与人之间的工程接口。
它降低维护者反复补问复现步骤、日志、测试和 Issue 关联的成本，也让贡献者提前知道验收标准。

### 子项目 README：本地运行入口

`api/README.md` 面向后端开发者，集中说明 `uv`、中间件、API、Worker、Celery Beat、测试与 Swagger 生成命令。
`web/README.md` 面向前端开发者，集中说明 workspace 依赖、环境变量、开发服务器、构建、Storybook、Lint 与 Test。

两者都接近开发 Runbook：命令准确性和执行顺序比概念介绍更重要。
根 README 说“如何使用 Dify”，子项目 README 说“如何开发 Dify 的某一部分”，从而避免全局入口被细节淹没。

### AGENTS.md / CLAUDE.md：可执行的目录级规范

这类文件主要面向代码贡献者和自动化编码 Agent。
它们不是一般产品文档，而是对目录内变更生效的工程规则。

根 `CLAUDE.md` 给出仓库全局约束，例如：

- 后端与前端的入口指南
- 后端命令通过 `uv run --project api` 执行
- 测试驱动、强类型和架构边界要求
- 用户可见前端字符串必须使用 i18n

`api/AGENTS.md` 再细化后端规则：

- 修改前必须阅读周边 docstrings 和 comments
- controller → service → core/domain 的分层
- Pydantic、SQLAlchemy、日志和异常约定
- 测试、Lint、类型检查命令
- API Schema 指南入口

`web/CLAUDE.md` 则聚焦前端：

- 测试和 Lint 指南
- i18n、生成 API Client 和 Overlay 规则
- UI primitive、SVG Icon 和 Design Token
- 本地、Jotai、feature store 和持久化状态的选择

这类文档的优势是**作用域明确且靠近代码**。
开发者进入 `api/` 或 `web/` 时能获取不同约束，不需要在一份超长全局规范中筛选。

### `docs/`：专题工作流与规则细化

专题文档适合承载篇幅较长、需要示例和维护细节的工程主题。
dify 的典型例子包括：

- `api/controllers/API_SCHEMA_GUIDE.md`：Flask-RESTX + Pydantic Schema 模式
- `web/docs/test.md`：Vitest 和 React Testing Library 的测试规范
- `web/docs/lint.md`：ESLint、TSSLint、Type Check 和 suppression 策略
- `web/docs/overlay.md`：Overlay primitive、可访问性与层级规则
- 根 `docs/` 下的多语言 README 与仓库级辅助内容

`CLAUDE.md` 适合写“必须遵守什么”，专题文档适合解释“如何做、为什么、如何验证”。
例如，`web/CLAUDE.md` 要求阅读测试文档，而 `web/docs/test.md` 进一步提供目录位置、查询优先级、Mock 和去抖动规则。

### Inline docstrings 和 comments：最接近实现的知识

仓库级文档无法描述每个模块的不变量、类生命周期和函数副作用。
这些信息应放在代码附近：

- 模块 docstring：目的、边界、关键不变量和陷阱
- 类 docstring：责任、生命周期、状态和并发假设
- 函数 docstring：参数、返回、异常和副作用
- 段落注释：非显然逻辑背后的权衡与历史约束

越局部、越容易随实现变化的信息，越应该靠近代码。
但注释不能只是翻译代码；`api/AGENTS.md` 明确要求 comments 解释“为什么”。

### 文档层级与单一事实来源

“单一事实来源”不意味着所有知识都放进一个文件，而是每类事实有权威所有者：

| 事实类型 | 推荐权威位置 |
| --- | --- |
| 项目定位和全局快速开始 | 根 `README.md` |
| 贡献与 PR 流程 | `CONTRIBUTING.md` |
| 子系统启动和常用命令 | `api/README.md`、`web/README.md` |
| 目录级编码约束 | `AGENTS.md`、`CLAUDE.md` |
| 专题工作流 | 对应 `docs/*.md` |
| API 契约 | Pydantic 模型和生成 OpenAPI |
| 局部不变量与副作用 | inline docstrings / comments |

其他文档应该链接权威位置，不要复制一份容易漂移的完整规则。
必要的简短摘要可以重复，但必须清楚指出哪里是 canonical guide。

## 💻 代码示例

### 用问题类型选择文档入口

下面的独立 Python 示例把常见工程问题映射到 dify 文档层级。
它体现的重点不是脚本本身，而是“按任务导航，而不是从根目录盲目搜索”。

**示例文件**：`examples/doc_router.py`  
**示例行号**：第 1-35 行

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentRoute:
    keyword: str
    path: str
    purpose: str


ROUTES = (
    DocumentRoute("install", "README.md", "项目定位与全局快速开始"),
    DocumentRoute("pull request", "CONTRIBUTING.md", "贡献与 PR 流程"),
    DocumentRoute("backend setup", "api/README.md", "后端环境与命令"),
    DocumentRoute("frontend setup", "web/README.md", "前端环境与命令"),
    DocumentRoute("api schema", "api/controllers/API_SCHEMA_GUIDE.md", "API 契约规则"),
    DocumentRoute("frontend test", "web/docs/test.md", "前端测试规范"),
    DocumentRoute("overlay", "web/docs/overlay.md", "Overlay 组件规则"),
)


def find_document(question: str) -> DocumentRoute | None:
    normalized = question.lower()
    for route in ROUTES:
        if route.keyword in normalized:
            return route
    return None


def main() -> None:
    question = "How should I verify an API schema change?"
    route = find_document(question)
    if route is None:
        print("Start from README.md and search the repository.")
        return
    print(f"Read {route.path}: {route.purpose}")


if __name__ == "__main__":
    main()
```

**说明**：

- `DocumentRoute` 把入口路径和职责绑定，避免“同一问题多个权威答案”
- 精确专题优先于宽泛入口，例如 API Schema 变化应直接进入专门指南
- 无法识别的问题回退到根 README 和仓库搜索，而不是随意猜测规则
- 真实团队可把类似映射做成贡献者导航页，但必须链接现有文档，不能复制其内容

## 🔍 dify 仓库源码解读

### CONTRIBUTING 中的 Pull Request 流程

**文件位置**：`/Users/xu/code/github/dify/CONTRIBUTING.md`  
**核心代码**（第 60-70 行）：

```markdown
| Valuable but not immediate | Future-Feature |

## Submitting your PR

### Pull Request Process

1. Fork the repository
1. Before you draft a PR, please create an issue to discuss the changes you want to make
1. Create a new branch for your changes
1. Please add tests for your changes accordingly
1. Ensure your code passes the existing tests
```

**解读**：

- 第 60 行承接前文 Feature Request 优先级，说明不是所有有价值建议都会立即实施
- 第 62-64 行建立清晰任务入口，读者可以快速扫描到 PR 流程
- 第 66-68 行要求先 Fork、先讨论 Issue、再创建分支，把共识建立放在实现成本之前
- 第 69-70 行把测试纳入提交定义，而不是交给维护者在评审后补充
- 该片段展示 CONTRIBUTING 的核心作用：把隐含协作习惯转成贡献者可以执行的检查表

### 前端目录级文档如何下钻

**文件位置**：`/Users/xu/code/github/dify/web/CLAUDE.md`  
**核心代码**（第 1-20 行）：

```markdown
## Frontend Workflow

- Refer to the `./docs/test.md` and `./docs/lint.md` for detailed frontend workflow instructions.
- For frontend coding tasks, also apply the repo-local `how-to-write-component` skill when the change touches React components, state ownership, routing, styling, or Tailwind classes.
- For frontend reviews, use the repo-local `frontend-code-review` skill as the canonical checklist.

## i18n

- User-facing strings must use `web/i18n/en-US/` keys instead of hardcoded text.
- When adding or renaming an i18n key, update all supported locale files with correct localized values. Do not leave fallback English in non-English locales unless the repo already intentionally does so for that exact key.

## Backend API Calls

- For new backend calls, and for surfaces already migrated to generated contracts, use `consoleQuery` / `consoleClient` from `@/service/client`. Do not add handwritten REST helpers, handwritten API types, mock-backed app state, or direct edits to generated contract files.

## Overlay Components (Mandatory)

- `../packages/dify-ui/README.md` is the permanent contract for overlay primitives, portals, root `isolation: isolate`, and the `z-50` / `z-60` layering.
- `./docs/overlay.md` records the current web overlay best practices.
- In new or modified code, use only overlay primitives from `@langgenius/dify-ui/*`.
```

**解读**：

- 第 3 行不复制测试和 Lint 全文，而是把读者导向更详细的专题指南
- 第 4-5 行把组件实现与评审连接到 canonical skill，减少检查标准分叉
- 第 7-10 行将 i18n 设为目录级硬约束，并明确所有 locale 都需同步
- 第 12-14 行规定后端 API 调用的统一入口，避免手写类型与生成契约漂移
- 第 16-20 行同时指出永久 contract、最佳实践文档和必须采用的组件来源
- 这体现“短规则 + 权威链接 + 明确禁令”的目录文档风格

## 🗂️ dify 文档层级总结

### 面向用户的发现层

**主要文件**：根 `README.md`、多语言 README、外部产品文档入口。  
**回答问题**：Dify 是什么？有哪些能力？如何最快运行？去哪里获得帮助？

这一层强调产品定位、可发现性和首次成功体验。
内容过于底层会干扰新用户，因此详细工程规范应下沉。

### 面向贡献者的协作层

**主要文件**：`CONTRIBUTING.md`、Pull Request Template。  
**回答问题**：怎样提出问题？怎样提交变更？需要提供哪些证据？

这一层统一协作预期，减少无效 Issue 和缺少测试、上下文的 PR。

### 面向子系统开发者的运行层

**主要文件**：`api/README.md`、`web/README.md`。  
**回答问题**：依赖什么？命令在哪运行？怎样启动、测试和构建？

这一层接近开发 Runbook，命令准确性和执行顺序最重要。

### 面向实现与评审的规范层

**主要文件**：根与目录级 `AGENTS.md` / `CLAUDE.md`。  
**回答问题**：修改这个目录时必须遵守哪些架构、类型、安全和流程约束？

这一层应简明、强约束，并链接详细 canonical guide。

### 面向专题任务的方法层

**主要文件**：`api/controllers/API_SCHEMA_GUIDE.md`、`web/docs/test.md`、`web/docs/lint.md`、`web/docs/overlay.md`。  
**回答问题**：如何正确完成某类工作？有哪些示例、陷阱和验证命令？

这一层允许更长解释，是团队工程实践沉淀的主要位置。

### 面向局部代码的契约层

**主要载体**：inline docstrings、paragraph/block comments。  
**回答问题**：此模块的边界是什么？函数有哪些副作用？为什么存在这段非显然逻辑？

这一层离代码最近，也最需要在重构时同步维护。

## ✅ 关键要点总结

- dify 的文档体系分布在 README、CONTRIBUTING、AGENTS.md / CLAUDE.md、专题 docs 和 inline docstrings 中
- 根 README 负责项目发现，子项目 README 负责本地开发入口
- CONTRIBUTING 将社区协作方式变成可执行流程
- AGENTS.md / CLAUDE.md 表达对特定目录生效的工程约束
- 专题 docs 展开测试、Lint、Overlay 和 API Schema 等复杂工作流
- docstrings 与 comments 保存最接近实现的不变量、副作用和“为什么”
- 好的分层不是消灭重复，而是明确权威来源并用链接建立导航

## 🧪 练习题

### 练习：基础（必做）

为下列问题选择最合适的首个文档入口，并解释原因：

- 第一次用 Docker 启动 Dify
- 为后端控制器增加响应 Schema
- 前端新增用户可见文案
- 提交 Bug Report
- 理解某函数为何会投递后台任务

可选入口包括根 README、CONTRIBUTING、api/README、web/CLAUDE、API_SCHEMA_GUIDE 和 inline docstring。

### 练习：进阶

绘制一张 dify 文档导航图，至少包含 10 个文件或目录节点。
对每条边标明“谁在什么任务下从这里进入下一份文档”，并找出两个可能发生内容漂移的位置。

### 练习：挑战（选做）

选择一个真实的 dify Pull Request 场景，例如“新增后端 API 并在前端调用”。
列出从开始到提交前必须阅读或检查的文档，并回答：

- 哪份文档是每类规则的 canonical source？
- 哪些局部 docstring 可能需要同步更新？
- 哪些内容可以通过测试或生成命令验证？
- 哪个重大选择可能需要 ADR，而不应只写在 PR 描述中？

## 📖 参考资料

- `/Users/xu/code/github/dify/README.md`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`
- `/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/xu/code/github/dify/CLAUDE.md`
- `/Users/xu/code/github/dify/api/README.md`
- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
- `/Users/xu/code/github/dify/web/README.md`
- `/Users/xu/code/github/dify/web/CLAUDE.md`
- `/Users/xu/code/github/dify/web/docs/test.md`
- `/Users/xu/code/github/dify/web/docs/lint.md`
- `/Users/xu/code/github/dify/web/docs/overlay.md`
- Write the Docs Documentation Guide：https://www.writethedocs.org/guide/
- Diátaxis Documentation Framework：https://diataxis.fr/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
