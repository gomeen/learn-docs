# 5.5 用户任务分配：候选人/候选组

> 深入理解 BPMN 中"用户任务分配"的 7 种 ruoyi 策略：指定用户、角色、部门、发起人、表达式等。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 的 7 种候选策略
- 知道每种策略的应用场景
- 理解 `BpmTaskCandidateStrategy` 接口的设计
- 能在 BPMN 中选用合适的策略

## 📚 前置知识

- ruoyi 工作流架构（详见 [ruoyi 工作流](./03-ruoyi-workflow.md)）
- 任务查询（详见 [任务查询](./16-task-query.md)）
- Task（详见 [Flowable 概念](./02-flowable-concepts.md)）
- 角色 / 部门（详见 [角色](../07-business-modules/08-role.md)、[部门](../07-business-modules/10-dept.md)）

## 1. 核心概念

### 1.1 ruoyi 的 7 种候选策略

| 策略 | 枚举 | 用途 |
|------|------|------|
| **指定用户** | `USER` | 审批人固定 |
| **指定角色** | `ROLE` | 某角色的所有人 |
| **部门成员** | `DEPT_MEMBER` | 某部门的所有人 |
| **部门负责人** | `DEPT_LEADER` | 某部门的 leader |
| **发起人** | `START_USER` | 流程发起人自己审 |
| **发起人部门负责人** | `START_USER_DEPT_LEADER` | 发起人所在部门 leader |
| **表单内用户** | `FORM_USER` | 从表单字段读取 |
| **自定义表达式** | `EXPRESSION` | SpEL 表达式 |

**Flowable 原生** vs **ruoyi 扩展**：

| 概念 | Flowable | ruoyi |
|------|---------|-------|
| **单个 assignee** | `assignee="userId"` | 通过 `candidateStrategy=USER, candidateParam=101` |
| **多个候选** | `candidateUsers="1,2,3"` | 策略类自动展开 |
| **候选组** | `candidateGroups="hr"` | 通过 `candidateStrategy=ROLE, candidateParam=2` |

### 1.2 策略接口

```java
public interface BpmTaskCandidateStrategy {
    BpmTaskCandidateStrategyEnum getStrategy();
    void validateParam(String param);
    default boolean isParamRequired() { return true; }
    Set<Long> calculateUsers(String param, DelegateExecution execution);
}
```

**关键方法**：`calculateUsers` 根据参数计算**候选用户集合**。

### 1.3 策略调用入口

`BpmTaskCandidateInvoker` 是所有策略的"路由器"：
- 注入 `List<BpmTaskCandidateStrategy>`
- 根据 `BpmTaskCandidateStrategyEnum` 路由到具体策略
- 提供 `validateBpmnConfig()` 校验策略配置

## 2. 代码示例

### 2.1 "指定用户"策略实现

```java
@Component
public class BpmTaskCandidateUserStrategy implements BpmTaskCandidateStrategy {

    @Override
    public BpmTaskCandidateStrategyEnum getStrategy() {
        return BpmTaskCandidateStrategyEnum.USER;
    }

    @Override
    public void validateParam(String param) {
        Assert.notNull(Long.parseLong(param), "用户编号不能为空");
    }

    @Override
    public Set<Long> calculateUsers(String param, DelegateExecution execution) {
        return CollUtil.newHashSet(Long.parseLong(param));
    }
}
```

### 2.2 "部门负责人"策略实现（简化）

```java
@Component
public class BpmTaskCandidateDeptLeaderStrategy extends AbstractBpmTaskCandidateDeptLeaderStrategy {

    @Override
    public BpmTaskCandidateStrategyEnum getStrategy() {
        return BpmTaskCandidateStrategyEnum.DEPT_LEADER;
    }

    @Override
    public Set<Long> calculateUsers(String param, DelegateExecution execution) {
        // 1. param = 部门 ID
        // 2. 调用 DeptApi.getDept(deptId).leaderUserId
        return CollUtil.newHashSet(deptApi.getDept(Long.parseLong(param)).getLeaderUserId());
    }
}
```

### 2.3 常见错误：策略参数忘了

```java
// ❌ 错误：选了"指定用户"但没填用户
candidateStrategy = "USER"
candidateParam = ""
// 部署时抛 MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG

// ✅ 正确
candidateStrategy = "USER"
candidateParam = "101"
```

## 3. 关键要点总结

- ruoyi 提供 7+ 种候选策略，分 4 大类
- 策略通过 `BpmTaskCandidateStrategy` 接口实现
- `BpmTaskCandidateInvoker` 用 Map 路由（O(1) 查找）
- 部署时 `validateBpmnConfig` 校验所有 UserTask 都有策略
- 自定义属性 `candidateStrategy` / `candidateParam` 存在 BPMN 扩展元素中
- 新增策略只需写一个 `@Component` 类，**Invoker 零修改**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
