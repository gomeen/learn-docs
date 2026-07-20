# 09 - Flowable 工作流

> ruoyi-vue-pro 集成 Flowable 实现工作流引擎，支持动态表单、流程设计、会签/或签。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 9.1 工作流基础

- [ ] [1.1 BPMN 2.0 规范](./01-bpmn.md)
- [ ] [1.2 Flowable 核心概念](./02-flowable-concepts.md)
- [ ] [1.3 ruoyi 工作流架构](./03-ruoyi-workflow.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [04-*-workflow-basics: 工作流基础与 ruoyi 架构](./04-*-workflow-basics.md)
  - 覆盖：01-bpmn.md, 02-flowable-concepts.md, 03-ruoyi-workflow.md


## 模块 9.2 流程定义

- [ ] [2.1 流程设计器：Modeler 集成](./05-modeler.md)
- [ ] [2.2 流程定义部署](./06-deploy.md)
- [ ] [2.3 流程版本管理](./07-version.md)
- [ ] [2.4 流程分类与标签](./08-category.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [09-*-definition-form: 流程模型 / 部署 / 版本 / 分类](./09-*-definition-form.md)
  - 覆盖：05-modeler.md, 06-deploy.md, 07-version.md, 08-category.md


## 模块 9.3 表单设计

- [ ] [3.1 动态表单 vs 表单设计器](./10-dynamic-form.md)
- [ ] [3.2 表单组件库](./11-form-components.md)
- [ ] [3.3 表单数据持久化](./12-form-data.md)
- [ ] [3.4 ruoyi 的 Form 设计](./13-ruoyi-form.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [14-*-dynamic-form: 动态表单与表单数据](./14-*-dynamic-form.md)
  - 覆盖：10-dynamic-form.md, 11-form-components.md, 12-form-data.md, 13-ruoyi-form.md


## 模块 9.4 流程执行

- [ ] [4.1 发起流程实例](./15-start-process.md)
- [ ] [4.2 任务查询：我的/待办/已办](./16-task-query.md)
- [ ] [4.3 审批：同意/拒绝/驳回](./17-approval.md)
- [ ] [4.4 委派/转办/加签/减签](./18-delegate.md)
- [ ] [4.5 流程变量与表单数据](./19-process-vars.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [20-*-process-exec: 流程执行：发起 / 待办 / 审批 / 委派](./20-*-process-exec.md)
  - 覆盖：15-start-process.md, 16-task-query.md, 17-approval.md, 18-delegate.md, 19-process-vars.md


## 模块 9.5 高级特性

- [ ] [5.1 多实例任务：会签/或签](./21-multi-instance.md)
- [ ] [5.2 网关：排他/并行/包容](./22-gateway.md)
- [ ] [5.3 子流程与调用活动](./23-sub-process.md)
- [ ] [5.4 流程监听器](./24-listener.md)
- [ ] [5.5 用户任务分配：候选人/候选组](./25-task-assign.md)
- [ ] [5.6 流程超时与催办](./26-timeout.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [27-*-advanced-flow: 高级：多实例 / 网关 / 监听器 / 超时](./27-*-advanced-flow.md)
  - 覆盖：21-multi-instance.md, 22-gateway.md, 23-sub-process.md, 24-listener.md, 25-task-assign.md, 26-timeout.md


## 模块 9.6 集成与扩展

- [ ] [6.1 与业务模块集成](./28-integration.md)
- [ ] [6.2 流程图高亮追踪](./29-trace.md)
- [ ] [6.3 自定义任务处理器](./30-custom-handler.md)
- [ ] [6.4 Flowable 6 vs Flowable 7](./31-flowable-version.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [32-*-workflow-integration: 业务集成与扩展](./32-*-workflow-integration.md)
  - 覆盖：28-integration.md, 29-trace.md, 30-custom-handler.md, 31-flowable-version.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- 工作流模块：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/`
- Modeler：`yudao-module-bpm/.../controller/admin/model/`
- 流程定义：`yudao-module-bpm/.../controller/admin/definition/`
- 流程实例：`yudao-module-bpm/.../controller/admin/instance/`
- 任务管理：`yudao-module-bpm/.../controller/admin/task/`
