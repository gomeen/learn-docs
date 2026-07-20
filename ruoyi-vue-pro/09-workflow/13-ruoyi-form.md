# 3.4 ruoyi 的 Form 设计

> 深入理解 ruoyi 的表单设计器：从前端可视化编辑到后端存储的完整链路。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 ruoyi 用 form-create / form-generator 作为前端表单设计器
- 理解 conf JSON 的标准化结构
- 区分"表单设计态"与"表单使用态"
- 能在 ruoyi 中扩展自定义组件

## 📚 前置知识

- 动态表单 / 组件 / 数据（详见 [动态表单](./10-dynamic-form.md)、[表单组件](./11-form-components.md)、[表单数据](./12-form-data.md)）
- Vue.js / form-create（详见 [Vue3 基础](../11-frontend/01-vue3-basics.md)）

## 1. 核心概念

### 1.1 表单设计态 vs 使用态

```
【设计态】 管理员在 /bpm/form/index 页面拖拽字段 → 保存为 conf JSON
   ↓
【使用态】 员工在"发起请假"页面看到表单渲染（按 conf JSON 渲染组件）
   ↓ 提交
【归档态】 流程变量存在 Flowable
```

### 1.2 ruoyi 的表单设计器技术选型

| 库 | 用途 |
|----|------|
| **form-create** | 动态生成表单（Vue 2） |
| **@form-create/naive-ui** | form-create 的 Naive UI 实现 |
| **form-create-designer** | 可视化设计器 |

**ruoyi 的做法**：
- 后端只存 conf JSON（不关心前端具体实现）
- 前端按 Vue 2 / Vue 3 选用不同 form-create 适配器

### 1.3 conf 字段的"双向"作用

**保存时**：从设计器读取 conf JSON → 后端 BpmFormDO.conf

**渲染时**：后端返回 conf JSON → 前端用 form-create 解析 → 渲染为表单

**这种设计的优势**：
- 后端不耦合前端技术栈
- 表单可被"导出 JSON → 复制到其他系统"复用
- 任何改动都不需要发版（改 JSON 即可）

## 2. 代码示例

### 2.1 完整 conf JSON 示例（带"字段权限"扩展）

```json
[
  {
    "field": "leaveType",
    "label": "请假类型",
    "type": "Select",
    "required": true,
    "options": [
      { "value": "1", "label": "事假" },
      { "value": "2", "label": "病假" }
    ],
    "permission": "EDIT"
  },
  {
    "field": "approveComment",
    "label": "审批意见",
    "type": "Textarea",
    "permission": "READ"
  },
  {
    "field": "salary",
    "label": "薪资",
    "type": "InputNumber",
    "permission": "HIDDEN"  // 敏感字段，员工看不见
  }
]
```

**说明**：
- `permission=EDIT`：可编辑
- `permission=READ`：只读
- `permission=HIDDEN`：隐藏

### 2.2 前端 form-create 渲染（伪代码）

```js
import formCreate from '@form-create/naive-ui'
import api from '@/api/bpm/form'

// 1. 拉取表单配置
const confJson = await api.getForm(formId)

// 2. 用 form-create 渲染
const form = formCreate.create({
  json: JSON.parse(confJson)  // 重点：传 conf JSON
})

// 3. 用户填写后提交
form.submit(async (formData) => {
  // formData = { leaveType: "1", days: 3, ... }
  await api.startProcess({ ...formData, processDefinitionKey: 'leave' })
})
```

### 2.3 常见错误：conf JSON 中包含函数

```json
// ❌ 错误：conf 中放了函数（序列化丢失）
{ "field": "total", "type": "InputNumber", "compute": "(a, b) => a + b" }

// ✅ 正确：把 compute 逻辑放到后端 EL 表达式
// 或在前端自定义组件中实现
```

## 3. 关键要点总结

- ruoyi 用 form-create 作为前端表单引擎，conf JSON 是前后端的"协议"
- conf JSON 标准化：field/label/type/options/required/rules/props/permission
- BpmFormDO 冗余存 `fields` 字符串（写时计算、读时高效）
- 字段权限（READ/EDIT/HIDDEN）实现"字段级权限"
- conf JSON 中不能放函数（序列化丢失），业务逻辑用后端 EL 表达式

---

**文档版本**：v1.0
**最后更新**：2026-07-13
