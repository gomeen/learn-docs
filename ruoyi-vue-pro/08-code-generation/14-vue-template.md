# 3.3 ruoyi 的 Vue 模板

> 解读 ruoyi 各种前端技术栈的 Vue 模板差异和核心占位符。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 支持的 9 种前端技术栈
- 解释 Vue 模板（`index.vue.vm` / `form.vue.vm`）的核心结构
- 理解不同前端框架的模板组织方式
- 理解 Vue2 vs Vue3 模板的关键差异

## 📚 前置知识

- Velocity / Java 模板（详见 [Velocity](./12-velocity.md)、[Java 模板](./13-java-template.md)）
- Vue 3 基础（详见 [Vue3 基础](../11-frontend/01-vue3-basics.md)）
- Element Plus / Vben（详见 [Element Plus](../11-frontend/12-element-plus.md)、[Vben](../11-frontend/15-vben.md)）

## 1. 核心概念

### 1.1 9 种前端技术栈

| `CodegenFrontTypeEnum` 值 | 模板目录 | 框架 |
|--------------------------|---------|------|
| `VUE2_ELEMENT_UI(10)` | `codegen/vue/` | Vue2 + Element UI |
| `VUE3_ELEMENT_PLUS(20)` | `codegen/vue3/` | Vue3 + Element Plus |
| `VUE3_VBEN2_ANTD_SCHEMA(30)` | `codegen/vue3_vben/` | Vue3 + Vben2 + Antd + Schema |
| `VUE3_VBEN5_ANTD_SCHEMA(40)` | `codegen/vue3_vben5_antd/schema/` | Vben5 + Antd + Schema |
| `VUE3_VBEN5_ANTD_GENERAL(41)` | `codegen/vue3_vben5_antd/general/` | Vben5 + Antd + 常规 |
| `VUE3_VBEN5_ANTDV_NEXT_SCHEMA(42)` | `codegen/vue3_vben5_antdv_next/schema/` | Vben5 + Antdv Next + Schema |
| `VUE3_VBEN5_ANTDV_NEXT_GENERAL(43)` | `codegen/vue3_vben5_antdv_next/general/` | Vben5 + Antdv Next + 常规 |
| `VUE3_VBEN5_EP_SCHEMA(50)` | `codegen/vue3_vben5_ele/schema/` | Vben5 + Element Plus + Schema |
| `VUE3_VBEN5_EP_GENERAL(51)` | `codegen/vue3_vben5_ele/general/` | Vben5 + Element Plus + 常规 |
| `VUE3_ADMIN_UNIAPP_WOT(60)` | `codegen/vue3_admin_uniapp/` | Vue3 + Uniapp（移动端） |

### 1.2 模板组织差异

- **标准 vue2 / vue3**：API + views/index + views/form (+ vue3 多一个 import)
- **Schema 模式**（vben）：API + views/{data.ts, index, form, import} + modules
- **General 模式**（vben）：API + views/{index, form, import} + modules
- **Uniapp**：API + components + views/index + views/form/index + views/detail/index

### 1.3 主子表子组件命名

- 标准 vue2/vue3：放在 `views/${businessName}/components/`
- Vben 5：放在 `views/${businessName}/modules/`
- 命名规范：`${subSimpleClassName}Form.vue` / `${subSimpleClassName}List.vue`

## 2. 代码示例

### 2.1 Vue3 + Element Plus 列表页生成效果（简化）

```vue
<template>
  <ContentWrap>
    <!-- 搜索栏 -->
    <el-form :model="queryParams" ref="queryFormRef" :inline="true">
      <el-form-item label="字典名称" prop="name">
        <el-input v-model="queryParams.name" placeholder="请输入字典名称" clearable />
      </el-form-item>
      <el-form-item>
        <el-button @click="handleQuery"><Icon icon="ep:search" />搜索</el-button>
        <el-button @click="resetQuery"><Icon icon="ep:refresh" />重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 列表 -->
    <el-table v-loading="loading" :data="list">
      <el-table-column label="字典编号" prop="id" />
      <el-table-column label="字典名称" prop="name" />
      <el-table-column label="字典类型" prop="type" />
      <el-table-column label="操作" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openForm('update', row.id)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </ContentWrap>
</template>
```

## 3. 关键要点总结

- 9 种前端框架分 7 个模板目录（部分共用）
- **标准 vue3** 模板：`index.vue` + `form.vue` + `import.vue`（导入）
- **Vben 5** 模板分 `schema`（配置式）和 `general`（模板式）
- **Uniapp** 模板独立组织（`views/form/index.vue` 等）
- API 模板输出 **TypeScript 接口**和 **axios 请求函数**
- 字典字段在 Vue 端用 `DICT_TYPE.xxx` + `getIntDictOptions` / `getDictLabel`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
