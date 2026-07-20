# 4.3 审批：同意/拒绝/驳回

> 深入理解 ruoyi 中的"审批"操作：通过、拒绝、驳回的区别与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"通过"、"拒绝"、"驳回"、"驳回到指定节点"四种操作
- 知道 ruoyi 在 `BpmTaskServiceImpl` 中如何实现这些操作
- 理解"驳回"在 Flowable 中是 `createChangeActivityStateBuilder()` 的应用
- 能在自己的流程中实现审批操作

## 📚 前置知识

- 任务查询（详见 [任务查询](./16-task-query.md)）
- 启动流程（详见 [启动流程](./15-start-process.md)）
- 网关基础（详见 [网关](./22-gateway.md)）

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

## 3. 关键要点总结

- 同意/拒绝用同一个 `taskService.complete()`，靠 `approveResult` 变量路由
- 驳回用 `runtimeService.createChangeActivityStateBuilder().moveActivityIdTo()`
- 驳回默认到上一个节点，找不到则让用户选
- ruoyi 注入 4 个业务变量：approveResult、approveComment、approveUserId、approveTime
- 驳回不修改原变量，**审批人不变**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
