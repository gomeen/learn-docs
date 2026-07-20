# 7.6.3 流程发起/审批

> 理解 ruoyi 流程实例（Process Instance）的发起、审批、终止。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 流程实例的生命周期
- 理解流程发起、审批通过/拒绝
- 学会流程终止、撤回、跳转等操作
- 能看懂流程任务处理的代码

## 📚 前置知识

- 流程定义（详见 [流程定义](./39-process-def.md)）
- 动态表单（详见 [动态表单](./40-dynamic-form.md)）
- Flowable API（详见 [启动流程](../09-workflow/15-start-process.md)、[审批](../09-workflow/17-approval.md)）

## 1. 核心概念

### 1.1 流程实例的状态

```
[草稿] ──发起──> [审批中] ──完成──> [已通过]
                   │
                   ├──拒绝──> [已拒绝]
                   ├──终止──> [已终止]
                   └──撤回──> [已撤回]
```

### 1.2 核心概念

| 概念 | 说明 |
|------|------|
| 流程实例 | 一次具体的流程执行 |
| 流程变量 | 流程中传递的数据 |
| 当前任务 | 等待审批的节点 |
| 审批历史 | 流程审批记录 |

### 1.3 流程发起/审批表

```sql
CREATE TABLE bpm_process_instance (
    id BIGINT,
    process_definition_id VARCHAR(64),
    business_key VARCHAR(64),     -- 业务主键
    start_user_id BIGINT,
    status INT,                   -- 状态
    start_time DATETIME,
    end_time DATETIME,
    form_variables TEXT           -- 表单变量 JSON
);
```

## 2. 代码示例

### 2.1 发起流程

```java
@PostMapping("/create")
@Operation(summary = "发起流程实例")
public CommonResult<String> createProcessInstance(@Valid @RequestBody BpmProcessInstanceCreateReqVO createReqVO) {
    return success(processInstanceService.createProcessInstance(getLoginUserId(), createReqVO));
}
```

### 2.2 发起流程核心逻辑

```java
@Transactional
@Override
public String createProcessInstance(Long userId, BpmProcessInstanceCreateReqVO reqVO) {
    // 1. 校验流程定义
    ProcessDefinition definition = repositoryService.createProcessDefinitionQuery()
            .processDefinitionId(reqVO.getProcessDefinitionId())
            .singleResult();
    Assert.notNull(definition, "流程定义不存在");
    // 2. 构造流程变量
    Map<String, Object> variables = reqVO.getVariables();
    // 3. 启动流程
    ProcessInstance instance = runtimeService.startProcessInstanceById(
            definition.getId(),
            reqVO.getBusinessKey(),
            variables);
    // 4. 记录到业务表
    ProcessInstanceExtDO ext = new ProcessInstanceExtDO();
    ext.setId(instance.getProcessInstanceId());
    ext.setProcessDefinitionId(definition.getId());
    ext.setBusinessKey(reqVO.getBusinessKey());
    ext.setStartUserId(userId);
    ext.setStatus(ProcessInstanceStatusEnum.RUNNING.getStatus());
    processInstanceExtMapper.insert(ext);
    return instance.getProcessInstanceId();
}
```

### 2.3 审批通过

```java
@PostMapping("/approve")
public CommonResult<Boolean> approveTask(@Valid @RequestBody BpmTaskApproveReqVO reqVO) {
    taskService.approveTask(getLoginUserId(), reqVO);
    return success(true);
}

@Transactional
@Override
public void approveTask(Long userId, BpmTaskApproveReqVO reqVO) {
    // 1. 校验任务
    Task task = taskService.createTaskQuery()
            .taskId(reqVO.getTaskId())
            .taskAssignee(String.valueOf(userId))
            .singleResult();
    Assert.notNull(task, "任务不存在或您不是审批人");
    // 2. 设置变量
    Map<String, Object> variables = reqVO.getVariables();
    // 3. 完成任务
    taskService.complete(task.getId(), variables);
    // 4. 记录审批意见
    taskExtService.addComment(userId, task, reqVO.getReason(), true);
}
```

### 2.4 审批拒绝

```java
@PostMapping("/reject")
public CommonResult<Boolean> rejectTask(@Valid @RequestBody BpmTaskRejectReqVO reqVO) {
    taskService.rejectTask(getLoginUserId(), reqVO);
    return success(true);
}
```

### 2.5 我的待办

```java
@GetMapping("/todo-page")
public CommonResult<PageResult<TaskRespVO>> getTodoTaskPage(@Valid TaskPageReqVO pageVO) {
    return success(taskService.getTodoTaskPage(getLoginUserId(), pageVO));
}
```

## 3. 关键要点总结

- 流程实例是一次具体的执行
- 流程状态：审批中、已通过、已拒绝、已终止
- 审批通过 = 调用 `taskService.complete()`
- 审批拒绝 = 跳转到结束节点
- 待办任务 = 当前用户为 assignee 的任务

---

**文档版本**：v1.0
**最后更新**：2026-07-13
