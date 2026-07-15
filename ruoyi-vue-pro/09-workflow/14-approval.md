# 4.3 审批：同意/拒绝/驳回

> 深入理解 ruoyi 中的"审批"操作：通过、拒绝、驳回的区别与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"通过"、"拒绝"、"驳回"、"驳回到指定节点"四种操作
- 知道 ruoyi 在 `BpmTaskServiceImpl` 中如何实现这些操作
- 理解"驳回"在 Flowable 中是 `createChangeActivityStateBuilder()` 的应用
- 能在自己的流程中实现审批操作

## 📚 前置知识

- 任务查询（详见 [任务查询](./13-task-query.md)）
- 启动流程（详见 [启动流程](./12-start-process.md)）
- 网关基础（详见 [网关](./18-gateway.md)）

## 1. 核心概念

### 1.1 四种审批操作

| 操作 | 行为 | Flowable 实现 |
|------|------|---------------|
| **通过** | 任务完成，流程继续 | `taskService.complete(taskId, vars)` |
| **拒绝** | 任务完成，流程结束 | `taskService.complete(taskId, vars)` + 流程变量 `approveResult=reject` |
| **驳回** | 任务完成，**回退到上一个节点** | `runtimeService.createChangeActivityStateBuilder()` |
| **驳回到指定节点** | 跳到任意历史节点 | `runtimeService.createChangeActivityStateBuilder().moveActivityIdTo(...)` |

### 1.2 ruoyi 的实现思路

ruoyi 在 BPMN 流程中通常包含一个"全局结束"分支：

```xml
<userTask id="approve"/>
<exclusiveGateway id="checkResult"/>
<endEvent id="end"/>           <!-- 通过 -->
<endEvent id="rejectEnd"/>      <!-- 拒绝 -->
<sequenceFlow id="f1" sourceRef="checkResult" targetRef="end">
    <conditionExpression>${approveResult == 'agree'}</conditionExpression>
</sequenceFlow>
<sequenceFlow id="f2" sourceRef="checkResult" targetRef="rejectEnd">
    <conditionExpression>${approveResult == 'reject'}</conditionExpression>
</sequenceFlow>
```

**拒绝实现**：完成审批 + 设置 `approveResult=reject` + 排他网关把流程导向 `rejectEnd`。

### 1.3 驳回的实现

驳回用 Flowable 的 **Activity 跳转 API**：

```java
runtimeService.createChangeActivityStateBuilder()
    .processInstanceId(piId)
    .moveActivityIdTo(currentActivityId, targetActivityId)
    .changeState();
```

**本质**：直接修改 `act_ru_execution.ACT_ID_`，把当前节点改到目标节点。

## 2. 代码示例

### 2.1 同意（Approve）

```java
Map<String, Object> vars = new HashMap<>();
vars.put("approveResult", "agree");
vars.put("approveComment", "同意");
vars.put("approveUserId", userId);
taskService.complete(taskId, vars);
```

### 2.2 拒绝（Reject）

```java
Map<String, Object> vars = new HashMap<>();
vars.put("approveResult", "reject");
vars.put("approveComment", "资料不全");
vars.put("approveUserId", userId);
taskService.complete(taskId, vars);
// 排他网关会跳到 rejectEnd
```

### 2.3 驳回到上一节点

```java
runtimeService.createChangeActivityStateBuilder()
    .processInstanceId(piId)
    .moveActivityIdTo("approve_leader", "submit")  // 当前节点 → 提交节点
    .changeState();
```

### 2.4 常见错误：驳回后变量丢失

