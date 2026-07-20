# 3.3 表单数据持久化

> 理解 ruoyi 中表单数据如何保存、读取、与流程变量关联。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道表单数据最终存储到 Flowable 的 `act_ru_variable` 表
- 区分"流程变量"和"表单业务数据"
- 理解审批时如何根据"流程实例 ID + 任务 key"获取表单数据
- 能用 `runtimeService.getVariable()` 读取流程变量

## 📚 前置知识

- 动态表单 / 组件（详见 [动态表单](./10-dynamic-form.md)、[表单组件](./11-form-components.md)）
- RuntimeService / TaskService（详见 [Flowable 概念](./02-flowable-concepts.md)）

## 1. 核心概念

### 1.1 表单数据的"三种存储"

| 存储位置 | 表 | 何时使用 |
|---------|----|---------|
| **流程变量** | `act_ru_variable`（运行时）、`act_hi_varinst`（历史） | 流程中所有节点共享 |
| **业务表** | 业务模块自己的表 | 业务数据持久化（如 `bpm_oa_leave`） |
| **附件** | `act_hi_attachment` | 文件/图片 |

**关键选择**：
- **简单数据**（如 days、reason）→ 流程变量
- **业务数据**（如请假结束后的考勤记录）→ 业务表

### 1.2 ruoyi 的"流程变量" vs "业务表"

ruoyi 的 OA 例子中：
- 流程运行时：`act_ru_variable` 存 `days`、`reason`
- 流程结束后：`bpm_oa_leave` 表存"申请单"，作为业务记录

**转换时机**：监听器 `BpmProcessInstanceEventListener` 在 `PROCESS_COMPLETED` 事件触发"业务数据归档"。

### 1.3 表单数据回显

审批页面需要：
- **发起人填写的原始数据**（`runtimeService.getVariable()`）
- **当前用户身份**（审批意见、附件）
- **流程流转历史**（`historyService.createHistoricActivityInstanceQuery()`）

```
[审批页面] /bpm/task/detail?taskId=xxx
   ↓ 后端查询
1. Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
2. Map<String, Object> variables = taskService.getVariables(task.getExecutionId());
3. List<HistoricActivityInstance> his = historyService.createHistoricActivityInstanceQuery()
        .processInstanceId(task.getProcessInstanceId()).list();
4. 组装为 BpmApprovalDetailRespVO 返回前端
```

## 2. 代码示例

### 2.1 启动流程时传入表单数据

```java
Map<String, Object> variables = new HashMap<>();
variables.put("name", "张三");
variables.put("days", 3);
variables.put("reason", "回家探亲");

ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave", variables);
```

### 2.2 审批中读取流程变量

```java
// 方式一：按执行流 ID
Map<String, Object> variables = runtimeService.getVariables(executionId);

// 方式二：按任务 ID
Map<String, Object> variables = taskService.getVariables(taskId);
```

### 2.3 完成审批时设置新变量

```java
Map<String, Object> variables = new HashMap<>();
variables.put("approveResult", "agree");
variables.put("approveComment", "同意");
variables.put("approveTime", new Date());

taskService.complete(taskId, variables);
```

### 2.4 常见错误：变量名拼写错误

```java
// ❌ 错误：审批节点 EL 表达式引用 ${days}，但提交时用了 dayCount
variables.put("dayCount", 3);

// ✅ 正确：所有地方都用 days（变量名要严格一致）
variables.put("days", 3);
```

## 3. 关键要点总结

- 表单数据 = 流程变量，存在 `act_ru_variable`（运行时）+ `act_hi_varinst`（历史）
- 启动流程用 `startProcessInstanceById()` 避免版本歧义
- 完成审批用 `taskService.complete(taskId, variables)` 传新变量
- ruoyi 强制设置 `startUserId` 变量（业务查询方便）
- ruoyi 完成审批注入 3 个业务变量：approveResult/approveUserId/approveTime

---

**文档版本**：v1.0
**最后更新**：2026-07-13
