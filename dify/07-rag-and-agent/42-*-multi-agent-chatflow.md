# 小验证：多 Agent 与 Chatflow/Workflow

> 覆盖：
> - [32-multi-agent](./38-multi-agent.md)
> - [33-agent-communication](./39-agent-communication.md)
> - [34-task-distribution](./40-task-distribution.md)
> - [35-chatflow-vs-workflow](./41-chatflow-vs-workflow.md)
>
> 预计：40～70 分钟 · 本地练习或改 dify 仓库

## 背景

多 Agent 协作与 Chatflow/Workflow 产品形态选择常被混用。验证：说清差异并做最小路由。

## 需求

1. `NOTES.md`：Chatflow vs Workflow 在状态、记忆、适用场景上的差异（结合 dify 代码/文档路径）。
2. 本地实现 supervisor 路由：根据用户意图关键字把任务派给 `research`/`code` 两个伪 agent，汇总回复。
3. 说明失败隔离：子 agent 超时如何影响总任务（设计 1 段伪代码）。

## 提示

- 对照 `41-chatflow-vs-workflow.md` 与 workflow 目录
- 通信协议可用内存队列模拟

## 验收标准

- [ ] 差异表 ≥5 条
- [ ] supervisor 路由可运行 demo
- [ ] 超时/隔离策略写清
- [ ] 有仓库或文档锚点

## 延伸（选做）

扩展为带共享 blackboard 的状态字典。
