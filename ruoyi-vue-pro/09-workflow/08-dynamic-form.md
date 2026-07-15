# 3.1 动态表单 vs 表单设计器

> 理解 ruoyi 中的"动态表单"与"流程表单"的关系：表单作为流程节点的输入模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"动态表单"（Dynamic Form）和"流程表单"（Process Form）
- 知道 ruoyi 的 `BpmFormDO` 字段结构：JSON 配置 + 类型
- 理解"表单与流程节点"的多对多关联
- 能在 Model 中给每个 UserTask 绑定表单

## 📚 前置知识

- ruoyi BPM 模块结构（详见 [ruoyi 工作流](./03-ruoyi-workflow.md)）
- JSON 基础
- 业务侧动态表单概述（详见 [业务动态表单](../07-business-modules/34-dynamic-form.md)）

## 1. 核心概念

### 1.1 两种表单的对比

| 维度 | 动态表单（Dynamic Form） | 流程表单（Process Form） |
|------|----------------------|------------------|
| 含义 | 表单模板，定义字段、校验、布局 | 流程节点上的"具体表单" |
| 存放 | `bpm_form` 表（ruoyi 自己） | `act_re_model.META_INFO_.formId` |
| 数量 | 一个项目可建多个 | 一个 Model 节点绑定一个 |
| 用途 | **节点填写数据**、申请人填写 | **节点展示数据**、审批人查看 |

**关系**：流程表单 = 动态表单模板 + 流程节点绑定

### 1.2 ruoyi 动态表单的字段类型

```
BpmFormDO：
  id: 1024
  name: "请假申请单"
  status: 0  // 0=启用 1=禁用
  conf: "[{field:'name',label:'姓名',type:'Input',required:true}, ...]"  // JSON
  fields: ["name", "days", "reason"]  // 字段列表（解析自 conf）
  remark: "请填写请假信息"
```

**conf 字段** = 表单的 JSON Schema，类似 form-generator / form-create 的格式。

### 1.3 表单与流程节点的多对多关系

```
BpmForm（请假申请单）
   ├── 绑定到 BpmModel 的"提交"节点（用于申请人填写）
   ├── 绑定到 BpmModel 的"直属领导审批"节点（用于审批人查看）
   └── 绑定到 BpmModel 的"HR 审批"节点（用于审批人查看）
```

**关键**：一个表单**可以被多个节点使用**。不同节点可以绑定**不同表单**（如审批节点用"审批意见"表单）。

## 2. 代码示例

### 2.1 创建动态表单

```bash
POST /admin-api/bpm/form/create
{
  "name": "请假申请单",
  "status": 0,
  "conf": "[{\"field\":\"name\",\"label\":\"姓名\",\"type\":\"Input\",\"required\":true}]",
  "remark": "请填写请假信息"
}
```

**说明**：`conf` 字段是 JSON 数组，每项包含 field、label、type、required 等。

### 2.2 流程发起时传入表单数据

```java
// 用户在前端填完表单，提交时把数据作为流程变量传入
Map<String, Object> variables = new HashMap<>();
variables.put("name", "张三");
variables.put("days", 3);
variables.put("reason", "回家探亲");

ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave", variables);
```

**说明**：表单数据会作为**流程变量**保存到 `act_ru_variable` 表，可在审批节点中用 EL 表达式引用：`${name}`。

### 2.3 常见错误：表单字段名与变量名不一致

```json
// ❌ 错误：表单字段叫 user_name，但流程变量用的是 username
// 提交时：variables = { "username": "张三" }
// 审批时 EL 引用 ${user_name} 找不到值
```

```json
// ✅ 正确：表单字段名 = 流程变量名 = 审批中引用的变量名
// form conf: "field": "username"
// variables: "username": "张三"
// EL: ${username}
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmFormController：动态表单 CRUD

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`
**核心代码**（行 25-60）：

```java
@Tag(name = "管理后台 - 动态表单")
@RestController
@RequestMapping("/bpm/form")
@Validated
public class BpmFormController {

    @Resource
    private BpmFormService formService;

    @PostMapping("/create")
    @Operation(summary = "创建动态表单")
    @PreAuthorize("@ss.hasPermission('bpm:form:create')")
    public CommonResult<Long> createForm(@Valid @RequestBody BpmFormSaveReqVO createReqVO) {
        return success(formService.createForm(createReqVO));
    }

    @PutMapping("/update")
    @Operation(summary = "更新动态表单")
    @PreAuthorize("@ss.hasPermission('bpm:form:update')")
    public CommonResult<Boolean> updateForm(@Valid @RequestBody BpmFormSaveReqVO updateReqVO) {
        formService.updateForm(updateReqVO);
        return success(true);
    }

    @DeleteMapping("/delete")
    @Operation(summary = "删除动态表单")
    @Parameter(name = "id", description = "编号", required = true)
    @PreAuthorize("@ss.hasPermission('bpm:form:delete')")
    public CommonResult<Boolean> deleteForm(@RequestParam("id") Long id) {
        formService.deleteForm(id);
        return success(true);
    }
```

**解读**：
- 第 28 行：`/bpm/form` 路由下管理动态表单
- 第 36-39 行：创建表单
- 第 42-46 行：更新表单
- 第 49-55 行：删除表单
- **关键设计**：所有操作都先经过 `@PreAuthorize` 权限校验，**再走 Service**，分层清晰

### 3.2 BpmModelController 中表单的关联查询

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmModelController.java`
**核心代码**（行 70-80）：

```java
// 获得 Form 表单
Set<Long> formIds = convertSet(list, model -> {
    BpmModelMetaInfoVO metaInfo = BpmModelConvert.INSTANCE.parseMetaInfo(model);
    return metaInfo != null ? metaInfo.getFormId() : null;
});
Map<Long, BpmFormDO> formMap = formService.getFormMap(formIds);
```

**解读**：
- 第 70-74 行：从 Model 的 `meta_info` 字段解析出 `formId`（formId 是存在 `BpmModelMetaInfoVO` 中的业务字段）
- 第 75 行：`formService.getFormMap(formIds)` 一次查出所有 Form（**避免 N+1**）
- **关键设计**：Model 与 Form **通过 formId 关联**，而不是外键（因为 Flowable Model 表结构不能改）

## 4. 关键要点总结

- 动态表单（`BpmFormDO`） = 表单模板（conf JSON）
- 流程表单 = 动态表单 + 流程节点绑定
- 流程发起时，表单字段 = 流程变量，**字段名要一致**
- ruoyi 用 `formService.getFormMap()` 批量查询避免 N+1
- 表单与 Model 通过 `metaInfo.formId` 关联（非外键）

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 动态表单的 conf 字段存什么格式？
2. 表单数据提交后存在 Flowable 哪张表？
3. 审批节点中如何引用表单字段？

**参考答案**：见 `solutions/08-dynamic-form.md`

### 练习 2：进阶

阅读 `BpmFormServiceImpl.createForm`，说明它如何从 `conf` JSON 中提取 `fields` 列表（用于后续 EL 引用）。

### 练习 3：挑战（选做）

实现"表单预览"接口：传入 formId，返回渲染好的表单 JSON（便于前端 form-create / form-generator 解析）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/definition/BpmFormDO.java`
- form-create 官方文档：https://www.form-create.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