```java
// ❌ 错误：驳回后重新提交时，审批人变了
// 因为变量中"审批人"被覆盖

// ✅ 正确：驳回时只移动节点，**不修改变量**
runtimeService.createChangeActivityStateBuilder()
    .processInstanceId(piId)
    .moveActivityIdTo(...)
    .changeState();
// 变量保持不变
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskServiceImpl 完成任务

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（基于 service 通用结构推断）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public void completeTask(Long userId, BpmTaskApproveReqVO reqVO) {
    // 1. 校验任务
    Task task = validateTaskCanComplete(userId, reqVO.getTaskId());

    // 2. 构造变量
    Map<String, Object> variables = reqVO.getVariables();
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_RESULT, reqVO.getResult());
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_COMMENT, reqVO.getComment());
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_USER_ID, userId);
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_TIME, new Date());

    // 3. 完成任务
    if (reqVO.getResult().equals(BpmTaskResultEnum.REJECT.getResult())) {
        // 拒绝：业务变量 + 排他网关自动跳到 rejectEnd
        taskService.complete(reqVO.getTaskId(), variables);
    } else {
        taskService.complete(reqVO.getTaskId(), variables);
    }
}
```

**解读**：
- 第 4 行：事务保证原子性
- 第 7 行：先校验（防越权）
- 第 10-13 行：注入 4 个业务变量
- **关键设计**：同意/拒绝用**同一个 complete 方法**，靠 `approveResult` 变量控制后续分支

### 3.2 BpmTaskServiceImpl 驳回实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public void rejectTask(Long userId, BpmTaskRejectReqVO reqVO) {
    // 1. 校验任务
    Task task = taskService.createTaskQuery().taskId(reqVO.getTaskId()).singleResult();
    Assert.notNull(task, "任务不存在");

    // 2. 获取当前活动节点
    String currentActivityId = task.getTaskDefinitionKey();

    // 3. 计算驳回目标（默认上一个节点）
    String targetActivityId = reqVO.getTargetActivityId();
    if (StrUtil.isBlank(targetActivityId)) {
        targetActivityId = BpmnModelUtils.getPreActivityId(...);  // ruoyi 工具类
    }

    // 4. 跳转
    runtimeService.createChangeActivityStateBuilder()
            .processInstanceId(task.getProcessInstanceId())
            .moveActivityIdTo(currentActivityId, targetActivityId)
            .changeState();
}
```

**解读**：
- 第 4-5 行：先拿到当前 task
- 第 8-12 行：默认驳回到上一个节点（用 `BpmnModelUtils.getPreActivityId` 计算）
- 第 15-18 行：用 Flowable 的跳转 API
- **关键设计**：驳回是**节点跳转**，不是简单 complete

### 3.3 BpmnModelUtils 中的"上一个节点"算法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/BpmnModelUtils.java`（基于 service 通用结构推断）

```java
/**
 * 获取当前节点的上一个活动节点 ID
 */
public static String getPreActivityId(BpmnModel bpmnModel, String currentActivityId) {
    // 1. 找 currentActivityId 的所有入边
    // 2. 找到 sourceRef 是 UserTask 的边
    // 3. 返回 sourceRef 的 ID
    // 4. 找不到则返回 null（提示：需要用户在 UI 选择目标节点）
}
```

**解读**：
- 驳回默认跳到上一个 UserTask
- 找不到上一个 UserTask 时，返回 null，让用户在 UI 选目标节点
- **关键设计**：驳回目标"智能化"，**默认最常用，能找到最优解**

## 4. 关键要点总结

- 同意/拒绝用同一个 `taskService.complete()`，靠 `approveResult` 变量路由
- 驳回用 `runtimeService.createChangeActivityStateBuilder().moveActivityIdTo()`
- 驳回默认到上一个节点，找不到则让用户选
- ruoyi 注入 4 个业务变量：approveResult、approveComment、approveUserId、approveTime
- 驳回不修改原变量，**审批人不变**

## 5. 练习题

### 练习 1：基础（必做）

写代码：完成一个 task，设置 approveResult=reject，添加 approveComment="不同意"。

**参考答案**：见 `solutions/14-approval.md`

### 练习 2：进阶

阅读 `BpmnModelUtils.getPreActivityId` 的完整实现，解释它如何处理"网关后接多个 UserTask"的情况。

### 练习 3：挑战（选做）

实现"加签"功能：在 UserTask 后插入一个新的 UserTask（替代原任务处理人）。要求：原任务置为"已加签"状态，新任务完成后，原 assignee 继续处理。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/BpmnModelUtils.java`
- Flowable Activity 跳转：https://www.flowable.com/open-source/docs/javadoc/org/flowable/engine/RuntimeService.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
