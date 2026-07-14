# 7.6.2 表单设计：动态表单

> 理解 ruoyi BPM 中的动态表单（Dynamic Form）设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 动态表单的设计
- 理解表单字段的 JSON 配置
- 学会在流程中使用动态表单
- 能扩展自定义表单类型

## 📚 前置知识

- 33-process-def.md
- JSON Schema 基础
- 04-dto-vo-do.md

## 1. 核心概念

### 1.1 动态表单 vs 静态表单

| 维度 | 静态表单 | 动态表单 |
|------|----------|----------|
| 字段 | 写死在 HTML | 存储在数据库 |
| 修改 | 改代码、部署 | 后台配置 |
| 复用 | 每个流程一份 | 多个流程共享 |
| 适用 | 字段固定 | 字段常变 |

### 1.2 ruoyi 动态表单结构

```json
{
  "fields": [
    {
      "type": "input",
      "key": "reason",
      "label": "请假原因",
      "required": true
    },
    {
      "type": "date",
      "key": "startDate",
      "label": "开始日期",
      "required": true
    },
    {
      "type": "number",
      "key": "days",
      "label": "请假天数",
      "required": true
    }
  ]
}
```

### 1.3 表单字段类型

| 类型 | 渲染 | 适用 |
|------|------|------|
| input | 文本框 | 短文本 |
| textarea | 多行文本 | 长文本 |
| number | 数字框 | 数字 |
| date | 日期 | 日期 |
| select | 下拉框 | 枚举 |
| radio | 单选 | 枚举 |
| checkbox | 多选 | 多个选项 |
| upload | 上传 | 文件 |
| editor | 富文本 | 长文本编辑 |

## 2. 代码示例

### 2.1 BpmFormController

```java
@PostMapping("/create")
public CommonResult<Long> createForm(@Valid @RequestBody BpmFormSaveReqVO createReqVO) {
    return success(formService.createForm(createReqVO));
}

@GetMapping("/list")
public CommonResult<List<BpmFormRespVO>> getFormList() {
    return success(formService.getFormList());
}

@GetMapping("/get")
public CommonResult<BpmFormRespVO> getForm(@RequestParam("id") Long id) {
    return success(formService.getForm(id));
}
```

### 2.2 表单字段配置

```java
@Data
public class FormField {
    private String type;     // 字段类型
    private String key;      // 字段名
    private String label;    // 显示标签
    private Boolean required;
    private Object defaultValue;
    private Map<String, Object> props;  // 其他属性
    // 例如 select 的 options
}
```

### 2.3 流程绑定表单

```java
// 在流程定义时指定表单
@PostMapping("/deploy")
public CommonResult<Long> deployProcessDefinition(
        @RequestParam("bpmnFile") MultipartFile bpmnFile,
        @RequestParam(value = "formId", required = false) Long formId) {
    return success(processDefinitionService.deployProcessDefinition(bpmnFile, formId));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmFormDO 核心字段

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/definition/BpmFormDO.java`

```java
@TableName("bpm_form")
@Data
public class BpmFormDO extends BaseDO {
    @TableId
    private Long id;
    private String name;        // 表单名
    private String status;      // 状态
    private String conf;        // 表单 JSON 配置
    private String fields;      // 字段列表
    private String remark;      // 备注
}
```

### 3.2 BpmFormController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`

```java
@Tag(name = "管理后台 - 流程表单")
@RestController
@RequestMapping("/bpm/form")
@Validated
public class BpmFormController {

    @Resource
    private BpmFormService formService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('bpm:form:create')")
    public CommonResult<Long> createForm(@Valid @RequestBody BpmFormSaveReqVO createReqVO) {
        return success(formService.createForm(createReqVO));
    }

    @GetMapping("/list")
    public CommonResult<List<BpmFormRespVO>> getFormList() {
        return success(formService.getFormList());
    }
}
```

## 4. 关键要点总结

- 动态表单的核心是 **JSON 配置**
- 表单定义存储在 `bpm_form` 表
- 表单字段通过 JSON 描述
- 前端通过 JSON Schema 动态渲染
- 表单可以被多个流程共享

## 5. 练习题

### 练习 1：基础（必做）

阅读 `BpmFormDO.java` 字段。

### 练习 2：进阶

阅读 `BpmFormServiceImpl.java`，理解表单的创建和保存。

### 练习 3：挑战（选做）

设计"出差申请"动态表单：包含出差人、目的地、开始/结束日期、预算。请用 JSON Schema 描述。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmFormController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
