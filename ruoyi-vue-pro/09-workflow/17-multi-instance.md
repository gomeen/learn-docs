# 5.1 多实例任务：会签/或签

> 深入理解 ruoyi 中"会签"、"或签"的多实例实现机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"会签"（Multi-Instance Sequential = false）和"或签"（Sequential = true）
- 知道多实例任务的 BPMN 配置：loopCardinality、completionCondition
- 理解 ruoyi 在 `BpmParallelMultiInstanceBehavior` 中的实现细节
- 能在 BPMN 设计中配置会签/或签

## 📚 前置知识

- 18-gateway.md（网关）
- 16-process-vars.md（流程变量）
- BPMN 2.0 Multi-Instance Task 规范

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmParallelMultiInstanceBehavior：并行多实例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmParallelMultiInstanceBehavior.java`
**核心代码**（行 21-50）：

```java
/**
 * 自定义的【并行】的【多个】流程任务的 assignee 负责人的分配
 * 第一步，基于分配规则，计算出分配任务的【多个】候选人们。
 * 第二步，将【多个】任务候选人们，设置到 DelegateExecution 的 collectionVariable 变量中，以便 BpmUserTaskActivityBehavior 使用它
 */
@Setter
public class BpmParallelMultiInstanceBehavior extends ParallelMultiInstanceBehavior {

    private BpmTaskCandidateInvoker taskCandidateInvoker;

    public BpmParallelMultiInstanceBehavior(Activity activity,
                                            AbstractBpmnActivityBehavior innerActivityBehavior) {
        super(activity, innerActivityBehavior);
        // 在解析/构造阶段基于 activityId 初始化与 activity 绑定且不变的字段，避免在运行期修改 Behavior 实例状态
        super.collectionExpression = null; // collectionExpression 和 collectionVariable 是互斥的
        super.collectionVariable = FlowableUtils.formatExecutionCollectionVariable(activity.getId());
        // 从 execution.getVariable() 读取当前所有任务处理的人的 key
        super.collectionElementVariable = FlowableUtils.formatExecutionCollectionElementVariable(activity.getId());
    }
```

**解读**：
- 第 31 行：继承 `ParallelMultiInstanceBehavior`（Flowable 官方）
- 第 33 行：注入 ruoyi 的 `BpmTaskCandidateInvoker`
- 第 40 行：collectionExpression 置 null（**与 collectionVariable 互斥**）
- 第 41 行：使用 `FlowableUtils.formatExecutionCollectionVariable` 生成集合变量名（按 activityId 隔离）
- **关键设计**：构造时**初始化不可变字段**，避免运行时修改 Behavior 状态

### 3.2 BpmSequentialMultiInstanceBehavior：串行多实例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmSequentialMultiInstanceBehavior.java`
**核心代码**（行 28-60）：

```java
/**
 * 自定义的【串行】的【多个】流程任务的 assignee 负责人的分配
 * 本质上，实现和 {@link BpmParallelMultiInstanceBehavior} 一样，只是继承的类不一样
 */
@Setter
public class BpmSequentialMultiInstanceBehavior extends SequentialMultiInstanceBehavior {

    private BpmTaskCandidateInvoker taskCandidateInvoker;

    public BpmSequentialMultiInstanceBehavior(Activity activity, AbstractBpmnActivityBehavior innerActivityBehavior) {
        super(activity, innerActivityBehavior);
        super.collectionExpression = null;
        super.collectionVariable = FlowableUtils.formatExecutionCollectionVariable(activity.getId());
        super.collectionElementVariable = FlowableUtils.formatExecutionCollectionElementVariable(activity.getId());
    }

    @Override
    protected int resolveNrOfInstances(DelegateExecution execution) {
        // 情况一：UserTask 节点
        if (execution.getCurrentFlowElement() instanceof UserTask) {
            @SuppressWarnings("unchecked")
            Set<Long> assigneeUserIds = (Set<Long>) execution.getVariableLocal(super.collectionVariable, Set.class);
            if (assigneeUserIds == null) {
                // 使用 LinkedHashSet 保证顺序
                assigneeUserIds = new LinkedHashSet<>(taskCandidateInvoker.calculateUsersByTask(execution));
```

**解读**：
- 第 29 行：继承 `SequentialMultiInstanceBehavior`
- 第 56 行：从 `execution.getVariableLocal` 读取已分配的审批人（**避免重复分配**）
- 第 60 行：使用 `LinkedHashSet`（**保证顺序**），这就是串行的关键
- **关键设计**：复用 Parallel 行为逻辑，**只换 collection 容器**（LinkedHashSet vs HashSet）

### 3.3 减签的实现思路

**减签** = 在 `assignees` 集合中删除一个 userId。但 Flowable 不会自动更新已创建的任务，需要：
1. 减少 `collectionVariable` 中的元素
2. 取消（complete with reject）被减签人的 task

```java
// 简化代码
public void removeSignUser(String taskId, Long userId) {
    // 1. 找到当前 task 的 collectionVariable
    // 2. 移除 userId
    // 3. 取消对应 userId 的 task
}
```

**注意**：Flowable 6/7 没有内置"减签" API，**需要业务层封装**。

## 4. 关键要点总结

- 会签 = `isSequential="false"`（并行）
- 或签 = `isSequential="true"`（串行）
- collection 必须是 `Collection<Long>`（userId 列表）
- ruoyi 用 `collectionVariable`（按 activityId 隔离）代替 `collectionExpression`
- `BpmSequentialMultiInstanceBehavior` 用 `LinkedHashSet` 保证顺序
- 减签需要业务层手动更新 collectionVariable + 取消 task

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 会签和或签的 BPMN 区别在哪里？
2. collection 必须传什么类型？
3. 完成条件怎么写"3 人全部通过"？

**参考答案**：见 `solutions/17-multi-instance.md`

### 练习 2：进阶

阅读 `BpmParallelMultiInstanceBehavior.resolveNrOfInstances` 完整实现（行 57+），解释它如何处理"审批人为空"的情况。

### 练习 3：挑战（选做）

实现"减签"接口：传入 taskId 和 userId，从 collection 中移除该 userId 并取消对应 task。要求事务保证一致性。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmParallelMultiInstanceBehavior.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmSequentialMultiInstanceBehavior.java`
- BPMN 2.0 多实例规范：https://www.omg.org/spec/BPMN/2.0/#P1411

---

**文档版本**：v1.0
**最后更新**：2026-07-13
