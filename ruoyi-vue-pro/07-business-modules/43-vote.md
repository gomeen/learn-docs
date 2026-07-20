# 7.6.5 会签/或签

> 理解 ruoyi BPM 中的会签和或签（多人审批）模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握会签和或签的区别
- 理解 Flowable 中的多人审批配置
- 学会在 ruoyi 中配置会签/或签
- 能扩展自定义审批模式

## 📚 前置知识

- 流程定义 / 实例（详见 [流程定义](./39-process-def.md)、[流程实例](./41-process-instance.md)）
- BPMN 2.0 多实例任务（详见 [多实例](../09-workflow/21-multi-instance.md)）

## 1. 核心概念

### 1.1 会签 vs 或签

| 模式 | 说明 | 场景 |
|------|------|------|
| **会签** | 所有人都必须审批通过 | 重大决策（董事会审批） |
| **或签** | 任一人通过即可 | 部门内审（任一经理） |
| **比例会签** | 60% 通过即可 | 灵活审批 |

### 1.2 BPMN 多实例任务

Flowable 通过 **Multi-Instance Task**（多实例任务）实现会签/或签：

```xml
<userTask id="multiReview" name="多人审批">
    <multiInstanceLoopCharacteristics isSequential="false">
        <!-- 候选人集合 -->
        <loopDataInputRef>assigneeList</loopDataInputRef>
        <!-- 审批条件：所有人都通过 -->
        <completionCondition>
            ${nrOfCompletedInstances/nrOfInstances >= 0.6}
        </completionCondition>
    </multiInstanceLoopCharacteristics>
</userTask>
```

### 1.3 完成条件

- **或签**：`${nrOfCompletedInstances >= 1}`（一人通过即可）
- **会签**：`${nrOfCompletedInstances == nrOfInstances}`（全部通过）
- **比例**：`${nrOfCompletedInstances/nrOfInstances >= 0.6}`（60% 通过）

## 2. 代码示例

### 2.1 动态设置会签/或签

```java
// 在流程中通过变量控制
public void startMultiReview(DelegateExecution execution) {
    // 1. 根据业务选择审批人
    List<Long> approvers = getApprovers(execution);
    // 2. 设置多实例候选人
    execution.setVariable("approvers", approvers);
    // 3. 设置通过条件
    execution.setVariable("approveRatio", "0.6");  // 60%
}
```

### 2.2 ruoyi 中简化配置

```java
@Data
public class BpmTaskAssignRuleDO {
    private Long id;
    private Long modelId;
    private String taskDefinitionKey;  // 任务节点
    private Integer type;              // 分配类型
    private String options;            // 配置 JSON
    // type: 1-用户 2-角色 3-部门 4-用户组
}
```

### 2.3 审批通过逻辑

```java
public void onTaskComplete(DelegateTask task) {
    // 1. 获取任务的所有审批人
    List<Long> approvers = (List<Long>) task.getVariable("approvers");
    // 2. 获取已完成数量
    Integer completed = (Integer) task.getVariable("nrOfCompletedInstances");
    Integer total = approvers.size();
    // 3. 判断是否通过
    if (completed == null || total == null) return;
    double ratio = (double) completed / total;
    // 4. 比例达到阈值
    if (ratio >= 0.6) {
        // 流程继续
    } else {
        // 流程不流转
    }
}
```

## 3. 关键要点总结

- 会签/或签通过 BPMN 多实例任务实现
- `isSequential="false"`：并行（同时审批）
- `completionCondition`：完成条件
- ruoyi 通过 `BpmTaskAssignRule` 简化配置

---

**文档版本**：v1.0
**最后更新**：2026-07-13
