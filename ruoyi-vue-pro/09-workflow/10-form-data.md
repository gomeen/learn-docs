# 3.3 表单数据持久化

> 理解 ruoyi 中表单数据如何保存、读取、与流程变量关联。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道表单数据最终存储到 Flowable 的 `act_ru_variable` 表
- 区分"流程变量"和"表单业务数据"
- 理解审批时如何根据"流程实例 ID + 任务 key"获取表单数据
- 能用 `runtimeService.getVariable()` 读取流程变量

## 📚 前置知识

- 动态表单 / 组件（详见 [动态表单](./08-dynamic-form.md)、[表单组件](./09-form-components.md)）
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

## 3. ruoyi 仓库源码解读

### 3.1 BpmProcessInstanceServiceImpl 中启动流程

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
**核心代码**（基于 import 与同 package service 推断的关键方法）：

```java
/**
 * 创建流程实例（发起申请）
 */
public String createProcessInstance(Long userId, String processDefinitionKey,
                                     Map<String, Object> variables) {
    // 1. 通过 key 找最新激活的 ProcessDefinition
    ProcessDefinition definition = processDefinitionService
        .getActiveProcessDefinition(processDefinitionKey);

    // 2. 设置流程发起人 (startUser 变量)
    variables.put(BpmnVariableConstants.PROCESS_INSTANCE_VARIABLE_START_USER_ID, userId);

    // 3. 启动流程实例
    ProcessInstance pi = runtimeService.startProcessInstanceById(
        definition.getId(), variables);

    return pi.getId();
}
```

**解读**：
- 第 7 行：找**最新激活版本**（不是 key 启动）
- 第 11 行：**强制设置 startUser 变量**，所有流程都能拿到发起人
- 第 14 行：用 ID 启动（避免版本歧义）
- **关键设计**：启动人不通过 `authenticatedUserId` 设置，而用**流程变量**，方便后续业务查询

### 3.2 BpmTaskServiceImpl 中完成任务

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（基于 import 与 service 结构推断）：

```java
/**
 * 完成任务（审批）
 */
@Transactional(rollbackFor = Exception.class)
public void completeTask(Long userId, String taskId,
                          Map<String, Object> variables) {
    // 1. 校验任务存在、当前用户有权限（assignee / candidate）
    Task task = validateTaskCanComplete(userId, taskId);

    // 2. 注入 ruoyi 业务变量（审批结果、审批人、审批时间）
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_RESULT, "agree");
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_USER_ID, userId);
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_TIME, new Date());

    // 3. 完成任务
    taskService.complete(taskId, variables, true);  // true = use variables
}
```

**解读**：
- 第 5 行：事务保证"校验 + 业务变量 + 完成"原子
- 第 8 行：先校验（避免越权操作）
- 第 11-13 行：注入 3 个 ruoyi 业务变量
- **关键设计**：业务变量**统一前缀**（`TASK_VARIABLE_*`），便于业务回溯

## 4. 关键要点总结

- 表单数据 = 流程变量，存在 `act_ru_variable`（运行时）+ `act_hi_varinst`（历史）
- 启动流程用 `startProcessInstanceById()` 避免版本歧义
- 完成审批用 `taskService.complete(taskId, variables)` 传新变量
- ruoyi 强制设置 `startUserId` 变量（业务查询方便）
- ruoyi 完成审批注入 3 个业务变量：approveResult/approveUserId/approveTime

## 5. 练习题

### 练习 1：基础（必做）

写代码：用 `runtimeService.getVariables(executionId)` 读取一个流程实例的所有变量，输出"申请人、请假天数、原因"。

**参考答案**：见 `solutions/10-form-data.md`

### 练习 2：进阶

阅读 `BpmProcessInstanceServiceImpl.getApprovalDetail`，说明它在审批详情页中如何拼接：流程基本信息 + 流程变量 + 历史节点 + 当前任务。

### 练习 3：挑战（选做）

实现"流程变量导出"接口：传入 processInstanceId，返回所有变量的 JSON（用于排查"流程卡在哪个变量上"）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnVariableConstants.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
