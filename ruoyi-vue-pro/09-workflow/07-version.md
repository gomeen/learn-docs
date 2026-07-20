# 2.3 流程版本管理

> 理解 ruoyi 中流程定义的版本控制：同 key 多次部署产生的多版本、如何查询/激活/挂起指定版本。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flowable 中"版本"由 `VERSION_` 字段自增维护
- 区分"激活"（suspensionState=1）和"挂起"（suspensionState=2）
- 知道 ruoyi 在 `BpmProcessDefinitionService` 中如何查询版本列表
- 能用 SQL 查 `act_re_procdef` 表的所有版本

## 📚 前置知识

- 部署原理（详见 [部署](./06-deploy.md)）
- Deployment / ProcessDefinition（详见 [Flowable 概念](./02-flowable-concepts.md)）

## 1. 核心概念

### 1.1 版本号自动生成

`act_re_procdef` 表的关键字段：

| 字段 | 含义 | 示例 |
|------|------|------|
| `ID_` | 主键 | `leave:2:50002` |
| `REV_` | 乐观锁版本 | 1 |
| `CATEGORY_` | 分类 | `oa` |
| `NAME_` | 流程名称 | `请假流程` |
| `KEY_` | 流程 key | `leave` |
| `VERSION_` | 版本号 | 2 |
| `DEPLOYMENT_ID_` | 部署 ID | `50001` |
| `SUSPENSION_STATE_` | 状态 | 1=激活，2=挂起 |
| `DERIVED_VERSION_` | 衍生版本 | 0 |

**主键生成规则**：`{key}:{version}:{derived_version}:{timestamp-derived}`

### 1.2 激活 vs 挂起

- **激活（Active）**：流程可以被 `startProcessInstanceByKey()` 启动
- **挂起（Suspended）**：流程不能被启动，已启动的实例也不能继续流转

**用途**：
- 旧版本自动挂起（防止"未完成实例跑到新版本"）
- 紧急情况下管理员可手动挂起新版本

### 1.3 ruoyi 对版本的封装

ruoyi 通过 `BpmProcessDefinitionService` 提供：
- `getProcessDefinitionPage()`：分页查询（含版本号、分类等）
- `getActiveProcessDefinition(key)`：获取指定 key 的**最新激活版本**
- `updateProcessDefinitionState(id, state)`：激活/挂起

**`bpm_process_definition_info` 表**（ruoyi 自己的表）：
- 存储"业务字段"：category、formId、description 等
- 与 `act_re_procdef.ID_` 关联

## 2. 代码示例

### 2.1 查询所有版本

```java
List<ProcessDefinition> list = repositoryService.createProcessDefinitionQuery()
    .processDefinitionKey("leave")
    .orderByProcessDefinitionVersion().desc()
    .list();
// 输出：[v2, v1]（按版本倒序）
```

### 2.2 挂起 / 激活

```java
// 挂起
repositoryService.suspendProcessDefinitionById("leave:1:50001");

// 激活
repositoryService.activateProcessDefinitionById("leave:1:50001");
```

### 2.3 常见错误：用 key 启动流程但忘记 key 有多版本

```java
// ❌ 错误：以为 processDefinitionKey() 启动的是特定版本
// 实际：Flowable 默认启动该 key 的最新激活版本
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave");

// ✅ 正确：明确指定版本（通过 ID 而非 key）
ProcessInstance pi = runtimeService.startProcessInstanceById("leave:2:50002");
```

## 3. 关键要点总结

- Flowable 用 `VERSION_` 自增管理版本，**同 key 多次部署产生多版本**
- 旧版本自动挂起（`SUSPENSION_STATE_=2`），防止"未完成实例跳版本"
- 启动流程用 key 会默认走"最新激活版本"，用 ID 可指定具体版本
- ruoyi 的 `BpmProcessDefinitionService` 提供分页查询、激活/挂起 API
- ruoyi 自己在 `bpm_process_definition_info` 表保存业务字段（category、formId 等）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
