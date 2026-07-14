# 4.4 委派/转办/加签/减签

> 深入理解 ruoyi 中"任务流转"的高级操作：委派、转办、加签、减签的区别与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"委派"（Delegate）、"转办"（Transfer）、"加签"（Add Sign）、"减签"（Remove Sign）
- 知道每种操作的业务场景
- 理解 ruoyi 在 Flowable 之上如何实现这些操作
- 能在 BPMN 设计中考虑这些操作的兼容性

## 📚 前置知识

- 14-approval.md（审批基础）
- 13-task-query.md（任务查询）
- Flowable 任务 API

## 1. 核心概念

### 1.1 四种操作的对比

| 操作 | 行为 | 业务场景 | Flowable API |
|------|------|---------|---------------|
| **委派**（Delegate） | 把任务**临时**给别人，**自己保留归属** | 请假时委托给同事处理 | `taskService.delegateTask(taskId, userId)` |
| **转办**（Transfer） | 把任务**永久**给别人，**自己不再是处理人** | 转交给部门其他同事 | `taskService.setAssignee(taskId, userId)` |
| **加签**（Add Sign） | 在当前 task 后**追加**新审批人 | 主管请求上级审批 | 创建新 UserTask + 跳转 |
| **减签**（Remove Sign） | 在会签中**减少**审批人 | 会签中某人放弃 | 修改多实例变量 |

**关键区别**：
- 委派：自己仍然是 assignee（**完成后回到自己**）
- 转办：自己不再是 assignee（**完成后流程继续**）
- 加签：插入**新节点**（**完成后回到原节点**）
- 减签：修改**集合变量**（多实例场景）

### 1.2 委派 vs 转办的本质

```
委派（Delegate）：
  task.delegate(userId)
  → task.assignee = userId  （但 owner = 原 assignee）
  → userId 完成 → task 回到 原 assignee（owner）手里
  → 这种情况原 assignee 还可以"resolve" 完成

转办（Transfer）：
  task.setAssignee(userId)
  → task.assignee = userId
  → userId 完成 → 流程继续（不会回到原 assignee）
```

### 1.3 加签的实现

加签分两种：

**前加签**：新审批人先批，**原 assignee 再批**
**后加签**：原 assignee 先批，**新审批人再批**

ruoyi 默认实现**前加签**：
1. 创建一个新 UserTask 节点（候选人 = 加签人）
2. 跳转原 task 到新节点
3. 新任务完成后，跳回原 task
4. 原 assignee 继续处理

## 2. 代码示例

### 2.1 委派

```java
// 张三委派给李四
taskService.delegateTask(taskId, "104");  // 104 = 李四的 userId
// task.assignee = 104, task.owner = 张三
// 李四完成后，任务回到 张三 手中
```

### 2.2 转办

```java
// 张三转给李四
taskService.setAssignee(taskId, "104");
// task.assignee = 104, owner 清空
// 李四完成后，流程继续
```

### 2.3 加签

```java
// 1. 在当前节点后加一个"加签节点"
UserTask addSignTask = ...;  // BPMN 操作
runtimeService.createChangeActivityStateBuilder()
    .processInstanceId(piId)
    .moveActivityIdTo("approve", "addSignNode")
    .changeState();
```

### 2.4 常见错误：委派后原 assignee 直接 complete

