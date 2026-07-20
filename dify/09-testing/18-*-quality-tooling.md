# 小验证：Lint · 类型检查 · pre-commit · dify 质量三件套

> 覆盖：
> - [12-lint-tools](./14-lint-tools.md)
> - [13-type-check](./15-type-check.md)
> - [14-pre-commit](./16-pre-commit.md)
> - [15-quality-in-dify](./17-quality-in-dify.md)
>
> 预计：40～70 分钟 · 本地练习或改 dify 仓库

## 背景

Ruff/mypy/pre-commit 是合并门槛。验证：在仓库跑通（或读通）质量命令，并修一处真实小问题。

## 需求

1. 从 `api/pyproject.toml` / Makefile / pre-commit 配置提取「提交前应跑命令」列表到 `NOTES.md`。
2. 本地对你改过的文件跑 ruff/format（若环境允许）；修 1 个真实 lint/typing 问题，或在自建小文件演示 ignore 与修复的差别。
3. 说明 CI 中质量 job 失败时的优先排查顺序。

## 提示

- `api/pyproject.toml`、`.pre-commit-config.yaml`
- 不要全局 `noqa` 压制

## 验收标准

- [ ] 命令列表与仓库一致
- [ ] 有一次成功的 lint/type 修复或可复现演示
- [ ] 排查顺序 ≥3 步
- [ ] 未关闭关键检查来「混过」

## 延伸（选做）

为新目录建议 mypy 渐进策略（strict 白名单）。
