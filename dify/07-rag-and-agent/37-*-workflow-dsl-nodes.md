# 小验证：工作流 DSL、自定义节点与 dify 执行器

> 覆盖：
> - [29-workflow-dsl](./34-workflow-dsl.md)
> - [30-custom-nodes](./35-custom-nodes.md)
> - [31-workflow-in-dify](./36-workflow-in-dify.md)
>
> 预计：30～50 分钟 · 读仓库 + 可选改动

## 背景

DSL 与节点类型注册把「画布上的图」变成可执行程序。本组对照仓库入口，理解真实节点基类与校验错误如何暴露。

## 需求

1. 阅读 `api/core/workflow/` 与 `graph_engine`，`NOTES.md` 记录：真实节点基类、执行入口、DSL/图加载相关路径（≥3 条路径）。
2. 对照本地 JSON 图（可用 33-*-workflow 的图）与仓库 DSL 字段：列一张「我的字段 → 仓库概念」映射（≥4 行）。
3. （改仓库选做，其一即可）为某节点的校验错误信息补充更明确的字段路径；或增加单元测试覆盖一个条件分支。
4. 用 3～5 行说明：自定义节点至少要实现哪些契约（run/validate 等，以仓库为准）。

## 提示

- `api/core/workflow/nodes/`、`graph_engine/`
- 先搜 `Node` 基类与 `GraphEngine` / 执行器命名
- 选做改动保持默认工作流行为

## 验收标准

- [ ] NOTES 入口路径正确
- [ ] 字段映射表 ≥4 行
- [ ] 自定义节点契约说明清楚
- [ ] 选做改动不破坏默认工作流（若未做选做，注明「仅阅读」）

## 延伸（选做）

导出一份最小 YAML DSL 示例，与 JSON 版对照。
