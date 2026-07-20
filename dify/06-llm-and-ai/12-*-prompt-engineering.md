# 小验证：Prompt 基础 · Few-shot · CoT · ReAct

> 覆盖：
> - [07-prompt-basics](./08-prompt-basics.md)
> - [08-few-shot](./09-few-shot.md)
> - [09-cot](./10-cot.md)
> - [10-react](./11-react.md)
>
> 预计：30～50 分钟 · 本地练习

## 背景

指令结构、示例驱动与推理范式决定模型输出稳定性。本组先落地可切换的 prompt 文本，评估与模板引擎见下一组。

## 需求

1. 本地写一个分类任务的 **system + user** 基础 prompt（指令、上下文、输出格式三块齐全）。
2. 写 **2 套** few-shot 模板：无示例 vs 2 示例；对比「预期行为」说明（可无真实 LLM 调用）。
3. 为同一任务各写一版 **CoT**（要求分步）与 **ReAct** 风格骨架（Thought/Action/Observation 占位即可）。
4. `NOTES.md` 用表格或列表对比：基础 / few-shot / CoT / ReAct 各自适用 1 个场景。

## 提示

- 输出格式尽量约束为 JSON 字段，便于后续评估
- 不要把真实 API Key 写进文件
- ReAct 此处只练 prompt 结构，不必接真工具

## 验收标准

- [ ] 基础 prompt 含指令、上下文、输出格式
- [ ] few-shot 两套可切换（文件或函数参数）
- [ ] CoT 与 ReAct 骨架可区分
- [ ] NOTES 有适用场景对比

## 延伸（选做）

给 few-shot 增加「反例」样本，说明可能带来的偏差。
