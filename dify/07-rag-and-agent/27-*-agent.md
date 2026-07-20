# 小验证：Agent 模式与 dify Agent 节点

> 覆盖：
> - [18-agent-concepts](./21-agent-concepts.md)
> - [19-react-deep-dive](./22-react-deep-dive.md)
> - [20-plan-execute](./23-plan-execute.md)
> - [21-reflection](./24-reflection.md)
> - [22-advanced-agent](./25-advanced-agent.md)
> - [23-agent-in-dify](./26-agent-in-dify.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

Agent 是「推理 + 工具」循环。验证：实现最小 ReAct 循环，并定位 dify Agent 节点。

## 需求

1. 本地 `react_agent.py`：伪 LLM（规则或脚本化决策）+ 2 工具，最大步数 N，防止死循环。
2. 解析「Thought/Action/Action Input/Observation」文本协议（可简化 JSON）。
3. 阅读 `api/core/agent/` 或 workflow agent 节点，`NOTES.md` 说明停止条件与消息存储。
4. （可选）为步数上限或超时错误信息做更友好文案。

## 提示

- 停止：达到 max_iterations / Final Answer
- 仓库 agent 与 workflow nodes 可能都有实现

## 验收标准

- [ ] 循环在 N 步内必停
- [ ] 工具错误可恢复为 Observation
- [ ] NOTES 含停止条件与文件路径
- [ ] 可选改动有前后文案对比

## 延伸（选做）

实现 plan-and-execute：先产出步骤列表再逐步执行。
