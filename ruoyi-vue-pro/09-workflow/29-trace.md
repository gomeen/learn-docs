# 6.2 流程图高亮追踪

> 理解 BPMN 中"流程图高亮追踪"的实现：用历史节点回放流程状态。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道"流程图追踪"的业务场景
- 理解 `HistoricActivityInstance` 表的查询方式
- 掌握 ruoyi 在审批详情页中拼接"已完成节点 / 当前节点 / 待办节点"的方法
- 能用 Flowable API 拿到流程的"当前状态"

## 📚 前置知识

- 任务查询（详见 [任务查询](./16-task-query.md)）
- HistoryService（详见 [Flowable 概念](./02-flowable-concepts.md)）
- BPMN 节点（详见 [BPMN](./01-bpmn.md)）

## 1. 核心概念

### 1.1 流程图高亮追踪的两种状态

| 状态 | 来源 | 含义 |
|------|------|------|
| **已完成节点** | `act_hi_actinst` | 已经执行过的节点（绿色） |
| **当前节点** | `act_ru_task` / `act_ru_execution` | 正在执行的节点（黄色） |
| **未来节点** | BPMN XML 解析 | 还未执行的节点（灰色） |

### 1.2 实现思路

```
[审批详情页] /bpm/process-instance/detail?id=xxx
   ↓ 后端查询
1. BpmnModel bpmnModel = repositoryService.getBpmnModel(processDefinitionId);
   // 拿到完整 BPMN 模型（含所有节点）
2. List<HistoricActivityInstance> finished = historyService
       .createHistoricActivityInstanceQuery()
       .processInstanceId(piId)
       .finished()
       .list();
   // 历史已完成节点
3. List<Task> currentTasks = taskService.createTaskQuery()
       .processInstanceId(piId)
       .list();
   // 当前活跃任务
4. 组装为 Map<String, NodeStatus>：
   - 节点 ID → 已完成/进行中/未来
5. 返回给前端，前端用 bpmn.js 高亮
```

### 1.3 ruoyi 的 `BpmApprovalDetailRespVO`

ruoyi 把流程追踪信息封装为 VO：
- 流程基本信息
- 流程变量
- 节点状态列表
- 审批历史
- 当前用户可执行的操作

## 2. 代码示例

### 2.1 查询历史节点

```java
List<HistoricActivityInstance> activities = historyService
    .createHistoricActivityInstanceQuery()
    .processInstanceId(piId)
    .finished()  // 只查已完成的
    .orderByHistoricActivityInstanceStartTime().asc()
    .list();
```

### 2.2 查询当前活跃任务

```java
List<Task> currentTasks = taskService.createTaskQuery()
    .processInstanceId(piId)
    .active()
    .list();
```

### 2.3 拼装节点状态

```java
// 简化版：构建 activityId -> status 映射
Map<String, String> nodeStatus = new HashMap<>();
// 已完成节点 → "FINISHED"
finishedActivities.forEach(a -> nodeStatus.put(a.getActivityId(), "FINISHED"));
// 当前节点 → "RUNNING"
currentTasks.forEach(t -> nodeStatus.put(t.getTaskDefinitionKey(), "RUNNING"));
// 其他节点（来自 BpmnModel） → "WAITING"
```

### 2.4 常见错误：忽略并行分支的状态

```java
// ❌ 错误：只查主流程节点，忽略并行分支
List<HistoricActivityInstance> list = historyService.createHistoricActivityInstanceQuery()
    .processInstanceId(piId)
    .list();  // 包含所有分支的节点

// ✅ 正确：需要按 activityType 区分
List<HistoricActivityInstance> userTasks = historyService.createHistoricActivityInstanceQuery()
    .processInstanceId(piId)
    .activityType("userTask")  // 只看 UserTask
    .list();
```

## 3. 关键要点总结

- 流程图追踪 = 已完成节点 + 当前节点 + 未来节点
- 已完成：HistoryService 查 `act_hi_actinst`
- 当前：TaskService 查 `act_ru_task`
- 未来：BPMN XML 解析 + 排除已执行的
- ruoyi 用 `BpmApprovalDetailRespVO` 封装追踪信息（含流程实例、变量、节点状态）
- 前端用 bpmn.js 根据 status 高亮节点

---

**文档版本**：v1.0
**最后更新**：2026-07-13
