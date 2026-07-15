# 7.6.4 任务分配：角色/部门/用户

> 理解 ruoyi BPM 中任务分配（Task Assignment）的多种策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi BPM 任务分配的多种方式
- 理解角色、部门、用户组、自定义分配
- 学会配置候选人和候选组
- 能实现自定义任务分配

## 📚 前置知识

- 流程定义（详见 [流程定义](./33-process-def.md)）
- 流程实例（详见 [流程实例](./35-process-instance.md)）
- 角色（详见 [角色](./08-role.md)）
- 任务分配策略专题（详见 [任务分配](../09-workflow/21-task-assign.md)）

## 1. 核心概念

### 1.1 任务分配方式

| 方式 | 说明 | 适用 |
|------|------|------|
| 直接指定用户 | assignee = userId | 直属上级 |
| 候选用户 | candidateUsers | 多个候选之一 |
| 候选组 | candidateGroups | 角色/部门 |
| 自定义分配 | TaskListener 动态 | 复杂规则 |

### 1.2 ruoyi 用户组

`BpmUserGroup` 是一组用户的集合，可以在流程中使用：

```java
public class BpmUserGroupDO {
    private Long id;
    private String name;     // 组名
    private String code;     // 编码（用于候选组）
    private String userIds;  // 成员用户 ID（逗号分隔）
    private Integer status;
}
```

### 1.3 任务分配配置

在 BPMN 流程中配置：

```xml
<userTask id="managerApprove" name="直属领导审批">
    <candidateGroups>dept_manager</candidateGroups>  <!-- 部门经理组 -->
</userTask>
```

或者通过监听器动态分配：

```java
public class ManagerTaskListener implements TaskListener {
    @Override
    public void notify(DelegateTask task) {
        // 查询部门经理
        Long managerId = userService.getDeptManager(task.getVariable("deptId"));
        task.setAssignee(String.valueOf(managerId));
    }
}
```

## 2. 代码示例

### 2.1 用户组管理

```java
@PostMapping("/create")
public CommonResult<Long> createUserGroup(@Valid @RequestBody BpmUserGroupSaveReqVO createReqVO) {
    return success(userGroupService.createUserGroup(createReqVO));
}

@GetMapping("/list")
public CommonResult<List<BpmUserGroupRespVO>> getUserGroupList() {
    return success(userGroupService.getUserGroupList());
}
```

### 2.2 流程表达式

ruoyi 支持在流程中用表达式配置候选人：

```java
public class BpmProcessExpressionDO {
    private Long id;
    private String name;       // 表达式名
    private String expression; // 表达式（如 ${deptManager}）
    private String type;       // 类型
}
```

### 2.3 任务监听器

```java
public class BpmProcessListenerDO {
    private Long id;
    private String name;       // 监听器名
    private String type;       // 类型：execution/task
    private String event;      // 事件：start/end/create
    private String valueType;  // value 类型：class/delegateExpression
    private String value;      // 具体值
}
```

### 2.4 候选人分配示例

```java
// 在 Service 中根据流程变量动态分配
public void assignManagerTask(DelegateTask task) {
    // 1. 获取发起人部门
    Long startUserId = (Long) task.getVariable("startUserId");
    Long deptId = userService.getDeptId(startUserId);
    // 2. 查询部门经理
    Long managerId = userService.getDeptManager(deptId);
    // 3. 设置候选人
    task.setAssignee(String.valueOf(managerId));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmUserGroupController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmUserGroupController.java`

```java
@Tag(name = "管理后台 - 用户组")
@RestController
@RequestMapping("/bpm/user-group")
@Validated
public class BpmUserGroupController {

    @Resource
    private BpmUserGroupService userGroupService;

    @PostMapping("/create")
    public CommonResult<Long> createUserGroup(@Valid @RequestBody BpmUserGroupSaveReqVO createReqVO) {
        return success(userGroupService.createUserGroup(createReqVO));
    }

    @GetMapping("/list")
    public CommonResult<List<BpmUserGroupRespVO>> getUserGroupList() {
        return success(userGroupService.getUserGroupList());
    }
}
```

### 3.2 流程表达式

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmProcessExpressionController.java`

```java
@Tag(name = "管理后台 - 流程表达式")
@RestController
@RequestMapping("/bpm/process-expression")
@Validated
public class BpmProcessExpressionController {

    @PostMapping("/create")
    public CommonResult<Long> createProcessExpression(@Valid @RequestBody BpmProcessExpressionSaveReqVO createReqVO) {
        return success(expressionService.createProcessExpression(createReqVO));
    }
}
```

## 4. 关键要点总结

- ruoyi 支持多种任务分配方式
- 用户组用于候选组
- 表达式用于动态候选人
- 监听器用于复杂分配逻辑
- 候选人可以是角色/部门/用户

## 5. 练习题

### 练习 1：基础（必做）

阅读 `BpmUserGroupDO.java` 字段。

### 练习 2：进阶

阅读 `BpmTaskServiceImpl.java`，理解如何查询用户的待办任务（基于 assignee）。

### 练习 3：挑战（选做）

设计"多级审批"任务分配：第一级处理后，自动找到上级部门的经理作为第二级审批人。说明实现思路。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
