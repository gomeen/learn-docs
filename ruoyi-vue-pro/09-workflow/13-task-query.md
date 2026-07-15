# 4.2 任务查询：我的/待办/已办

> 深入理解 ruoyi 中"任务查询"的不同维度：待办、已办、我的发起。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"待办"、"已办"、"我的发起"三种查询的区别
- 掌握 Flowable 的 `TaskQuery` / `HistoricTaskInstanceQuery` 用法
- 理解 ruoyi 在 `BpmTaskController` 中提供的多个查询接口
- 知道 ruoyi 如何在查询时拼接"流程实例"、"流程定义"、"用户"等数据

## 📚 前置知识

- 流程实例基础（详见 [启动流程](./12-start-process.md)）
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

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskController 待办接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmTaskController.java`
**核心代码**（行 66-90）：

```java
@GetMapping("todo-page")
@Operation(summary = "获取 Todo 待办任务分页")
@PreAuthorize("@ss.hasPermission('bpm:task:query')")
public CommonResult<PageResult<BpmTaskRespVO>> getTaskTodoPage(@Valid BpmTaskPageReqVO pageVO) {
    PageResult<Task> pageResult = taskService.getTaskTodoPage(getLoginUserId(), pageVO);
    if (CollUtil.isEmpty(pageResult.getList())) {
        return success(PageResult.empty());
    }

    // 拼接数据
    Map<String, ProcessInstance> processInstanceMap = processInstanceService.getProcessInstanceMap(
            convertSet(pageResult.getList(), Task::getProcessInstanceId));
    Map<Long, AdminUserRespDTO> userMap = adminUserApi.getUserMap(
            convertSet(processInstanceMap.values(), instance -> Long.valueOf(instance.getStartUserId())));
    Map<String, BpmProcessDefinitionInfoDO> processDefinitionInfoMap = processDefinitionService.getProcessDefinitionInfoMap(
            // ... 省略
    );
```

**解读**：
- 第 67 行：路由 `/bpm/task/todo-page`
- 第 70 行：调 `taskService.getTaskTodoPage(userId, pageVO)` 拿到 Task 列表
- 第 76-77 行：批量查 ProcessInstance（**用 Map 缓存，避免 N+1**）
- 第 78-79 行：批量查 User 头像/昵称
- **关键设计**：所有"关联查询"都用 Map 拼装，**不写循环单查**

### 3.2 BpmTaskServiceImpl 待办查询实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（基于同 package service 推断）：

```java
@Override
public PageResult<Task> getTaskTodoPage(Long userId, BpmTaskPageReqVO pageVO) {
    TaskQuery query = taskService.createTaskQuery()
            .taskCandidateOrAssigned(String.valueOf(userId))  // 候选+assignee
            .active()                                          // 激活
            .orderByTaskCreateTime().desc();

    if (pageVO.getProcessDefinitionKey() != null) {
        query.processDefinitionKey(pageVO.getProcessDefinitionKey());
    }
    if (StrUtil.isNotBlank(pageVO.getName())) {
        query.taskNameLike("%" + pageVO.getName() + "%");
    }

    long total = query.count();
    List<Task> list = query.listPage(pageVO.getPageNo(), pageVO.getPageSize());
    return new PageResult<>(list, total);
}
```

**解读**：
- 第 4 行：`taskCandidateOrAssigned` 是关键，**支持候选人和 assignee 两种情况**
- 第 5 行：只查激活的（未挂起）
- 第 8-13 行：可选的过滤条件
- **关键设计**：单一查询支持多种过滤，**前端用 VO 传过滤项**

### 3.3 已办查询实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**：

```java
@Override
public PageResult<HistoricTaskInstance> getTaskDonePage(Long userId, BpmTaskPageReqVO pageVO) {
    HistoricTaskInstanceQuery query = historyService.createHistoricTaskInstanceQuery()
            .finished()                                    // 已完成
            .taskAssignee(String.valueOf(userId))          // 我处理过
            .orderByHistoricTaskInstanceEndTime().desc();

    // 分页
    long total = query.count();
    List<HistoricTaskInstance> list = query.listPage(pageVO.getPageNo(), pageVO.getPageSize());
    return new PageResult<>(list, total);
}
```

**解读**：
- 第 4 行：`taskAssignee` 严格匹配 assignee（**不含候选人**）
- 第 5 行：`finished()` 限定为已完成
- **关键设计**：已办只看 assignee 维度，**候选人转交后不算"已办"**

## 4. 关键要点总结

- 待办用 `TaskQuery`（`act_ru_task`），已办用 `HistoricTaskInstanceQuery`（`act_hi_taskinst`）
- 待办查询用 `taskCandidateOrAssigned()` 兼容候选人和 assignee
- 关联数据（流程实例、用户、流程定义）用 Map 批量查询，避免 N+1
- ruoyi 提供 `/bpm/task/todo-page`、`/done-page`、`/my-page` 三种查询
- 我的发起用 `HistoricProcessInstanceQuery` + `startedBy(userId)`

## 5. 练习题

### 练习 1：基础（必做）

写 SQL：查 userId=1 的所有**待办任务**（在 act_ru_task 中）：
```sql
SELECT * FROM act_ru_task WHERE ??? ;
```

**参考答案**：见 `solutions/13-task-query.md`

### 练习 2：进阶

阅读 `BpmTaskServiceImpl.getTaskMyPage`，它如何同时查询待办和已办？是用 UNION 还是两个 query？

### 练习 3：挑战（选做）

新增"抄送我的"查询：实现 `BpmProcessInstanceCopyServiceImpl.getCopyToMePage(userId, pageVO)`，查询所有把 userId 抄送的流程。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmTaskController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
- Flowable 任务查询文档：https://www.flowable.com/open-source/docs/javadoc/org/flowable/engine/TaskService.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
