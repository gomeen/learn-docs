# 1.2 Flowable 核心概念

> 掌握 Flowable 引擎的核心对象、Service API 与表结构，能定位到 ruoyi 集成的具体类。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 ProcessEngine、RepositoryService、RuntimeService、TaskService、HistoryService 五大服务
- 理解 Deployment、ProcessDefinition、ProcessInstance、Task、Execution、HistoricProcessInstance 之间的关系
- 掌握 Flowable 内置的核心表（ACT_RE_*、ACT_RU_*、ACT_HI_*、ACT_ID_*、ACT_GE_*）作用
- 能读懂 ruoyi 中调用 Flowable 服务的代码

## 📚 前置知识

- BPMN 2.0 基础（详见 [BPMN](./01-bpmn.md)）
- Spring Bean / 依赖注入（详见 [IoC](../02-spring-boot/01-ioc.md)）
- 关系型数据库基础（表、主外键）

## 1. 核心概念

### 1.1 五大 Service

| Service | 中文名 | 职责 | 常用方法 |
|---------|-------|------|---------|
| `RepositoryService` | 仓库服务 | 流程定义、部署、查询 | `createDeployment()`、`createProcessDefinitionQuery()` |
| `RuntimeService` | 运行时服务 | 启动流程、读运行时变量、操作执行 | `startProcessInstanceByKey()`、`getVariable()` |
| `TaskService` | 任务服务 | 我的任务、完成任务、转办 | `createTaskQuery()`、`complete()`、`addCandidateUser()` |
| `HistoryService` | 历史服务 | 已完成实例、节点历史 | `createHistoricProcessInstanceQuery()` |
| `ManagementService` | 管理服务 | 作业管理、数据库表 | `createJobQuery()` |

**关系图**：

```
ProcessEngine（流程引擎：所有 Service 的容器）
  ├─ RepositoryService   ── 静态资源（流程定义、部署包）
  ├─ RuntimeService      ── 运行时状态（执行流、变量）
  ├─ TaskService         ── 用户任务（待办、已办）
  ├─ HistoryService      ── 历史归档（完成后归档）
  └─ ManagementService   ── 后台作业（定时器、异步）
```

### 1.2 核心对象生命周期

```
[开发者] 部署 .bpmn20.xml
   ↓
[RepositoryService] Deployment（部署对象）
   ↓ 解析后
ProcessDefinition（流程定义，可被多次启动）
   ↓ 启动
[RuntimeService] startProcessInstanceByKey(...)
   ↓
ProcessInstance（流程实例 1 次申请 = 1 个实例）
   ├─ Execution（执行流，可能有多个：并行分支）
   └─ Task（用户任务，UserTask 时产生）
   ↓ 流程完成
[HistoryService] HistoricProcessInstance（历史归档）
```

### 1.3 Flowable 表前缀

| 前缀 | 含义 | 例子 |
|------|------|------|
| `ACT_RE_*` | REpository 仓库（流程定义、部署） | `ACT_RE_DEPLOYMENT`、`ACT_RE_PROCDEF` |
| `ACT_RU_*` | RUntime 运行时（执行、任务、变量） | `ACT_RU_TASK`、`ACT_RU_VARIABLE` |
| `ACT_HI_*` | HIstory 历史（完成的实例、节点） | `ACT_HI_PROCINST`、`ACT_HI_ACTINST` |
| `ACT_GE_*` | GEneral 通用（二进制、表结构） | `ACT_GE_BYTEARRAY` |
| `ACT_ID_*` | IDentity 身份（用户/组，可选） | `ACT_ID_USER`（ruoyi 不用 Flowable 自带身份） |

## 2. 代码示例

### 2.1 部署 + 启动 + 完成任务（最小闭环）

```java
// 1. 部署流程
Deployment deploy = repositoryService.createDeployment()
        .addClasspathResource("processes/leave.bpmn20.xml")
        .name("请假流程")
        .deploy();

// 2. 启动流程实例
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave",
        Map.of("startUserId", 1L, "days", 3));

// 3. 查询张三的待办
List<Task> tasks = taskService.createTaskQuery()
        .taskAssignee("1")
        .processInstanceId(pi.getId())
        .list();

// 4. 完成任务
taskService.complete(tasks.get(0).getId(),
        Map.of("approveResult", "agree"));
```

**说明**：四行核心代码串起"部署 → 启动 → 查询 → 完成"的完整生命周期。

### 2.2 常见错误：把 `taskService` 当成 `runtimeService`

```java
// ❌ 错误：用 TaskService 启动流程（TaskService 没有 start 方法）
taskService.startProcessInstanceByKey("leave");  // 编译报错

// ✅ 正确：启动流程属于运行时服务
runtimeService.startProcessInstanceByKey("leave");
```

### 2.3 常见错误：忘记释放 `historicProcessInstance`

```java
// ❌ 错误：频繁查询历史表导致数据库压力大
for (int i = 0; i < 1000; i++) {
    HistoricProcessInstance hi = historyService
        .createHistoricProcessInstanceQuery()
        .processInstanceId(id)
        .singleResult();
    // ... 用完未处理
}

// ✅ 正确：配合 PageResult 批量查询，并设置超时清理策略
// ruoyi 中通过 deleteHistoricData 等定时任务清理
```

## 3. 关键要点总结

- **五大 Service**：Repository（部署） / Runtime（运行时） / Task（待办） / History（历史） / Management（作业）
- **核心对象**：Deployment → ProcessDefinition → ProcessInstance → Task → HistoricProcessInstance
- **表前缀**：RE 仓库、RU 运行时、HI 历史、GE 通用
- ruoyi 在自己的 `*ServiceImpl` 中调用 Flowable 官方 Service，**通过 `@Resource` 注入**
- 启动流程用 `RuntimeService.startProcessInstanceByKey()`，完成任务用 `TaskService.complete()`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
