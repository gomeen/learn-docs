# 11.02 项目级代码规范：`AGENTS.md` 模式

> 理解 `AGENTS.md` / `CLAUDE.md` 是给 AI Agent 看的项目级指南，以及如何写好它。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释 `AGENTS.md` 和 `CLAUDE.md` 的诞生背景和目标受众
- 区分"给人看的 README"和"给 Agent 看的 AGENTS.md"
- 列出 `AGENTS.md` 应该包含的核心章节
- 阅读并理解 dify 的 `api/AGENTS.md` 和 `web/CLAUDE.md`
- 为自己的项目起草一份 `AGENTS.md`

## 📚 前置知识

- 已完成 [01-pep8.md](./01-pep8.md)
- 基本的 Markdown 文档写作能力
- 了解大模型 / AI Agent 的基本工作原理

## 1. 核心概念

### 1.1 为什么需要 `AGENTS.md`

`AGENTS.md` 是一种**约定俗成**的文件名，专门给 AI Agent（Claude Code、Cursor、Aider 等）阅读的项目级上下文文件。它由 Anthropic、Cursor、Zed 等工具链在 2024 年下半年共同推广：

- `README.md` 写给**人**——介绍项目是什么、怎么用
- `AGENTS.md` 写给**Agent**——告诉 Agent 怎么修改、怎么测试、什么不能动

一个真实的痛点：当你让 AI 帮你重构代码，它默认会用 `print()` 调试、用 `requests.get()` 做 HTTP 调用、忽视项目既有的命名约定。
`AGENTS.md` 就是用来约束这些行为的。

### 1.2 `AGENTS.md` vs `CLAUDE.md`

两者本质相同——都是给 AI 的项目上下文，区别只在生态：

| 文件 | 生态 | 谁会读 |
|---|---|---|
| `AGENTS.md` | 通用 / 中性 | 所有支持该约定的 Agent（Cursor、Aider、Continue.dev、Claude Code 等） |
| `CLAUDE.md` | Claude 专属 | Anthropic 的 Claude Code CLI |

dify 同时使用两者：
- `/Users/xu/code/github/dify/api/AGENTS.md` —— 后端规范（通用）
- `/Users/xu/code/github/dify/web/CLAUDE.md` —— 前端规范（Claude 专属）

### 1.3 `AGENTS.md` 应该包含什么

一个合格的 `AGENTS.md` 应覆盖：

1. **范围与边界**（Where can the agent work?）：哪些目录可以改、哪些不能动
2. **必读章节**（Must-check sections）：调用某类功能前必须看的文档/模块注释
3. **代码风格**（Coding style）：命名、缩进、类型注解、注释规范
4. **架构约束**（Architecture boundaries）：分层（controller → service → core）、tenant awareness
5. **测试规范**（Testing rules）：如何跑测试、用什么框架、覆盖要求
6. **反模式**（Anti-patterns）：明确禁止的做法
7. **工具链命令**（Tooling commands）：lint / format / type-check / test 的具体命令

## 2. 代码示例

### 2.1 一个最小可用的 `AGENTS.md`

```markdown
# AGENTS.md —— 项目级 Agent 指南

## 工作范围
- 可修改：`src/`、`tests/`、`docs/`
- 不可修改：`vendor/`、`migrations/`、`*.lock`

## 必读
- 修改 `src/api/` 前必须读 `docs/api-contract.md`
- 修改数据库 schema 前必须读 `docs/db-conventions.md`

## 代码风格
- Python 3.11+，所有函数必须有类型注解
- 使用 Ruff 做 lint 和 format
- 行宽上限 100 字符

## 架构
- 分层：controllers → services → repositories → models
- 跨层调用必须通过依赖注入容器

## 测试
- 使用 pytest
- 每个新功能必须配一个测试文件
- 跑测试命令：`uv run --project . pytest`

## 禁止
- 不要直接调用 `subprocess`，统一通过 `libs/process.py`
- 不要在 commit message 中包含密钥
```

### 2.2 反例：哪些内容不要放进 `AGENTS.md`

```markdown
# ❌ 反例 1：把营销内容写进 AGENTS.md

## 项目介绍
Dify 是一个非常棒的开源 LLM 平台，由 langgenius 公司开发，
拥有 50k+ GitHub Stars，已经服务了上百万用户……

# 这样的内容应该写在 README.md 里
```

```markdown
# ❌ 反例 2：内容过细导致维护成本爆炸

## 命名
### 变量名
- 布尔变量必须以 is_、has_、can_ 开头
- 计数器变量必须以 _count 结尾
- 长度超过 30 字符的变量名禁止使用
...
# 一旦改一个规则，所有引用都得改
```

### 3.1 后端 `api/AGENTS.md`：Notes for Agent（节选）

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`

```markdown
## Notes for Agent (must-check)

Before changing any backend code under `api/`, you MUST read the surrounding docstrings and comments. These notes contain required context (invariants, edge cases, trade-offs) and are treated as part of the spec.

Look for:

- The module (file) docstring at the top of a source code file
- Docstrings on classes and functions/methods
- Paragraph/block comments for non-obvious logic

### What to write where

- Keep notes scoped: module notes cover module-wide context, class notes cover class-wide context, function/method notes cover behavioural contracts, and paragraph/block comments cover local "why". Avoid duplicating the same content across scopes unless repetition prevents misuse.
- **Module (file) docstring**: purpose, boundaries, key invariants, and "gotchas" that a new reader must know before editing.
  - Include cross-links to the key collaborators (modules/services) when discovery is otherwise hard.
  - Prefer stable facts (invariants, contracts) over ephemeral "today we…" notes.
