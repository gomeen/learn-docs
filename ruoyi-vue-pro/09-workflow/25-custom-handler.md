# 6.3 自定义任务处理器

> 理解 ruoyi 中"自定义任务处理器"的扩展机制：实现自己的 ApprovalType、ProcessEventHandler。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 ruoyi 中"自动审批"（无人参与）的实现
- 理解"自定义候选人策略"如何注册
- 掌握"自定义监听器"的注入方式
- 能在自己的业务中扩展工作流

## 📚 前置知识

- 多实例（详见 [多实例](./17-multi-instance.md)）
- 监听器（详见 [监听器](./20-listener.md)）
- 候选策略（详见 [任务分配](./21-task-assign.md)）

## 1. 核心概念

### 1.1 自定义任务处理器的 4 大类

| 扩展点 | 父类/接口 | 用途 |
|--------|----------|------|
| **自定义候选人策略** | `BpmTaskCandidateStrategy` | 增加新的审批人分配规则 |
| **自定义节点行为** | `UserTaskActivityBehavior` | 改变 task 创建逻辑 |
| **自定义监听器** | `TaskListener` / `ExecutionListener` | 监听特定事件 |
| **自动审批** | `BpmUserTaskApproveTypeEnum` | 无人参与审批 |

### 1.2 自动审批

BPMN 中某些节点可以**自动通过**（如"自动审核"节点）：
- `AUTO_APPROVE`：进入节点时自动通过
- `AUTO_REJECT`：进入节点时自动拒绝

ruoyi 的实现：在 `BpmUserTaskActivityBehavior.handleAssignments` 中检查 `approveType`。

### 1.3 自定义节点行为的应用

**典型场景**：
- 任务创建时自动加签
- 任务完成时同步到其他系统
- 任务分配时根据规则动态计算 assignee

实现方式：继承 `UserTaskActivityBehavior` 或 `MultiInstanceBehavior`，重写相关方法。

## 2. 代码示例

### 2.1 自定义候选人策略

```java
@Component
public class BpmTaskCandidateMyStrategy implements BpmTaskCandidateStrategy {

    @Override
    public BpmTaskCandidateStrategyEnum getStrategy() {
        // 1. 在 BpmTaskCandidateStrategyEnum 中新增枚举值
        // 2. 返回这个枚举
        return BpmTaskCandidateStrategyEnum.MY_STRATEGY;
    }

    @Override
    public Set<Long> calculateUsers(String param, DelegateExecution execution) {
        // 自己的业务逻辑
        return CollUtil.newHashSet(101L);
    }
}
```

### 2.2 自定义节点行为（自动审批）

```java
@Component
public class AutoApproveUserTaskBehavior extends UserTaskActivityBehavior {
    @Override
    protected void handleAssignments(...) {
        Integer approveType = BpmnModelUtils.parseApproveType(userTask);
        if (approveType == BpmUserTaskApproveTypeEnum.AUTO_APPROVE.getType()) {
            // 自动通过：直接 complete，不创建 task
            // 实际上 ruoyi 在 BpmUserTaskActivityBehavior 中处理
        } else {
            super.handleAssignments(...);
        }
    }
}
```

### 2.3 自定义监听器

```java
@Component
public class MyTaskListener implements TaskListener {
    @Override
    public void notify(DelegateTask task) {
        if ("complete".equals(task.getEventName())) {
            // 任务完成时同步到业务系统
            externalSystem.sync(task.getProcessInstanceId());
        }
    }
}
```

### 2.4 常见错误：自定义策略未注册到枚举

```java
// ❌ 错误：自定义策略但没在 BpmTaskCandidateStrategyEnum 加枚举
public BpmTaskCandidateStrategyEnum getStrategy() {
    return BpmTaskCandidateStrategyEnum.MY_STRATEGY;  // 编译报错：枚举不存在
}

// ✅ 正确：先在 BpmTaskCandidateStrategyEnum 中加枚举
public enum BpmTaskCandidateStrategyEnum {
    USER, ROLE, ..., MY_STRATEGY  // 新增
}
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmUserTaskActivityBehavior 钩子方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmUserTaskActivityBehavior.java`
**核心代码**（行 31-60）：

```java
/**
 * 自定义的【单个】流程任务的 assignee 负责人的分配
 * 第一步，基于分配规则，计算出分配任务的【单个】候选人。如果找不到，则直接报业务异常，不继续执行后续的流程；
 * 第二步，随机选择一个候选人，则选择作为 assignee 负责人。
 */
@Slf4j
public class BpmUserTaskActivityBehavior extends UserTaskActivityBehavior {

    @Setter
    private BpmTaskCandidateInvoker taskCandidateInvoker;

    public BpmUserTaskActivityBehavior(UserTask userTask) {
        super(userTask);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    protected void handleAssignments(TaskService taskService, String assignee, String owner,
        List<String> candidateUsers, List<String> candidateGroups, TaskEntity task, ExpressionManager expressionManager,
        DelegateExecution execution, ProcessEngineConfigurationImpl processEngineConfiguration) {
        // 第一步，获得任务的候选用户
        Long assigneeUserId = calculateTaskCandidateUsers(execution);
        // 第二步，设置作为负责人
        if (assigneeUserId != null) {
            TaskHelper.changeTaskAssignee(task, String.valueOf(assigneeUserId));
        }
    }
```

