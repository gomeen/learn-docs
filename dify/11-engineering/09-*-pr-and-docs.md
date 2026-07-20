# 小验证：PR 规范与文档体系

> 覆盖：
> - [06-pr-in-dify](./07-pr-in-dify.md)
> - [07-doc-in-dify](./08-doc-in-dify.md)
>
> 预计：40～60 分钟 · 本地练习或改 dify 仓库

## 背景

PR 模板与文档层级决定审查成本。验证：按模板写一份「假想改动」PR 描述，并梳理文档入口。

## 需求

1. 阅读 `.github/PULL_REQUEST_TEMPLATE.md`，用它写一份针对「假想 bugfix」的完整 PR 描述（本地 `PR_DRAFT.md`）。
2. 列出 dify 文档入口（根 README、api AGENTS、deploy docs 等）与各自读者。
3. 给 `learn-docs` 或仓库某 README 提一处**真实**的文字改进（断链、过时命令、歧义句）——若暂不提 PR，也要给出 diff。

## 提示

- `.github/PULL_REQUEST_TEMPLATE.md`
- `CONTRIBUTING.md`
- 文档改动要可验证

## 验收标准

- [ ] PR 草稿覆盖模板全部必填段
- [ ] 文档地图 ≥4 个入口
- [ ] 有一处具体文字/链接修正提案
- [ ] 语气温和、可执行

## 延伸（选做）

补一份 ADR 骨架描述该假想技术决策。
