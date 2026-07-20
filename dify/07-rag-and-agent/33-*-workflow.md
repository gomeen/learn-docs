# 小验证：工作流引擎 · 节点 · 变量 · 控制流 · 执行

> 覆盖：
> - [24-workflow-engine](./28-workflow-engine.md)
> - [25-workflow-nodes](./29-workflow-nodes.md)
> - [26-workflow-variables](./30-workflow-variables.md)
> - [27-workflow-control-flow](./31-workflow-control-flow.md)
> - [28-workflow-execution](./32-workflow-execution.md)
>
> 预计：40～60 分钟 · 本地练习

## 背景

图执行与变量系统是工作流产品的底座。本组用极简本地执行器吃透顺序、分支与变量池；DSL/自定义节点与仓库对照见 [37-*-workflow-dsl-nodes](./37-*-workflow-dsl-nodes.md)。

## 需求

1. 本地实现极简图执行器：节点 dict + edges，支持 `start → llm_stub → end`。
2. 增加一个 `if` 分支节点（基于变量真值），覆盖 true/false 两条路径。
3. 变量池：`set/get` 全局变量；节点输出写入 `nodes.<id>.output`（或等价结构）。
4. 用断言证明：顺序执行结果与分支选择正确；`NOTES.md` 画 5 行 ASCII 或 mermaid 示意你的图。

## 提示

- DSL 可先用 JSON 而非 YAML
- `llm_stub` 可返回固定字符串
- 状态机不必完整，跑通即可

## 验收标准

- [ ] 本地图执行覆盖顺序与分支
- [ ] 变量读写有断言
- [ ] NOTES 有图结构示意
- [ ] 代码可重复运行

## 延伸（选做）

支持简单 loop 节点（最大次数守卫）。