**解读**：
- 第 32 行：继承 `UserTaskActivityBehavior`（Flowable 官方）
- 第 42-50 行：覆盖 `handleAssignments` 钩子方法
- 第 47 行：调用自己的 `calculateTaskCandidateUsers`（下方方法）
- **关键设计**：用"模板方法模式"插入 ruoyi 业务逻辑

### 3.2 BpmActivityBehaviorFactory：Behavior 工厂

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmActivityBehaviorFactory.java`
**核心代码**（基于同 package service 推断）：

```java
public class BpmActivityBehaviorFactory extends DefaultActivityBehaviorFactory {

    @Autowired
    private BpmTaskCandidateInvoker taskCandidateInvoker;

    @Override
    public UserTaskActivityBehavior createUserTaskActivityBehavior(UserTask userTask) {
        // 1. 判断是否多实例
        if (userTask.getLoopCharacteristics() != null) {
            if (userTask.getLoopCharacteristics().isSequential()) {
                return new BpmSequentialMultiInstanceBehavior(userTask, ...);
            } else {
                return new BpmParallelMultiInstanceBehavior(userTask, ...);
            }
        }
        // 2. 单实例：返回 ruoyi 自定义 Behavior
        BpmUserTaskActivityBehavior behavior = new BpmUserTaskActivityBehavior(userTask);
        behavior.setTaskCandidateInvoker(taskCandidateInvoker);
        return behavior;
    }
}
```

**解读**：
- 继承 `DefaultActivityBehaviorFactory`（Flowable 官方）
- 覆盖 `createUserTaskActivityBehavior` 工厂方法
- **关键设计**：用**工厂模式**注册自定义 Behavior

### 3.3 全局事件监听器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
**核心代码**（行 38-65）：

```java
@Component
@Slf4j
public class BpmTaskEventListener extends AbstractFlowableEngineEventListener {

    @Resource
    @Lazy
    private BpmModelService modelService;
    @Resource
    @Lazy
    private BpmTaskService taskService;

    public static final Set<FlowableEngineEventType> TASK_EVENTS = ImmutableSet.<FlowableEngineEventType>builder()
            .add(FlowableEngineEventType.TASK_CREATED)
            .add(FlowableEngineEventType.TASK_ASSIGNED)
            .add(FlowableEngineEventType.TASK_COMPLETED)
            .add(FlowableEngineEventType.ACTIVITY_CANCELLED)
            .add(FlowableEngineEventType.TIMER_FIRED)
            .build();

    public BpmTaskEventListener() {
        super(TASK_EVENTS);
    }
```

**解读**：
- 继承 `AbstractFlowableEngineEventListener`（Flowable 官方）
- 在 `BpmFlowableConfiguration` 中注册到 ProcessEngine
- **关键设计**：用 `@Component` 让 Spring 自动注册，**无需手动注册**

## 4. 关键要点总结

- 4 大扩展点：候选人策略、节点行为、监听器、自动审批
- 候选人策略：实现 `BpmTaskCandidateStrategy` 接口 + 注册枚举
- 节点行为：继承 `UserTaskActivityBehavior` + 用 `BpmActivityBehaviorFactory` 工厂
- 监听器：实现 `TaskListener` + BPMN 中配置
- 自动审批：在 `BpmUserTaskActivityBehavior` 中检查 `approveType`
- **关键设计**：用 Spring `@Component` 自动注册，**零配置**

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 自定义候选人策略要实现哪个接口？
2. 自定义节点行为要继承哪个类？
3. 监听器如何注册到 Flowable 引擎？

**参考答案**：见 `solutions/25-custom-handler.md`

### 练习 2：进阶

阅读 `BpmActivityBehaviorFactory` 完整实现，说明它如何区分"单实例"、"并行多实例"、"串行多实例"。

### 练习 3：挑战（选做）

新增"按工号段分配"策略：当申请人的工号是 1001-2000 范围时，分配给"部门A"；2001-3000 范围分配给"部门B"。要求写出策略类、注册枚举、测试用例。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmUserTaskActivityBehavior.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmActivityBehaviorFactory.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
- Flowable 扩展文档：https://www.flowable.com/open-source/docs/javadoc/org/flowable/engine/impl/bpmn/parser/factory/ActivityBehaviorFactory.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