- **Class docstring**: responsibility, lifecycle, invariants, and how it should be used (or not used).
  - If the class is intentionally stateful, note what state exists and what methods mutate it.
  - If concurrency/async assumptions matter, state them explicitly.
- **Function/method docstring**: behavioural contract.
  - Document arguments, return shape, side effects (DB writes, external I/O, task dispatch), and raised domain exceptions.
  - Add examples only when they prevent misuse.
- **Paragraph/block comments**: explain *why* (trade-offs, historical constraints, surprising edge cases), not what the code already states.
  - Keep comments adjacent to the logic they justify; delete or rewrite comments that no longer match reality.

### Rules (must follow)

In this section, "notes" means module/class/function docstrings plus any relevant paragraph/block comments.

- **Before working**
  - Read the notes in the area you'll touch; treat them as part of the spec.
  - If a docstring or comment conflicts with the current code, treat the **code as the single source of truth** and update the docstring or comment to match reality.
  - If important intent/invariants/edge cases are missing, add them in the closest docstring or comment (module for overall scope, function for behaviour).
- **During working**
  - Keep the notes in sync as you discover constraints, make decisions, or change approach.
  - If you move/rename responsibilities across modules/classes, update the affected docstrings and comments so readers can still find the "why" and the invariants.
  - Record non-obvious edge cases, trade-offs, and the test/verification plan in the nearest docstring or comment that will stay correct.
  - Keep the notes **coherent**: integrate new findings into the relevant docstrings and comments; avoid append-only "recent fix" / changelog-style additions.
- **When finishing**
  - Update the notes to reflect what changed, why, and any new edge cases/tests.
  - Remove or rewrite any comments that could be mistaken as current guidance but no longer apply.
  - Keep docstrings and comments concise and accurate; they are meant to prevent repeated rediscovery.
```

**解读**：
- 第 1 行：文件以 `# API Agent Guide` 开头，明确告诉 Agent 这是 API 目录的指南
- 第 5 行：**"You MUST read the surrounding docstrings and comments"** —— 这是关键约束。dify 把模块内 docstring 视为"规范的延伸"
- 第 8-10 行：列举 Agent 必须找的内容：模块 docstring、类 docstring、函数 docstring、段落注释
- 第 13 行：**"Keep notes scoped"** —— 文档应该分层级，不重复
- 第 15-18 行：定义**模块 docstring** 的内容：purpose、boundaries、invariants、gotchas
- 第 19-22 行：定义**类 docstring** 的内容：responsibility、lifecycle、invariants、状态
- 第 24-26 行：定义**函数 docstring** 的内容：behavioural contract（参数、返回、副作用、异常）
- 第 28-30 行：**Paragraph/block comments** 必须解释 *why*（trade-off、历史约束、反直觉边界），紧贴代码；不再适用的注释要删除或重写
- 第 35-37 行 **Before working**：注释和代码冲突时**以代码为单一真源**，并更新注释
- 第 40 行：发现新约束/决策时**立即**记到最近 docstring，不能事后补
- 第 41 行 **"Keep the notes coherent"**：禁止把注释当 changelog 用——这是 Git log 干的事

### 3.2 前端 `CLAUDE.md`：硬约束优于软建议

**文件位置**：`/Users/xu/code/github/dify/web/CLAUDE.md`
**核心代码**（行 15-23）：

```markdown
## Overlay Components (Mandatory)

- `../packages/dify-ui/README.md` is the permanent contract for overlay primitives, portals, root `isolation: isolate`, and the `z-50` / `z-60` layering.
- `./docs/overlay.md` records the current web overlay best practices.
- In new or modified code, use only overlay primitives from `@langgenius/dify-ui/*`.
- Do not introduce overlay imports from `@/app/components/base/*`; when touching existing callers, migrate them.
```

**解读**：
- 第 17 行：**"Mandatory"** —— 用强语义词标识硬约束，比"建议"、"prefer"更明确
- 第 18 行：指向**永久契约**文件 `packages/dify-ui/README.md`，告诉 Agent 调 overlay 组件前必读
- 第 21 行：**"Do not introduce..."** —— 明确禁止，避免 Agent 自动引入旧组件路径
- 第 22 行：**"when touching existing callers, migrate them"** —— 不仅禁止新增，还要求迁移存量，体现渐进式重构思想
- 整个段落非常短，但每条都是**可执行的硬约束**，没有模糊空间

## 3. 关键要点总结

- `AGENTS.md` 写给 AI Agent，`README.md` 写给人——目标受众不同
- `AGENTS.md` 的黄金结构：**范围 / 必读 / 风格 / 架构 / 测试 / 反模式 / 工具链命令**
- 用**强语义词**（Mandatory、MUST、Do not）而非"建议"——给 Agent 明确的边界
- dify 的 `api/AGENTS.md` 是行业最佳实践范本：分层注释规范（模块 / 类 / 函数 / 段落）、架构边界（controller → service → core）
- 写完 `AGENTS.md` 后，**实际跑一次 Agent 看会不会违反规则**——这是检验 AGENTS.md 是否真的有效的唯一方法

---

**文档版本**：v1.0
**最后更新**：2026-07-13
