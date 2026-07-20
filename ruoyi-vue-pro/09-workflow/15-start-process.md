# 4.1 发起流程实例

> 理解 ruoyi 中"发起流程实例"（Start Process）的完整流程：API → Service → Flowable。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 `startProcessInstanceById` vs `startProcessInstanceByKey` 的区别
- 理解 ruoyi 启动流程时的"额外动作"：设置 startUserId、设置流程变量、保存业务数据
- 掌握 `BpmProcessInstanceServiceImpl.createProcessInstance` 的关键步骤
- 能用 Postman 创建一个流程实例

## 📚 前置知识

- ProcessInstance / RuntimeService（详见 [Flowable 概念](./02-flowable-concepts.md)）
- 表单变量（详见 [表单数据](./12-form-data.md)）
- 流程设计（详见 [Modeler](./05-modeler.md)）

## 1. 核心概念

### 1.1 启动流程的两种方式

| 方式 | 方法 | 行为 |
|------|------|------|
| **By Key** | `runtimeService.startProcessInstanceByKey("leave")` | 启动该 key 的**最新激活版本** |
| **By ID** | `runtimeService.startProcessInstanceById("leave:1:5001")` | 启动**指定版本** |
| **By Message** | `runtimeService.startProcessInstanceByMessage("msg")` | 通过消息事件触发 |

**ruoyi 偏好**：
- 默认用 `By ID`（避免版本歧义）
- 前端选流程时传**完整 ID**，而不是 key

### 1.2 启动时发生了什么？

```
[BpmProcessInstanceServiceImpl.createProcessInstance]
  ↓ 1. 校验流程定义存在
  ↓ 2. 校验 formId 合法
  ↓ 3. 注入 startUserId、startTime
  ↓ 4. 调用 runtimeService.startProcessInstanceById
  ↓
[Flowable RuntimeService]
  ↓ 1. 创建 act_ru_execution 记录
  ↓ 2. 创建 act_ru_task 记录（首个 UserTask）
  ↓ 3. 创建 act_ru_variable 记录（流程变量）
  ↓
[BpmTaskEventListener.taskCreated]  // 事件回调
  ↓ 1. 推送消息通知
  ↓ 2. 写自定义业务表（如 bpm_oa_leave）
  ↓
[前端] 待办列表自动刷新
```

### 1.3 ruoyi 的"启动人"机制

ruoyi 用**流程变量**（而非 `authenticatedUserId`）存启动人：

```java
variables.put(BpmnVariableConstants.PROCESS_INSTANCE_VARIABLE_START_USER_ID, userId);
```

**好处**：
- 流程历史可追溯（即使换了登录用户）
- 任何业务代码都能 `runtimeService.getVariable("PROCESS-INSTANCE-VARIABLE-START-USER-ID")` 拿到

## 2. 代码示例

### 2.1 发起流程（Java 代码）

```java
public String startProcess(Long userId, String processDefinitionId,
                            Map<String, Object> variables) {
    // 1. 设置发起人
    variables.put("PROCESS-INSTANCE-VARIABLE-START-USER-ID", userId);
    variables.put("PROCESS-INSTANCE-VARIABLE-START-TIME", new Date());

    // 2. 启动流程
    ProcessInstance pi = runtimeService.startProcessInstanceById(
        processDefinitionId, variables);

    return pi.getId();  // 返回流程实例 ID
}
```

### 2.2 通过 REST 接口发起

```bash
POST /admin-api/bpm/process-instance/create
{
  "processDefinitionId": "leave:1:5001",
  "variables": {
    "leaveType": "1",
    "days": 3,
    "reason": "回家探亲"
  }
}
```

**响应**：
```json
{
  "code": 0,
  "data": "55001"  // 流程实例 ID
}
```

### 2.3 常见错误：传了 key 而不是 ID

```java
// ❌ 错误：传了 key（如果将来有 v2，v1 的实例可能跑错版本）
runtimeService.startProcessInstanceByKey("leave", variables);

// ✅ 正确：传完整 ID（绑死版本）
runtimeService.startProcessInstanceById("leave:1:5001", variables);
```

## 3. 关键要点总结

- 启动流程用 `startProcessInstanceById()` 而非 ByKey（避免版本歧义）
- ruoyi 强制注入 `startUserId` 流程变量
- 启动时校验：流程定义、表单字段、变量合法性
- 启动后通过 `BpmTaskEventListener` 触发通知、写业务表
- 流程实例 ID 返回给前端，前端跳转到"我的流程"页

---

**文档版本**：v1.0
**最后更新**：2026-07-13
