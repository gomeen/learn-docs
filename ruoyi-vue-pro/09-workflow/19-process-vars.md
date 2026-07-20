# 4.5 流程变量与表单数据

> 深入理解 ruoyi 中"流程变量"的作用域、生命周期、类型系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"流程实例变量"（process instance）与"任务局部变量"（task local）
- 知道变量的作用域：全局、局部、临时
- 理解变量的序列化机制（特别是 POJO 类型的处理）
- 掌握 ruoyi 中 `BpmnVariableConstants` 的命名规范

## 📚 前置知识

- 表单数据持久化（详见 [表单数据](./12-form-data.md)）
- 启动流程（详见 [启动流程](./15-start-process.md)）
- 审批操作（详见 [审批](./17-approval.md)）

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

## 3. 关键要点总结

- 流程变量分三类：全局变量（process instance）、局部变量（execution）、任务局部变量（task local）
- 变量名 = 表单字段名 = EL 引用名，**三者严格一致**
- 并行分支的变量**不共享**（独立 Execution）
- ruoyi 用 `BpmnVariableConstants` 集中管理变量名
- 业务变量与表单变量混合存，通过命名空间区分

---

**文档版本**：v1.0
**最后更新**：2026-07-13
