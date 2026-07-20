# 3.2 表单组件库

> 理解 ruoyi 动态表单的组件库：基于 form-create / form-generator 的字段类型系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 动态表单支持的所有字段类型（Input、Select、DatePicker、Upload 等）
- 理解 conf JSON 的字段结构：field、label、type、options、required、rules
- 知道如何扩展自定义组件
- 能看懂一份完整的表单 conf 配置

## 📚 前置知识

- 动态表单基础（详见 [动态表单](./10-dynamic-form.md)）
- Vue / 前端表单（详见 [Element Form](../11-frontend/13-element-form.md)）

## 1. 核心概念

### 1.1 ruoyi 动态表单的字段类型

ruoyi 的动态表单基于 **form-create**（Vue 2）/ **form-create / naive-ui** 风格，字段类型丰富：

| 类别 | 字段类型 | 用途 |
|------|---------|------|
| **输入类** | `Input`、`InputNumber`、`Textarea` | 文本/数字输入 |
| **选择类** | `Select`、`Radio`、`Checkbox`、`Cascader` | 单/多选 |
| **日期类** | `DatePicker`、`TimePicker`、`DateRangePicker` | 日期选择 |
| **文件类** | `Upload`、`UploadFile`、`UploadImage` | 上传 |
| **富文本** | `Editor`（wangEditor/Tinymce） | 长文本 |
| **组合类** | `UserSelectByDept`、`UserSelectByRole` | **ruoyi 特有**：人员选择 |
| **特殊** | `Button`、`Divider` | 装饰 |

### 1.2 conf 字段的 JSON 结构

每个字段都是一个 JSON 对象：
```json
{
  "field": "leaveDays",
  "label": "请假天数",
  "type": "InputNumber",
  "required": true,
  "rules": [{ "required": true, "message": "请输入请假天数" }],
  "props": { "min": 1, "max": 365 },
  "inject": { ... },   // 自定义属性
  "event": { "change": "..." }  // 事件
}
```

**关键字段**：
- `field`：**字段名（=流程变量名）**
- `label`：标签
- `type`：字段类型
- `rules`：校验规则（async-validator 格式）
- `props`：透传给底层组件的 props

### 1.3 ruoyi 特有的人员选择组件

```
UserSelectByDept:  按部门选人 → 调用 system API 查 user 列表
UserSelectByRole:  按角色选人 → 调用 system API 查 user 列表
```

**实现思路**：在 form-create 的自定义组件中，调用 `AdminUserApi` 拉取数据。

## 2. 代码示例

### 2.1 一份完整的请假表单 conf

```json
[
  {
    "field": "leaveType",
    "label": "请假类型",
    "type": "Select",
    "required": true,
    "options": [
      { "value": "1", "label": "事假" },
      { "value": "2", "label": "病假" },
      { "value": "3", "label": "年假" }
    ],
    "rules": [{ "required": true, "message": "请选择请假类型" }]
  },
  {
    "field": "startDate",
    "label": "开始日期",
    "type": "DatePicker",
    "required": true
  },
  {
    "field": "days",
    "label": "请假天数",
    "type": "InputNumber",
    "required": true,
    "props": { "min": 1, "max": 365 }
  },
  {
    "field": "reason",
    "label": "请假事由",
    "type": "Textarea",
    "props": { "rows": 4 }
  },
  {
    "field": "attachment",
    "label": "证明材料",
    "type": "UploadFile",
    "props": { "maxSize": 5, "accept": ".jpg,.png,.pdf" }
  }
]
```

### 2.2 后端解析 conf 提取字段

```java
// 简化代码：根据 conf JSON 解析出 fields 列表
public List<String> parseFields(String confJson) {
    List<Map<String, Object>> confList = JsonUtils.parseArray(confJson, Map.class);
    return confList.stream()
            .map(c -> c.get("field").toString())
            .collect(Collectors.toList());
}
// 输出：["leaveType", "startDate", "days", "reason", "attachment"]
```

### 2.3 常见错误：options 不写 value

```json
// ❌ 错误：options 缺 value
{ "field": "leaveType", "type": "Select",
  "options": [{ "label": "事假" }] }

// ✅ 正确
{ "field": "leaveType", "type": "Select",
  "options": [{ "value": "1", "label": "事假" }] }
```

## 3. 关键要点总结

- 字段类型丰富：输入/选择/日期/文件/富文本/人员选择等
- `conf` 是 JSON 数组，每项含 `field` / `label` / `type` / `rules` / `props`
- ruoyi 特有 `UserSelectByDept` / `UserSelectByRole`：调用 system API
- `fields` 字段在 DB 冗余存（逗号分隔），**查询时不用解析 conf**
- 字段可配 `permission`：READ/EDIT/HIDDEN，实现字段级权限

---

**文档版本**：v1.0
**最后更新**：2026-07-13