```java
// ❌ 错误：张三委派给李四后，张三又直接完成任务
taskService.delegateTask(taskId, "104");
taskService.complete(taskId);  // 张三不应该 complete
// 正确：等李四处理后回到张三手里，张三才能 complete
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskServiceImpl 委派实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（基于 service 通用结构推断）：

```java
@Override
public void delegateTask(Long userId, String taskId, Long delegateUserId) {
    // 1. 校验任务可委派
    Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
    Assert.notNull(task, "任务不存在");
    if (!StrUtil.equals(task.getAssignee(), String.valueOf(userId))) {
        throw exception(TASK_NOT_OWNER);
    }

    // 2. 委派（Flowable API）
    taskService.delegateTask(taskId, String.valueOf(delegateUserId));

    // 3. 写业务表（ruoyi 特有）
    bpmTaskDelegateService.createDelegate(taskId, userId, delegateUserId);
}
```

**解读**：
- 第 4-5 行：先校验任务存在
- 第 6-8 行：只有当前 assignee 才能委派
- 第 11 行：用 Flowable 的 delegate API
- 第 14 行：在 ruoyi 业务表 `bpm_task_delegate` 中记录委派历史
- **关键设计**：Flowable 任务数据 + ruoyi 业务数据**双写**

### 3.2 BpmTaskServiceImpl 转办实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**：

```java
@Override
public void transferTask(Long userId, String taskId, Long transferUserId) {
    // 1. 校验
    Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
    if (!StrUtil.equals(task.getAssignee(), String.valueOf(userId))) {
        throw exception(TASK_NOT_OWNER);
    }

    // 2. 转办：直接改 assignee
    taskService.setAssignee(taskId, String.valueOf(transferUserId));

    // 3. 写业务表
    bpmTaskTransferService.createTransfer(taskId, userId, transferUserId);
}
```

**解读**：
- 第 4-7 行：同样要校验所有权
- 第 10 行：直接 `setAssignee`（转办 = 改 assignee）
- 第 13 行：业务表记录
- **关键设计**：委派用 `delegateTask`、转办用 `setAssignee`，**两者用不同 API**

### 3.3 加签实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（简化版）：

```java
@Override
public void addSignTask(Long userId, String taskId, AddSignReqVO reqVO) {
    // 1. 校验
    Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
    if (!StrUtil.equals(task.getAssignee(), String.valueOf(userId))) {
        throw exception(TASK_NOT_OWNER);
    }

    // 2. 在 BPMN 中动态插入"加签节点"
    //    这步较复杂：需要 BpmnModel 修改 + 重新部署 + 触发节点创建
    // 简化思路：用一个固定的"加签 UserTask" + 候选人变量
    Map<String, Object> variables = new HashMap<>();
    variables.put("addSignUserId", reqVO.getAddSignUserId());
    variables.put("addSignReason", reqVO.getReason());

    // 3. 跳转到加签节点
    runtimeService.createChangeActivityStateBuilder()
            .processInstanceId(task.getProcessInstanceId())
            .moveActivityIdTo(task.getTaskDefinitionKey(), "addSignNode")
            .changeState();
}
```

**解读**：
- 第 4-7 行：同样要校验所有权
- 第 11-14 行：注入"加签人"变量
- 第 17-21 行：跳转到加签节点
- **关键设计**：加签 = **动态插入节点** + 跳转
- **注意**：BPMN 必须在设计时预留 `addSignNode` 节点（不能完全动态创建 BPMN 元素）

## 4. 关键要点总结

- **委派**（delegate）：临时给别人，**自己保留归属**（owner 字段）
- **转办**（transfer）：永久给别人，**自己不再是处理人**
- **加签**：在当前 task 后插入新审批人
- **减签**：多实例中修改集合变量
- ruoyi 在 `bpm_task_delegate` / `bpm_task_transfer` 表中记录历史
- 加签依赖 BPMN 预留的"加签节点"，不能完全动态创建 BPMN

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 委派和转办的本质区别是什么？
2. 加签前需要 BPMN 做什么准备？
3. 减签适用于什么场景？

**参考答案**：见 `solutions/15-delegate.md`

### 练习 2：进阶

阅读 `BpmTaskServiceImpl` 中委派、转办、加签的完整实现，列出每种操作涉及的 Flowable API。

### 练习 3：挑战（选做）

实现"催办"接口：传入 taskId，给当前 assignee 发送系统通知 + 邮件。要求用 `ManagementService.createMessage()` 或 `BpmMessageService`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- Flowable TaskService 委派：https://www.flowable.com/open-source/docs/javadoc/org/flowable/engine/TaskService.html#delegateTask-java.lang.String-java.lang.String-

---

**文档版本**：v1.0
**最后更新**：2026-07-13
