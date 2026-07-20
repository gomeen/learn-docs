# 5.1 多实例任务：会签/或签

> 深入理解 ruoyi 中"会签"、"或签"的多实例实现机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"会签"（Multi-Instance Sequential = false）和"或签"（Sequential = true）
- 知道多实例任务的 BPMN 配置：loopCardinality、completionCondition
- 理解 ruoyi 在 `BpmParallelMultiInstanceBehavior` 中的实现细节
- 能在 BPMN 设计中配置会签/或签

## 📚 前置知识

- 网关（详见 [网关](./22-gateway.md)）
- 流程变量（详见 [流程变量](./19-process-vars.md)）
- BPMN 2.0 Multi-Instance Task（详见 [BPMN](./01-bpmn.md)）

## 1. 核心概念

### 1.1 会签 vs 或签

| 维度 | 会签（Parallel Multi-Instance） | 或签（Sequential Multi-Instance） |
|------|-------------------------------|----------------------------------|
| **执行方式** | **所有**审批人同时收到任务 | 审批人**依次**审批 |
| **完成条件** | 全部 approve / 任一 reject | 全部 approve / 任一 reject（**按顺序**） |
| **场景** | 3 人同时审批一个合同 | 部门负责人 → HR → 财务 |
| **BPMN 属性** | `multiInstanceType="parallel"` | `multiInstanceType="sequential"` |

### 1.2 多实例任务的 BPMN 元素

```xml
<userTask id="approve" name="多人审批">
    <!-- 多实例配置 -->
    <multiInstanceLoopCharacteristics isSequential="false">
        <!-- 集合变量：审批人列表 -->
        <collection>${assignees}</collection>
        <!-- 当前元素变量 -->
        <loopDataInputRef>assignee</loopDataInputRef>
        <!-- 完成条件：3 人全部通过 -->
        <completionCondition>${nrOfCompletedInstances/nrOfInstances >= 1}</completionCondition>
    </multiInstanceLoopCharacteristics>
</userTask>
```

### 1.3 ruoyi 的实现思路

ruoyi 在 Flowable 的 `MultiInstanceBehavior` 基础上扩展：
- `BpmParallelMultiInstanceBehavior`：并行（会签）
- `BpmSequentialMultiInstanceBehavior`：串行（或签）
- 两者都通过 `BpmTaskCandidateInvoker` 计算候选用户
- 写入 `collectionVariable`（如 `ASSIGNEE_USER_IDS#approve`），`BpmUserTaskActivityBehavior` 读取

## 2. 代码示例

### 2.1 会签 BPMN 配置

```xml
<userTask id="approve" name="3人会签">
    <multiInstanceLoopCharacteristics
        isSequential="false"  <!-- 并行 -->
        collection="${assignees}"
        elementVariable="assignee">
        <completionCondition>${completeCount >= 3}</completionCondition>
    </multiInstanceLoopCharacteristics>
</userTask>
```

### 2.2 或签 BPMN 配置

```xml
<userTask id="approve" name="3人依次审批">
    <multiInstanceLoopCharacteristics
        isSequential="true"  <!-- 串行 -->
        collection="${assignees}"
        elementVariable="assignee">
        <completionCondition>${approved == true || rejected == true}</completionCondition>
    </multiInstanceLoopCharacteristics>
</userTask>
```

### 2.3 启动时传入 assignees

```java
Map<String, Object> variables = new HashMap<>();
variables.put("assignees", Arrays.asList(101L, 102L, 103L));  // 3 个审批人
ProcessInstance pi = runtimeService.startProcessInstanceByKey("contract-approve", variables);
```

### 2.4 常见错误：assignees 写成 String

```java
// ❌ 错误：传了字符串，Flowable 当成单个元素
variables.put("assignees", "101,102,103");
// 实际生成的 UserTask 只有 1 个，assignee = "101,102,103"

// ✅ 正确：传 List 或 Set
variables.put("assignees", Arrays.asList(101L, 102L, 103L));
// 生成 3 个 UserTask
```

## 3. 关键要点总结

- 会签 = `isSequential="false"`（并行）
- 或签 = `isSequential="true"`（串行）
- collection 必须是 `Collection<Long>`（userId 列表）
- ruoyi 用 `collectionVariable`（按 activityId 隔离）代替 `collectionExpression`
- `BpmSequentialMultiInstanceBehavior` 用 `LinkedHashSet` 保证顺序
- 减签需要业务层手动更新 collectionVariable + 取消 task

---

**文档版本**：v1.0
**最后更新**：2026-07-13
