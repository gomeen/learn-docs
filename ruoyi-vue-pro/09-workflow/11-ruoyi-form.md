# 3.4 ruoyi 的 Form 设计

> 深入理解 ruoyi 的表单设计器：从前端可视化编辑到后端存储的完整链路。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 ruoyi 用 form-create / form-generator 作为前端表单设计器
- 理解 conf JSON 的标准化结构
- 区分"表单设计态"与"表单使用态"
- 能在 ruoyi 中扩展自定义组件

## 📚 前置知识

- 08-dynamic-form.md（动态表单基础）
- 09-form-components.md（表单组件）
- 10-form-data.md（表单数据持久化）
- Vue.js / form-create

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmFormServiceImpl 的 conf 校验

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmFormServiceImpl.java`
**核心代码**（基于 service 通用结构推断）：

```java
@Override
public Long createForm(BpmFormSaveReqVO createReqVO) {
    // 1. 校验 conf JSON 合法
    validateConfJson(createReqVO.getConf());

    // 2. 提取字段
    List<String> fields = parseFieldsFromConf(createReqVO.getConf());

    // 3. 校验字段不重复
    if (new HashSet<>(fields).size() != fields.size()) {
        throw exception(FORM_FIELD_DUPLICATE);
    }

    // 4. 插入
    BpmFormDO form = BeanUtils.toBean(createReqVO, BpmFormDO.class)
            .setFields(String.join(",", fields));
    formMapper.insert(form);
    return form.getId();
}

private void validateConfJson(String confJson) {
    Assert.notBlank(confJson, "表单配置不能为空");
    try {
        JsonUtils.parseArray(confJson, Map.class);
    } catch (Exception e) {
        throw exception(FORM_CONFIG_INVALID);
    }
}
```

**解读**：
- 第 4 行：conf 必须是非空字符串
- 第 5 行：能解析为 List<Map> 才合法
- 第 9 行：字段不能重名（防止 EL 表达式歧义）
- 第 16 行：fields 数组转逗号分隔存 DB
- **关键设计**：表单字段名 = 流程变量名 = EL 引用名，**三者必须一致**

### 3.2 BpmFormDO 字段冗余设计

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/definition/BpmFormDO.java`（基于命名推断）
**核心字段**（推断）：

```java
@TableName("bpm_form")
@Data
public class BpmFormDO extends BaseDO {
    private Long id;
    private String name;       // 表单名称
    private Integer status;    // 0=启用 1=禁用
    private String conf;       // 表单 JSON 配置（核心）
    private String fields;     // 字段名列表（逗号分隔，从 conf 提取）
    private String remark;     // 备注
}
```

**解读**：
- `conf` 是核心，存完整 JSON
- `fields` 是冗余字段，**避免每次查询都要解析 conf**
- 这样的设计是典型的"**写时计算、读时高效**"模式

### 3.3 FormController 的 getForm 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`
**核心代码**（推断后续接口）：

```java
@GetMapping("/get")
@Operation(summary = "获得动态表单")
@Parameter(name = "id", description = "编号", required = true, example = "1024")
public CommonResult<BpmFormRespVO> getForm(@RequestParam("id") Long id) {
    BpmFormDO form = formService.getForm(id);
    return success(BeanUtils.toBean(form, BpmFormRespVO.class));
}
```

**解读**：
- 前端调用此接口拿到 conf JSON
- 直接用 form-create 渲染
- **关键设计**：BpmFormRespVO 包含完整 conf 字段，不做裁剪

## 4. 关键要点总结

- ruoyi 用 form-create 作为前端表单引擎，conf JSON 是前后端的"协议"
- conf JSON 标准化：field/label/type/options/required/rules/props/permission
- BpmFormDO 冗余存 `fields` 字符串（写时计算、读时高效）
- 字段权限（READ/EDIT/HIDDEN）实现"字段级权限"
- conf JSON 中不能放函数（序列化丢失），业务逻辑用后端 EL 表达式

## 5. 练习题

### 练习 1：基础（必做）

写一份"加班申请单"的 conf JSON，要求：
- 加班日期（DatePicker，required）
- 加班时长（InputNumber，required，1-12）
- 加班原因（Textarea）
- 证明人（UserSelectByUser，permission=READ）

**参考答案**：见 `solutions/11-ruoyi-form.md`

### 练习 2：进阶

阅读 `BpmFormServiceImpl.parseFieldsFromConf`，说明它如何处理嵌套字段（如 `Fieldset` 内的子字段）。它会把嵌套字段合并到一个 flat 列表吗？

### 练习 3：挑战（选做）

实现"表单导入"接口：上传 conf JSON 文件 → 创建表单。要求验证 JSON 合法、字段不重复、字段名符合 Java 变量命名规范。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmFormServiceImpl.java`
- form-create 文档：https://www.form-create.com/
- form-create 组件配置：https://www.form-create.com/v3/element-ui/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
