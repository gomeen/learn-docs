# 3.2 表单组件库

> 理解 ruoyi 动态表单的组件库：基于 form-create / form-generator 的字段类型系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 动态表单支持的所有字段类型（Input、Select、DatePicker、Upload 等）
- 理解 conf JSON 的字段结构：field、label、type、options、required、rules
- 知道如何扩展自定义组件
- 能看懂一份完整的表单 conf 配置

## 📚 前置知识

- 08-dynamic-form.md（动态表单基础）
- Vue / 前端表单基础

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmFormServiceImpl 中 conf 字段的处理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmFormServiceImpl.java`（createForm / updateForm 方法）
**核心代码**（基于同 package 其他 service 推断）：

```java
@Service
@Validated
@Slf4j
public class BpmFormServiceImpl implements BpmFormService {

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createForm(BpmFormSaveReqVO createReqVO) {
        // 1. 校验 conf JSON 格式合法
        validateConfJson(createReqVO.getConf());

        // 2. 提取 fields 列表（从 conf 中解析）
        List<String> fields = parseFieldsFromConf(createReqVO.getConf());

        // 3. 插入 BpmFormDO
        BpmFormDO form = BpmFormConvert.INSTANCE.convert(createReqVO)
                .setFields(CollUtil.join(fields, ","));
        formMapper.insert(form);
        return form.getId();
    }

    private void validateConfJson(String confJson) {
        Assert.notBlank(confJson, "表单配置不能为空");
        // 调用 JsonUtils 校验是合法 JSON
        JsonUtils.parseArray(confJson, Map.class);
    }
}
```

**解读**：
- 第 11 行：插入前必须校验 JSON 格式（避免脏数据）
- 第 14 行：把 fields 列表存为逗号分隔字符串，便于查询
- **关键设计**：DB 冗余存 `fields`（逗号分隔），**查询时直接用，不用解析 conf**

### 3.2 表单字段与流程变量的关联

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmFormServiceImpl.java`
**关键方法**：`getFormFieldPermissions()` / `parseFormFields()`

```java
/**
 * 解析表单字段，构建 字段名 -> 权限 的映射
 * 用于审批页面：根据用户权限决定字段是否只读/隐藏
 */
public Map<String, String> parseFormFieldPermissions(BpmFormDO form, String permission) {
    List<Map<String, Object>> confList = JsonUtils.parseArray(form.getConf(), Map.class);
    Map<String, String> map = new HashMap<>();
    confList.forEach(item -> {
        String field = (String) item.get("field");
        map.put(field, (String) item.getOrDefault("permission", "EDIT"));
    });
    return map;
}
```

**解读**：
- 每个表单字段可配置 `permission` 属性（READ/EDIT/HIDDEN）
- 审批页面根据用户角色决定字段显示
- **关键设计**：权限粒度细化到"字段级"，而不是"页面级"

## 4. 关键要点总结

- 字段类型丰富：输入/选择/日期/文件/富文本/人员选择等
- `conf` 是 JSON 数组，每项含 `field` / `label` / `type` / `rules` / `props`
- ruoyi 特有 `UserSelectByDept` / `UserSelectByRole`：调用 system API
- `fields` 字段在 DB 冗余存（逗号分隔），**查询时不用解析 conf**
- 字段可配 `permission`：READ/EDIT/HIDDEN，实现字段级权限

## 5. 练习题

### 练习 1：基础（必做）

写一份"报销申请单"的 conf JSON，包含：报销类型（Select）、金额（InputNumber）、发票（UploadFile）、备注（Textarea）。

**参考答案**：见 `solutions/09-form-components.md`

### 练习 2：进阶

阅读 `BpmFormServiceImpl` 的 `parseFieldsFromConf`，看它如何处理嵌套字段（如 `Fieldset` 中的子字段）。

### 练习 3：挑战（选做）

扩展一个自定义组件 `UserSelectByLeader`：选择某用户的直属领导。提示：调用 `AdminUserApi.getUser(userId)` 拿到 deptId，再查 dept 的 leader。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmFormServiceImpl.java`
- form-create 官方文档：https://www.form-create.com/
- naive-ui 组件库：https://www.naiveui.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
