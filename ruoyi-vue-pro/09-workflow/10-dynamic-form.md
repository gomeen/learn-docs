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
- 业务侧动态表单概述（详见 [业务动态表单](../07-business-modules/40-dynamic-form.md)）

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

## 3. 关键要点总结

- 动态表单（`BpmFormDO`） = 表单模板（conf JSON）
- 流程表单 = 动态表单 + 流程节点绑定
- 流程发起时，表单字段 = 流程变量，**字段名要一致**
- ruoyi 用 `formService.getFormMap()` 批量查询避免 N+1
- 表单与 Model 通过 `metaInfo.formId` 关联（非外键）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
