# 4.4 委派/转办/加签/减签

> 深入理解 ruoyi 中"任务流转"的高级操作：委派、转办、加签、减签的区别与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"委派"（Delegate）、"转办"（Transfer）、"加签"（Add Sign）、"减签"（Remove Sign）
- 知道每种操作的业务场景
- 理解 ruoyi 在 Flowable 之上如何实现这些操作
- 能在 BPMN 设计中考虑这些操作的兼容性

## 📚 前置知识

- 审批基础（详见 [审批](./17-approval.md)）
- 任务查询（详见 [任务查询](./16-task-query.md)）
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

## 3. 关键要点总结

- **委派**（delegate）：临时给别人，**自己保留归属**（owner 字段）
- **转办**（transfer）：永久给别人，**自己不再是处理人**
- **加签**：在当前 task 后插入新审批人
- **减签**：多实例中修改集合变量
- ruoyi 在 `bpm_task_delegate` / `bpm_task_transfer` 表中记录历史
- 加签依赖 BPMN 预留的"加签节点"，不能完全动态创建 BPMN

---

**文档版本**：v1.0
**最后更新**：2026-07-13
