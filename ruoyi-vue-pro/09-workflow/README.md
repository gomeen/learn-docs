# 09 - Flowable 工作流

> ruoyi-vue-pro 集成 Flowable 实现工作流引擎，支持动态表单、流程设计、会签/或签。

## 模块 9.1 工作流基础

- [ ] [1.1 BPMN 2.0 规范](./01-bpmn.md)
- [ ] [1.2 Flowable 核心概念](./02-flowable-concepts.md)
- [ ] [1.3 ruoyi 工作流架构](./03-ruoyi-workflow.md)

## 模块 9.2 流程定义

- [ ] [2.1 流程设计器：Modeler 集成](./04-modeler.md)
- [ ] [2.2 流程定义部署](./05-deploy.md)
- [ ] [2.3 流程版本管理](./06-version.md)
- [ ] [2.4 流程分类与标签](./07-category.md)

## 模块 9.3 表单设计

- [ ] [3.1 动态表单 vs 表单设计器](./08-dynamic-form.md)
- [ ] [3.2 表单组件库](./09-form-components.md)
- [ ] [3.3 表单数据持久化](./10-form-data.md)
- [ ] [3.4 ruoyi 的 Form 设计](./11-ruoyi-form.md)

## 模块 9.4 流程执行

- [ ] [4.1 发起流程实例](./12-start-process.md)
- [ ] [4.2 任务查询：我的/待办/已办](./13-task-query.md)
- [ ] [4.3 审批：同意/拒绝/驳回](./14-approval.md)
- [ ] [4.4 委派/转办/加签/减签](./15-delegate.md)
- [ ] [4.5 流程变量与表单数据](./16-process-vars.md)

## 模块 9.5 高级特性

- [ ] [5.1 多实例任务：会签/或签](./17-multi-instance.md)
- [ ] [5.2 网关：排他/并行/包容](./18-gateway.md)
- [ ] [5.3 子流程与调用活动](./19-sub-process.md)
- [ ] [5.4 流程监听器](./20-listener.md)
- [ ] [5.5 用户任务分配：候选人/候选组](./21-task-assign.md)
- [ ] [5.6 流程超时与催办](./22-timeout.md)

## 模块 9.6 集成与扩展

- [ ] [6.1 与业务模块集成](./23-integration.md)
- [ ] [6.2 流程图高亮追踪](./24-trace.md)
- [ ] [6.3 自定义任务处理器](./25-custom-handler.md)
- [ ] [6.4 Flowable 6 vs Flowable 7](./26-flowable-version.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- 工作流模块：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/`
- Modeler：`yudao-module-bpm/.../controller/admin/model/`
- 流程定义：`yudao-module-bpm/.../controller/admin/definition/`
- 流程实例：`yudao-module-bpm/.../controller/admin/instance/`
- 任务管理：`yudao-module-bpm/.../controller/admin/task/`
