# 11 - 工程实践与协作

> 工程能力的最后一公里：代码规范、文档、Code Review、开源协作。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定 |
|------|----------|------------|
| 命名 / 重构 / CR / 文档 / 估时等 | [`_common/20-engineering`](../../_common/20-engineering/) | PEP8、docstring、`*-in-dify` |
| SOLID 理论 | [`_fundamentals/06-design-patterns/24-solid`](../../_fundamentals/06-design-patterns/24-solid.md) | `05-solid.md`（Python 示例） |

## 前置依赖

- 所有其他分类（贯穿全程）

## 模块 11.1 代码规范

- [ ] [1.1 PEP 8 与 Python 代码风格](./01-pep8.md)
- [ ] [1.2 项目级代码规范：`AGENTS.md` 模式](./02-agents-md.md)
- [ ] [1.3 命名规范：变量、函数、类、模块](../../_common/20-engineering/01-naming.md)
- [ ] [1.4 注释与文档字符串：何时写、写什么](./03-docstring.md)
- [ ] [1.5 dify 的代码规范分析（API + Web）](./04-style-in-dify.md)

## 模块 11.2 重构与设计

- [ ] [2.1 重构基础：Red-Green-Refactor](../../_common/20-engineering/02-refactor-basics.md)
- [ ] [2.2 识别代码坏味道](../../_common/20-engineering/03-code-smells.md)
- [ ] [2.3 SOLID 原则](./05-solid.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [06-*-style-and-solid: 代码规范 · docstring · SOLID](./06-*-style-and-solid.md)
  - 覆盖：01-pep8.md, 02-agents-md.md, 03-docstring.md, 04-style-in-dify.md, 05-solid.md


- [ ] [2.4 DRY / KISS / YAGNI](../../_common/20-engineering/04-dry-kiss-yagni.md)
- [ ] [2.5 模块化与包设计](../../_common/20-engineering/05-modular-design.md)

## 模块 11.3 Code Review

- [ ] [3.1 Code Review 的价值与流程](../../_common/20-engineering/06-code-review.md)
- [ ] [3.2 Reviewer 检查清单：功能 / 设计 / 风格](../../_common/20-engineering/07-review-checklist.md)
- [ ] [3.3 提 PR 的最佳实践](../../_common/20-engineering/08-pr-best-practices.md)
- [ ] [3.4 dify 的 PR 规范（`.github/PULL_REQUEST_TEMPLATE.md`）](./07-pr-in-dify.md)

## 模块 11.4 文档与知识管理

- [ ] [4.1 技术文档写作：README / ADR / Runbook](../../_common/20-engineering/09-tech-writing.md)
- [ ] [4.2 API 文档：OpenAPI / Swagger](../../_common/20-engineering/10-api-doc.md)
- [ ] [4.3 架构决策记录（ADR）](../../_common/20-engineering/11-adr.md)
- [ ] [4.4 dify 的文档体系分析](./08-doc-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [09-*-pr-and-docs: PR 规范与文档体系](./09-*-pr-and-docs.md)
  - 覆盖：07-pr-in-dify.md, 08-doc-in-dify.md


## 模块 11.5 开源协作

- [x] [5.1 Issue 管理：标签、模板、优先级](../../_common/20-engineering/12-issue-management.md)
- [x] [5.2 Contributing 指南编写](./10-contributing.md)
- [x] [5.3 发布流程：语义化版本与 Changelog](../../_common/20-engineering/13-release-process.md)
- [x] [5.4 社区互动：Discord / Discussions](./11-community.md)
- [x] [5.5 dify 的开源协作模式分析](./12-oss-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [13-*-oss-collaboration: Contributing · 社区 · 开源协作模式](./13-*-oss-collaboration.md)
  - 覆盖：10-contributing.md, 11-community.md, 12-oss-in-dify.md


## 模块 11.6 软技能

- [ ] [6.1 估时与排期：避免过度乐观](../../_common/20-engineering/14-estimation.md)
- [ ] [6.2 技术债务管理](../../_common/20-engineering/15-tech-debt.md)
- [ ] [6.3 知识分享：内部 Tech Talk](../../_common/20-engineering/16-tech-talk.md)
- [ ] [6.4 跨团队协作与沟通](../../_common/20-engineering/17-collaboration.md)

## 🎯 dify 仓库对应位置

- 后端规范：`/Users/xu/code/github/dify/api/AGENTS.md`
- 前端规范：`/Users/xu/code/github/dify/web/CLAUDE.md`
- 总贡献指南：`/Users/xu/code/github/dify/CONTRIBUTING.md`
- PR 模板：`/Users/xu/code/github/dify/.github/PULL_REQUEST_TEMPLATE.md`
- Issue 模板：`/Users/xu/code/github/dify/.github/ISSUE_TEMPLATE/`
- Changelog：`/Users/xu/code/github/dify/CHANGELOG.md`（如有）
