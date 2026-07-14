# 2.1 流程设计器：Modeler 集成

> 理解 ruoyi 如何集成 Flowable Modeler（bpmn.js 流程设计器），实现"画流程图 → 生成 XML → 保存到数据库"。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 ruoyi 的"流程设计器"是 bpmn.js（前端）+ Flowable Model（后端）的组合
- 理解 Model、Deployment、ProcessDefinition 的关系
- 掌握 ruoyi 提供的 `/bpm/model/*` 路由的作用
- 能找到"设计流程图"对应到 ruoyi 的具体代码位置

## 📚 前置知识

- 01-bpmn.md（BPMN 规范）
- 02-flowable-concepts.md（Model / Deployment 对象）
- 前端基础：知道 bpmn.js、Vue

## 1. 核心概念

### 1.1 Flowable Modeler 是什么？

**Flowable Modeler** 是官方提供的 Web 端流程设计器，本质是一个**集成 bpmn.js 的 Vue/Angular 应用**。它允许用户：
- 在网页上**拖拽**节点（Start、User、Service、Gateway、End）
- 配置**审批人**、**表单**、**监听器**
- 一键**保存为 BPMN XML** 到后端

### 1.2 ruoyi 的"简化版"设计器

ruoyi **没有直接用 Flowable 官方 Modeler**，而是自己封装了一个"简化模型"（`BpmSimpleModelNodeVO`）：

| 维度 | 官方 Modeler | ruoyi 自研 |
|------|------------|----------|
| 节点类型 | 全 BPMN | 简化（Start/User/End/Exclusive/Parallel/ServiceTask） |
| 存储格式 | 完整 BPMN XML | **简化 JSON**（保存到 `act_de_model` 的 `model_editor_json` 字段） |
| 部署时 | 直接部署 XML | **后端转回**标准 BPMN XML 再部署 |
| 扩展性 | 改 bpmn.js 源码 | 改 ruoyi 自己的 `SimpleModelUtils` |

**为什么这么做？**
- 前端不必实现完整的 BPMN 规范
- ruoyi 可以加入自己的"审批人策略"等业务概念
- 用户体验更简洁

### 1.3 Model → ProcessDefinition 的生命周期

```
用户在前端画流程（拖拽节点）
   ↓ POST /bpm/model/create  保存简化 JSON 到 act_de_model
Model（Flowable 表 ACT_RE_MODEL）
   ↓ POST /bpm/model/deploy  触发"简化 JSON → BPMN XML"转换
BpmSimpleModelUtils.convertToBpmnXml(json)
   ↓
Deployment（ACT_RE_DEPLOYMENT）
   ↓
ProcessDefinition（ACT_RE_PROCDEF）
   ↓ 可被 startProcessInstanceByKey 启动
```

## 2. 代码示例

### 2.1 创建一个 Model

```bash
POST /admin-api/bpm/model/create
{
  "name": "请假流程",
  "key": "leave",
  "category": "oa",
  "formId": 1024
}
```

**说明**：
- `name`：流程名称
- `key`：流程 key（用于 `startProcessInstanceByKey(key)`）
- `category`：分类
- `formId`：关联的动态表单 ID

### 2.2 部署 Model 到 Flowable

```bash
POST /admin-api/bpm/model/deploy?id=2001
```

**说明**：传入 Model 的 ID，后端会：
1. 读取 `model_editor_json` 字段
2. 调用 `SimpleModelUtils.convertToBpmnXml()` 转 BPMN XML
3. 调用 `repositoryService.createDeployment().addBytes(...).deploy()`

### 2.3 常见错误：未配置审批人策略就部署

```bash
# ❌ 错误：模型中某个 UserTask 没设置审批人
POST /bpm/model/deploy
# 响应：500 "审批人未配置"

# ✅ 正确：每个 UserTask 都配置候选人策略（指定用户/角色/部门/发起人等）
```

**原因**：`BpmTaskCandidateInvoker.validateBpmnConfig()` 在部署前会校验（详见 `BpmTaskCandidateInvoker.java` 第 57-80 行）。

## 3. ruoyi 仓库源码解读

### 3.1 BpmModelController：Model 的入口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmModelController.java`
**核心代码**（行 41-80）：

