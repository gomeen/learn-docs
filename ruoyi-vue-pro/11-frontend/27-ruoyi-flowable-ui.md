# 11.6.5 工作流设计器前端

> 了解 ruoyi 的工作流设计器前端：BPMN.js 集成，实现可视化流程设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解工作流设计器的基本概念
- 掌握 BPMN.js 的集成方式
- 理解 ruoyi 工作流设计页的实现
- 能在 ruoyi 中使用工作流组件

## 📚 前置知识

- 工作流基础（详见 [BPMN](../09-workflow/01-bpmn.md)、[ruoyi 工作流](../09-workflow/03-ruoyi-workflow.md)）
- Vue3 / Element（详见 [Vue3 基础](./01-vue3-basics.md)、[Element Plus](./10-element-plus.md)）
- Vite（详见 [Vite](./15-vite.md)）

## 1. 核心概念

### 1.1 什么是工作流设计器？

工作流设计器是一个**可视化拖拽编辑器**，让用户通过拖拽节点、连线来设计业务流程（例如请假流程、报销流程、审批流程）。

### 1.2 BPMN 2.0 规范

BPMN（Business Process Model and Notation）是 OMG 制定的业务流程建模标准：

```
[开始] → [用户任务] → [审批] → [结束]
   圆圈      矩形       菱形      圆圈
```

主要元素：
- **开始/结束事件**（圆圈）
- **用户任务**（矩形）：需要人操作
- **服务任务**（矩形带齿轮）：自动执行
- **网关**（菱形）：条件分支
- **连线**（箭头）：流转方向

### 1.3 BPMN.js 简介

bpmn.js 是 BPMN 2.0 的 JavaScript 实现：
- **建模器**（bpmn-js + diagram-js）：可视化编辑
- **属性面板**（bpmn-js-properties-panel）：编辑节点属性
- **导入导出**：XML 格式（标准 BPMN 文件）

### 1.4 ruoyi 工作流设计器位置

ruoyi 工作流设计器位于：
- 后端：`yudao-module-bpm`（基于 Flowable 引擎）
- 前端：`yudao-ui-admin-vue3/src/views/bpm/`

主要页面：
- `bpm/model/` —— 流程模型列表
- `bpm/design/` —— 可视化设计器
- `bpm/process/` —— 流程实例
- `bpm/task/` —— 我的待办

## 2. 代码示例

### 2.1 安装 BPMN.js

```bash
pnpm add bpmn-js bpmn-js-properties-panel camunda-bpmn-moddle
```

### 2.2 最简 BPMN.js 设计器

```vue
<!-- DesignProcess.vue -->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import BpmnModeler from 'bpmn-js/lib/Modeler'
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'
import 'bpmn-js-properties-panel/dist/assets/bpmn-js-properties-panel.css'

const canvasRef = ref<HTMLDivElement>()
let modeler: BpmnModeler

onMounted(() => {
  modeler = new BpmnModeler({
    container: canvasRef.value!,
    propertiesPanel: { parent: '#js-properties-panel' }
  })

  // 创建空白流程图
  modeler.createDiagram()
})

async function exportXml() {
  const { xml } = await modeler.saveXML({ format: true })
  console.log('XML:', xml)
  // 调后端接口保存
}
</script>

<template>
  <div class="process-container">
    <div ref="canvasRef" class="canvas"></div>
    <div id="js-properties-panel" class="properties-panel"></div>
  </div>
</template>

<style>
.process-container { display: flex; height: 100vh; }
.canvas { flex: 1; }
.properties-panel { width: 300px; border-left: 1px solid #ccc; }
</style>
```

### 2.3 加载已有流程图

```ts
async function loadProcess(xml: string) {
  await modeler.importXML(xml)
  modeler.get('canvas').zoom('fit-viewport')
}
```

### 2.4 自定义节点

```ts
import { customTranslateModule } from './customTranslate'

modeler = new BpmnModeler({
  container: canvasRef.value!,
  additionalModules: [customTranslateModule]
})
```

### 2.5 ruoyi 风格的简化设计器

ruoyi 通常**不直接用 bpmn-js**，而是基于它做了一层 Vue 包装：

