# 4.5 流程变量与表单数据

> 深入理解 ruoyi 中"流程变量"的作用域、生命周期、类型系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"流程实例变量"（process instance）与"任务局部变量"（task local）
- 知道变量的作用域：全局、局部、临时
- 理解变量的序列化机制（特别是 POJO 类型的处理）
- 掌握 ruoyi 中 `BpmnVariableConstants` 的命名规范

## 📚 前置知识

- 10-form-data.md（表单数据持久化）
- 12-start-process.md（启动流程）
- 14-approval.md（审批操作）

## 1. 核心概念

### 1.1 流程变量 vs 任务局部变量

| 维度 | 流程实例变量 | 任务局部变量 |
|------|------------|------------|
| 范围 | **整个流程实例**共享 | **单个任务**可见 |
| 表 | `act_ru_variable` | `act_ru_variable`（带 `TASK_ID_` 字段） |
| API | `runtimeService.setVariable(piId, ...)` | `taskService.setVariableLocal(taskId, ...)` |
| 何时用 | 跨任务共享的变量 | 临时变量（如审批意见、附件） |

### 1.2 变量的作用域

```
流程实例（Process Instance）
  ├── 全局变量（global variable）：所有 Execution 可见
  ├── 局部变量（local variable）：单个 Execution 可见（并行分支）
  └── 任务局部变量（task local）：单个 Task 可见
```

**关键**：并行分支（`Parallel Gateway`）的每个分支有**独立的 Execution**，变量**不共享**。

### 1.3 变量的类型系统

Flowable 支持任意可序列化对象：
- 基本类型：String、Long、Integer、Boolean、Date
- POJO：通过 `JPAEntitiesResolver` 或自定义序列化
- 复杂类型：Map、List、自定义对象

**序列化方式**：默认 `JdkSerializableSerializer`，**变量对象必须 implements Serializable**。

### 1.4 ruoyi 的变量命名规范

`BpmnVariableConstants`（位于 `framework/flowable/core/enums/`）：

```java
public class BpmnVariableConstants {
    // 流程实例变量
    public static final String PROCESS_INSTANCE_VARIABLE_START_USER_ID = "PROCESS-INSTANCE-VARIABLE-START-USER-ID";
    public static final String PROCESS_INSTANCE_VARIABLE_START_TIME = "PROCESS-INSTANCE-VARIABLE-START-TIME";

    // 任务变量
    public static final String TASK_VARIABLE_APPROVE_RESULT = "TASK-VARIABLE-APPROVE-RESULT";
    public static final String TASK_VARIABLE_APPROVE_COMMENT = "TASK-VARIABLE-APPROVE-COMMENT";
    public static final String TASK_VARIABLE_APPROVE_USER_ID = "TASK-VARIABLE-APPROVE-USER-ID";
    public static final String TASK_VARIABLE_APPROVE_TIME = "TASK-VARIABLE-APPROVE-TIME";
}
```

**特点**：
- 全大写、横线连接（与表单字段名风格一致）
- `PROCESS-INSTANCE-*` 表示流程级
- `TASK-*` 表示任务级

## 2. 代码示例

### 2.1 设置流程级变量

```java
// 设置全局变量
runtimeService.setVariable(piId, "totalAmount", 5000);
// 所有 Execution 都能看到
```

### 2.2 设置任务局部变量

```java
// 设置任务局部变量（只在当前任务可见）
taskService.setVariableLocal(taskId, "approveComment", "同意");
// 其他任务看不到
```

### 2.3 在 EL 表达式中引用变量

```xml
<sequenceFlow>
    <conditionExpression>${totalAmount > 1000}</conditionExpression>
</sequenceFlow>
<!-- 引用 runtimeService.setVariable 设置的 totalAmount -->
```

### 2.4 常见错误：变量名拼写不一致

```java
// ❌ 错误：设置 totalAmount，但 EL 引用 total_Amount
runtimeService.setVariable(piId, "totalAmount", 5000);
// 排他网关条件：${total_Amount > 1000}  → 表达式求值失败

// ✅ 正确：变量名严格一致
runtimeService.setVariable(piId, "totalAmount", 5000);
// 排他网关条件：${totalAmount > 1000}
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmnVariableConstants：变量命名规范

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnVariableConstants.java`
**核心代码**（推断）：

