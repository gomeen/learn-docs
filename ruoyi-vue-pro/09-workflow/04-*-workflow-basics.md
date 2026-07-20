# 小验证：工作流基础与 ruoyi 架构

> 覆盖：
- [BPMN](./01-bpmn.md)
- [Flowable 概念](./02-flowable-concepts.md)
- [ruoyi 工作流架构](./03-ruoyi-workflow.md)
>
> 预计：30～60 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

先对齐 BPMN 元素与 Flowable 服务 API，再看 ruoyi 封装层。

## 需求

1. 画一个请假 BPMN：开始 → 用户任务 → 排他网关 → 结束（通过/驳回）。
2. 对照 Flowable：Repository/Runtime/Task/History 服务各自职责。
3. 在 `/Users/xu/code/github/ruoyi-vue-pro` 的 `yudao-module-bpm` 中找到对上述服务的封装入口。
4. 说明 ruoyi 在引擎之上还管理了哪些业务表（模型、表单、分类等）。

## 提示

- 不必先上设计器，纸面/文本 BPMN 也可。
- 关注封装层不要直接散落操作引擎。

## 验收标准

- [ ] BPMN 草图完成
- [ ] 四大服务职责说明正确
- [ ] 封装入口类路径记录
- [ ] 业务表/领域对象列表
- [ ] 能说清引擎与业务模块边界

## 延伸（选做）

- 用 Flowable 独立示例项目跑一个最小流程。
- 阅读 process engine 配置 Bean。
