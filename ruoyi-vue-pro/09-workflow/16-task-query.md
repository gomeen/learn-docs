# 4.2 任务查询：我的/待办/已办

> 深入理解 ruoyi 中"任务查询"的不同维度：待办、已办、我的发起。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"待办"、"已办"、"我的发起"三种查询的区别
- 掌握 Flowable 的 `TaskQuery` / `HistoricTaskInstanceQuery` 用法
- 理解 ruoyi 在 `BpmTaskController` 中提供的多个查询接口
- 知道 ruoyi 如何在查询时拼接"流程实例"、"流程定义"、"用户"等数据

## 📚 前置知识

- 流程实例基础（详见 [启动流程](./15-start-process.md)）
- Task / HistoryService（详见 [Flowable 概念](./02-flowable-concepts.md)）
- Flowable 的查询 API

## 1. 核心概念

### 1.1 三种查询的区别

| 查询 | Flowable API | 表 | 含义 |
|------|-------------|----|------|
| **待办**（Todo） | `taskService.createTaskQuery()` | `act_ru_task` | 当前用户**未完成**的任务 |
| **已办**（Done） | `historyService.createHistoricTaskInstanceQuery()` | `act_hi_taskinst` | 当前用户**已完成**的任务 |
| **我的发起** | `historyService.createHistoricProcessInstanceQuery()` | `act_hi_procinst` | 当前用户**作为发起人**的流程 |

### 1.2 ruoyi 的查询接口

```
GET /bpm/task/todo-page           待办分页
GET /bpm/task/done-page           已办分页
GET /bpm/task/my-page             我参与的任务（包含待办+已办）

GET /bpm/process-instance/my-page 我的发起分页
```

### 1.3 查询的"数据拼装"

返回给前端的 VO 不只包含 Task 本身，还包含：

```
BpmTaskRespVO
  ├── task 基本信息（id, name, createTime, assignee）
  ├── processInstance 流程实例信息（id, startUser, startTime）
  ├── processDefinition 流程定义信息（key, name, category, formId）
  └── 当前用户是否可操作
```

**实现方式**：分批查询 + Map 拼接（避免 N+1）。

## 2. 代码示例

### 2.1 待办查询

```java
public List<Task> getTodoTasks(Long userId) {
    return taskService.createTaskQuery()
        .taskAssignee(String.valueOf(userId))  // 当前用户是 assignee
        .active()                              // 任务未结束
        .orderByTaskCreateTime().desc()
        .list();
}
```

### 2.2 已办查询

```java
public List<HistoricTaskInstance> getDoneTasks(Long userId) {
    return historyService.createHistoricTaskInstanceQuery()
        .taskAssignee(String.valueOf(userId))   // 我处理过的
        .finished()                             // 已完成
        .orderByHistoricTaskInstanceEndTime().desc()
        .list();
}
```

### 2.3 常见错误：用 taskService 查询已办

```java
// ❌ 错误：TaskQuery 查不到已办任务（已办的不在 act_ru_task）
List<Task> done = taskService.createTaskQuery()
    .taskAssignee(userId)
    .list();  // 只有"未完成"的任务

// ✅ 正确：已办用 HistoryService
historyService.createHistoricTaskInstanceQuery().list();
```

## 3. 关键要点总结

- 待办用 `TaskQuery`（`act_ru_task`），已办用 `HistoricTaskInstanceQuery`（`act_hi_taskinst`）
- 待办查询用 `taskCandidateOrAssigned()` 兼容候选人和 assignee
- 关联数据（流程实例、用户、流程定义）用 Map 批量查询，避免 N+1
- ruoyi 提供 `/bpm/task/todo-page`、`/done-page`、`/my-page` 三种查询
- 我的发起用 `HistoricProcessInstanceQuery` + `startedBy(userId)`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