```java
@Tag(name = "管理后台 - 流程模型")
@RestController
@RequestMapping("/bpm/model")
@Validated
public class BpmModelController {

    @Resource
    private BpmModelService modelService;
    @Resource
    private BpmFormService formService;
    @Resource
    private BpmCategoryService categoryService;
    @Resource
    private BpmProcessDefinitionService processDefinitionService;

    @Resource
    private AdminUserApi adminUserApi;
    @Resource
    private DeptApi deptApi;

    @GetMapping("/list")
    @Operation(summary = "获得模型分页")
    @Parameter(name = "name", description = "模型名称", example = "芋艿")
    public CommonResult<List<BpmModelRespVO>> getModelList(@RequestParam(value = "name", required = false) String name) {
        List<Model> list = modelService.getModelList(name);
        if (CollUtil.isEmpty(list)) {
            return success(Collections.emptyList());
        }

        // 获得 Form 表单
        Set<Long> formIds = convertSet(list, model -> {
            BpmModelMetaInfoVO metaInfo = BpmModelConvert.INSTANCE.parseMetaInfo(model);
            return metaInfo != null ? metaInfo.getFormId() : null;
        });
        Map<Long, BpmFormDO> formMap = formService.getFormMap(formIds);
```

**解读**：
- 第 43 行：`/bpm/model` 是 Model 操作的根路由
- 第 64 行：`getModelList` 接收 `name` 参数做模糊查询
- 第 71-74 行：从 Model 的 `metaInfo` 字段解析出 formId（每个 Model 可绑定一个动态表单）
- 第 75 行：批量获取 Form，避免 N+1 查询
- **关键设计**：路由层只做"拼装数据"，不写业务逻辑，所有 `modelService.getModelList(name)` 等操作下沉到 Service

### 3.2 BpmProcessDefinitionController：已部署流程的查询

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmProcessDefinitionController.java`
**核心代码**（行 39-60）：

```java
@Tag(name = "管理后台 - 流程定义")
@RestController
@RequestMapping("/bpm/process-definition")
@Validated
public class BpmProcessDefinitionController {

    @Resource
    private BpmProcessDefinitionService processDefinitionService;
    @Resource
    private BpmFormService formService;
    @Resource
    private BpmCategoryService categoryService;

    @GetMapping("/page")
    @Operation(summary = "获得流程定义分页")
    @PreAuthorize("@ss.hasPermission('bpm:process-definition:query')")
    public CommonResult<PageResult<BpmProcessDefinitionRespVO>> getProcessDefinitionPage(
            BpmProcessDefinitionPageReqVO pageReqVO) {
        PageResult<ProcessDefinition> pageResult = processDefinitionService.getProcessDefinitionPage(pageReqVO);
        if (CollUtil.isEmpty(pageResult.getList())) {
            return success(PageResult.empty(pageResult.getTotal()));
        }
```

**解读**：
- 第 41 行：`/bpm/process-definition` 是已部署定义的查询入口
- 第 54 行：`@PreAuthorize` 权限校验
- 第 56-57 行：直接调用 `processDefinitionService.getProcessDefinitionPage()`，**返回的是 Flowable 原生 `ProcessDefinition`**
- **关键设计**：Model（设计态）和 ProcessDefinition（运行态）**是两套独立资源**，分别在不同 Controller 维护

## 4. 关键要点总结

- ruoyi **没有直接用 Flowable 官方 Modeler**，自己实现了"简化模型 + 后端转 BPMN"
- 流程图存储在 `act_de_model`（Flowable Model 表）的 `model_editor_json` 字段（JSON 格式）
- 部署时：JSON → BPMN XML → Deployment → ProcessDefinition
- 部署前会校验"审批人是否配置"，未配置则抛 `MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG`
- 路由层：Model 在 `/bpm/model`，ProcessDefinition 在 `/bpm/process-definition`

## 5. 练习题

### 练习 1：基础（必做）

阅读 `BpmModelController.java`，列出至少 6 个接口路径，并标注哪些是"写"操作（创建/更新/部署），哪些是"读"操作（列表/详情）。

**参考答案**：见 `solutions/04-modeler.md`

### 练习 2：进阶

阅读 `framework/flowable/core/util/SimpleModelUtils.java`，找到 `convertToBpmnXml` 方法（简化模型 → BPMN XML 的转换器）。说明该方法大致做了哪些事？是否支持并行网关？

### 练习 3：挑战（选做）

为 ruoyi 增加一个"导入 BPMN XML"功能：用户上传 `.bpmn20.xml` 文件，ruoyi 自动转换为简化 JSON 并创建 Model。要求写出 Controller 层的核心代码。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmModelController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmProcessDefinitionController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
- bpmn.js 官方文档：https://bpmn.io/toolkit/bpmn-js/
- Flowable Modeler 源码：https://github.com/flowable/flowable-engine/tree/main/modules/flowable-ui/modeler

---

**文档版本**：v1.0
**最后更新**：2026-07-13
