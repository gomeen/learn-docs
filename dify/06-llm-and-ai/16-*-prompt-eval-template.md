# 小验证：Prompt 评估、模板与 dify 解析

> 覆盖：
> - [11-prompt-evaluation](./13-prompt-evaluation.md)
> - [12-prompt-template](./14-prompt-template.md)
> - [13-prompt-in-dify](./15-prompt-in-dify.md)
>
> 预计：30～50 分钟 · 本地练习或改 dify 仓库

## 背景

模板变量与评估方法把「写得好的 prompt」变成可维护资产。对照 dify 解析器，避免自己造一套不兼容占位符。

## 需求

1. 本地实现 `render(template: str, vars: dict) -> str`，支持 `{{name}}`；未定义变量策略（保留/报错）可配置。
2. 设计 **3 条** 迷你评估用例（输入变量 → 期望子串或结构）；对同一模板跑「通过/失败」断言（可无 LLM）。
3. 阅读 dify `PromptTemplateParser` 或 `api/core/llm_generator/prompts.py`（以实际路径为准），`NOTES.md` 记录特殊占位符与截断策略（≥2 条）。
4. （可选）为某内置 prompt 字符串做一次不影响语义的可读性整理（拆多行），能跑相关测试更好。

## 提示

- `api/core/prompt/`、`api/core/llm_generator/`
- 注意不要把密钥写进模板
- 评估用例要可自动判定，避免纯主观「感觉更好」

## 验收标准

- [ ] 模板渲染对缺失变量行为明确
- [ ] ≥3 条评估用例可运行
- [ ] 对照仓库写出 ≥2 条实现差异/要点
- [ ] 可选改动无行为破坏

## 延伸（选做）

给 render 增加格式过滤器，如 `{{name|upper}}`。
