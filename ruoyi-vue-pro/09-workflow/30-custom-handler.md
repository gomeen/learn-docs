# 6.3 自定义任务处理器

> 理解 ruoyi 中"自定义任务处理器"的扩展机制：实现自己的 ApprovalType、ProcessEventHandler。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 ruoyi 中"自动审批"（无人参与）的实现
- 理解"自定义候选人策略"如何注册
- 掌握"自定义监听器"的注入方式
- 能在自己的业务中扩展工作流

## 📚 前置知识

- 多实例（详见 [多实例](./21-multi-instance.md)）
- 监听器（详见 [监听器](./24-listener.md)）
- 候选策略（详见 [任务分配](./25-task-assign.md)）

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

## 3. 关键要点总结

- 4 大扩展点：候选人策略、节点行为、监听器、自动审批
- 候选人策略：实现 `BpmTaskCandidateStrategy` 接口 + 注册枚举
- 节点行为：继承 `UserTaskActivityBehavior` + 用 `BpmActivityBehaviorFactory` 工厂
- 监听器：实现 `TaskListener` + BPMN 中配置
- 自动审批：在 `BpmUserTaskActivityBehavior` 中检查 `approveType`
- **关键设计**：用 Spring `@Component` 自动注册，**零配置**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
