# 2.2 流程定义部署

> 深入理解 ruoyi 中"流程部署"的完整链路：JSON 模型 → BPMN XML → Deployment → ProcessDefinition。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"部署"（Deployment）和"流程定义"（ProcessDefinition）的关系
- 理解 ruoyi 部署时的"前置校验"：审批人配置、节点完整性
- 掌握"部署一次生成 N 个 ProcessDefinition"的机制（同 key 多次部署产生历史版本）
- 能定位 ruoyi 中 `modelService.deployModel(id)` 的实现

## 📚 前置知识

- 设计器与 Model（详见 [Modeler](./05-modeler.md)）
- Deployment / ProcessDefinition（详见 [Flowable 概念](./02-flowable-concepts.md)）
- 版本管理（详见 [版本](./07-version.md)）

## 1. 核心概念

### 1.1 部署的本质

"部署" = 把流程定义**写入 Flowable 引擎**，包含三件事：
1. 把 BPMN XML 保存到 `act_ge_bytearray` 表（`BYTES_` 字段）
2. 在 `act_re_deployment` 表插入一条记录
3. 在 `act_re_procdef` 表插入一条 **ProcessDefinition** 记录

**关键**：每次部署都会产生**新的 Deployment + 新的 ProcessDefinition**（同 key 也会共存）。

### 1.2 版本号的产生

`ProcessDefinition.VERSION_` 由 Flowable 自动维护：**同 key 第一次部署 = version 1，第二次部署 = version 2**。旧版本不会被删除，而是 `SUSPENSION_STATE_ = 2`（挂起）。

```
部署 leave v1 → ACT_RE_PROCDEF: key=leave, version=1, deployment_id=D1
部署 leave v2 → ACT_RE_PROCDEF: key=leave, version=2, deployment_id=D2
                ACT_RE_PROCDEF: key=leave, version=1, SUSPENSION_STATE_=2
```

### 1.3 ruoyi 部署时做的额外校验

ruoyi 在 `BpmTaskCandidateInvoker.validateBpmnConfig()`（行 57-80）中校验：

| 校验项 | 错误码 |
|--------|-------|
| 每个 UserTask 是否配置了审批人策略 | `MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG` |
| 策略参数是否必填且已填 | 同上 |
| 节点是否有未连接的边 | `MODEL_DEPLOY_FAIL_BPMN_INVALID` |

**目的**：避免"流程启动后找不到审批人而卡住"。

## 2. 代码示例

### 2.1 ruoyi 部署流程的 Java 代码（简化版）

```java
// Service 层的 deploy 方法大致逻辑
public void deployModel(String modelId) {
    // 1. 读取 Model
    Model model = repositoryService.getModel(modelId);
    byte[] bpmnBytes = SimpleModelUtils.convertToBpmnXml(
        model.getEditorJson(), model.getName(), model.getKey());

    // 2. 校验 BPMN
    bpmTaskCandidateInvoker.validateBpmnConfig(bpmnBytes);

    // 3. 部署
    Deployment deployment = repositoryService.createDeployment()
        .name(model.getName())
        .addBytes(model.getKey() + ".bpmn20.xml", bpmnBytes)
        .deploy();

    // 4. 关联 Model 与 Deployment（ruoyi 业务字段）
    processDefinitionService.createProcessDefinition(deployment, model);
}
```

**说明**：
- 第 4 行：`addBytes` 第一个参数是"资源名称"，Flowable 要求以 `.bpmn20.xml` 结尾才能识别为 BPMN
- 第 8 行：部署后，ruoyi 会在自己 `bpm_process_definition` 表保存额外业务字段（分类、表单 ID 等）

### 2.2 启动流程时使用"最新版本"

```java
// Flowable 默认 startProcessInstanceByKey 用最新版本
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave");

// 如需启动指定版本
ProcessInstance pi = runtimeService.startProcessInstanceById(
    "leave:1:5001"  // 格式：key:version:deployment_id_derived
);
```

### 2.3 常见错误：直接覆盖部署

```java
// ❌ 错误：试图"覆盖"旧版本（Flowable 没有这个概念）
repositoryService.createDeployment()
    .addBytes(...)  // 这会创建新的 deployment + 新的 version
    .deploy();

// ✅ 正确：意识到每次部署都是"新版本"
```

## 3. 关键要点总结

- 部署 = `repositoryService.createDeployment().addBytes(...).deploy()`
- 同 key 多次部署产生**多版本**，Flowable 用 `SUSPENSION_STATE_` 标记旧版本
- 部署时 BPMN 资源名必须以 `.bpmn20.xml` 结尾
- ruoyi 在部署前**强制校验审批人配置**，未配置则拒绝部署
- 启动流程用 `startProcessInstanceByKey()` 默认走**最新版本**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