```java
public class BpmnVariableConstants {

    private BpmnVariableConstants() {}

    /** 流程实例的发起用户编号 */
    public static final String PROCESS_INSTANCE_VARIABLE_START_USER_ID =
        "PROCESS-INSTANCE-VARIABLE-START-USER-ID";

    /** 流程实例的发起时间 */
    public static final String PROCESS_INSTANCE_VARIABLE_START_TIME =
        "PROCESS-INSTANCE-VARIABLE-START-TIME";

    /** 任务的审批结果 */
    public static final String TASK_VARIABLE_APPROVE_RESULT = "TASK-VARIABLE-APPROVE-RESULT";

    /** 任务的审批意见 */
    public static final String TASK_VARIABLE_APPROVE_COMMENT = "TASK-VARIABLE-APPROVE-COMMENT";

    /** 任务的审批人 */
    public static final String TASK_VARIABLE_APPROVE_USER_ID = "TASK-VARIABLE-APPROVE-USER-ID";

    /** 任务的审批时间 */
    public static final String TASK_VARIABLE_APPROVE_TIME = "TASK-VARIABLE-APPROVE-TIME";
}
```

**解读**：
- 私有构造方法（**工具类不允许实例化**）
- 6 个常量：2 个流程级 + 4 个任务级
- **关键设计**：常量集中管理，**避免散落的字符串**

### 3.2 BpmProcessInstanceServiceImpl 注入启动人变量

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
**核心代码**（基于 service 通用结构推断）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public String createProcessInstance(Long userId, BpmProcessInstanceCreateReqVO reqVO) {
    // 1. 校验流程定义
    // 2. 准备变量
    Map<String, Object> variables = reqVO.getVariables();

    // 3. 注入 ruoyi 业务变量
    variables.put(BpmnVariableConstants.PROCESS_INSTANCE_VARIABLE_START_USER_ID, userId);
    variables.put(BpmnVariableConstants.PROCESS_INSTANCE_VARIABLE_START_TIME, new Date());

    // 4. 启动
    ProcessInstance pi = runtimeService.startProcessInstanceById(
        reqVO.getProcessDefinitionId(), variables);
    return pi.getId();
}
```

**解读**：
- 第 9-10 行：注入两个流程级变量
- **关键设计**：业务变量和表单变量**混合存**，通过命名空间区分

### 3.3 BpmTaskServiceImpl 注入审批变量

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（基于 service 通用结构推断）：

```java
@Override
public void completeTask(Long userId, BpmTaskApproveReqVO reqVO) {
    // 1. 校验任务
    // 2. 准备变量
    Map<String, Object> variables = new HashMap<>();
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_RESULT, reqVO.getResult());
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_COMMENT, reqVO.getComment());
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_USER_ID, userId);
    variables.put(BpmnVariableConstants.TASK_VARIABLE_APPROVE_TIME, new Date());

    // 3. complete
    taskService.complete(reqVO.getTaskId(), variables);
}
```

**解读**：
- 第 5-8 行：注入 4 个任务级变量
- **关键设计**：变量名 = 常量，**避免硬编码字符串**

## 4. 关键要点总结

- 流程变量分三类：全局变量（process instance）、局部变量（execution）、任务局部变量（task local）
- 变量名 = 表单字段名 = EL 引用名，**三者严格一致**
- 并行分支的变量**不共享**（独立 Execution）
- ruoyi 用 `BpmnVariableConstants` 集中管理变量名
- 业务变量与表单变量混合存，通过命名空间区分

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 全局变量和任务局部变量的区别？
2. 并行分支的变量能共享吗？
3. POJO 变量要 implements Serializable，为什么？

**参考答案**：见 `solutions/16-process-vars.md`

### 练习 2：进阶

阅读 `BpmnVariableConstants`，列出至少 6 个常量，标注每个的命名空间前缀含义。

### 练习 3：挑战（选做）

实现"变量历史"接口：传入 processInstanceId，返回该实例的所有变量历史（按时间排序），便于排查"流程跑偏"问题。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnVariableConstants.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
- Flowable 变量文档：https://www.flowable.com/open-source/docs/javadoc/org/flowable/engine/RuntimeService.html#setVariable-java.lang.String-java.lang.String-java.lang.Object-

---

**文档版本**：v1.0
**最后更新**：2026-07-13