```vue
<!-- bpm/design/index.vue（约定） -->
<script setup lang="ts">
const xml = ref('')
const processKey = ref('leave')

function onSave() {
  // 调后端接口
  BpmModelApi.updateXml({ key: processKey.value, xml: xml.value })
}
</script>

<template>
  <div class="flex h-full">
    <BpmnDesign v-model="xml" :process-key="processKey" />
    <div class="w-300px">
      <el-button type="primary" @click="onSave">保存</el-button>
    </div>
  </div>
</template>
```

### 2.6 常见错误：bpmn-js 样式没引入

```ts
// ❌ 错误：只引入了 JS，没引样式
import BpmnModeler from 'bpmn-js/lib/Modeler'

// ✅ 正确：必须引入 3 个 CSS
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'
import 'bpmn-js-properties-panel/dist/assets/bpmn-js-properties-panel.css'
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 工作流模块结构

虽然本仓库的 vue3 子项目是独立仓库，但工作流模块约定结构：

```
src/views/bpm/
├── model/                          # 流程模型
│   ├── index.vue                   # 模型列表
│   └── create.vue                  # 创建模型
├── design/                         # 设计器
│   └── index.vue                   # 可视化设计
├── process/                        # 流程实例
│   └── index.vue                   # 实例列表
├── task/                           # 我的待办
│   ├── todo.vue                    # 待办
│   └── done.vue                    # 已办
└── category/                       # 流程分类
    └── index.vue
```

### 3.2 后端 BPM 模块

ruoyi 后端用 **Flowable**（不是 Camunda）作为工作流引擎：
- `yudao-module-bpm/` 是工作流模块
- `yudao-spring-boot-starter-bpm` 是 starter
- 自动建库（Flowable 自带 ACT_* 25+ 张表）

### 3.3 流程定义 XML 格式

ruoyi 设计的流程保存为 BPMN XML：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <process id="leave" name="请假流程">
    <startEvent id="start" />
    <userTask id="apply" name="提交申请" />
    <userTask id="approve" name="主管审批" />
    <endEvent id="end" />
    <sequenceFlow id="flow1" sourceRef="start" targetRef="apply" />
    <sequenceFlow id="flow2" sourceRef="apply" targetRef="approve" />
    <sequenceFlow id="flow3" sourceRef="approve" targetRef="end" />
  </process>
</definitions>
```

### 3.4 与本仓库代码的关联

本仓库主要是 MES 模块，没有工作流相关代码。但 ruoyi 后端的 `yudao-module-bpm` 完整实现了流程引擎：

```
yudao-module-bpm/
├── src/main/java/cn/iocoder/yudao/module/bpm/
│   ├── controller/
│   │   ├── BpmModelController.java       # 流程模型
│   │   ├── BpmProcessController.java     # 流程实例
│   │   └── BpmTaskController.java        # 待办
│   ├── service/
│   ├── dal/                              # 数据库访问
│   └── framework/                        # 流程定义、监听器
```

## 4. 关键要点总结

- **BPMN 2.0** = 业务流程建模标准（开始/任务/网关/结束）
- **bpmn-js** = BPMN 的 JS 实现，提供可视化设计器
- ruoyi 工作流引擎用 **Flowable**（不是 Camunda）
- 设计器保存为 **BPMN XML**，后端部署为流程定义
- 流程设计页 = 左侧调色板 + 中间画布 + 右侧属性面板
- 启动流程 = `runtimeService.startProcessInstanceByKey(key)`
- 待办列表 = `taskService.createTaskQuery().taskAssignee(userId).list()`

## 5. 练习题

### 练习 1：基础（必做）

用 bpmn-js 创建一个最简单的流程图（开始 → 任务 → 结束），并把 XML 导出到控制台。

### 练习 2：进阶

为设计器增加"自定义属性面板"：每个用户任务节点都可以配置"审批人"（用户/角色/部门），保存到 XML 的扩展属性中。

### 练习 3：挑战（选做）

实现"流程模板市场"：管理员上传 BPMN 文件，用户一键部署为自己的流程模型。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/`（后端工作流模块）
- BPMN.js 官方：https://bpmn.io/toolkit/bpmn-js/
- Flowable 官方：https://www.flowable.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13