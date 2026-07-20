# 小验证：代码规范 · docstring · SOLID

> 覆盖：
> - [01-pep8](./01-pep8.md)
> - [02-agents-md](./02-agents-md.md)
> - [03-docstring](./03-docstring.md)
> - [04-style-in-dify](./04-style-in-dify.md)
> - [05-solid](./05-solid.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

可读性与 SOLID 约束协作效率。验证：读 AGENTS.md，重构一段「坏味道」代码。

## 需求

1. 精读 `/Users/xu/code/github/dify/api/AGENTS.md`，摘 10 条与你日常相关的规则到 `NOTES.md`。
2. 本地（或仓库小范围）找一段过长函数，做一次提取函数/策略拆分，体现至少 1 条 SOLID（在注释标明）。
3. 为公开函数补 Google 或项目风格 docstring。
4. 对照 ruff/black 配置说明命名与导入排序要求。

## 提示

- `api/AGENTS.md`、`web/CLAUDE.md`（可选对照）
- 重构保持行为，最好带测试

## 验收标准

- [ ] 10 条规则摘录非空泛
- [ ] 重构 diff 可读，职责更清晰
- [ ] docstring 含参数/返回/异常（如适用）
- [ ] 风格与项目一致

## 延伸（选做）

用前/后圈复杂度或行数对比说明收益。
