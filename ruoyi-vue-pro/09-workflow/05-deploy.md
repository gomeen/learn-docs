# 2.2 流程定义部署

> 深入理解 ruoyi 中"流程部署"的完整链路：JSON 模型 → BPMN XML → Deployment → ProcessDefinition。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"部署"（Deployment）和"流程定义"（ProcessDefinition）的关系
- 理解 ruoyi 部署时的"前置校验"：审批人配置、节点完整性
- 掌握"部署一次生成 N 个 ProcessDefinition"的机制（同 key 多次部署产生历史版本）
- 能定位 ruoyi 中 `modelService.deployModel(id)` 的实现

## 📚 前置知识

- 设计器与 Model（详见 [Modeler](./04-modeler.md)）
- Deployment / ProcessDefinition（详见 [Flowable 概念](./02-flowable-concepts.md)）
- 版本管理（详见 [版本](./06-version.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 部署校验逻辑

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/BpmTaskCandidateInvoker.java`
**核心代码**（行 51-80）：

```java
/**
 * 校验流程模型的任务分配规则全部都配置了
 * 目的：如果有规则未配置，会导致流程任务找不到负责人，进而流程无法进行下去！
 *
 * @param bpmnBytes BPMN XML
 */
public void validateBpmnConfig(byte[] bpmnBytes) {
    BpmnModel bpmnModel = BpmnModelUtils.getBpmnModel(bpmnBytes);
    assert bpmnModel != null;
    List<UserTask> userTaskList = BpmnModelUtils.getBpmnModelElements(bpmnModel, UserTask.class);
    // 遍历所有的 UserTask，校验审批人配置
    userTaskList.forEach(userTask -> {
        // 1.1 非人工审批，无需校验审批人配置
        Integer approveType = BpmnModelUtils.parseApproveType(userTask);
        if (ObjectUtils.equalsAny(approveType,
                BpmUserTaskApproveTypeEnum.AUTO_APPROVE.getType(),
                BpmUserTaskApproveTypeEnum.AUTO_REJECT.getType())) {
            return;
        }
        // 1.2 非空校验
        Integer strategy = BpmnModelUtils.parseCandidateStrategy(userTask);
        String param = BpmnModelUtils.parseCandidateParam(userTask);
        if (strategy == null) {
            throw exception(MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG, userTask.getName());
        }
        BpmTaskCandidateStrategy candidateStrategy = getCandidateStrategy(strategy);
        if (candidateStrategy.isParamRequired() && StrUtil.isBlank(param)) {
            throw exception(MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG, userTask.getName());
        }
```

**解读**：
- 第 58 行：用 `BpmnModelUtils.getBpmnModel` 解析 XML
- 第 60 行：拿到所有 UserTask
- 第 64-68 行：**自动审批**（无人参与）跳过校验
- 第 71-75 行：strategy 不能为空，否则抛 `MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG`
- 第 76-79 行：策略如果需要参数（如"指定用户"需要 userId），参数不能为空
- **关键设计**：把"审批人配置"问题在**部署阶段就发现**，而不是运行时"找不到审批人"

### 3.2 BpmModelServiceImpl 中的部署入口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmModelServiceImpl.java`（deployModel 方法）
**核心代码**（基于同 package 其他 service 推断）：

```java
@Service
@Validated
@Slf4j
public class BpmModelServiceImpl implements BpmModelService {

    @Resource
    private RepositoryService repositoryService;     // Flowable 部署
    @Resource
    private BpmTaskCandidateInvoker taskCandidateInvoker;  // 校验候选人
    @Resource
    private BpmProcessDefinitionService processDefinitionService;  // 创建业务定义
    @Resource
    private ModelRepository modelRepository;  // 操作 act_de_model 表

    public String deployModel(String modelId) {
        // 1. 读取 Model（Flowable Model + ruoyi 业务字段）
        // 2. JSON → BPMN XML 转换
        // 3. 校验 BPMN
        // 4. repositoryService.createDeployment()...
        // 5. processDefinitionService.createProcessDefinition(...)
        return deployment.getId();
    }
}
```

**解读**：
- ruoyi 的 deploy 是**"两步"**：先在 Flowable 创建 Deployment，再在 ruoyi 自己的 `bpm_process_definition_info` 表保存业务字段
- **关键设计**：Flowable 只存"流程图"，ruoyi 自己的表存"业务元数据"（分类、表单 ID、图标等）

## 4. 关键要点总结

- 部署 = `repositoryService.createDeployment().addBytes(...).deploy()`
- 同 key 多次部署产生**多版本**，Flowable 用 `SUSPENSION_STATE_` 标记旧版本
- 部署时 BPMN 资源名必须以 `.bpmn20.xml` 结尾
- ruoyi 在部署前**强制校验审批人配置**，未配置则拒绝部署
- 启动流程用 `startProcessInstanceByKey()` 默认走**最新版本**

## 5. 练习题

### 练习 1：基础（必做）

解释 `repositoryService.createDeployment().addBytes("leave.bpmn20.xml", bytes).deploy();` 中三个方法的作用。

**参考答案**：见 `solutions/05-deploy.md`

### 练习 2：进阶

阅读 `BpmTaskCandidateInvoker.validateBpmnConfig` 后续 50 行代码，解释"具体策略校验"（行 80+）做了哪些事？举出至少 2 种策略的校验逻辑。

### 练习 3：挑战（选做）

写一个定时任务，每天凌晨 2 点清理 30 天前部署的、`SUSPENSION_STATE_=2`（旧版本）的 ProcessDefinition。要求写出 `@Scheduled` 注解 + MyBatis 删除逻辑。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/BpmTaskCandidateInvoker.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmModelServiceImpl.java`
- Flowable 部署章节：https://www.flowable.com/open-source/docs/bpmn/ch14-API/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
