# 7.6.3 流程发起/审批

> 理解 ruoyi 流程实例（Process Instance）的发起、审批、终止。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 流程实例的生命周期
- 理解流程发起、审批通过/拒绝
- 学会流程终止、撤回、跳转等操作
- 能看懂流程任务处理的代码

## 📚 前置知识

- 33-process-def.md
- 34-dynamic-form.md
- Flowable API

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmTaskController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 流程任务")
@RestController
@RequestMapping("/bpm/task")
@Validated
public class BpmTaskController {

    @Resource
    private BpmTaskService taskService;

    @GetMapping("/todo-page")
    @Operation(summary = "获得我的待办任务分页")
    public CommonResult<PageResult<BpmTaskRespVO>> getTodoTaskPage(@Valid BpmTaskPageReqVO pageVO) {
        return success(taskService.getTodoTaskPage(SecurityFrameworkUtils.getLoginUserId(), pageVO));
    }

    @PostMapping("/approve")
    @Operation(summary = "通过任务")
    public CommonResult<Boolean> approveTask(@Valid @RequestBody BpmTaskApproveReqVO reqVO) {
        taskService.approveTask(SecurityFrameworkUtils.getLoginUserId(), reqVO);
        return success(true);
    }

    @PostMapping("/reject")
    @Operation(summary = "拒绝任务")
    public CommonResult<Boolean> rejectTask(@Valid @RequestBody BpmTaskRejectReqVO reqVO) {
        taskService.rejectTask(SecurityFrameworkUtils.getLoginUserId(), reqVO);
        return success(true);
    }
}
```

### 3.2 BpmProcessInstanceController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmProcessInstanceController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 流程实例")
@RestController
@RequestMapping("/bpm/process-instance")
@Validated
public class BpmProcessInstanceController {

    @Resource
    private BpmProcessInstanceService processInstanceService;

    @PostMapping("/create")
    @Operation(summary = "发起流程实例")
    public CommonResult<String> createProcessInstance(@Valid @RequestBody BpmProcessInstanceCreateReqVO createReqVO) {
        return success(processInstanceService.createProcessInstance(
                SecurityFrameworkUtils.getLoginUserId(), createReqVO));
    }

    @DeleteMapping("/cancel")
    @Operation(summary = "取消流程实例")
    public CommonResult<Boolean> cancelProcessInstance(@Valid @RequestBody BpmProcessInstanceCancelReqVO cancelReqVO) {
        processInstanceService.cancelProcessInstance(SecurityFrameworkUtils.getLoginUserId(), cancelReqVO);
        return success(true);
    }

    @GetMapping("/my-page")
    @Operation(summary = "获得我的流程实例分页")
    public CommonResult<PageResult<BpmProcessInstanceRespVO>> getMyProcessInstancePage(
            @Valid BpmProcessInstanceMyPageReqVO pageVO) {
        return success(processInstanceService.getMyProcessInstancePage(
                SecurityFrameworkUtils.getLoginUserId(), pageVO));
    }
}
```

## 4. 关键要点总结

- 流程实例是一次具体的执行
- 流程状态：审批中、已通过、已拒绝、已终止
- 审批通过 = 调用 `taskService.complete()`
- 审批拒绝 = 跳转到结束节点
- 待办任务 = 当前用户为 assignee 的任务

## 5. 练习题

### 练习 1：基础（必做）

阅读 `BpmProcessInstanceDO.java` 字段。

### 练习 2：进阶

阅读 `BpmTaskServiceImpl.java`，理解审批通过和拒绝的流程。

### 练习 3：挑战（选做）

设计"流程加签"功能：审批人 A 收到任务后，可以把任务转给 B 处理（A 之后还会收回）。列出实现思路。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/`
- Flowable 任务服务：https://www.flowable.com/open-source/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
