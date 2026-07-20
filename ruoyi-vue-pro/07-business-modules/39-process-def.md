# 7.6.1 流程定义：Modeler

> 理解 ruoyi 工作流（BPM）模块的流程定义，基于 Flowable 引擎。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi BPM 模块的整体设计
- 理解 Flowable 工作流引擎的核心概念
- 学会流程定义（Modeler）的使用
- 能看懂流程定义的代码

## 📚 前置知识

- 工作流基础（BPMN 2.0，详见 [BPMN](../09-workflow/01-bpmn.md)）
- Flowable 引擎基础（详见 [Flowable 概念](../09-workflow/02-flowable-concepts.md)）
- 树形结构（详见 [部门](./10-dept.md)）

## 1. 核心概念

### 1.1 BPM 是什么？

BPM（Business Process Management）是**业务流程管理**。在企业内部，常见的请假、报销、采购等流程，都需要多级审批，BPM 引擎就是用来建模和执行这些流程的。

**典型场景**：
- 员工请假 → 直属领导 → HR 审批
- 报销申请 → 部门负责人 → 财务
- 采购申请 → 部门 → 采购部 → 总经理

### 1.2 ruoyi BPM 架构

ruoyi 使用 **Flowable** 作为底层引擎，封装出更易用的接口：

```
[管理后台 Modeler] → [BPM 定义] → [Flowable Engine] → [数据库]
[用户表单填写]   → [发起流程]   → [审批流转]
[用户审批页]    → [任务处理]   → [流程结束]
```

### 1.3 BPM 核心概念

| 概念 | 说明 | 例子 |
|------|------|------|
| **流程定义** | 流程的模板（XML） | "请假流程" |
| **流程实例** | 一次具体的流程执行 | "张三 7 月请假" |
| **任务** | 待办任务 | "李四审批" |
| **表单** | 收集数据的表单 | "请假原因、天数" |
| **流程分类** | 流程的分类 | "行政类、财务类" |
| **用户组** | 审批人组 | "HR 组" |

## 2. 代码示例

### 2.1 流程定义

```java
@Tag(name = "管理后台 - 流程定义")
@RestController
@RequestMapping("/bpm/process-definition")
@Validated
public class BpmProcessDefinitionController {

    @Resource
    private BpmProcessDefinitionService processDefinitionService;

    @GetMapping("/page")
    public CommonResult<PageResult<BpmProcessDefinitionRespVO>> getProcessDefinitionPage(
            @Valid BpmProcessDefinitionPageReqVO pageVO) {
        return success(processDefinitionService.getProcessDefinitionPage(pageVO));
    }

    @PostMapping("/deploy")
    @Operation(summary = "部署流程定义")
    public CommonResult<Boolean> deployProcessDefinition(@RequestParam("bpmnFile") MultipartFile bpmnFile,
                                                          @RequestParam(value = "simulateJson", required = false) String simulateJson) {
        processDefinitionService.deployProcessDefinition(bpmnFile, simulateJson);
        return success(true);
    }
}
```

### 2.2 流程分类

```java
@PostMapping("/create")
public CommonResult<Long> createCategory(@Valid @RequestBody BpmCategorySaveReqVO createReqVO) {
    return success(categoryService.createCategory(createReqVO));
}

@GetMapping("/list")
public CommonResult<List<BpmCategoryRespVO>> getCategoryList() {
    return success(categoryService.getCategoryList());
}
```

### 2.3 自定义表单

```java
@PostMapping("/create")
public CommonResult<Long> createForm(@Valid @RequestBody BpmFormSaveReqVO createReqVO) {
    return success(formService.createForm(createReqVO));
}

@GetMapping("/get")
public CommonResult<BpmFormRespVO> getForm(@RequestParam("id") Long id) {
    return success(formService.getForm(id));
}
```

## 3. 关键要点总结

- ruoyi BPM 基于 Flowable 引擎
- 流程定义 = BPMN XML 文件
- 流程定义可以版本管理
- 流程状态：激活 / 挂起
- 流程分类是树形结构
- 表单可以独立定义，与流程绑定

---

**文档版本**：v1.0
**最后更新**：2026-07-13
