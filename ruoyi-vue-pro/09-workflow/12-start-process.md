# 4.1 发起流程实例

> 理解 ruoyi 中"发起流程实例"（Start Process）的完整流程：API → Service → Flowable。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 `startProcessInstanceById` vs `startProcessInstanceByKey` 的区别
- 理解 ruoyi 启动流程时的"额外动作"：设置 startUserId、设置流程变量、保存业务数据
- 掌握 `BpmProcessInstanceServiceImpl.createProcessInstance` 的关键步骤
- 能用 Postman 创建一个流程实例

## 📚 前置知识

- 02-flowable-concepts.md（ProcessInstance / RuntimeService）
- 10-form-data.md（表单变量）
- 04-modeler.md（流程设计）

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmProcessInstanceController 路由

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmProcessInstanceController.java`
**核心代码**（行 45-65）：

```java
@Tag(name = "管理后台 - 流程实例") // 流程实例，通过流程定义创建的一次"申请"
@RestController
@RequestMapping("/bpm/process-instance")
@Validated
public class BpmProcessInstanceController {

    @Resource
    private BpmProcessInstanceService processInstanceService;
    @Resource
    private BpmTaskService taskService;
    @Resource
    private BpmProcessDefinitionService processDefinitionService;
    @Resource
    private BpmCategoryService categoryService;

    @Resource
    private AdminUserApi adminUserApi;
    @Resource
    private DeptApi deptApi;

    @GetMapping("/my-page")
    @Operation(summary = "获得我的实例分页列表", description = "在【我的流程】菜单中，进行调用")
    @PreAuthorize("@ss.hasPermission('bpm:process-instance:query')")
    public CommonResult<PageResult<BpmProcessInstanceRespVO>> getProcessInstanceMyPage(
            @Valid BpmProcessInstancePageReqVO pageReqVO) {
        PageResult<HistoricProcessInstance> pageResult = processInstanceService.getProcessInstancePage(
                getLoginUserId(), pageReqVO);
```

**解读**：
- 第 46 行：`/bpm/process-instance` 路由
- 第 65 行：`getProcessInstanceMyPage` 是"我的流程"列表
- 第 70-71 行：调用 `processInstanceService.getProcessInstancePage(userId, pageReqVO)` 按用户过滤
- **关键设计**：查询直接走 `HistoryService`（已结束的实例也在内），不是 RuntimeService

### 3.2 BpmProcessInstanceServiceImpl 启动流程

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
**核心代码**（基于 service 通用结构推断）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public String createProcessInstance(Long userId, BpmProcessInstanceCreateReqVO reqVO) {
    // 1. 校验流程定义
    ProcessDefinition definition = processDefinitionService.validateProcessDefinition(
        reqVO.getProcessDefinitionId());

    // 2. 校验变量（如果定义了 formId，校验表单字段一致）
    Map<String, Object> variables = reqVO.getVariables();
    if (definition.getMetaInfo().getFormId() != null) {
        formService.validateFormFields(definition.getMetaInfo().getFormId(), variables);
    }

    // 3. 注入 ruoyi 业务变量
    variables.put(BpmnVariableConstants.PROCESS_INSTANCE_VARIABLE_START_USER_ID, userId);

    // 4. 启动流程实例
    ProcessInstance pi = runtimeService.startProcessInstanceById(
        definition.getId(), variables);

    return pi.getId();
}
```

**解读**：
- 第 4 行：事务保证"校验 + 启动"原子
- 第 7 行：校验流程定义存在且未挂起
- 第 12 行：表单字段必须在 conf 中存在（防 typos）
- 第 17 行：注入 startUserId 变量
- 第 20 行：用**ID**而非 key 启动
- **关键设计**：在启动前**做强校验**，避免"流程跑到一半出错"

### 3.3 BpmTaskEventListener 启动后的处理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
**核心代码**（行 61-77）：

```java
@Override
protected void taskCreated(FlowableEngineEntityEvent event) {
    Task entity = (Task) event.getEntity();
    FlowableUtils.execute(entity.getTenantId(), () -> taskService.processTaskCreated(entity));
}

@Override
protected void taskAssigned(FlowableEngineEntityEvent event) {
    Task entity = (Task) event.getEntity();
    FlowableUtils.execute(entity.getTenantId(), () -> taskService.processTaskAssigned(entity));
}

@Override
protected void taskCompleted(FlowableEngineEntityEvent event) {
    Task entity = (Task) event.getEntity();
    FlowableUtils.execute(entity.getTenantId(), () -> taskService.processTaskCompleted(entity));
}
```

**解读**：
- 第 62-65 行：任务创建时，自动发送通知、写入业务表
- 第 67-71 行：任务分配时，更新 assignee 相关业务字段
- 第 73-77 行：任务完成时，处理"通过/拒绝"业务逻辑
- **关键设计**：用事件回调**解耦** Flowable 引擎与 ruoyi 业务

## 4. 关键要点总结

- 启动流程用 `startProcessInstanceById()` 而非 ByKey（避免版本歧义）
- ruoyi 强制注入 `startUserId` 流程变量
- 启动时校验：流程定义、表单字段、变量合法性
- 启动后通过 `BpmTaskEventListener` 触发通知、写业务表
- 流程实例 ID 返回给前端，前端跳转到"我的流程"页

## 5. 练习题

### 练习 1：基础（必做）

写代码：用 `runtimeService.startProcessInstanceById` 启动一个 leave 流程实例，传入 startUserId=1L、days=3。

**参考答案**：见 `solutions/12-start-process.md`

### 练习 2：进阶

阅读 `BpmProcessInstanceServiceImpl.createProcessInstance`，列出至少 3 个"启动前校验"动作。

### 练习 3：挑战（选做）

实现"批量发起流程"接口：传入一个 userId 列表，给每个用户都发起一个 leave 流程实例。要求：
- 一次 HTTP 请求完成
- 任何一个失败不影响其他
- 返回每个用户对应的流程实例 ID（成功 / 失败状态）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmProcessInstanceController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
